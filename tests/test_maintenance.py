"""Pruebas del mantenimiento periódico y de los avisos (lógica sin Home Assistant)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from custom_components.dec_deepal import alert_rules as ar
from custom_components.dec_deepal import maintenance as mt
from custom_components.dec_deepal.registries import load_all
from custom_components.dec_deepal.telemetry import signals as s

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "dec_deepal"


def _record(**changes) -> mt.MaintenanceRecord:  # noqa: ANN003
    values = {"services_done": 1, "last_date": date(2026, 3, 10), "last_km": 19500}
    return mt.MaintenanceRecord(**{**values, **changes})


# ---------------------------------------------------------------------------
# Cuánto falta
# ---------------------------------------------------------------------------


def test_add_months_clamps_short_months() -> None:
    assert mt.add_months(date(2026, 3, 10), 12) == date(2027, 3, 10)
    assert mt.add_months(date(2024, 2, 29), 12) == date(2025, 2, 28)
    assert mt.add_months(date(2026, 8, 31), 6) == date(2027, 2, 28)
    assert mt.add_months(date(2026, 11, 15), 3) == date(2027, 2, 15)


def test_status_counts_from_last_service() -> None:
    """Se cuenta desde la última revisión hecha, no desde un plan fijo."""
    current = mt.status(_record(), date(2026, 10, 9), 31000)
    assert current.number == 2
    assert current.due_date == date(2027, 3, 10)
    assert current.due_km == 39500
    assert current.days_left == 152
    assert current.km_left == 8500
    assert current.level == mt.LEVEL_OK and current.steps == frozenset()


def test_status_steps_and_levels() -> None:
    record = _record()
    # Quedan 47 días y 2.000 km: escalones de 2 meses, 3.000 y 2.000 km.
    soon = mt.status(record, date(2027, 1, 22), 37500)
    assert (soon.days_left, soon.km_left) == (47, 2000)
    assert soon.steps == {"d60", "k3000", "k2000"}
    assert soon.level == mt.LEVEL_SOON
    # Por kilómetros, aunque falte mucho tiempo.
    assert mt.status(record, date(2026, 6, 1), 39600).level == mt.LEVEL_OVERDUE
    # Por fecha, sin conocer el cuentakilómetros.
    late = mt.status(record, date(2027, 3, 22), None)
    assert late.km_left is None and late.days_left == -12
    assert late.level == mt.LEVEL_OVERDUE and mt.STEP_OVERDUE in late.steps


def test_each_step_is_notified_once() -> None:
    record = _record()
    first = mt.status(record, date(2027, 1, 9), 30000)  # quedan 60 días
    assert mt.pending_notice(record, first) == "remaining"
    mt.mark_notified(record, first)
    assert mt.pending_notice(record, mt.status(record, date(2027, 1, 20), 30000)) is None
    second = mt.status(record, date(2027, 2, 8), 30000)  # queda 1 mes
    assert mt.pending_notice(record, second) == "remaining"
    mt.mark_notified(record, second)
    overdue = mt.status(record, date(2027, 3, 11), 30000)
    assert mt.pending_notice(record, overdue) == "overdue"
    mt.mark_notified(record, overdue)
    assert mt.pending_notice(record, mt.status(record, date(2027, 4, 1), 45000)) is None


def test_late_setup_sends_a_single_notice() -> None:
    """Configurado cuando ya se cumplen varios escalones: un solo aviso."""
    record = _record()
    current = mt.status(record, date(2027, 2, 25), 38800)
    assert current.steps == {"d60", "d30", "d15", "k3000", "k2000", "k1000"}
    assert mt.pending_notice(record, current) == "remaining"
    mt.mark_notified(record, current)
    assert mt.pending_notice(record, current) is None


def test_register_service_restarts_the_count() -> None:
    record = _record(notified={"d60", "k3000"})
    mt.register_service(record, date(2027, 2, 20), 39850)
    assert record.services_done == 2 and record.notified == set()
    assert record.history == [{"number": 2, "date": "2027-02-20", "km": 39850}]
    current = mt.status(record, date(2027, 2, 20), 39850)
    assert current.number == 3 and current.due_km == 59850
    assert current.due_date == date(2028, 2, 20)
    assert mt.MaintenanceRecord.from_dict(record.to_dict()) == record


# ---------------------------------------------------------------------------
# Plan del S05 (manual de usuario)
# ---------------------------------------------------------------------------


def test_s05_plan_from_the_manual() -> None:
    plan = load_all(INTEGRATION).vehicles.get("s05_2024").maintenance
    assert (plan.interval_km, plan.interval_months) == (20000, 12)

    def has(number: int, trim: str, text: str) -> bool:
        return any(text in name for name in plan.operations_for(number, trim))

    # En todas las revisiones.
    assert all(has(number, "max", "Neumáticos") for number in range(1, 11))
    # Líquido de frenos: cada 2 años → 2.ª, 4.ª... (también la 8.ª, a los 160.000 km).
    assert [n for n in range(1, 11) if has(n, "max", "líquido de frenos")] == [2, 4, 6, 8, 10]
    # Refrigerante: cada 3 años.
    assert [n for n in range(1, 11) if has(n, "max", "refrigerante")] == [3, 6, 9]
    # Reductor trasero: cada 5 años. El delantero, solo en el AWD.
    assert [n for n in range(1, 11) if has(n, "pro", "reductor trasero")] == [5, 10]
    assert [n for n in range(1, 11) if has(n, "max_awd", "reductor delantero")] == [3, 6, 9]
    assert not any(has(n, "max", "reductor delantero") for n in range(1, 11))
    # Un coche sin plan (genérico) usa el intervalo habitual, sin operaciones.
    generic = load_all(INTEGRATION).vehicles.generic.maintenance
    assert generic.operations == () and generic.interval_km == 20000


# ---------------------------------------------------------------------------
# Avisos
# ---------------------------------------------------------------------------


def test_charge_events() -> None:
    idle = {s.CHARGING: False, s.BATTERY_LEVEL: 45}
    charging = {s.CHARGING: True, s.BATTERY_LEVEL: 46, s.REMAINING_CHARGE_MIN: 180}
    assert ar.charge_event(idle, charging) == ar.ALERT_CHARGE_STARTED
    # Al arrancar (sin lectura anterior) o sin dato, no se avisa.
    assert ar.charge_event(None, charging) is None
    assert ar.charge_event({s.CHARGING: None}, charging) is None
    assert ar.charge_event(charging, charging) is None
    # Se para a media carga → interrumpida.
    assert ar.charge_event(charging, {s.CHARGING: False, s.BATTERY_LEVEL: 63}) == ar.ALERT_CHARGE_INTERRUPTED
    # Se para con la batería llena, o cuando quedaban pocos minutos → terminada.
    assert ar.charge_event(charging, {s.CHARGING: False, s.BATTERY_LEVEL: 100}) == ar.ALERT_CHARGE_FINISHED
    ending = {s.CHARGING: True, s.BATTERY_LEVEL: 79, s.REMAINING_CHARGE_MIN: 4}
    assert ar.charge_event(ending, {s.CHARGING: False, s.BATTERY_LEVEL: 80}) == ar.ALERT_CHARGE_FINISHED


def test_problems_are_notified_once_until_they_clear() -> None:
    active: set[str] = set()
    assert ar.new_problems({s.WARNING_ABS: False}, active) == []
    assert ar.new_problems({s.WARNING_ABS: True, s.TIRE_ALARM_FRONT_LEFT: True}, active) == [
        s.WARNING_ABS,
        s.TIRE_ALARM_FRONT_LEFT,
    ]
    # Sigue encendido, o el coche no manda el dato: no se repite.
    assert ar.new_problems({s.WARNING_ABS: True}, active) == []
    assert ar.new_problems({s.WARNING_ABS: None}, active) == []
    # Se apaga y vuelve a encenderse: aviso nuevo.
    assert ar.new_problems({s.WARNING_ABS: False}, active) == []
    assert ar.new_problems({s.WARNING_ABS: True}, active) == [s.WARNING_ABS]
    assert ar.PROBLEM_SIGNALS[s.WARNING_TPMS] == ar.ALERT_TIRES
    # El airbag se enciende solo al despertar el coche: no avisa.
    assert s.WARNING_AIRBAG not in ar.PROBLEM_SIGNALS
    assert ar.new_problems({s.WARNING_AIRBAG: True}, set()) == []
    assert ar.PROBLEM_SIGNALS[s.KEY_BATTERY_LOW] == ar.ALERT_KEY_BATTERY


def test_every_problem_signal_has_a_named_entity() -> None:
    """El nombre del testigo en el aviso sale del sensor binario de la misma clave."""
    import json

    names = json.loads((INTEGRATION / "translations" / "es.json").read_text(encoding="utf-8"))
    binary = names["entity"]["binary_sensor"]
    assert [signal for signal in ar.PROBLEM_SIGNALS if signal not in binary] == []
    options = names["selector"]["alert_type"]["options"]
    assert set(options) == set(ar.ALERT_TYPES)


def test_texts() -> None:
    kwargs = {"number": 2, "due_date": "10/03/2027", "due_km": 39500}
    assert (
        ar.maintenance_text("remaining", days_left=47, km_left=2000, language="es", **kwargs)
        == "Quedan 2.000 km o 47 días para la 2ª revisión."
    )
    assert (
        ar.maintenance_text("remaining", days_left=15, km_left=None, language="es", **kwargs)
        == "Quedan 15 días para la 2ª revisión."
    )
    assert (
        ar.maintenance_text("overdue", days_left=-3, km_left=-120, language="es", **kwargs)
        == "Mantenimiento vencido: la 2ª revisión tocaba el 10/03/2027 o a los 39.500 km."
    )
    assert (
        ar.maintenance_text("remaining", days_left=47, km_left=2000, language="en-GB", **kwargs)
        == "2,000 km or 47 days left until the 2nd service."
    )
    assert ar.charge_text(ar.ALERT_CHARGE_FINISHED, 80.4, "es") == "Carga terminada (batería al 80 %)."
    assert ar.charge_text(ar.ALERT_CHARGE_STARTED, None, "es") == "Carga iniciada."
    assert (
        ar.problem_text(ar.ALERT_WARNINGS, ["Testigo ABS", "Testigo frenos"], "es")
        == "Testigo encendido: Testigo ABS y Testigo frenos."
    )
    assert "CR2032" in ar.problem_text(ar.ALERT_KEY_BATTERY, [], "es")
    assert [ar.ordinal(n, "en") for n in (1, 2, 3, 4, 11, 21)] == ["1st", "2nd", "3rd", "4th", "11th", "21st"]
