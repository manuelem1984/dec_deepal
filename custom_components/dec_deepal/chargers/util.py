"""Ayudas para leer estados de Home Assistant y fechas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.const import (
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import State
from homeassistant.util import dt as dt_util




def _number(state: State | None) -> float | None:
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, ""):
        return None
    try:
        return float(state.state)
    except ValueError:
        return None


def _flag(state: State | None) -> bool | None:
    """Estado sí/no de una entidad (``None`` = no se sabe)."""
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        return None
    if state.state in (STATE_ON, "true", "plugged", "connected", "charging", "locked"):
        return True
    number = _number(state)
    if number is not None:
        return number > 0
    return False


def _iso(when: datetime | None) -> str | None:
    return None if when is None else when.isoformat()


def _when(value: Any) -> datetime | None:
    return dt_util.parse_datetime(value) if isinstance(value, str) else None
