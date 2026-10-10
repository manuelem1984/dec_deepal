"""Pruebas de ITV y seguro (lógica sin Home Assistant)."""

from __future__ import annotations

from datetime import date

from custom_components.dec_deepal import alert_rules as ar
from custom_components.dec_deepal import documents as doc
from custom_components.dec_deepal.maintenance import LEVEL_OK, LEVEL_OVERDUE, LEVEL_SOON

REGISTRATION = date(2022, 11, 26)


# ---------------------------------------------------------------------------
# ITV
# ---------------------------------------------------------------------------


def test_itv_rule_for_spanish_cars() -> None:
    """Primera a los 4 años; cada 2 hasta los 10; anual después."""
    record = doc.ItvRecord(registration_date=REGISTRATION)
    assert doc.itv_due(record) == date(2026, 11, 26)
    doc.register_itv(record, date(2026, 11, 20))
    assert doc.itv_due(record) == date(2028, 11, 20)  # coche de 4 años: 2 años
    doc.register_itv(record, date(2030, 11, 18))
    assert doc.itv_due(record) == date(2032, 11, 18)  # 8 años: aún 2 años
    doc.register_itv(record, date(2032, 11, 30))
    assert doc.itv_due(record) == date(2033, 11, 30)  # ya tiene 10: anual
    assert record.history == ["2026-11-20", "2030-11-18", "2032-11-30"]


def test_itv_rules_come_from_the_country() -> None:
    """Las normas son del país de la cuenta: otro país, otros plazos."""
    from pathlib import Path

    from custom_components.dec_deepal.registries import load_all

    integration = Path(__file__).parents[1] / "custom_components" / "dec_deepal"
    spain = load_all(integration).countries.get("es").rules
    assert spain == doc.DEFAULT_RULES
    assert (spain.itv_first_months, spain.itv_interval_months, spain.insurance_notice_days) == (48, 24, 30)
    # Un país con inspección a los 3 años y anual desde entonces.
    other = doc.CountryRules(itv_first_months=36, itv_interval_months=12)
    record = doc.ItvRecord(registration_date=REGISTRATION)
    assert doc.itv_due(record, other) == date(2025, 11, 26)
    doc.register_itv(record, date(2025, 11, 20))
    assert doc.itv_due(record, other) == date(2026, 11, 20)
    assert doc.itv_status(record, date(2026, 11, 21), other).level == LEVEL_OVERDUE


def test_itv_manual_date_until_next_registration() -> None:
    record = doc.ItvRecord(registration_date=REGISTRATION, next_override=date(2026, 10, 1))
    assert doc.itv_due(record) == date(2026, 10, 1)
    assert doc.itv_calculated(record) == date(2026, 11, 26)
    doc.register_itv(record, date(2026, 9, 28))
    assert record.next_override is None and doc.itv_due(record) == date(2028, 9, 28)
    assert doc.ItvRecord.from_dict(record.to_dict()) == record


def test_itv_steps_once_each() -> None:
    record = doc.ItvRecord(registration_date=REGISTRATION)
    assert doc.itv_status(record, date(2026, 9, 1)).level == LEVEL_OK
    current = doc.itv_status(record, date(2026, 10, 10))  # quedan 47 días
    assert (current.days_left, current.level, current.steps) == (47, LEVEL_SOON, {"d60"})
    assert doc.itv_pending_notice(record, current) == "remaining"
    record.notified |= current.steps
    assert doc.itv_pending_notice(record, doc.itv_status(record, date(2026, 10, 20))) is None
    for day, steps in ((date(2026, 10, 27), {"d60", "d30"}), (date(2026, 11, 11), {"d60", "d30", "d15"})):
        current = doc.itv_status(record, day)
        assert current.steps == steps and doc.itv_pending_notice(record, current) == "remaining"
        record.notified |= current.steps
    # El último día aún no está vencida; al día siguiente, sí (y se avisa una vez).
    assert doc.itv_status(record, date(2026, 11, 26)).level == LEVEL_SOON
    overdue = doc.itv_status(record, date(2026, 11, 27))
    assert overdue.level == LEVEL_OVERDUE and doc.itv_pending_notice(record, overdue) == "overdue"
    record.notified |= overdue.steps
    assert doc.itv_pending_notice(record, doc.itv_status(record, date(2027, 1, 1))) is None


# ---------------------------------------------------------------------------
# Seguro
# ---------------------------------------------------------------------------


def _insurance(**changes) -> doc.InsuranceRecord:  # noqa: ANN003
    values = {"renewal_date": date(2027, 3, 14), "company": "Mutua Ejemplo", "policy": "0123"}
    return doc.InsuranceRecord(**{**values, **changes})


def test_insurance_dates_and_levels() -> None:
    record = _insurance()
    assert record.cancel_deadline == date(2027, 2, 12)  # 30 días antes
    assert _insurance(notice_days=60).cancel_deadline == date(2027, 1, 13)
    far = doc.insurance_status(record, date(2026, 10, 9))
    assert (far.days_to_renewal, far.days_to_cancel, far.level) == (156, 126, LEVEL_OK)
    soon = doc.insurance_status(record, date(2027, 1, 13))  # 30 días antes del límite
    assert soon.level == LEVEL_SOON and soon.steps == {"c30"}
    last = doc.insurance_status(record, date(2027, 2, 12))
    assert last.days_to_cancel == 0 and last.level == LEVEL_OVERDUE
    assert doc.STEP_LAST_DAY in last.steps
    # Pasado el plazo ya no hay nada que hacer: sin testigo hasta la renovación.
    late = doc.insurance_status(record, date(2027, 2, 20))
    assert late.level == LEVEL_OK and late.steps == frozenset() and late.days_to_cancel == -8


def test_insurance_notices_and_renewal() -> None:
    record = _insurance()
    kinds = []
    for day in (date(2027, 1, 13), date(2027, 1, 14), date(2027, 1, 28), date(2027, 2, 12), date(2027, 2, 13)):
        current = doc.insurance_status(record, day)
        kinds.append(doc.insurance_pending_notice(record, current))
        record.notified |= current.steps
    assert kinds == ["cancel", None, "cancel", "last_day", None]
    # El día de la renovación la ficha pasa al año siguiente y se reinician los avisos.
    assert not doc.insurance_roll(record, date(2027, 3, 13))
    assert doc.insurance_roll(record, date(2027, 3, 14))
    assert record.renewal_date == date(2028, 3, 14) and record.notified == set()
    # Home Assistant apagado dos años: se pone al día de una vez.
    assert doc.insurance_roll(record, date(2030, 1, 1)) and record.renewal_date == date(2030, 3, 14)
    assert doc.InsuranceRecord.from_dict(record.to_dict()) == record


# ---------------------------------------------------------------------------
# Textos y tipos de aviso
# ---------------------------------------------------------------------------


def test_texts() -> None:
    assert (
        ar.itv_text("remaining", days_left=30, due_date="26/11/2026", language="es")
        == "Quedan 30 días para la ITV (límite: 26/11/2026)."
    )
    assert ar.itv_text("remaining", days_left=0, due_date="x", language="es") == "Hoy es el último día para pasar la ITV."
    assert ar.itv_text("overdue", days_left=-3, due_date="26/11/2026", language="es") == "ITV vencida desde el 26/11/2026."
    common = {"deadline": "12/02/2027", "renewal": "14/03/2027", "language": "es"}
    assert (
        ar.insurance_text("cancel", days_to_cancel=15, company="Mutua Ejemplo", **common)
        == "Seguro: quedan 15 días para poder desistir (hasta el 12/02/2027). Renueva el 14/03/2027."
    )
    assert (
        ar.insurance_text("last_day", days_to_cancel=0, company="", **common)
        == "Seguro: hoy es el último día para avisar a tu aseguradora si no quieres renovar."
    )
    assert ar.insurance_text("renewed", days_to_cancel=0, company="x", **common) == (
        "Seguro renovado hoy. Próxima renovación: 14/03/2027."
    )
    assert "ITV" in ar.itv_text("overdue", days_left=-1, due_date="1/1", language="en")


def test_new_alert_types_start_enabled() -> None:
    """Quien configuró los avisos antes de existir ITV y seguro los recibe sin tocar nada."""
    old = ["charge_finished", "maintenance"]
    assert ar.enabled_types(old, None) == {"charge_finished", "maintenance", "itv", "insurance"}
    # Tras guardar con la lista nueva a la vista, manda lo que marque.
    assert ar.enabled_types(old, list(ar.ALERT_TYPES)) == set(old)
    assert ar.enabled_types(None, None) == set(ar.ALERT_TYPES)
    assert set(doc.INSURANCE_KINDS) == {
        "third_party",
        "third_party_plus",
        "comprehensive_excess",
        "comprehensive",
    }
