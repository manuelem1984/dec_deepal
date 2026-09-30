"""Diagnósticos: el JSON de "Descargar diagnósticos" (ficha de la integración).

Pensado para adjuntarlo a un Issue sin miedo: todo pasa por
:func:`~.debug.redact.redact` (tokens, VIN, móvil, PIN, identificadores...).

Contenido:

- ``integracion``: versión, país, opciones (sin PIN).
- ``catalogos``: modelos cargados y avisos de iconos.
- ``vehiculos``: por coche →
    - ``modelo``/``version``/``color`` reconocidos,
    - ``senales`` (valores interpretados) y ``origen`` de cada una,
    - ``mqtt`` en bruto y ``mqtt_sin_mapear`` (candidatas a nuevas entidades),
    - ``rest`` en bruto,
    - ``avisos`` de la última lectura.
- ``registro_depuracion``: últimos eventos (HTTP, MQTT, comandos...). Con el
  modo depuración activo incluye los cuerpos completos.
- ``capturas``: las capturas hechas con ``dec_deepal.capture_snapshot``.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .const import OPT_APPEARANCE, OPT_PIN, VERSION
from .debug.capture import build_snapshot
from .debug.redact import redact
from .runtime import DecDeepalConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DecDeepalConfigEntry
) -> dict[str, Any]:
    """Construye el informe de diagnóstico de una cuenta."""
    runtime = entry.runtime_data
    # Opciones sin el PIN ni la apariencia (que va indexada por id de
    # vehículo; versión y color ya aparecen en cada vehículo). No se pasan por
    # redact() para que "pin_enabled"/"pin_mode" sigan siendo legibles.
    options = {
        key: value
        for key, value in entry.options.items()
        if key not in (OPT_PIN, OPT_APPEARANCE)
    }

    vehicles: dict[str, Any] = {}
    for vehicle in runtime.vehicles.values():
        snapshot = build_snapshot("diagnostico", vehicle.info.display_name, vehicle.coordinator.data)
        vehicles[vehicle.info.display_name] = {
            "info": vehicle.info.to_dict(),
            "modelo": vehicle.model.id,
            "version": vehicle.trim,
            "color": vehicle.color,
            "usa_mqtt": vehicle.coordinator.use_mqtt,
            "ultima_lectura_ok": vehicle.coordinator.last_update_success,
            "armado": vehicle.runner.is_armed,
            **snapshot,
        }

    report = redact(
        {
            "integracion": {
                "version": VERSION,
                "pais": runtime.country.id,
                "modo_depuracion": runtime.recorder.verbose,
            },
            "catalogos": {
                "modelos": sorted(runtime.registries.vehicles.models),
                "iconos_svg": sorted(runtime.registries.icons.available),
                "avisos_iconos": runtime.registries.icons.warnings,
            },
            "vehiculos": vehicles,
            "registro_depuracion": runtime.recorder.events(),
            "capturas": list(runtime.captures.values()),
        }
    )
    report["integracion"]["opciones"] = options
    return report
