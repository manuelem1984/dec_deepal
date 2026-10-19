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
    country = load_all(integration).countries.get("es")
    # El módulo de ITV solo se ofrece en los países que lo tienen dado de alta.
    assert country.itv is True
    spain = country.rules
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
    assert (current.days_left, current.level, current.steps) == (47, LEVEL_SOON, {"t1"})
    assert doc.itv_pending_notice(record, current) == "remaining"
    record.notified |= current.steps
    assert doc.itv_pending_notice(record, doc.itv_status(record, date(2026, 10, 20))) is None
    for day, steps in ((date(2026, 10, 27), {"t1", "t2"}), (date(2026, 11, 11), {"t1", "t2", "t3"})):
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
    assert soon.level == LEVEL_SOON and soon.steps == {"c1"}
    last = doc.insurance_status(record, date(2027, 2, 12))
    assert last.days_to_cancel == 0 and last.level == LEVEL_OVERDUE
    assert doc.STEP_LAST_DAY in last.steps
    # Pasado el plazo ya no hay nada que hacer: sin testigo hasta la renovación.
    late = doc.insurance_status(record, date(2027, 2, 20))
    assert late.level == LEVEL_OK and late.days_to_cancel == -8
    # Lo único que queda son los avisos de renovación (22 días: el de 30 ya ha saltado),
    # que no encienden el testigo.
    assert late.steps == {"r1"} and late.days_to_renewal == 22
    assert doc.insurance_status(record, date(2027, 3, 1)).steps == {"r1", "r2"}
    # Con los plazos de un coche que los ha cambiado.
    custom = doc.insurance_status(record, date(2027, 1, 3), cancel_steps=(45, 10), renewal_steps=(20, 5))
    assert custom.steps == {"c1"} and custom.level == LEVEL_SOON
    # Lo guardado antes de la 2.5.0 (escalones con el valor en el nombre) se sigue leyendo.
    old = doc.InsuranceRecord.from_dict({"renewal_date": "2027-03-14", "notified": ["c30", "c15"]})
    assert old.notified == {"c1", "c2"}
    assert doc.ItvRecord.from_dict({"registration_date": "2022-01-01", "notified": ["d60", "overdue"]}).notified == {"t1", "overdue"}


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


def test_who_gets_each_alert() -> None:
    """Cada coche reparte sus avisos en cuatro grupos, cada uno con sus destinos."""
    me, her = "mobile_app_manuel", "mobile_app_ella"
    config = {
        "vehicles": {
            "changote": {
                "car": [me],
                "car_types": ["charge_finished", "warnings"],
                "car_known": list(ar.CAR_ALERT_TYPES),
                "maintenance": [me],
                "itv": [me],
                "insurance": [me, her],
            },
            # El coche de ella: sus avisos son suyos; los papeles, de él.
            "changuito": {
                "car": [her],
                "car_types": list(ar.CAR_ALERT_TYPES),
                "car_known": list(ar.CAR_ALERT_TYPES),
                "maintenance": [me],
                "itv": [me],
                "insurance": [],
            },
        }
    }
    mine, hers = ar.route_for(config, "changote"), ar.route_for(config, "changuito")
    assert mine.targets_for(ar.ALERT_CHARGE_FINISHED) == (me,)
    assert mine.targets_for(ar.ALERT_CHARGE_STARTED) == ()  # ese aviso está desactivado
    assert mine.targets_for(ar.ALERT_INSURANCE) == (me, her)
    assert hers.targets_for(ar.ALERT_CHARGE_STARTED) == (her,)
    assert hers.targets_for(ar.ALERT_ITV) == (me,) and hers.targets_for(ar.ALERT_MAINTENANCE) == (me,)
    assert hers.targets_for(ar.ALERT_INSURANCE) == ()  # grupo sin destinos: no avisa
    # Un coche que no está en la lista, o una cuenta sin avisos: nada.
    assert ar.route_for(config, "otro") == ar.NO_ROUTE and ar.route_for(None, "x") == ar.NO_ROUTE
    # Lo que se guarda es lo que se lee.
    assert ar.route_for({"vehicles": {"c": mine.to_dict()}}, "c") == mine
    # Un tipo de aviso que no existía al guardar nace activado.
    old = {"vehicles": {"c": {"car": [me], "car_types": ["warnings"], "car_known": ["warnings", "tires"]}}}
    assert ar.ALERT_CHARGE_STARTED in ar.route_for(old, "c").car_types
    assert ar.ALERT_TIRES not in ar.route_for(old, "c").car_types


def test_alerts_configured_before_2_4_keep_working() -> None:
    """Formato anterior (una lista para toda la cuenta): todos los coches avisan igual que antes."""
    old = {
        "targets": ["mobile_app_manuel"],
        "types": ["charge_finished", "maintenance", "itv"],
        "known_types": list(ar.ALERT_TYPES),
        "persistent": True,
    }
    route = ar.route_for(old, "cualquiera")
    everyone = ("mobile_app_manuel", ar.TARGET_PANEL)  # el panel pasa a ser un destino más
    assert route.targets_for(ar.ALERT_CHARGE_FINISHED) == everyone
    assert route.targets_for(ar.ALERT_CHARGE_STARTED) == ()
    assert route.targets_for(ar.ALERT_MAINTENANCE) == everyone
    assert route.targets_for(ar.ALERT_ITV) == everyone
    assert route.targets_for(ar.ALERT_INSURANCE) == ()
    assert ar.panel_name("es") == "Notificaciones de Home Assistant"
    # Los avisos nuevos (renovación del seguro) nacen sin destinos: antes no los recibía nadie.
    old["types"] = list(ar.ALERT_TYPES)
    route = ar.route_for(old, "c")
    assert route.targets_for("insurance_c1") == everyone and route.targets_for("insurance_renewed") == everyone
    assert route.targets_for("insurance_r1") == () and route.targets_for("insurance_r2") == ()


def test_each_notice_has_its_own_targets_and_thresholds() -> None:
    """Formato de la 2.5.0 (panel): destinos aviso a aviso y plazos por coche."""
    me, bell = "mobile_app_manuel", ar.TARGET_PANEL
    stored = {
        "notices": {"charge_finished": [me], "maintenance_t3": [me, bell], "maintenance_k2": [me], "insurance_r1": [me]},
        "thresholds": {"maintenance_t1": 90, "maintenance_k1": 4000, "bogus": 3},
    }
    route = ar.route_for({"vehicles": {"c": stored}}, "c")
    assert route.targets_for("charge_finished") == (me,) and route.targets_for("charge_started") == ()
    assert route.targets_for("maintenance_t3") == (me, bell) and route.targets_for("maintenance_t1") == ()
    # Un apartado entero: los destinos de cualquiera de sus avisos.
    assert route.targets_for(ar.ALERT_MAINTENANCE) == (me, bell) and route.targets_for(ar.ALERT_ITV) == ()
    assert route.car_types == {"charge_finished"}
    # Plazos: los cambiados y, para el resto, los de fábrica.
    assert route.steps("maintenance", "t") == (90, 30, 15)
    assert route.steps("maintenance", "k") == (4000, 2500, 1000)
    assert route.steps("itv", "t") == (60, 30, 15)
    assert route.steps("insurance", "c") == (30, 15) and route.steps("insurance", "r") == (30, 15)
    assert route.thresholds == {"maintenance_t1": 90, "maintenance_k1": 4000}
    assert ar.route_for({"vehicles": {"c": route.to_dict()}}, "c") == route
    assert len(ar.NOTICES) == 30 and [n.id for n in ar.NOTICES if n.opt_in] == ["insurance_r1", "insurance_r2"]
    # Los del cargador (2.6.0b1) nacen sin destinos: el cargador usa los de carga.
    assert [n.id for n in ar.NOTICES if n.section == "charger"] == [
        "charger_confirm", "charger_unlocked", "charger_not_charging", "charger_finished", "charger_locked", "charger_limit", "charger_full",
    ]

    # El apartado clásico de Configurar (por grupos) pisa los destinos del grupo
    # y respeta lo que no sabe tocar: plazos y avisos nuevos.
    coarse = ar.Route.from_groups({"car": [bell], "maintenance": [me]}, ["tires"], base=route)
    assert coarse.targets_for("tires") == (bell,) and coarse.targets_for("charge_finished") == ()
    assert coarse.targets_for("maintenance_t1") == (me,) and coarse.targets_for("maintenance_overdue") == (me,)
    assert coarse.targets_for("insurance_r1") == (me,) and coarse.targets_for("insurance_c1") == ()
    assert coarse.thresholds == route.thresholds


def test_thresholds_are_validated() -> None:
    assert ar.clean_thresholds(None) == {} and ar.clean_thresholds({"itv_t1": 60}) == {}
    assert ar.clean_thresholds({"itv_t1": 45.0, "maintenance_k3": 500}) == {"itv_t1": 45, "maintenance_k3": 500}
    for bad, code, notice in (
        ({"itv_t1": 0}, ar.ERROR_THRESHOLD_RANGE, "itv_t1"),
        ({"itv_t1": 400}, ar.ERROR_THRESHOLD_RANGE, "itv_t1"),
        ({"maintenance_k1": "5000"}, ar.ERROR_THRESHOLD_RANGE, "maintenance_k1"),
        ({"maintenance_k1": 50}, ar.ERROR_THRESHOLD_RANGE, "maintenance_k1"),
        # El aviso 1 tiene que saltar antes que el 2, y el 2 antes que el 3.
        ({"itv_t1": 20}, ar.ERROR_THRESHOLD_ORDER, "itv_t2"),
        ({"maintenance_k2": 1000}, ar.ERROR_THRESHOLD_ORDER, "maintenance_k3"),
        ({"insurance_r2": 30}, ar.ERROR_THRESHOLD_ORDER, "insurance_r2"),
    ):
        try:
            ar.clean_thresholds(bad)
        except ar.ThresholdError as err:
            assert (err.code, err.notice) == (code, notice), bad
        else:
            raise AssertionError(bad)
    # Unos plazos guardados que ya no valen no rompen nada: se usan los de fábrica.
    broken = ar.route_for({"vehicles": {"c": {"notices": {}, "thresholds": {"itv_t1": 5}}}}, "c")
    assert broken.thresholds == {} and broken.steps("itv", "t") == (60, 30, 15)
    assert set(doc.INSURANCE_KINDS) == {
        "third_party",
        "third_party_plus",
        "comprehensive_excess",
        "comprehensive",
    }
