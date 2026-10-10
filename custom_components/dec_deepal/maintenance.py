"""Mantenimiento periódico: cuánto falta para la próxima revisión.

Lógica pura (sin Home Assistant), para poder probarla sola. Quien la usa:

- ``alerts.py`` guarda la ficha de cada coche y envía los avisos.
- ``binary_sensor.py`` / ``sensor.py`` muestran el testigo, los días y los km.
- ``options_flow.py`` (Configurar → Mantenimiento) y el servicio
  ``dec_deepal.register_maintenance`` la modifican.

Cómo se cuenta
--------------
Desde la **última revisión hecha** (o desde la matriculación, si aún no ha
pasado ninguna): la siguiente toca a los ``interval_months`` meses o a los
``interval_km`` kilómetros, lo que llegue antes. El **número de revisión**
(1.ª, 2.ª...) solo sirve para saber qué operaciones incluye, según el plan del
modelo (``mantenimiento:`` en ``vehicles/vehicles.yaml``).

Avisos
------
Hay siete escalones (:data:`DAY_STEPS`, :data:`KM_STEPS` y "vencido"). Cada
uno se avisa una sola vez por revisión: la ficha recuerda los ya avisados
(``notified``). Si de golpe se cumplen varios (p. ej. al configurarlo tarde),
sale un único aviso con la situación actual.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Final

from .textos_generados import BASE_LANGUAGE, BORROWED_LANGUAGES

DEFAULT_INTERVAL_KM: Final = 20000
DEFAULT_INTERVAL_MONTHS: Final = 12

#: Escalones de aviso por tiempo (días que quedan) y por distancia (km).
DAY_STEPS: Final = (60, 30, 15)
KM_STEPS: Final = (3000, 2000, 1000)
STEP_OVERDUE: Final = "overdue"

LEVEL_OK: Final = "ok"
#: Dentro del margen de aviso (testigo ámbar en la tarjeta).
LEVEL_SOON: Final = "soon"
#: Fecha o kilómetros superados (testigo rojo).
LEVEL_OVERDUE: Final = "overdue"

#: Revisiones que se guardan en el historial (las más recientes).
MAX_HISTORY: Final = 30


@dataclass(frozen=True, slots=True)
class Operation:
    """Una operación del plan de mantenimiento."""

    #: Nombre por idioma (``{"es": ..., "en": ..., "pt": ...}``).
    names: dict[str, str]
    #: Cada cuántas revisiones toca (1 = en todas, 2 = en las pares...).
    every: int = 1
    #: Versiones a las que afecta (vacío = todas).
    trims: tuple[str, ...] = ()

    def name(self, language: str = "es") -> str:
        """Nombre en el idioma pedido; si falta, en inglés o en el primero que haya."""
        base = language.replace("_", "-").split("-")[0].lower()
        base = BORROWED_LANGUAGES.get(base, base)
        return (
            self.names.get(base)
            or self.names.get(BASE_LANGUAGE)
            or next(iter(self.names.values()))
        )

    def applies(self, number: int, trim: str | None) -> bool:
        """¿Toca en la revisión ``number`` de un coche de esta versión?"""
        if self.trims and trim not in self.trims:
            return False
        return number % self.every == 0


@dataclass(frozen=True, slots=True)
class MaintenancePlan:
    """Plan de mantenimiento de un modelo."""

    interval_km: int = DEFAULT_INTERVAL_KM
    interval_months: int = DEFAULT_INTERVAL_MONTHS
    operations: tuple[Operation, ...] = ()

    def operations_for(self, number: int, trim: str | None, language: str = "es") -> list[str]:
        """Operaciones de la revisión ``number`` (1 = la primera), en un idioma."""
        return [op.name(language) for op in self.operations if op.applies(number, trim)]


@dataclass(slots=True)
class MaintenanceRecord:
    """Ficha de mantenimiento de un coche (lo que se guarda en disco)."""

    #: Revisiones ya pasadas (0 = ninguna).
    services_done: int
    #: Fecha de la última revisión (o de matriculación si ``services_done`` es 0).
    last_date: date
    #: Kilómetros en ese momento.
    last_km: int = 0
    interval_km: int = DEFAULT_INTERVAL_KM
    interval_months: int = DEFAULT_INTERVAL_MONTHS
    #: Revisiones registradas: ``{"number", "date", "km"}``, de antigua a nueva.
    history: list[dict[str, Any]] = field(default_factory=list)
    #: Escalones ya avisados de la próxima revisión.
    notified: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        """Para guardar en disco."""
        return {
            "services_done": self.services_done,
            "last_date": self.last_date.isoformat(),
            "last_km": self.last_km,
            "interval_km": self.interval_km,
            "interval_months": self.interval_months,
            "history": list(self.history),
            "notified": sorted(self.notified),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> MaintenanceRecord:
        """Desde lo guardado en disco."""
        return cls(
            services_done=int(raw.get("services_done", 0)),
            last_date=date.fromisoformat(str(raw["last_date"])),
            last_km=int(raw.get("last_km", 0)),
            interval_km=int(raw.get("interval_km", DEFAULT_INTERVAL_KM)),
            interval_months=int(raw.get("interval_months", DEFAULT_INTERVAL_MONTHS)),
            history=list(raw.get("history", [])),
            notified=set(raw.get("notified", [])),
        )


@dataclass(frozen=True, slots=True)
class MaintenanceStatus:
    """Situación de la próxima revisión en un día y con unos km concretos."""

    #: Número de la próxima revisión (1 = la primera).
    number: int
    due_date: date
    due_km: int
    #: Días que quedan (negativo = vencida hace esos días).
    days_left: int
    #: Kilómetros que quedan (``None`` si no se conoce el cuentakilómetros).
    km_left: int | None
    level: str
    #: Escalones de aviso ya alcanzados.
    steps: frozenset[str]


def add_months(start: date, months: int) -> date:
    """``start`` + ``months`` meses (el 31 pasa al último día si el mes es más corto)."""
    index = start.month - 1 + months
    year, month = start.year + index // 12, index % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def status(record: MaintenanceRecord, today: date, odometer_km: float | None) -> MaintenanceStatus:
    """Calcula cuánto falta para la próxima revisión."""
    due_date = add_months(record.last_date, record.interval_months)
    due_km = record.last_km + record.interval_km
    days_left = (due_date - today).days
    km_left = None if odometer_km is None else round(due_km - odometer_km)

    steps = {f"d{days}" for days in DAY_STEPS if days_left <= days}
    if km_left is not None:
        steps |= {f"k{km}" for km in KM_STEPS if km_left <= km}
    overdue = days_left <= 0 or (km_left is not None and km_left <= 0)
    if overdue:
        steps.add(STEP_OVERDUE)
    return MaintenanceStatus(
        number=record.services_done + 1,
        due_date=due_date,
        due_km=due_km,
        days_left=days_left,
        km_left=km_left,
        level=LEVEL_OVERDUE if overdue else LEVEL_SOON if steps else LEVEL_OK,
        steps=frozenset(steps),
    )


def pending_notice(record: MaintenanceRecord, current: MaintenanceStatus) -> str | None:
    """Qué aviso toca enviar ahora: ``"overdue"``, ``"remaining"`` o ``None``.

    No modifica la ficha: tras enviar, llamar a :func:`mark_notified`.
    """
    new = current.steps - record.notified
    # Tras el aviso de "vencido" ya no hay más hasta registrar la revisión.
    if not new or STEP_OVERDUE in record.notified:
        return None
    return "overdue" if STEP_OVERDUE in new else "remaining"


def mark_notified(record: MaintenanceRecord, current: MaintenanceStatus) -> None:
    """Da por avisados todos los escalones alcanzados."""
    record.notified |= current.steps


def register_service(record: MaintenanceRecord, when: date, km: int) -> None:
    """Anota una revisión hecha: pasa a la siguiente y reinicia los avisos."""
    record.services_done += 1
    record.last_date = when
    record.last_km = km
    record.notified = set()
    record.history.append({"number": record.services_done, "date": when.isoformat(), "km": km})
    del record.history[:-MAX_HISTORY]
