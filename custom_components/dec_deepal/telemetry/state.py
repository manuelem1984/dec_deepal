"""Estado del vehículo: fusión de MQTT + REST + último valor conocido.

Reglas de fusión (en este orden), pensadas a partir de lo observado con el
coche real y de lo aprendido por Deepal Alternative:

1. **Base: MQTT.** Es la fuente principal del S05.
2. **REST rellena huecos:** si una señal no llegó por MQTT pero sí por REST,
   se usa la del REST (p. ej. temperatura exterior, si algún día llega).
3. **REST manda en confort** (asientos, volante, desempañado): el MQTT guarda
   el último nivel configurado aunque esté apagado, así que no es fiable
   (✅ comprobado con dos capturas reales). Excepción: si el informe REST es
   *más antiguo* que el MQTT, no se usa (no pisar un dato nuevo con uno viejo).
4. **Conservar el último valor** en confort y clima: si ninguna fuente lo
   informa esta vez (módulo dormido, ``6``...), se mantiene el anterior en vez
   de mostrar "Desconocido" o, peor, "apagado".
5. **Valores optimistas** (tras un comando) se aplican encima, en el
   coordinador (ver :func:`apply_holds`).

Además se guarda de dónde salió cada valor (``sources``) para diagnóstico.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final

from . import signals as s
from .derived import DERIVED
from .mqtt_map import map_mqtt
from .rest_map import map_rest

#: Señales en las que el REST tiene prioridad sobre el MQTT (regla 3).
REST_PRIORITY: Final = frozenset(
    {
        s.SEAT_HEAT_DRIVER,
        s.SEAT_HEAT_PASSENGER,
        s.SEAT_VENT_DRIVER,
        s.SEAT_VENT_PASSENGER,
        s.STEERING_WHEEL_HEAT,
        s.FRONT_DEFROST,
    }
)

#: Señales que conservan su último valor si esta vez no llegan (regla 4).
KEEP_LAST: Final = REST_PRIORITY | {s.CLIMATE_ON, s.CLIMATE_TARGET_C}

SOURCE_MQTT: Final = "mqtt"
SOURCE_REST: Final = "rest"
SOURCE_PREVIOUS: Final = "anterior"
SOURCE_OPTIMISTIC: Final = "optimista"
SOURCE_DERIVED: Final = "calculado"


@dataclass(slots=True)
class VehicleState:
    """Foto del vehículo en un momento dado."""

    #: Señales con valor ``{señal: valor}`` (las calculadas no están aquí).
    values: dict[str, Any] = field(default_factory=dict)
    #: De dónde salió cada valor: "mqtt", "rest", "anterior" u "optimista".
    sources: dict[str, str] = field(default_factory=dict)
    #: Parámetros MQTT en bruto de esta lectura (para diagnóstico).
    mqtt_raw: dict[str, Any] | None = None
    #: Servicios MQTT con código desconocido (para investigar).
    mqtt_unknown: dict[str, Any] = field(default_factory=dict)
    #: JSON REST en bruto de esta lectura (para diagnóstico).
    rest_raw: dict[str, Any] | None = None
    #: Cuándo se hizo la lectura (hora de Home Assistant, UTC).
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    #: Problemas no fatales de esta lectura (p. ej. "REST falló: ...").
    warnings: list[str] = field(default_factory=list)

    def get(self, signal: str) -> Any:
        """Valor de una señal (normal o calculada). ``None`` si no hay dato."""
        if signal in DERIVED:
            return DERIVED[signal](self.values)
        return self.values.get(signal)

    def source(self, signal: str) -> str | None:
        """Origen del valor de una señal."""
        if signal in DERIVED:
            return SOURCE_DERIVED
        return self.sources.get(signal)


def build_state(
    *,
    mqtt_params: Mapping[str, Any] | None,
    rest_raw: Mapping[str, Any] | None,
    previous: VehicleState | None,
) -> VehicleState:
    """Construye el estado aplicando las reglas del principio del módulo.

    Args:
        mqtt_params: parámetros MQTT en bruto, o ``None`` si no hubo lectura.
        rest_raw: JSON REST en bruto, o ``None`` si no hubo lectura.
        previous: estado anterior (para la regla 4), o ``None``.
    """
    mqtt_values = map_mqtt(dict(mqtt_params)) if mqtt_params else {}
    rest_values = map_rest(dict(rest_raw)) if rest_raw else {}

    values: dict[str, Any] = {}
    sources: dict[str, str] = {}

    # Regla 1: base MQTT.
    for signal, value in mqtt_values.items():
        values[signal] = value
        sources[signal] = SOURCE_MQTT

    # ¿El REST es al menos tan reciente como el MQTT?
    mqtt_time = mqtt_values.get(s.REPORT_TIME)
    rest_time = rest_values.get(s.REPORT_TIME)
    rest_is_stale = (
        mqtt_time is not None and rest_time is not None and rest_time < mqtt_time
    )

    for signal, value in rest_values.items():
        if signal in REST_PRIORITY:
            # Regla 3 (con la excepción del REST antiguo).
            if not rest_is_stale or signal not in values:
                values[signal] = value
                sources[signal] = SOURCE_REST
        elif signal not in values:
            # Regla 2: rellenar huecos.
            values[signal] = value
            sources[signal] = SOURCE_REST

    # "Conectado a la nube": el coche respondió por MQTT en esta lectura. Si
    # solo hubo REST, se usa su indicador (si lo trae).
    if mqtt_params:
        values[s.CLOUD_CONNECTED] = True
        sources[s.CLOUD_CONNECTED] = SOURCE_MQTT
    elif rest_raw:
        connect = (rest_raw.get("vehicleStatus") or {}).get("connectStatus")
        if connect is not None:
            values[s.CLOUD_CONNECTED] = connect == 1
            sources[s.CLOUD_CONNECTED] = SOURCE_REST

    # Regla 4: conservar el último valor conocido.
    if previous is not None:
        for signal in KEEP_LAST:
            if signal not in values and previous.values.get(signal) is not None:
                values[signal] = previous.values[signal]
                sources[signal] = SOURCE_PREVIOUS

    return VehicleState(
        values=values,
        sources=sources,
        mqtt_raw=dict(mqtt_params) if mqtt_params else None,
        rest_raw=dict(rest_raw) if rest_raw else None,
    )


@dataclass(slots=True)
class OptimisticHold:
    """Valor esperado tras un comando, mantenido hasta confirmarse o caducar."""

    value: Any
    expires_at: float  # time.monotonic()


def apply_holds(
    state: VehicleState, holds: dict[str, OptimisticHold], now: float
) -> None:
    """Aplica los valores optimistas pendientes sobre ``state`` (regla 5).

    Modifica ``state`` y ``holds`` en sitio:
    - Si el coche ya informa el valor esperado → se confirma y se borra.
    - Si caducó → se borra (manda lo que diga el coche).
    - Si no → se impone el valor esperado.

    Evita que, justo después de un comando, una lectura con datos anteriores
    al cambio "devuelva" la entidad a su estado viejo.
    """
    for signal in list(holds):
        hold = holds[signal]
        if now >= hold.expires_at or state.values.get(signal) == hold.value:
            del holds[signal]
            continue
        state.values[signal] = hold.value
        state.sources[signal] = SOURCE_OPTIMISTIC
