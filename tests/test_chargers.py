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
        has=lambda feature: False,
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
    assert sent[0].data["message"].startswith("Changote está enchufado en Garaje. ¿Desbloqueo el cargador? Mantén pulsada")
    # Al tocarla se abre el panel en la ventana de elegir el coche.
    assert sent[0].data["data"]["url"].startswith("/dec-deepal-panel?elegir=")
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


async def test_lock_when_full(hass: HomeAssistant, manager: ChargerManager, freezer) -> None:  # noqa: ANN001
    """Al 100 % y sin cargar 30 min: se bloquea solo. Una pausa antes del 100 %, no."""
    sent = _notify(hass)
    async_mock_service(hass, "switch", "turn_off")
    turn_on = async_mock_service(hass, "switch", "turn_on")
    manager._vehicle("car1")[1].coordinator.data[s.BATTERY_LEVEL] = 92
    await manager.async_save_charger({**GARAJE, "vehicles": ["car1"], "unlock": "none"})
    await manager.async_set_settings(True, "people")
    charger_id = next(iter(manager.chargers))
    manager._device_id = lambda vehicle_id: f"dev_{vehicle_id}" if vehicle_id else None
    hass.states.async_set(LOCK, "off")
    hass.states.async_set(PLUG, "on")
    hass.states.async_set(CHARGING, "on")
    await hass.async_block_till_done()

    # Una pausa al 95 % (la compañía): no se programa el bloqueo.
    hass.states.async_set(ENERGY, "2.3", {"unit_of_measurement": "kWh"})
    hass.states.async_set(CHARGING, "off")
    await hass.async_block_till_done()
    assert manager.status(charger_id)["session"]["lock_at"] is None
    # El % estimado sale para la tarjeta del coche, mientras no informe.
    estimate = manager.statuses()["estimates"]["dev_car1"]
    assert (estimate["state"], estimate["charger"], round(estimate["level"])) == ("finished", "Garaje", 95)

    # Reanuda y llega al 100 %: a los 30 min sin cargar, se bloquea y avisa.
    hass.states.async_set(CHARGING, "on")
    hass.states.async_set(ENERGY, "6.2", {"unit_of_measurement": "kWh"})
    await hass.async_block_till_done()
    hass.states.async_set(CHARGING, "off")
    await hass.async_block_till_done()
    session = manager.status(charger_id)["session"]
    assert session["lock_at"] is not None and session["level"] == 100
    freezer.tick(timedelta(minutes=30, seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert [call.data["entity_id"] for call in turn_on] == [LOCK]
    assert sent[-1].data["message"] == "Garaje bloqueado: la carga terminó hace 30 min."

    # Con el ajuste quitado, la tarjeta del coche no recibe el % estimado.
    await manager.async_set_settings(True, "people", show_estimate=False)
    assert manager.statuses()["estimates"] == {} and manager.statuses()["show_estimate"] is False


async def test_reads_the_car_while_charging(hass: HomeAssistant, manager: ChargerManager, freezer) -> None:  # noqa: ANN001
    """Con cobertura: despierta y lee el coche cada 10 min; dos fallos = sin cobertura comprobada."""
    results = ["informe_nuevo", "fallo", "sin_informe"]
    calls: list[str] = []
    car = manager._vehicle("car1")[1]

    async def wake() -> str:
        result = results[len(calls)]
        calls.append(result)
        if result == "informe_nuevo":
            car.coordinator.data.update({s.BATTERY_LEVEL: 70, s.REPORT_TIME: dt_util.utcnow()})
        return result

    car.coordinator.wake_enabled = True
    car.coordinator.async_wake_and_wait = wake
    await manager.async_save_charger({**GARAJE, "vehicles": ["car1"], "unlock": "none", "coverage": "yes", "read_interval": 10})
    await manager.async_set_settings(True, "people")
    charger_id = next(iter(manager.chargers))
    hass.states.async_set(PLUG, "on")
    hass.states.async_set(CHARGING, "on")
    await hass.async_block_till_done()
    assert manager.status(charger_id)["session"]["estimated"] is True

    for _ in range(3):
        freezer.tick(timedelta(minutes=10, seconds=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        if len(calls) == 1:
            # Primera lectura: dato real, ya no es estimado.
            session = manager.status(charger_id)["session"]
            assert session["estimated"] is False and session["level"] == 70 and session["no_coverage"] is False
    assert calls == ["informe_nuevo", "fallo", "sin_informe"]
    assert manager.status(charger_id)["session"]["no_coverage"] is True
    # Comprobado sin cobertura: deja de intentarlo en esta carga.
    freezer.tick(timedelta(minutes=30))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert len(calls) == 3


async def test_energy_from_power(hass: HomeAssistant, manager: ChargerManager, freezer) -> None:  # noqa: ANN001
    """Sin contador de energía (o parado), los kWh salen de la potencia por el tiempo."""
    await manager.async_save_charger({**GARAJE, "vehicles": ["car1"], "unlock": "none", "coverage": "no",
                                      "entities": {"plugged": PLUG, "charging": CHARGING, "power": POWER}})
    await manager.async_set_settings(True, "people")
    charger_id = next(iter(manager.chargers))
    hass.states.async_set(PLUG, "on")
    hass.states.async_set(POWER, "3600", {"unit_of_measurement": "W"})
    hass.states.async_set(CHARGING, "on")
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=30))
    session = manager.status(charger_id)["session"]
    assert session["energy"] == 1.8 and session["energy_source"] == "power"
    # 56 % + 1,8 kWh × 0,9 en 68,8 kWh.
    assert session["level"] == 58.4


async def _charge(hass: HomeAssistant, kwh: float) -> None:
    """Una carga entera sin cobertura: enchufar, cargar ``kwh`` y desenchufar."""
    hass.states.async_set(ENERGY, "0", {"unit_of_measurement": "kWh"})
    hass.states.async_set(PLUG, "on")
    hass.states.async_set(CHARGING, "on")
    await hass.async_block_till_done()
    hass.states.async_set(ENERGY, str(kwh), {"unit_of_measurement": "kWh"})
    hass.states.async_set(CHARGING, "off")
    await hass.async_block_till_done()
    hass.states.async_set(PLUG, "off")
    await hass.async_block_till_done()


async def test_charge_limit_locks_and_continues(hass: HomeAssistant, manager: ChargerManager) -> None:
    """Límite al 80 %: al llegar (estimado) se bloquea el cargador; «Seguir hasta el 100 %» desbloquea."""
    sent = _notify(hass)
    turn_on = async_mock_service(hass, "switch", "turn_on")
    turn_off = async_mock_service(hass, "switch", "turn_off")
    await manager.async_save_charger({**GARAJE, "vehicles": ["car1"], "unlock": "none", "relock": False})
    await manager.async_set_settings(True, "people")
    await manager.async_set_limit_settings({"enabled": True})
    await manager.async_set_car_limit("car1", None, limit=80, check=False)
    charger_id = next(iter(manager.chargers))
    hass.states.async_set(LOCK, "off")
    hass.states.async_set(PLUG, "on")
    hass.states.async_set(POWER, "3700", {"unit_of_measurement": "W"})
    hass.states.async_set(CHARGING, "on")
    await hass.async_block_till_done()

    # 56 % + 10 kWh × 0,9 en 68,8 kWh = 69 %: aún no; faltan ≈ 2 h 15 min para el 80 %.
    hass.states.async_set(ENERGY, "10", {"unit_of_measurement": "kWh"})
    await hass.async_block_till_done()
    session = manager.status(charger_id)["session"]
    assert (session["target"], session["minutes_to_target"], session["limit_hit"]) == (80, 135, False)
    assert turn_on == []

    # 19 kWh: ≈ 81 %. Se bloquea y avisa, con el botón para seguir.
    hass.states.async_set(ENERGY, "19", {"unit_of_measurement": "kWh"})
    await hass.async_block_till_done()
    assert [call.data["entity_id"] for call in turn_on] == [LOCK]
    notice = sent[-1].data
    assert notice["title"] == "DEC Deepal Changote"
    assert notice["message"] == "Ha llegado al ≈ 81 % (límite: 80 %): Garaje bloqueado para no pasar del límite."
    assert [action["title"] for action in notice["data"]["actions"]] == ["Seguir hasta el 100 %"]
    # Deja de cargar: no llega otro aviso de "carga terminada".
    count = len(sent)
    hass.states.async_set(LOCK, "on")
    hass.states.async_set(CHARGING, "off")
    await hass.async_block_till_done()
    assert len(sent) == count
    session = manager.status(charger_id)["session"]
    assert session["limit_hit"] is True and session["limit_locked"] is True

    # «Seguir hasta el 100 %»: desbloquea y esta carga ya no se para.
    hass.bus.async_fire("mobile_app_notification_action", {"action": f"DEC_DEEPAL_CHARGER|{charger_id}|full"}, context=Context())
    await hass.async_block_till_done()
    assert [call.data["entity_id"] for call in turn_off] == [LOCK]
    session = manager.status(charger_id)["session"]
    assert session["target"] is None and session["limit_hit"] is False
    # Al desenchufar, una carga que no llegó al 100 %.
    hass.states.async_set(PLUG, "off")
    await hass.async_block_till_done()
    assert manager._cars["car1"]["incomplete"] == 1


async def test_raising_the_limit_resumes(hass: HomeAssistant, manager: ChargerManager) -> None:
    """Parada en el 70 %: si en la tarjeta suben el límite (o «Solo esta: 100 %»), se desbloquea."""
    turn_on = async_mock_service(hass, "switch", "turn_on")
    turn_off = async_mock_service(hass, "switch", "turn_off")
    await manager.async_save_charger({**GARAJE, "vehicles": ["car1"], "unlock": "none"})
    await manager.async_set_settings(True, "people")
    await manager.async_set_limit_settings({"enabled": True, "notify": False})
    await manager.async_set_car_limit("car1", None, limit=70, check=False)
    hass.states.async_set(LOCK, "off")
    hass.states.async_set(PLUG, "on")
    hass.states.async_set(CHARGING, "on")
    await hass.async_block_till_done()
    hass.states.async_set(ENERGY, "11", {"unit_of_measurement": "kWh"})
    await hass.async_block_till_done()
    assert len(turn_on) == 1
    hass.states.async_set(LOCK, "on")
    hass.states.async_set(CHARGING, "off")
    await hass.async_block_till_done()
    await manager.async_set_car_limit("car1", None, limit=90, check=False)
    assert [call.data["entity_id"] for call in turn_off] == [LOCK]
    assert manager.target("car1") == 90


async def test_full_reminder_every_n(hass: HomeAssistant, manager: ChargerManager) -> None:
    """Cada 3 cargas sin llegar al 100 %: aviso con «La próxima al 100 %»; o, sin preguntar, la hace."""
    sent = _notify(hass)
    async_mock_service(hass, "switch", "turn_on")
    async_mock_service(hass, "switch", "turn_off")
    await manager.async_save_charger({**GARAJE, "vehicles": ["car1"], "unlock": "none", "relock": False})
    await manager.async_set_settings(True, "people")
    await manager.async_set_limit_settings({"enabled": True, "remind": True, "every": 3})
    await manager.async_set_car_limit("car1", None, limit=80, check=False)
    charger_id = next(iter(manager.chargers))
    hass.states.async_set(LOCK, "off")

    for _ in range(3):
        await _charge(hass, 5)
    reminder = sent[-1].data
    assert reminder["message"].startswith("Lleva 3 cargas sin llegar al 100 %.")
    assert [action["title"] for action in reminder["data"]["actions"]] == ["La próxima al 100 %", "Ahora no"]
    assert reminder["data"]["actions"][0]["action"] == f"DEC_DEEPAL_CHARGER|{charger_id}|nextfull:car1"

    # «La próxima al 100 %»: el límite no para la siguiente; al llegar al 100 %, se vuelve a contar desde 0.
    hass.bus.async_fire("mobile_app_notification_action", {"action": reminder["data"]["actions"][0]["action"]}, context=Context())
    await hass.async_block_till_done()
    assert manager._cars["car1"]["once_full"] is True and manager.target("car1") == 100
    await _charge(hass, 40)
    assert manager._cars["car1"] == {"limit": 80, "once_full": False, "incomplete": 0}
    assert manager.target("car1") == 80

    # Sin preguntar: a las 3 incompletas, la siguiente al 100 % (y se avisa).
    await manager.async_set_limit_settings({"auto": True})
    for _ in range(3):
        await _charge(hass, 5)
    assert manager._cars["car1"]["once_full"] is True
    assert sent[-1].data["message"].startswith("Lleva 3 cargas sin llegar al 100 %: la próxima llegará al 100 %")


async def test_car_limit_from_the_card(hass: HomeAssistant, manager: ChargerManager, hass_ws_client, hass_admin_user) -> None:  # noqa: ANN001
    """La tarjeta del coche (por dispositivo) cambia el límite; en el PHEV también se manda al coche."""
    from homeassistant.components import websocket_api
    from homeassistant.setup import async_setup_component

    from custom_components.dec_deepal.panel import cargadores

    assert await async_setup_component(hass, "websocket_api", {})
    for command in cargadores.COMMANDS:
        websocket_api.async_register_command(hass, command)
    hass.data.setdefault(DOMAIN, {})["chargers"] = manager
    manager._device_id = lambda vehicle_id: f"dev_{vehicle_id}" if vehicle_id else None
    # car2 es un PHEV: su límite propio se cambia con la orden del coche.
    sent: list[tuple[str, int]] = []
    car2 = manager._vehicle("car2")[1]
    car2.has = lambda feature: feature == "limite_carga"

    async def run(name: str, send, optimistic=None) -> None:  # noqa: ANN001
        await send()

    async def charge_limit(vehicle_id: str, percent: int) -> str:
        sent.append((vehicle_id, percent))
        return "cmd"

    car2.runner = SimpleNamespace(run=run)
    manager._vehicle("car2")[0].runtime_data.commands = SimpleNamespace(charge_limit=charge_limit)
    await manager.async_save_charger(GARAJE)
    await manager.async_set_settings(True, "people")
    client = await hass_ws_client(hass)

    await client.send_json({"id": 1, "type": "dec_deepal/panel/set_limit", "enabled": True, "every": 5})
    assert (await client.receive_json())["success"]
    assert manager.limit["enabled"] is True and manager.limit["every"] == 5
    await client.send_json({"id": 2, "type": "dec_deepal/chargers/car_limit", "device_id": "dev_car2", "limit": 90})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    assert sent == [("car2", 90)]
    await client.send_json({"id": 3, "type": "dec_deepal/chargers/car_limit", "device_id": "dev_car2", "once_full": True})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    assert sent[-1] == ("car2", 100)
    await client.send_json({"id": 4, "type": "dec_deepal/chargers/car_limit", "device_id": "dev_car2", "limit": 85})
    assert not (await client.receive_json())["success"]

    cars = manager.statuses(hass_admin_user)["cars"]
    assert cars["dev_car2"] == {"vehicle_id": "car2", "limit": 90, "once_full": True, "incomplete": 0, "target": 100, "can_control": True}
    assert cars["dev_car1"]["limit"] == 100
    # Una persona que no es de ese coche no puede cambiarlo.
    other = SimpleNamespace(id="otra", is_admin=False)
    with pytest.raises(ChargerError, match="unauthorized"):
        await manager.async_set_car_limit("car2", other, limit=70)
    config = manager.panel_config()["limit"]
    assert config["every_choices"] == [3, 4, 5, 6] and [car["id"] for car in config["cars"]] == ["car1", "car2"]
