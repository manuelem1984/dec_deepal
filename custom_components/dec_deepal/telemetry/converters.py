"""Conversores reutilizables: de valor en bruto a valor limpio.

Regla de oro: si el valor no se puede interpretar, se devuelve ``None``
(la entidad mostrará "Desconocido"). Nunca se inventa un valor.

Cada conversor recibe un único valor en bruto y devuelve el valor limpio.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Final

#: Valor que manda el coche en ``chargDeltMins`` cuando no hay estimación.
CHARGE_TIME_SENTINEL: Final = 8191


def to_int(value: Any) -> int | None:
    """Número entero (acepta ``"12"``, ``12.7`` → 12)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> float | None:
    """Número decimal."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_bool(value: Any) -> bool | None:
    """``0`` → ``False``; cualquier otro número → ``True``."""
    number = to_int(value)
    return None if number is None else number != 0


def connector(value: Any) -> bool | None:
    """Estado de la manguera de carga. ✅ verificado con el coche.

    **No** es un booleano simple: ``0`` y ``1`` significan *no enchufada*;
    ``2`` o más, *enchufada* (se ha visto ``3`` cargando en AC). Con un
    booleano normal, el ``1`` que manda el coche desenchufado se leía mal.
    """
    number = to_int(value)
    return None if number is None else number >= 2


def seat_level(value: Any) -> int | None:
    """Nivel de asiento 0-3. ``6`` (módulo dormido) u otro valor → ``None``.

    Escala 1:1 con la app (verificado por Deepal Alternative en un S05 real).
    La versión anterior dividía entre 2, basándose en un material de
    referencia que resultó no aplicar al S05.
    """
    number = to_int(value)
    if number is None or not 0 <= number <= 3:
        return None
    return number


def charge_minutes(value: Any) -> int | None:
    """Minutos de carga restantes; ``8191`` = sin estimación → ``None``."""
    number = to_int(value)
    if number is None or number == CHARGE_TIME_SENTINEL or number < 0:
        return None
    return number


def tenths(value: Any) -> float | None:
    """Valor en décimas → unidades (``225`` → ``22.5``)."""
    number = to_float(value)
    return None if number is None else number / 10


def humidity_tenths(value: Any) -> float | None:
    """Humedad en décimas de % (``453`` → ``45.3``); fuera de 0-100 → ``None``."""
    humidity = tenths(value)
    if humidity is None or not 0 <= humidity <= 100:
        return None
    return humidity


def locked_if_zero(value: Any) -> bool | None:
    """Cerradura: ``0`` = bloqueada → ``True``. ⚠️ Pendiente de confirmar en S05.

    Lo indican tanto el material de referencia del proyecto anterior como
    Deepal Alternative (``driverLock == 0``). Si se demuestra lo contrario, se
    cambia aquí y todas las entidades de cierre se corrigen a la vez.
    """
    number = to_int(value)
    return None if number is None else number == 0


def timestamp(value: Any) -> datetime | None:
    """Fecha del informe del coche → ``datetime`` en UTC.

    Acepta texto ISO 8601 (``"2026-09-30T10:00:00Z"``) y números epoch en
    segundos o milisegundos.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        seconds = value / 1000 if abs(value) >= 100_000_000_000 else value
        try:
            return datetime.fromtimestamp(seconds, UTC)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str) and value.strip():
        text = value.strip()
        if text.lstrip("-").isdigit():
            return timestamp(int(text))
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    return None
