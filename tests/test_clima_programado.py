"""2.6.0b17: climatización programada con protección de batería (climate_schedule.py)."""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.dec_deepal import climate_schedule as cs
from custom_components.dec_deepal.alert_rules import ALERT_CLIMATE_SCHEDULE
from custom_components.dec_deepal.api.commands import DeepalCommands
from custom_components.dec_deepal.telemetry import signals as s
from custom_components.dec_deepal.telemetry.state import VehicleState

from .test_plan_carga import _setup, server  # noqa: F401 - fixture


def test_from_dict_cleans_what_is_stored() -> None:
    schedule = cs.ClimateSchedule.from_dict({"enabled": 1, "time": "7:5", "days": "x", "temperature": 40, "min_battery": 95})
    assert schedule == cs.ClimateSchedule(enabled=True, time="07:05", days=cs.DAYS_WEEKDAYS, temperature=32.0, min_battery=80)
    assert cs.ClimateSchedule.from_dict("roto") == cs.ClimateSchedule()


def test_days() -> None:
    monday, saturday = date(2027, 1, 25), date(2027, 1, 30)
    assert cs.ClimateSchedule(days=cs.DAYS_WEEKDAYS).is_day(monday)
    assert not cs.ClimateSchedule(days=cs.DAYS_WEEKDAYS).is_day(saturday)
    assert cs.ClimateSchedule(days=cs.DAYS_WEEKENDS).is_day(saturday)
    assert cs.ClimateSchedule(days=cs.DAYS_DAILY).is_day(monday)


def test_battery_protection() -> None:
    schedule = cs.ClimateSchedule(min_battery=30)
    parked = {s.POWER_STATUS: 0}

    def decide(**values: object) -> str | None:
        return cs.decide(schedule, VehicleState(values={**parked, **values}, sources={}))

    assert decide(battery_level=55) is None
    assert decide(battery_level=20) == cs.RESULT_LOW_BATTERY
    assert decide() == cs.RESULT_LOW_BATTERY  # sin saber la batería, no se arriesga
    # Enchufado, sí (la carga lo cubre).
    assert decide(battery_level=20, charge_state=1) is None
    assert decide(battery_level=55, power_status=2) == cs.RESULT_POWER_ON
    assert cs.decide(cs.ClimateSchedule(min_battery=0), VehicleState(values=parked, sources={})) is None


async def test_runs_once_at_its_time(hass: HomeAssistant, hass_storage: dict, freezer) -> None:  # noqa: ANN001
    await hass.config.async_set_time_zone("Europe/Madrid")
    freezer.move_to("2027-01-25 07:29:00+01:00")  # lunes
    hass.config.language = "es"
    values = {s.POWER_STATUS: 0, s.BATTERY_LEVEL: 60}
    runner = SimpleNamespace(run=AsyncMock(), commands=SimpleNamespace(air_conditioner=AsyncMock(return_value="c")))
    vehicle = SimpleNamespace(
        info=SimpleNamespace(vehicle_id="car1", display_name="Changote"),
        coordinator=SimpleNamespace(data=VehicleState(values=values, sources={})),
        runner=runner,
    )
    alerts = MagicMock()
    manager = cs.ClimateScheduleManager(hass, {"car1": vehicle}, alerts)
    await manager.async_load()
    await manager.async_update("car1", enabled=True, time="07:30", temperature=21.5)
    manager.async_start()

    for _ in range(3):  # 07:30, 07:31 y 07:32: solo salta una vez
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    runner.run.assert_awaited_once()
    assert runner.run.await_args.kwargs["optimistic"] == {s.CLIMATE_ON: True, s.CLIMATE_TARGET_C: 21.5}
    alerts.notify.assert_called_once_with("car1", ALERT_CLIMATE_SCHEDULE, "Climatización programada encendida a 21.5 °C.")
    assert manager.get("car1").last_run == "2027-01-25"

    # Batería baja: no se enciende y se dice por qué.
    vehicle.coordinator.data = VehicleState(values={**values, s.BATTERY_LEVEL: 12}, sources={})
    assert await manager.async_run("car1") == cs.RESULT_LOW_BATTERY
    assert "12 %" in alerts.notify.call_args.args[2] and runner.run.await_count == 1
    # El coche no acepta la orden.
    vehicle.coordinator.data = VehicleState(values=values, sources={})
    runner.run.side_effect = HomeAssistantError("no")
    assert await manager.async_run("car1") == cs.RESULT_FAILED
    manager.async_stop()
    await hass.async_block_till_done()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_schedule_entities(hass: HomeAssistant, server: dict) -> None:  # noqa: F811
    await _setup(hass)
    registry = er.async_get(hass)
    ids = {
        e.translation_key: e.entity_id
        for e in registry.entities.values()
        if e.platform == "dec_deepal" and (e.translation_key or "").startswith("climate_schedule")
    }
    assert set(ids) == {
        "climate_schedule", "climate_schedule_time", "climate_schedule_days",
        "climate_schedule_temperature", "climate_schedule_min_battery",
    }  # fmt: skip
    assert hass.states.get(ids["climate_schedule"]).state == "off"
    assert hass.states.get(ids["climate_schedule_days"]).state == "weekdays"

    await hass.services.async_call("switch", "turn_on", {"entity_id": ids["climate_schedule"]}, blocking=True)
    await hass.services.async_call(
        "time", "set_value", {"entity_id": ids["climate_schedule_time"], "time": "06:45:00"}, blocking=True
    )
    await hass.services.async_call(
        "select", "select_option", {"entity_id": ids["climate_schedule_days"], "option": "daily"}, blocking=True
    )
    await hass.services.async_call(
        "number", "set_value", {"entity_id": ids["climate_schedule_temperature"], "value": 23}, blocking=True
    )
    await hass.services.async_call(
        "number", "set_value", {"entity_id": ids["climate_schedule_min_battery"], "value": 40}, blocking=True
    )
    assert hass.states.get(ids["climate_schedule"]).state == "on"
    assert hass.states.get(ids["climate_schedule_time"]).state == "06:45:00"
    assert hass.states.get(ids["climate_schedule_days"]).state == "daily"
    assert float(hass.states.get(ids["climate_schedule_temperature"]).state) == 23
    assert float(hass.states.get(ids["climate_schedule_min_battery"]).state) == 40
    # Cambiar la programación no manda nada al coche.
    assert not any("air" in str(call.args[0]) for call in DeepalCommands.send.await_args_list)
