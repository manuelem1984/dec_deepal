"""2.6.0b17: «Carga en vivo» y «Coche abierto o sin bloquear» (alerts/vivo.py)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed, async_mock_service

from custom_components.dec_deepal.alert_rules import TARGET_PANEL
from custom_components.dec_deepal.alerts import AlertManager
from custom_components.dec_deepal.alerts.vivo import open_parts
from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.const import OPT_ALERTS
from custom_components.dec_deepal.registries import load_all
from custom_components.dec_deepal.telemetry import signals as s

from .test_alert_manager import FakeCoordinator

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "dec_deepal"
PHONE = "mobile_app_test"
OPTIONS = {
    OPT_ALERTS: {
        "vehicles": {
            "car1": {
                "notices": {"charge_live": [PHONE, TARGET_PANEL], "left_open": [PHONE]},
                "thresholds": {"left_open": 15},
            }
        }
    }
}
PARKED = {s.POWER_STATUS: 0, s.LOCKED_DRIVER: True, s.LOCKED_PASSENGER: True}


def _vehicle(coordinator: FakeCoordinator, *, pin: str | None = "1234") -> SimpleNamespace:
    model = load_all(INTEGRATION).vehicles.get("s05_2024")
    runner = SimpleNamespace(run=AsyncMock(), commands=SimpleNamespace(control_pin=pin, doors=AsyncMock(return_value="c1")))
    return SimpleNamespace(
        info=VehicleInfo(vehicle_id="car1", nickname="Changote"),
        coordinator=coordinator,
        model=model,
        trim="max",
        runner=runner,
        has=lambda feature: model.has(feature, "max"),
    )


class Coordinator(FakeCoordinator):
    """Con las señales calculadas (bloqueado, encendido...), como el de verdad."""

    def push(self, values: dict[str, Any]) -> None:
        from custom_components.dec_deepal.telemetry.state import VehicleState

        state = VehicleState(values=dict(values), sources={})
        self.data = state
        for listener in list(self._listeners):
            listener()


async def _manager(hass: HomeAssistant, coordinator: FakeCoordinator, **kwargs: Any) -> AlertManager:
    hass.config.language = "es"
    manager = AlertManager(hass, "entry1", OPTIONS, {"car1": _vehicle(coordinator, **kwargs)})
    await manager.async_load()
    manager.async_start()
    await hass.async_block_till_done()
    return manager


def test_open_parts_only_with_the_car_off() -> None:
    off = {s.POWER_ON: False, s.CENTRAL_LOCKED: False, s.TRUNK_OPEN: True, s.WINDOW_REAR_LEFT: True}
    assert open_parts(off) == ["left_open_unlocked", "left_open_windows", "left_open_trunk"]
    assert open_parts({**off, s.POWER_ON: True}) == []  # en marcha, normal
    assert open_parts({s.CENTRAL_LOCKED: False}) == []  # sin saber si está encendido


@pytest.mark.usefixtures("enable_custom_integrations", "hass_storage")
async def test_live_charging_updates_and_clears(hass: HomeAssistant, freezer) -> None:  # noqa: ANN001
    freezer.move_to("2027-01-22 20:00:00+00:00")
    calls = async_mock_service(hass, "notify", PHONE)
    coordinator = Coordinator({})
    manager = await _manager(hass, coordinator)

    coordinator.push({**PARKED, s.CHARGING: True, s.BATTERY_LEVEL: 56, s.REMAINING_CHARGE_MIN: 100})
    await hass.async_block_till_done()
    live = [call for call in calls if call.data.get("data", {}).get("tag") == "dec_deepal_charge_live_car1"]
    assert len(live) == 1
    data = live[0].data["data"]
    assert live[0].data["message"].startswith("Cargando: 56 % · termina hacia las ")
    assert data["progress"] == 56 and data["progress_max"] == 100 and data["live_update"] is True
    assert data["when"] == int((dt_util.now() + timedelta(minutes=100)).timestamp())
    assert "priority" not in data and "critical" not in str(data)  # nunca crítica

    # La misma lectura no se repite; una nueva la actualiza (misma tag).
    coordinator.push({**PARKED, s.CHARGING: True, s.BATTERY_LEVEL: 56, s.REMAINING_CHARGE_MIN: 100})
    coordinator.push({**PARKED, s.CHARGING: True, s.BATTERY_LEVEL: 60, s.REMAINING_CHARGE_MIN: 80})
    await hass.async_block_till_done()
    live = [call for call in calls if call.data.get("data", {}).get("tag") == "dec_deepal_charge_live_car1"]
    assert [call.data["data"].get("progress") for call in live] == [56, 60]

    # Al acabar, se quita.
    coordinator.push({**PARKED, s.CHARGING: False, s.BATTERY_LEVEL: 80})
    await hass.async_block_till_done()
    assert calls[-1].data["message"] == "clear_notification"
    assert calls[-1].data["data"] == {"tag": "dec_deepal_charge_live_car1"}
    await manager.async_stop()


@pytest.mark.usefixtures("enable_custom_integrations", "hass_storage")
async def test_left_open_once_with_lock_button(hass: HomeAssistant, freezer) -> None:  # noqa: ANN001
    freezer.move_to("2027-01-22 20:00:00+00:00")
    calls = async_mock_service(hass, "notify", PHONE)
    coordinator = Coordinator({})
    manager = await _manager(hass, coordinator)
    runner = manager._vehicles["car1"].runner

    # Apagado y sin bloquear: aún no (15 min en el panel)...
    open_car = {**PARKED, s.LOCKED_DRIVER: False, s.TRUNK_OPEN: True}
    coordinator.push(open_car)
    await hass.async_block_till_done()
    assert calls == []
    # ...y al cumplirse, sin esperar a otra lectura: una vez, con el botón Bloquear.
    freezer.tick(timedelta(minutes=15, seconds=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert len(calls) == 1
    assert calls[0].data["message"] == "Apagado desde hace 15 min: sin bloquear y maletero abierto."
    assert calls[0].data["data"]["actions"] == [{"action": "DEC_DEEPAL_LOCK|car1", "title": "Bloquear"}]
    coordinator.push(open_car)
    await hass.async_block_till_done()
    assert len(calls) == 1

    # El botón bloquea (solo bloquear) y confirma.
    hass.bus.async_fire("mobile_app_notification_action", {"action": "DEC_DEEPAL_LOCK|car1"})
    await hass.async_block_till_done()
    runner.run.assert_awaited_once()
    assert runner.run.await_args.kwargs["optimistic"] == {s.LOCKED_DRIVER: True, s.LOCKED_PASSENGER: True}
    assert calls[-1].data["message"] == "Coche bloqueado."
    # Otro botón (de otro coche o de otra cosa) no hace nada.
    hass.bus.async_fire("mobile_app_notification_action", {"action": "DEC_DEEPAL_LOCK|car9"})
    await hass.async_block_till_done()
    assert runner.run.await_count == 1

    # Si falla, se dice por qué.
    runner.run.side_effect = HomeAssistantError("Primero desbloquea")
    hass.bus.async_fire("mobile_app_notification_action", {"action": "DEC_DEEPAL_LOCK|car1"})
    await hass.async_block_till_done()
    assert calls[-1].data["message"] == "No se pudo bloquear: Primero desbloquea"

    # Cerrado todo, vuelve a vigilar desde cero.
    coordinator.push(PARKED)
    coordinator.push(open_car)
    await hass.async_block_till_done()
    count = len(calls)
    freezer.tick(timedelta(minutes=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert len(calls) == count + 1
    await manager.async_stop()


@pytest.mark.usefixtures("enable_custom_integrations", "hass_storage")
async def test_left_open_without_pin_has_no_button(hass: HomeAssistant, freezer) -> None:  # noqa: ANN001
    freezer.move_to("2027-01-22 20:00:00+00:00")
    calls = async_mock_service(hass, "notify", PHONE)
    coordinator = Coordinator({})
    manager = await _manager(hass, coordinator, pin=None)
    coordinator.push({**PARKED, s.LOCKED_DRIVER: False})
    freezer.tick(timedelta(minutes=20))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert len(calls) == 1 and "actions" not in calls[0].data["data"]
    await manager.async_stop()
