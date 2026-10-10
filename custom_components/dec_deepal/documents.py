"""ITV y seguro del coche: fechas, cuánto falta y qué aviso toca.

Lógica pura (sin Home Assistant), como ``maintenance.py``. La usan
``alerts.py`` (guarda las fichas y envía los avisos), las entidades y
Configurar → ITV / Seguro.

ITV
---
La próxima fecha se calcula con las normas del país de la cuenta
(:class:`CountryRules`; las de España: la primera a los 4 años de la
matriculación; después, cada 2 años mientras el coche tenga menos de 10, y
cada año a partir de entonces). El usuario puede fijar otra
fecha (``next_override``), que vale hasta que registre la siguiente ITV.
Avisos: quedan 2 meses, 1 mes, 15 días y vencida.

Seguro
------
Dos fechas: la **renovación** y el **límite de desistimiento** (renovación
menos ``notice_days``; hasta ese día se puede avisar de que no se renueva).
Avisos: 30 y 15 días antes del límite, el último día y el día de la
renovación. Al llegar la renovación, la ficha pasa sola al año siguiente.

El número de póliza y los teléfonos solo se enseñan en la tarjeta: no van a
ninguna entidad ni a los diagnósticos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Final

from .maintenance import LEVEL_OK, LEVEL_OVERDUE, LEVEL_SOON, add_months

# ---------------------------------------------------------------------------
# ITV
# ---------------------------------------------------------------------------

ITV_DAY_STEPS: Final = (60, 30, 15)


@dataclass(frozen=True, slots=True)
class CountryRules:
    """Normas que dependen del PAÍS (no del idioma): ITV y preaviso del seguro.

    Los valores por defecto son los de España. Cada país puede cambiarlos en
    ``countries/countries.yaml`` → ``normas``.
    """

    #: Meses desde la matriculación hasta la primera inspección.
    itv_first_months: int = 48
    #: Meses entre inspecciones mientras el coche es "joven".
    itv_interval_months: int = 24
    #: Edad del coche (meses) a partir de la cual el intervalo es el reducido.
    itv_reduced_from_months: int = 120
    #: Meses entre inspecciones a partir de esa edad.
    itv_reduced_interval_months: int = 12
    #: Días antes de la renovación del seguro en que acaba el plazo para no renovar.
    insurance_notice_days: int = 30


#: Normas de España (las de por defecto).
DEFAULT_RULES: Final = CountryRules()
STEP_OVERDUE: Final = "overdue"
MAX_HISTORY: Final = 30


@dataclass(slots=True)
class ItvRecord:
    """Ficha de ITV de un coche (lo que se guarda en disco)."""

    registration_date: date
    #: Última ITV pasada (``None`` = ninguna todavía).
    last_date: date | None = None
    #: Próxima fecha puesta a mano (``None`` = calculada).
    next_override: date | None = None
    #: ITV registradas (fechas ISO), de antigua a nueva.
    history: list[str] = field(default_factory=list)
    notified: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        """Para guardar en disco."""
        return {
            "registration_date": self.registration_date.isoformat(),
            "last_date": self.last_date.isoformat() if self.last_date else None,
            "next_override": self.next_override.isoformat() if self.next_override else None,
            "history": list(self.history),
            "notified": sorted(self.notified),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ItvRecord:
        """Desde lo guardado en disco."""
        return cls(
            registration_date=date.fromisoformat(str(raw["registration_date"])),
            last_date=date.fromisoformat(raw["last_date"]) if raw.get("last_date") else None,
            next_override=(
                date.fromisoformat(raw["next_override"]) if raw.get("next_override") else None
            ),
            history=list(raw.get("history", [])),
            notified=set(raw.get("notified", [])),
        )


@dataclass(frozen=True, slots=True)
class DueStatus:
    """Situación de un vencimiento en un día concreto."""

    due_date: date
    #: Días que quedan (negativo = vencido hace esos días).
    days_left: int
    level: str
    steps: frozenset[str]


def itv_calculated(record: ItvRecord, rules: CountryRules = DEFAULT_RULES) -> date:
    """Próxima ITV según las normas del país (sin la fecha puesta a mano)."""
    if record.last_date is None:
        return add_months(record.registration_date, rules.itv_first_months)
    old = record.last_date >= add_months(record.registration_date, rules.itv_reduced_from_months)
    return add_months(
        record.last_date,
        rules.itv_reduced_interval_months if old else rules.itv_interval_months,
    )


def itv_due(record: ItvRecord, rules: CountryRules = DEFAULT_RULES) -> date:
    """Próxima ITV: la puesta a mano o la calculada."""
    return record.next_override or itv_calculated(record, rules)


def itv_status(record: ItvRecord, today: date, rules: CountryRules = DEFAULT_RULES) -> DueStatus:
    """Cuánto falta para la próxima ITV."""
    due = itv_due(record, rules)
    days_left = (due - today).days
    steps = {f"d{days}" for days in ITV_DAY_STEPS if days_left <= days}
    overdue = days_left < 0
    if overdue:
        steps.add(STEP_OVERDUE)
    return DueStatus(
        due_date=due,
        days_left=days_left,
        level=LEVEL_OVERDUE if overdue else LEVEL_SOON if steps else LEVEL_OK,
        steps=frozenset(steps),
    )


def itv_pending_notice(record: ItvRecord, current: DueStatus) -> str | None:
    """Aviso de ITV que toca: ``"overdue"``, ``"remaining"`` o ``None``."""
    new = current.steps - record.notified
    if not new or STEP_OVERDUE in record.notified:
        return None
    return "overdue" if STEP_OVERDUE in new else "remaining"


def register_itv(record: ItvRecord, when: date) -> None:
    """Anota una ITV pasada: se recalcula la siguiente y se reinician los avisos."""
    record.last_date = when
    record.next_override = None
    record.notified = set()
    record.history.append(when.isoformat())
    del record.history[:-MAX_HISTORY]


# ---------------------------------------------------------------------------
# Seguro
# ---------------------------------------------------------------------------

KIND_THIRD_PARTY: Final = "third_party"
KIND_THIRD_PARTY_PLUS: Final = "third_party_plus"
KIND_COMPREHENSIVE_EXCESS: Final = "comprehensive_excess"
KIND_COMPREHENSIVE: Final = "comprehensive"
#: Tipos de seguro, en el orden del desplegable (nombres en translations).
INSURANCE_KINDS: Final = (
    KIND_THIRD_PARTY,
    KIND_THIRD_PARTY_PLUS,
    KIND_COMPREHENSIVE_EXCESS,
    KIND_COMPREHENSIVE,
)
DEFAULT_NOTICE_DAYS: Final = 30
#: Avisos antes del límite de desistimiento (días) y el del último día.
CANCEL_DAY_STEPS: Final = (30, 15)
STEP_LAST_DAY: Final = "last_day"


@dataclass(slots=True)
class InsuranceRecord:
    """Ficha del seguro de un coche (lo que se guarda en disco)."""

    renewal_date: date
    company: str = ""
    policy: str = ""
    kind: str = KIND_THIRD_PARTY
    #: Días antes de la renovación en que acaba el plazo para no renovar.
    notice_days: int = DEFAULT_NOTICE_DAYS
    phone_assistance: str = ""
    phone_company: str = ""
    notified: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        """Para guardar en disco."""
        return {
            "renewal_date": self.renewal_date.isoformat(),
            "company": self.company,
            "policy": self.policy,
            "kind": self.kind,
            "notice_days": self.notice_days,
            "phone_assistance": self.phone_assistance,
            "phone_company": self.phone_company,
            "notified": sorted(self.notified),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> InsuranceRecord:
        """Desde lo guardado en disco."""
        return cls(
            renewal_date=date.fromisoformat(str(raw["renewal_date"])),
            company=str(raw.get("company") or ""),
            policy=str(raw.get("policy") or ""),
            kind=str(raw.get("kind") or KIND_THIRD_PARTY),
            notice_days=int(raw.get("notice_days", DEFAULT_NOTICE_DAYS)),
            phone_assistance=str(raw.get("phone_assistance") or ""),
            phone_company=str(raw.get("phone_company") or ""),
            notified=set(raw.get("notified", [])),
        )

    @property
    def cancel_deadline(self) -> date:
        """Último día para avisar de que no se renueva."""
        return self.renewal_date - timedelta(days=self.notice_days)


@dataclass(frozen=True, slots=True)
class InsuranceStatus:
    """Situación del seguro en un día concreto."""

    renewal_date: date
    cancel_deadline: date
    days_to_renewal: int
    #: Días hasta el límite de desistimiento (negativo = plazo pasado).
    days_to_cancel: int
    level: str
    steps: frozenset[str]


def insurance_status(record: InsuranceRecord, today: date) -> InsuranceStatus:
    """Cuánto falta para la renovación y para el límite de desistimiento.

    Testigo: ámbar desde 30 días antes del límite; rojo el último día. Pasado
    el plazo ya no hay nada que hacer hasta la renovación: sin testigo.
    """
    days_to_cancel = (record.cancel_deadline - today).days
    steps: set[str] = set()
    level = LEVEL_OK
    if days_to_cancel >= 0:
        steps = {f"c{days}" for days in CANCEL_DAY_STEPS if days_to_cancel <= days}
        if days_to_cancel == 0:
            steps.add(STEP_LAST_DAY)
            level = LEVEL_OVERDUE
        elif steps:
            level = LEVEL_SOON
    return InsuranceStatus(
        renewal_date=record.renewal_date,
        cancel_deadline=record.cancel_deadline,
        days_to_renewal=(record.renewal_date - today).days,
        days_to_cancel=days_to_cancel,
        level=level,
        steps=frozenset(steps),
    )


def insurance_pending_notice(record: InsuranceRecord, current: InsuranceStatus) -> str | None:
    """Aviso de seguro que toca: ``"last_day"``, ``"cancel"`` o ``None``."""
    new = current.steps - record.notified
    if not new:
        return None
    return "last_day" if STEP_LAST_DAY in new else "cancel"


def insurance_roll(record: InsuranceRecord, today: date) -> bool:
    """Si ya llegó la renovación, pasa la ficha al año siguiente.

    Returns:
        ``True`` si se ha renovado (hay que avisar y guardar).
    """
    rolled = False
    while record.renewal_date <= today:
        record.renewal_date = add_months(record.renewal_date, 12)
        record.notified = set()
        rolled = True
    return rolled
