"""Sesiones de carga: la que está en curso y la última terminada.

El coche solo dice "estoy cargando" y el nivel de batería; con eso se apunta
cuándo y con cuánto empezó cada carga y cuándo y con cuánto terminó. Es lo
que enseña la ventana de carga de la tarjeta ("Esta carga" y "Última carga").

Se guarda con el coche (``vehicle_data.CHARGE``) para que no se pierda al
reiniciar Home Assistant::

    {
        "current": {"start": "2026-10-12T14:22:00+02:00", "start_level": 44, "start_range": 217},
        "last":    {"start": ..., "start_level": 22, "start_range": 108,
                    "end": ..., "end_level": 80, "end_range": 394},
    }

Sin Home Assistant: son funciones puras (ver ``tests/test_charging.py``).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final

CURRENT: Final = "current"
LAST: Final = "last"

#: Una "carga" más corta que esto y sin ganar batería no se apunta: es el
#: coche dudando al enchufar, no una carga.
MIN_SECONDS: Final = 120

_START_FIELDS: Final = ("start", "start_level", "start_range")
_END_FIELDS: Final = ("end", "end_level", "end_range")


def _number(value: Any) -> float | None:
    """Número tal cual, o ``None`` (los booleanos no cuentan)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _session(raw: Any, fields: tuple[str, ...]) -> dict[str, Any] | None:
    """Una sesión guardada, solo con los campos que se entienden."""
    if not isinstance(raw, Mapping):
        return None
    session: dict[str, Any] = {}
    for field in fields:
        value = raw.get(field)
        if field in ("start", "end"):
            if not isinstance(value, str):
                return None
            try:
                datetime.fromisoformat(value)
            except ValueError:
                return None
            session[field] = value
        else:
            session[field] = _number(value)
    return session


def clean(raw: Any) -> dict[str, Any]:
    """Lo guardado, validado (lo que no se entiende se descarta)."""
    if not isinstance(raw, Mapping):
        return {}
    state: dict[str, Any] = {}
    if (current := _session(raw.get(CURRENT), _START_FIELDS)) is not None:
        state[CURRENT] = current
    if (last := _session(raw.get(LAST), _START_FIELDS + _END_FIELDS)) is not None:
        state[LAST] = last
    return state


def update(
    state: Mapping[str, Any] | None,
    charging: bool | None,
    level: float | None,
    range_km: float | None,
    now: datetime,
) -> tuple[dict[str, Any], bool]:
    """Pone al día las sesiones con una lectura del coche.

    Se puede llamar las veces que haga falta con la misma lectura: solo cambia
    algo cuando la carga empieza o termina.

    Args:
        state: Lo guardado hasta ahora.
        charging: ¿Está cargando? ``None`` = no se sabe (no se toca nada).
        level: Nivel de batería (%), si se conoce.
        range_km: Autonomía (km), si se conoce.
        now: Momento de la lectura.

    Returns:
        El estado nuevo y si ha cambiado (para guardarlo).
    """
    result = clean(state)
    current = result.get(CURRENT)
    stamp = now.isoformat(timespec="seconds")
    level, range_km = _number(level), _number(range_km)

    if charging is True:
        if current is None:
            result[CURRENT] = {"start": stamp, "start_level": level, "start_range": range_km}
            return result, True
        # El nivel puede llegar un poco después que el "estoy cargando".
        changed = False
        for field, value in (("start_level", level), ("start_range", range_km)):
            if current.get(field) is None and value is not None:
                current[field] = value
                changed = True
        return result, changed

    if charging is False and current is not None:
        del result[CURRENT]
        seconds = (now - datetime.fromisoformat(current["start"])).total_seconds()
        gained = level is not None and current.get("start_level") is not None and level > current["start_level"]
        if seconds >= MIN_SECONDS or gained:
            result[LAST] = {**current, "end": stamp, "end_level": level, "end_range": range_km}
        return result, True

    return result, False


def attributes(state: Mapping[str, Any] | None) -> dict[str, Any]:
    """Atributos del sensor "Cargando" (los lee la tarjeta)."""
    state = state or {}
    result: dict[str, Any] = {}
    if current := state.get(CURRENT):
        result["carga_actual"] = {
            "inicio": current["start"],
            "nivel_inicio": current.get("start_level"),
            "autonomia_inicio": current.get("start_range"),
        }
    if last := state.get(LAST):
        result["ultima_carga"] = {
            "inicio": last["start"],
            "fin": last["end"],
            "nivel_inicio": last.get("start_level"),
            "nivel_fin": last.get("end_level"),
            "autonomia_inicio": last.get("start_range"),
            "autonomia_fin": last.get("end_range"),
        }
    return result
