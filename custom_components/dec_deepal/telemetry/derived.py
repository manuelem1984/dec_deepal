"""Señales calculadas a partir de otras señales.

Se calculan **al leerlas**, no al recibir los datos. Así, si un comando cambia
un valor de forma optimista (p. ej. bloquear puertas), las señales derivadas
(``central_locked``) se actualizan solas sin lógica adicional.

Cada función recibe el dict ``{señal: valor}`` ya fusionado y devuelve el
valor calculado o ``None`` si no hay datos suficientes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Final

from . import signals as s

# Estados posibles de "Estado de carga" (también son sus claves de traducción).
CHARGE_DISCONNECTED: Final = "disconnected"
CHARGE_CONNECTED_AC: Final = "connected_ac"
CHARGE_CONNECTED_DC: Final = "connected_dc"
CHARGE_CHARGING_AC: Final = "charging_ac"
CHARGE_CHARGING_DC: Final = "charging_dc"
CHARGE_STATUS_OPTIONS: Final = (
    CHARGE_DISCONNECTED,
    CHARGE_CONNECTED_AC,
    CHARGE_CONNECTED_DC,
    CHARGE_CHARGING_AC,
    CHARGE_CHARGING_DC,
)


def charge_status(values: Mapping[str, Any]) -> str | None:
    """Combina "cargando" + conector AC + conector DC en un único estado. ✅

    Orden de evaluación:
    1. Nada enchufado y sin cargar → ``disconnected``.
    2. AC enchufado sin cargar → ``connected_ac``.
    3. DC enchufado sin cargar → ``connected_dc``.
    4. AC cargando → ``charging_ac``.
    5. DC cargando → ``charging_dc``.
    Si falta cualquiera de los tres datos → ``None`` (no se adivina).
    """
    ac = values.get(s.AC_CONNECTOR)
    dc = values.get(s.DC_CONNECTOR)
    charging = values.get(s.CHARGING)
    if ac is None or dc is None or charging is None:
        return None
    if not ac and not dc and not charging:
        return CHARGE_DISCONNECTED
    if ac and not charging:
        return CHARGE_CONNECTED_AC
    if dc and not charging:
        return CHARGE_CONNECTED_DC
    if ac and charging:
        return CHARGE_CHARGING_AC
    if dc and charging:
        return CHARGE_CHARGING_DC
    return None


def remaining_charge_hhmm(values: Mapping[str, Any]) -> str | None:
    """Tiempo de carga restante como texto ``H:MM`` (idea de Deepal Alternative)."""
    minutes = values.get(s.REMAINING_CHARGE_MIN)
    if minutes is None:
        return None
    hours, rest = divmod(int(minutes), 60)
    return f"{hours}:{rest:02d}"


def any_door_open(values: Mapping[str, Any]) -> bool | None:
    """Alguna de las 4 puertas **o el maletero** abierta. El capó no cuenta.

    ``None`` solo si no se sabe nada de ninguna de las cinco.
    """
    doors = [
        values.get(signal)
        for signal in (
            s.DOOR_FRONT_LEFT,
            s.DOOR_FRONT_RIGHT,
            s.DOOR_REAR_LEFT,
            s.DOOR_REAR_RIGHT,
            s.TRUNK_OPEN,
        )
    ]
    if all(door is None for door in doors):
        return None
    return any(door is True for door in doors)


def central_locked(values: Mapping[str, Any]) -> bool | None:
    """Coche bloqueado: las dos cerraduras delanteras bloqueadas. ⚠️

    El S05 solo informa de las dos delanteras; las traseras siguen al cierre
    centralizado. Si cualquiera está desbloqueada → ``False``.
    """
    locks = [values.get(s.LOCKED_DRIVER), values.get(s.LOCKED_PASSENGER)]
    if all(lock is None for lock in locks):
        return None
    return not any(lock is False for lock in locks)


def power_on(values: Mapping[str, Any]) -> bool | None:
    """Coche encendido: estado de alimentación distinto de 0.

    Observado en un S05 real (30-09-2026): ``powerStatusFeedBack`` vale 0 con
    el coche apagado y 2 en marcha (circulando o parado con el coche
    arrancado). ``engineStatus`` NO sirve en un eléctrico: vale 0 también
    circulando. Otros valores (¿1 = accesorios?) se consideran encendido.
    """
    status = values.get(s.POWER_STATUS)
    return None if status is None else status != 0


def charger_plugged(values: Mapping[str, Any]) -> bool | None:
    """Manguera enchufada: la de AC (Tipo 2) o la de DC (CCS2).

    ``None`` solo si no se sabe nada de ninguna de las dos. La usa la "Vista
    de carga" para el cable conectado sin cargar.
    """
    connectors = [values.get(s.AC_CONNECTOR), values.get(s.DC_CONNECTOR)]
    if all(connector is None for connector in connectors):
        return None
    return any(connector is True for connector in connectors)


#: Señal calculada → función que la calcula.
DERIVED: Final[dict[str, Callable[[Mapping[str, Any]], Any]]] = {
    s.CHARGE_STATUS: charge_status,
    s.REMAINING_CHARGE_HHMM: remaining_charge_hhmm,
    s.ANY_DOOR_OPEN: any_door_open,
    s.CENTRAL_LOCKED: central_locked,
    s.POWER_ON: power_on,
    s.CHARGER_PLUGGED: charger_plugged,
}
