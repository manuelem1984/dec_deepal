"""Formas de lo que se guarda en ``.storage/dec_deepal.chargers`` (tipos, sin lógica).

Son ``TypedDict``: en ejecución siguen siendo ``dict`` normales (lo que se
guarda en disco no cambia). Sirven para documentar cada clave en un solo sitio
y para que el editor avise si se escribe mal una.
"""

from __future__ import annotations

from typing import TypedDict


class ChargerConfig(TypedDict):
    """Un cargador, tal como lo deja :func:`~.config.clean_charger`."""

    id: str
    name: str
    #: Papel → entidad (``plugged`` siempre; el resto, opcional).
    entities: dict[str, str]
    #: En un interruptor: ¿encendido = bloqueado?
    lock_on_locked: bool
    vehicles: list[str]
    coverage: str  # "yes" | "no" | "unknown"
    unlock: str  # "none" | "confirm"
    notify_confirm: bool
    remind_minutes: int
    relock: bool
    relock_minutes: int
    relock_notify: bool
    lock_full: bool
    lock_full_minutes: int
    read_interval: int
    loss: float
    learn: bool
    price: float | None
    price_entity: str


class Session(TypedDict, total=False):
    """La carga en curso de un cargador (de enchufar a desenchufar). Fechas en ISO."""

    plugged_at: str
    vehicle_id: str | None
    #: Cómo se supo el coche: ``car``, ``user`` o ``single``.
    assigned: str | None
    asked: bool
    unlocked_at: str | None
    charging_since: str
    finished_at: str
    #: Cuándo se bloqueará solo al terminar (``lock_full``).
    lock_at: str
    # Del coche al asignarlo.
    soc_start: float | None
    range_start: float | None
    odometer: float | None
    # Energía: contador del cargador y potencia por tiempo.
    energy_start: float | None
    energy_meter: float
    energy_power: float
    pw_at: str
    pw_w: float
    energy: float
    energy_source: str  # "meter" | "power"
    # Leer el coche mientras carga.
    read_ok: str
    read_failures: int
    no_coverage: bool
    # Límite de carga.
    limit_hit: str
    limit_locked: bool
    full: bool


class HistoryRecord(TypedDict):
    """Una carga terminada (las últimas ``HISTORY_SIZE`` de cada cargador)."""

    start: str | None
    end: str
    charging_since: str | None
    finished_at: str | None
    vehicle_id: str | None
    energy: float
    cost: float | None
    soc_start: float | None
    soc_end: float | None
    estimated: bool
    odometer: float | None
    #: Ya se miró si el coche volvió a informar (y se midió la pérdida).
    learned: bool


class CarLimit(TypedDict):
    """Límite de carga de un coche."""

    limit: int  # 70, 80, 90 o 100
    #: «Solo esta: 100 %» / «La próxima al 100 %».
    once_full: bool
    #: Cargas seguidas sin llegar al 100 %.
    incomplete: int


class LimitSettings(TypedDict):
    """Opciones del límite de carga y del recordatorio del 100 % (Ajustes)."""

    enabled: bool
    notify: bool
    remind: bool
    every: int
    auto: bool


__all__ = ["CarLimit", "ChargerConfig", "HistoryRecord", "LimitSettings", "Session"]
