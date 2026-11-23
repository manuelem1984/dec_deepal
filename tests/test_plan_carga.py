"""Plan de carga (carga programada): lectura del REST, reglas del coche y órdenes."""

from __future__ import annotations

import time
from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dec_deepal.api import endpoints
from custom_components.dec_deepal.api.client import DeepalClient
from custom_components.dec_deepal.api.commands import DeepalCommands
from custom_components.dec_deepal.api.models import CommandResult, CommandStatus
from custom_components.dec_deepal.api.mqtt.client import MqttReading
from custom_components.dec_deepal.api.session import DeepalSession
from custom_components.dec_deepal.charge_plan_control import gmt_offset
from custom_components.dec_deepal.const import DOMAIN
from custom_components.dec_deepal.telemetry import charge_plan as cp
from custom_components.dec_deepal.telemetry import signals as s
from custom_components.dec_deepal.telemetry.rest_map import map_rest
from custom_components.dec_deepal.telemetry.state import build_state

from .test_setup_platforms import PARAMS, VEHICLE

ACTIVE = {"planId": "57", "startTime": "0130", "endTime": "0700", "isValid": 1, "timeZone": "GMT+01:00"}
OLD = {"planId": "41", "startTime": "2300", "endTime": "0600", "isValid": 0}


# --- Lectura ---------------------------------------------------------------------------------------


def test_signals_from_the_plan_list() -> None:
    values = map_rest({"charge": {"chargePlanList": [OLD, ACTIVE]}})
    assert values[s.CHARGE_PLAN_ON] is True
    assert values[s.CHARGE_PLAN_START] == "01:30"  # el activo, aunque no sea el primero
    assert values[s.CHARGE_PLAN_END] == "07:00"
    assert values[s.CHARGE_PLAN_UNTIL_FULL] is False
    # «Hasta llenar»: sin hora de fin.
    full = map_rest({"charge": {"chargePlanList": [{"planId": "9", "startTime": "0200", "isValid": 1}]}})
    assert full[s.CHARGE_PLAN_UNTIL_FULL] is True and s.CHARGE_PLAN_END not in full
    # Sin planes activos: apagado. Sin lista en el informe: nada (se conserva lo último).
    assert map_rest({"charge": {"chargePlanList": [OLD]}})[s.CHARGE_PLAN_ON] is False
    assert map_rest({"charge": {"chargePlanList": []}})[s.CHARGE_PLAN_ON] is False
    assert s.CHARGE_PLAN_ON not in map_rest({"charge": {}})


def test_times_kept_after_the_plan_is_deleted() -> None:
    on = build_state(mqtt_params=None, rest_raw={"charge": {"chargePlanList": [ACTIVE]}}, previous=None)
    off = build_state(mqtt_params=None, rest_raw={"charge": {"chargePlanList": []}}, previous=on)
    assert off.get(s.CHARGE_PLAN_ON) is False
    assert off.get(s.CHARGE_PLAN_START) == "01:30" and off.get(s.CHARGE_PLAN_END) == "07:00"


def test_clock_conversions() -> None:
    assert cp.hhmm_to_clock("0130") == "01:30"
    assert cp.hhmm_to_clock(930) is None  # sin el cero: no es el formato del coche
    assert cp.hhmm_to_clock("2460") is None
    assert cp.clock_to_hhmm("07:05:00") == "0705"
    assert cp.minutes_between("23:30", "00:15") == 45  # pasa la medianoche


# --- Qué órdenes mandar ----------------------------------------------------------------------------


def test_plan_change_replaces_and_switches_off() -> None:
    change = cp.plan_change([OLD, ACTIVE], enabled=True, start="02:00", end="06:00", phev=False)
    assert change.delete == ("57",) and change.add == ("0200", "0600")
    full = cp.plan_change([], enabled=True, start="02:00", end=None, phev=False)
    assert full.delete == () and full.add == ("0200", None)
    off = cp.plan_change([OLD, ACTIVE], enabled=False, start=None, end=None, phev=False)
    assert off.delete == ("57",) and off.add is None


def test_plan_change_refuses_what_the_car_rejects() -> None:
    app_plan = {**ACTIVE, "planId": cp.APP_PLAN_ID}
    with pytest.raises(cp.PlanError) as caught:
        cp.plan_change([app_plan], enabled=False, start=None, end=None, phev=True)
    assert caught.value.key == "charge_plan_set_in_app"
    # En el EV el id "1" es un plan más.
    assert cp.plan_change([app_plan], enabled=False, start=None, end=None, phev=False).delete == ("1",)
    with pytest.raises(cp.PlanError) as caught:
        cp.plan_change([], enabled=True, start="01:00", end="01:20", phev=False)
    assert caught.value.key == "charge_plan_too_short"
    assert caught.value.placeholders == {"start": "01:00", "end": "01:20"}
    with pytest.raises(cp.PlanError) as caught:
        cp.plan_change([], enabled=True, start=None, end="05:00", phev=False)
    assert caught.value.key == "charge_plan_no_start"


async def test_gmt_offset(hass: HomeAssistant) -> None:
    await hass.config.async_set_time_zone("Europe/Madrid")
    assert gmt_offset(hass) in ("GMT+01:00", "GMT+02:00")
    await hass.config.async_set_time_zone("America/Santiago")
    assert gmt_offset(hass).startswith("GMT-0")


# --- Desde Home Assistant --------------------------------------------------------------------------


@pytest.fixture
def server() -> Iterator[dict]:
    """El servidor falso; ``state["plans"]`` es la lista de planes que devuelve el REST."""
    state: dict = {"plans": [ACTIVE]}

    async def get_condition(_self: DeepalClient, _vehicle_id: str) -> dict:
        return {"charge": {"chargePlanList": list(state["plans"])}}

    params = {**PARAMS, "lastUpdatedTime": int(time.time() * 1000)}
    with (
        patch.object(DeepalClient, "get_vehicles", AsyncMock(return_value=[VEHICLE])),
        patch.object(DeepalClient, "get_capabilities", AsyncMock(return_value=None)),
        patch.object(DeepalClient, "read_mqtt", AsyncMock(return_value=MqttReading(params=params, model_code="SC6464AAKBEV"))),
        patch.object(DeepalClient, "get_condition", get_condition),
        patch("custom_components.dec_deepal.async_register_frontend", AsyncMock()),
        patch("custom_components.dec_deepal.async_register_panel", AsyncMock()),
        patch.object(DeepalCommands, "send", AsyncMock(return_value="cmd1")),
        patch.object(DeepalCommands, "result", AsyncMock(return_value=CommandResult(CommandStatus.SUCCESS, 0))),
        patch.object(DeepalCommands, "condition_inquiry", AsyncMock(return_value="cmd2")),
        patch("custom_components.dec_deepal.command_runner.REFRESH_DELAYS", ()),
    ):
        yield state


async def _setup(hass: HomeAssistant) -> dict[str, str]:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=3,
        data={
            "country": "es",
            "session": DeepalSession(device_id="dev1", access_token="a", user_id="u1").to_dict(),
            "vehicles": [VEHICLE.to_dict()],
        },
        options={"appearance": {"car1": {"model": "s05_2024", "trim": "max", "color": "deep_space_black"}}},
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, "http", {})
    hass.config.components.update({"frontend", "panel_custom"})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return {
        e.translation_key: e.entity_id
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if e.translation_key and e.translation_key.startswith("charge_plan")
    }


def _sent(path: str) -> list[dict]:
    return [call.args[2] for call in DeepalCommands.send.await_args_list if call.args[0] == path]


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_charge_plan_entities_and_commands(hass: HomeAssistant, server: dict) -> None:
    ids = await _setup(hass)
    assert set(ids) == {"charge_plan", "charge_plan_until_full", "charge_plan_start", "charge_plan_end"}
    assert hass.states.get(ids["charge_plan"]).state == "on"
    assert hass.states.get(ids["charge_plan_start"]).state == "01:30:00"
    assert hass.states.get(ids["charge_plan_end"]).state == "07:00:00"

    # Cambiar la hora con el plan encendido: se borra el activo y se añade el nuevo (EV).
    await hass.services.async_call(
        "time", "set_value", {"entity_id": ids["charge_plan_start"], "time": "02:00:00"}, blocking=True
    )
    assert _sent(endpoints.CHARGE_DELETE_PLAN)[-1]["planId"] == "57"
    added = _sent(endpoints.CHARGE_ADD_PLAN)[-1]
    assert added["startTime"] == "0200" and added["endTime"] == "0700" and added["endSwitch"] == 1
    assert added["timeZone"] == "GMT+01:00"  # la del plan que ya tenía el coche
    assert hass.states.get(ids["charge_plan_start"]).state == "02:00:00"

    # Apagar: se borra el plan activo.
    server["plans"] = [{**ACTIVE, "planId": "58", "startTime": "0200"}]
    await hass.services.async_call("switch", "turn_off", {"entity_id": ids["charge_plan"]}, blocking=True)
    assert _sent(endpoints.CHARGE_DELETE_PLAN)[-1]["planId"] == "58"
    assert hass.states.get(ids["charge_plan"]).state == "off"

    # Con el plan apagado, cambiar la hora no manda nada: solo se apunta.
    server["plans"] = []
    sends = DeepalCommands.send.await_count
    await hass.services.async_call(
        "time", "set_value", {"entity_id": ids["charge_plan_end"], "time": "06:30:00"}, blocking=True
    )
    assert DeepalCommands.send.await_count == sends
    assert hass.states.get(ids["charge_plan_end"]).state == "06:30:00"

    # La acción para automatizaciones: encender «hasta llenar» a las 03:00.
    device_id = er.async_get(hass).async_get(ids["charge_plan"]).device_id
    await hass.services.async_call(
        DOMAIN,
        "set_charge_plan",
        {"device_id": device_id, "enabled": True, "start": "03:00", "until_full": True},
        blocking=True,
    )
    added = _sent(endpoints.CHARGE_ADD_PLAN)[-1]
    assert added["startTime"] == "0300" and "endTime" not in added and added["endSwitch"] == 0
    assert hass.states.get(ids["charge_plan_until_full"]).state == "on"

    # Menos de 30 minutos: error traducido y nada enviado.
    sends = DeepalCommands.send.await_count
    with pytest.raises(HomeAssistantError) as caught:
        await hass.services.async_call(
            DOMAIN,
            "set_charge_plan",
            {"device_id": device_id, "enabled": True, "start": "03:00", "end": "03:10"},
            blocking=True,
        )
    assert caught.value.translation_key == "charge_plan_too_short"
    assert DeepalCommands.send.await_count == sends
