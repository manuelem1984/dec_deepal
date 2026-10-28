"""Constantes de los avisos: horas tranquilas y revisión diaria."""

from __future__ import annotations

from typing import Final

#: Los avisos de mantenimiento solo salen a estas horas (hora local).
QUIET_BEFORE_HOUR: Final = 8
QUIET_FROM_HOUR: Final = 22
#: Revisión diaria del mantenimiento (y, a medianoche, de los días que quedan).
DAILY_CHECK_HOURS: Final = (0, 10)
