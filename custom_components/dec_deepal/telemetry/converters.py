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

#: Estados de carga del S05 (``ChrgSts``), comprobados moviendo la manguera
#: por todos los estados en un S05 real (15-10-2026). ⚠️ Pendiente de
#: comprobar con un S05 de España.
CHARGE_STATE_NONE: Final = 0  # sin cargar
CHARGE_STATE_AC_CONNECTED: Final = 1  # manguera AC puesta, sin cargar
CHARGE_STATE_DC_CONNECTED: Final = 2  # manguera DC puesta, sin cargar
CHARGE_STATE_AC_CHARGING: Final = 3  # cargando en alterna
CHARGE_STATE_DC_CHARGING: Final = 4  # cargando en continua
#: Carga detenida con la manguera puesta: se vio con el cargador AC desactivado
#: (o bloqueado) y el cable sin quitar (corriente 0 y sin tiempo restante).
#: No dice de qué tipo es la manguera. Visto por Deepal Alternative el
#: 25-10-2026; es lo que pasa cuando DEC Deepal bloquea el cargador.
CHARGE_STATE_STOPPED: Final = 5
CHARGE_STATES: Final = frozenset(range(CHARGE_STATE_NONE, CHARGE_STATE_STOPPED + 1))
CHARGING_STATES: Final = frozenset({CHARGE_STATE_AC_CHARGING, CHARGE_STATE_DC_CHARGING})

#: Ninguna corriente de carga real se acerca a esto (el pico en DC ronda los
#: 480 A). El coche ha llegado a mandar 2538 A (y -2538) aparcado tras una
#: carga DC.
MAX_CHARGE_CURRENT_A: Final = 600.0


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


def percent(value: Any) -> float | None:
    """Un porcentaje de 0 a 100; fuera de ese rango es un dato falso → ``None``."""
    number = to_float(value)
    return number if number is not None and 0 <= number <= 100 else None


def positive(value: Any) -> float | None:
    """Una cantidad (km, litros) mayor o igual que 0; si no → ``None``."""
    number = to_float(value)
    return number if number is not None and number >= 0 else None


def charge_state(value: Any) -> int | None:
    """Estado de carga ``ChrgSts`` (0-5). Cualquier otro valor → ``None``."""
    number = to_int(value)
    return number if number in CHARGE_STATES else None


def charging_from_state(value: Any) -> bool | None:
    """¿Está cargando? Solo los estados 3 y 4.

    Con la manguera puesta y sin cargar (1, 2 y 5) el coche **no** carga: antes
    cualquier valor distinto de 0 contaba como "cargando", así que enchufar
    la manguera encendía "Cargando", abría una sesión y mandaba el aviso.
    Un estado desconocido → ``None`` (no se adivina).
    """
    state = charge_state(value)
    return None if state is None else state in CHARGING_STATES


def charge_current(value: Any) -> float | None:
    """Corriente de carga en A, siempre en positivo.

    El coche la manda con el signo de la batería: cargando en DC se ha visto
    ``-60.5``, que es una carga real de 60,5 A. Se usa el valor absoluto; por
    encima de 600 A (``2538``, ``-2538``) es un valor falso → ``None``.
    """
    number = to_float(value)
    if number is None or abs(number) > MAX_CHARGE_CURRENT_A:
        return None
    return abs(number)


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

    Escala 1:1 con la app (verificado en un S05 real).
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


def humidity(value: Any) -> float | None:
    """Humedad interior en %; fuera de 0-100 → ``None``.

    El coche la envía de dos formas, según el momento (visto en coches
    reales): en % (``61.0``) o en décimas de % (``453`` = 45,3 %). Un valor
    por encima de 100 solo puede ser lo segundo. (Una humedad real por debajo
    del 10 % enviada en décimas se leería mal, pero en un habitáculo no se da.)
    """
    number = to_float(value)
    if number is None:
        return None
    if number > 100:
        number /= 10
    return number if 0 <= number <= 100 else None


def locked_if_zero(value: Any) -> bool | None:
    """Cerradura: ``0`` = bloqueada → ``True``. ⚠️ Pendiente de confirmar en S05.

    Lo indica el material de referencia (``driverLock == 0``). Si se demuestra lo contrario, se
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
