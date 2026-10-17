"""Cargadores: desbloquear al confirmar el coche, avisos, estimación y pérdidas."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest
from homeassistant.core import Context, HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.dec_deepal.alert_rules import route_for
from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.chargers import (
    CONTROL_ADMINS,
    ChargerError,
    ChargerManager,
    clean_charger,
    estimate_level,
    estimate_minutes,
    measured_loss,
)
from custom_components.dec_deepal.const import DOMAIN, OPT_ALERTS
from custom_components.dec_deepal.telemetry import signals as s

ME = "mobile_app_iphone_de_manuel"
PLUG = "binary_sensor.evse_conectado"
CHARGING = "binary_sensor.evse_cargando"
POWER = "sensor.evse_potencia"
ENERGY = "sensor.evse_energia"
LOCK = "switch.evse_bloquear"
GARAJE = {
    "name": "Garaje",
    "entities": {"plugged": PLUG, "charging": CHARGING, "power": POWER, "energy": ENERGY, "lock": LOCK},
    "vehicles": ["car1", "car2"],
    "coverage": "no",
    "unlock": "confirm",
    "relock_minutes": 5,
    "price": 0.114,
}


def _car(vehicle_id: str, name: str, level: float) -> SimpleNamespace:
    trim = SimpleNamespace(battery_kwh=68.8)
    return SimpleNamespace(
        info=VehicleInfo(vehicle_id=vehicle_id, nickname=name, vin=f"VIN{vehicle_id}"),
        coordinator=SimpleNamespace(
            data={
                s.BATTERY_LEVEL: level,
                s.RANGE_KM: 300,
                s.ODOMETER_KM: 3645.0,
                s.REPORT_TIME: dt_util.utcnow() - timedelta(hours=3),
            }
        ),
        model=SimpleNamespace(trims={"max": trim}),
        trim="max",
    )


@pytest.fixture
async def manager(hass: HomeAssistant):  # noqa: ANN201
    hass.config.language = "es"
    vehicles = {"car1": _car("car1", "Changote", 56), "car2": _car("car2", "Changuito", 40)}
    # Avisos de carga al iPhone (los del cargador no tienen destinos: usan estos).
    options = {OPT_ALERTS: {"targets": [ME], "types": ["charge_finished"], "persistent": False}}
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=options)
    entry.add_to_hass(hass)
    entry.runtime_data = SimpleNamespace(
        vehicles=vehicles,
        alerts=SimpleNamespace(
            route=lambda vehicle_id: route_for(options[OPT_ALERTS], vehicle_id),
            people=lambda vehicle_id: ["person.manuel"] if vehicle_id == "car1" else [],
        ),
    )
    for entity_id, state in ((PLUG, "off"), (CHARGING, "off"), (POWER, "0"), (ENERGY, "0"), (LOCK, "on")):
        hass.states.async_set(entity_id, state)
    manager = ChargerManager(hass)
    await manager.async_load()
    yield manager
    manager.async_stop()


def _notify(hass: HomeAssistant) -> list:
    return async_mock_service(hass, "notify", ME)


def test_clean_charger() -> None:
    with pytest.raises(ChargerError, match="charger_name"):
        clean_charger({"name": " "})
    with pytest.raises(ChargerError, match="charger_plugged"):
        clean_charger({"name": "Garaje", "entities": {"charging": CHARGING}})
    with pytest.raises(ChargerError, match="charger_entity"):
        clean_charger({"name": "Garaje", "entities": {"plugged": PLUG, "lock": "sensor.algo"}})
    charger = clean_charger({**GARAJE, "remind_minutes": 7, "loss": 80, "vehicles": ["car1", "otro"]}, ["car1"])
    # Lo que no vale vuelve a su valor de fábrica o a su límite.
    assert charger["remind_minutes"] == 15 and charger["loss"] == 40 and charger["vehicles"] == ["car1"]
    assert charger["lock_on_locked"] is True and charger["relock"] is True and charger["learn"] is True


def test_estimates() -> None:
    # 56 % + 4,2 kWh del cargador con un 10 % de pérdidas en 68,8 kWh.
    assert round(estimate_level(56, 4.2, 10, 68.8), 1) == 61.5
    assert estimate_level(None, 4.2, 10, 68.8) is None and estimate_level(56, 4.2, 10, None) is None
    # Del 61,5 % al 100 % a 3,9 kW.
    assert round(estimate_minutes(61.5, 3900, 10, 68.8)) == 453
    assert measured_loss(56, 62, 4.6, 68.8) == 10.3
    assert measured_loss(56, 56, 4.6, 68.8) is None and measured_loss(56, 90, 4.6, 68.8) is None


async def test_two_cars_without_coverage(hass: HomeAssistant, manager: ChargerManager, freezer) -> None:  # noqa: ANN001
    sent = _notify(hass)
    turn_off = async_mock_service(hass, "switch", "turn_off")
    turn_on = async_mock_service(hass, "switch", "turn_on")
    await manager.async_save_charger(GARAJE)
    await manager.async_set_settings(True, "people")
    charger_id = next(iter(manager.chargers))

    # Enchufan: sin cobertura, se pregunta en seguida qué coche es.
    hass.states.async_set(PLUG, "on")
    await hass.async_block_till_done()
    assert len(sent) == 1
    payload = sent[0].data
    assert payload["title"] == "DEC Deepal · Garaje"
    assert payload["message"].startswith("Hay un coche enchufado en Garaje")
    assert [action["title"] for action in payload["data"]["actions"]] == ["Changote", "Changuito", "No desbloquear"]
    status = manager.status(charger_id)
    assert status["session"]["waiting"] is True and status["locked"] is True

    # Nadie contesta: recordatorio a los 15 min.
    freezer.tick(timedelta(minutes=15, seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert sent[-1].data["message"].startswith("El cargador de Garaje sigue bloqueado")

    # Eligen Changote desde la notificación: se desbloquea.
    hass.bus.async_fire(
        "mobile_app_notification_action", {"action": f"DEC_DEEPAL_CHARGER|{charger_id}|car1"}, context=Context()
    )
    await hass.async_block_till_done()
    assert [call.data["entity_id"] for call in turn_off] == [LOCK]
    hass.states.async_set(LOCK, "off")
    await hass.async_block_till_done()

    # Carga: sin cobertura, el % se estima con los kWh del cargador.
    hass.states.async_set(CHARGING, "on")
    hass.states.async_set(POWER, "3900", {"unit_of_measurement": "W"})
    hass.states.async_set(ENERGY, "4.2", {"unit_of_measurement": "kWh"})
    await hass.async_block_till_done()
    session = manager.status(charger_id)["session"]
    assert session["vehicle"] == "Changote" and session["assigned"] == "user"
    assert session["estimated"] is True and session["level"] == 61.5
    assert session["energy"] == 4.2 and session["cost"] == 0.48 and session["minutes_left"] == 453

    # Termina: aviso con los datos del cargador, al coche (título con su nombre).
    hass.states.async_set(CHARGING, "off")
    await hass.async_block_till_done()
    finished = sent[-1].data
    assert finished["title"] == "DEC Deepal Changote"
    assert finished["message"] == "Carga terminada en Garaje · 56 % → ≈ 61 % · +4,2 kWh · 0,48 €."

    # Desenchufan: se apunta y, a los 5 min, se bloquea solo y avisa.
    hass.states.async_set(PLUG, "off")
    await hass.async_block_till_done()
    last = manager.status(charger_id)["last"]
    assert (last["vehicle"], last["energy"], last["cost"], last["estimated"]) == ("Changote", 4.2, 0.48, True)
    freezer.tick(timedelta(minutes=5, seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert [call.data["entity_id"] for call in turn_on] == [LOCK]
    assert sent[-1].data["message"] == "Garaje bloqueado: la manguera se desconectó hace 5 min."
    assert sent[-1].data["data"]["actions"][0]["title"] == "Desbloquear otra vez"

    # Vuelve la cobertura con un 62 %: se mide la pérdida de esa carga.
    manager._vehicle("car1")[1].coordinator.data.update({s.BATTERY_LEVEL: 62, s.REPORT_TIME: dt_util.utcnow()})
    manager._learn()
    assert manager.measured(charger_id) == {"value": 1.7, "count": 1}
    assert manager.status(charger_id)["last"]["soc_end"] == 62


async def test_one_car_with_coverage_unlocks_alone(hass: HomeAssistant, manager: ChargerManager, freezer) -> None:  # noqa: ANN001
    sent = _notify(hass)
    turn_off = async_mock_service(hass, "switch", "turn_off")
    await manager.async_save_charger({**GARAJE, "vehicles": ["car1"], "coverage": "yes"})
    await manager.async_set_settings(True, "people")

    hass.states.async_set(PLUG, "on")
    await hass.async_block_till_done()
    assert sent == []  # con cobertura, primero se espera al coche
    # El coche informa: manguera puesta.
    manager._vehicle("car1")[1].coordinator.data.update({s.CHARGER_PLUGGED: True, s.REPORT_TIME: dt_util.utcnow()})
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert [call.data["entity_id"] for call in turn_off] == [LOCK]
    assert sent[-1].data["title"] == "DEC Deepal Changote"
    assert sent[-1].data["message"] == "Garaje desbloqueado: Changote confirmó la manguera. Ya puede cargar."

    # Desbloqueado y la compañía no carga en 10 min: aviso.
    hass.states.async_set(LOCK, "off")
    freezer.tick(timedelta(minutes=10, seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert sent[-1].data["message"].startswith("Desbloqueado hace 10 min y Garaje no carga")


async def test_one_car_without_answer_asks_one(hass: HomeAssistant, manager: ChargerManager, freezer) -> None:  # noqa: ANN001
    sent = _notify(hass)
    await manager.async_save_charger({**GARAJE, "vehicles": ["car1"], "coverage": "unknown"})
    await manager.async_set_settings(True, "people")
    hass.states.async_set(PLUG, "on")
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=5, seconds=31))
    for _ in range(12):
        freezer.tick(timedelta(seconds=31))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    assert sent[0].data["message"] == "Changote está enchufado en Garaje. ¿Desbloqueo el cargador?"
    assert [action["title"] for action in sent[0].data["data"]["actions"]] == ["Desbloquear", "No"]


async def test_permissions(hass: HomeAssistant, manager: ChargerManager, hass_admin_user) -> None:  # noqa: ANN001
    await manager.async_save_charger(GARAJE)
    await manager.async_set_settings(True, "people")
    charger_id = next(iter(manager.chargers))
    owner = await hass.auth.async_create_user("Manuel")
    other = await hass.auth.async_create_user("Visita")
    hass.states.async_set("person.manuel", "home", {"user_id": owner.id})
    assert manager.can_control(charger_id, hass_admin_user)
    assert manager.can_control(charger_id, owner)
    assert not manager.can_control(charger_id, other)
    with pytest.raises(ChargerError, match="unauthorized"):
        await manager.async_set_lock(charger_id, False, other)
    await manager.async_set_settings(True, CONTROL_ADMINS)
    assert not manager.can_control(charger_id, owner) and manager.can_control(charger_id, hass_admin_user)


async def test_disabled_does_nothing(hass: HomeAssistant, manager: ChargerManager) -> None:
    sent = _notify(hass)
    await manager.async_save_charger(GARAJE)
    hass.states.async_set(PLUG, "on")
    await hass.async_block_till_done()
    assert sent == [] and manager.statuses()["chargers"] == []


async def test_websocket_commands(hass: HomeAssistant, manager: ChargerManager, hass_ws_client) -> None:  # noqa: ANN001
    """Panel (guardar, activar) y tarjeta (suscripción, elegir el coche)."""
    from homeassistant.components import websocket_api
    from homeassistant.setup import async_setup_component

    from custom_components.dec_deepal.panel import cargadores

    assert await async_setup_component(hass, "websocket_api", {})
    for command in cargadores.COMMANDS:
        websocket_api.async_register_command(hass, command)
    turn_off = async_mock_service(hass, "switch", "turn_off")
    hass.data.setdefault(DOMAIN, {})["chargers"] = manager
    client = await hass_ws_client(hass)

    await client.send_json({"id": 1, "type": "dec_deepal/panel/save_charger", "charger": {"name": "Garaje", "entities": {}}})
    assert (await client.receive_json())["error"]["code"] == "charger_plugged"
    await client.send_json({"id": 2, "type": "dec_deepal/panel/save_charger", "charger": GARAJE})
    charger_id = (await client.receive_json())["result"]["id"]
    await client.send_json({"id": 3, "type": "dec_deepal/panel/set_chargers", "enabled": True, "control": "people"})
    assert (await client.receive_json())["success"]

    # La tarjeta se suscribe y recibe el estado al momento y con cada cambio.
    await client.send_json({"id": 4, "type": "dec_deepal/chargers/subscribe"})
    assert (await client.receive_json())["success"]
    first = (await client.receive_json())["event"]
    assert first["enabled"] is True and first["chargers"][0]["name"] == "Garaje"
    assert first["chargers"][0]["can_control"] is True and first["chargers"][0]["session"] is None
    hass.states.async_set(PLUG, "on")
    await hass.async_block_till_done()
    event = (await client.receive_json())["event"]
    while not (event["chargers"][0]["session"] or {}).get("waiting"):
        event = (await client.receive_json())["event"]

    # Elegir el coche desde la tarjeta desbloquea.
    await client.send_json({"id": 5, "type": "dec_deepal/chargers/confirm", "charger_id": charger_id, "vehicle_id": "car2"})
    while (reply := await client.receive_json()).get("id") != 5:
        pass
    assert reply["success"] and [call.data["entity_id"] for call in turn_off] == [LOCK]
    assert manager.status(charger_id)["session"]["vehicle"] == "Changuito"
