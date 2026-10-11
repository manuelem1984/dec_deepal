"""Historial de cambios de las señales de un coche (para los diagnósticos).

La última lectura dice cómo está el coche; no dice **qué pasó**. Este módulo
compara cada lectura con la anterior y devuelve lo que ha cambiado, para
guardarlo en el registro: así un diagnóstico enseña, por ejemplo, que el
testigo del airbag estuvo encendido de las 10:02 a las 10:03, o la secuencia
de una carga.

Lógica pura (sin Home Assistant), para poder probarla sola.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from ..telemetry import signals as s

#: Señales que cambian en casi todas las lecturas: llenarían el historial sin
#: aportar nada. Su valor actual ya está en ``senales``.
NOISY_SIGNALS: Final = frozenset(
    {
        s.REPORT_TIME,
        s.RANGE_KM,
        s.ODOMETER_KM,
        s.INSIDE_TEMP_C,
        s.CABIN_HUMIDITY,
        s.CHARGE_CURRENT,
        s.AC_CHARGE_CURRENT,
        s.DC_CHARGE_CURRENT,
        s.REMAINING_CHARGE_MIN,
        s.TIRE_PRESSURE_FRONT_LEFT,
        s.TIRE_PRESSURE_FRONT_RIGHT,
        s.TIRE_PRESSURE_REAR_LEFT,
        s.TIRE_PRESSURE_REAR_RIGHT,
    }
)


def _text(value: Any) -> str:
    """Valor tal como se lee en el diagnóstico (``None`` = sin dato)."""
    return "—" if value is None else str(value)


def changes(previous: Mapping[str, Any] | None, current: Mapping[str, Any]) -> list[str]:
    """Señales que han cambiado entre dos lecturas: ``["charging: False → True"]``.

    La primera lectura (sin anterior) no cuenta como cambio. Se devuelven
    textos, no un diccionario, para que el filtro de datos sensibles (que
    mira los nombres de las claves) no oculte señales como ``pin_arm``.
    """
    if previous is None:
        return []
    changed = []
    for signal in sorted(set(previous) | set(current)):
        if signal in NOISY_SIGNALS:
            continue
        before, after = previous.get(signal), current.get(signal)
        if before != after:
            changed.append(f"{signal}: {_text(before)} → {_text(after)}")
    return changed
