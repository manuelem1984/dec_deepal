"""2.6.0b6: combustible y límite de carga del PHEV, testigos con el coche apagado,
lista de coches vacía, configuración MQTT reutilizada y mensajes rotos."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dec_deepal.api import client as client_module
from custom_components.dec_deepal.api import commands as commands_module
from custom_components.dec_deepal.api import endpoints
from custom_components.dec_deepal.api.client import DeepalClient
from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.api.mqtt import client as mqtt_client
from custom_components.dec_deepal.api.mqtt import protocol
from custom_components.dec_deepal.const import CONF_VEHICLES, DOMAIN
from custom_components.dec_deepal.registries import load_all
from custom_components.dec_deepal.telemetry import converters as c
from custom_components.dec_deepal.telemetry import signals as s
from custom_components.dec_deepal.telemetry.state import build_state
from custom_components.dec_deepal.vehicle_sync import async_sync_vehicles

from .test_registries import INTEGRATION


# --- 1. Combustible del PHEV ------------------------------------------------------------------


def test_fuel_from_mqtt_and_rest() -> None:
    mqtt = build_state(mqtt_params={"remainingFuel": "45", "remainedOilMile": "512"}, rest_raw=None, previous=None)
    assert (mqtt.get(s.FUEL_LEVEL), mqtt.get(s.FUEL_RANGE_KM)) == (45.0, 512.0)
    # REST: litros y autonomía WLTC (la europea) antes que la NEDC; y el límite de carga.
    rest = {
        "fuel": {"leftPercent": 60, "leftVolume": 30.5, "fuelNedcRemainingMileage": 700, "fuelWltcRemainingMileage": 610},
        "charge": {"maxSocPercent": 90},
    }
    state = build_state(mqtt_params=None, rest_raw=rest, previous=None)
    assert (state.get(s.FUEL_LEVEL), state.get(s.FUEL_VOLUME_L), state.get(s.FUEL_RANGE_KM)) == (60.0, 30.5, 610.0)
    assert state.get(s.CHARGE_LIMIT) == 90.0
    # Con el coche dormido (no llegan), se conserva el último valor.
    later = build_state(mqtt_params={"soc": 50}, rest_raw=None, previous=state)
    assert later.get(s.FUEL_LEVEL) == 60.0 and later.get(s.CHARGE_LIMIT) == 90.0


def test_percent_and_positive() -> None:
    assert [c.percent(value) for value in ("45", 0, 100, 150, -1, "x")] == [45.0, 0.0, 100.0, None, None, None]
    assert [c.positive(value) for value in ("12.5", 0, -3, None)] == [12.5, 0.0, None, None]


def test_catalogue_fuel_and_charge_limit() -> None:
    vehicles = load_all(INTEGRATION).vehicles
    ev, phev = vehicles.get("s05_2024"), vehicles.get("s05_phev")
    assert phev.has("combustible") and phev.has("limite_carga")
    assert not ev.has("combustible") and not ev.has("limite_carga")


# --- 2. Límite de carga: la orden ----------------------------------------------------------------


async def test_charge_limit_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """Firma con un número de serie de tipo 2 y manda chargePercentageMax."""
    posts: list[tuple[str, dict]] = []

    async def post(path, payload=None, **_kwargs):  # noqa: ANN001, ANN202
        posts.append((path, payload))
        return "cifrado" if path == endpoints.SERIAL_NO else {"commandId": "c1"}

    monkeypatch.setattr(commands_module, "decrypt_with_private_key", lambda _key, _data: "serie")
    monkeypatch.setattr(commands_module, "sign_payload", lambda _key, _payload: "firma")
    account = SimpleNamespace(
        session=SimpleNamespace(private_key_pem="clave"), transport=SimpleNamespace(post=post), call=lambda action: action()
    )
    commands = commands_module.DeepalCommands(account)
    assert await commands.charge_limit("car9", 85) == "c1"
    assert posts[0] == (endpoints.SERIAL_NO, {"type": "2"})
    path, payload = posts[1]
    assert path == endpoints.CHARGE_PERCENTAGE
    assert payload["command"] == "charge_max" and payload["chargePercentageMax"] == 85 and payload["vehicleId"] == "car9"


# --- 3. Testigos con el coche apagado ---------------------------------------------------------------


def test_warnings_only_trusted_with_the_car_on() -> None:
    on = build_state(mqtt_params={"powerStatusFeedBack": 2, "absLightStatus": 0}, rest_raw=None, previous=None)
    assert on.get(s.WARNING_ABS) is False
    # Despertado y apagado: manda el ABS encendido sin motivo → se queda el último de fiar.
    woken = build_state(mqtt_params={"powerStatusFeedBack": 0, "absLightStatus": 1}, rest_raw=None, previous=on)
    assert woken.get(s.WARNING_ABS) is False
    # Sin un valor anterior, no se sabe (mejor que un falso aviso).
    cold = build_state(mqtt_params={"powerStatusFeedBack": 0, "absLightStatus": 1}, rest_raw=None, previous=None)
    assert cold.get(s.WARNING_ABS) is None
    # Encendido, el testigo encendido sí cuenta.
    real = build_state(mqtt_params={"powerStatusFeedBack": 2, "absLightStatus": 1}, rest_raw=None, previous=woken)
    assert real.get(s.WARNING_ABS) is True


# --- 4. Lista de coches vacía -------------------------------------------------------------------------


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_empty_vehicle_list_retires_nothing(hass: HomeAssistant) -> None:
    car = VehicleInfo(vehicle_id="car1", nickname="Changote", vin="VIN1")
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_VEHICLES: [car.to_dict()]}, options={})
    entry.add_to_hass(hass)
    await async_sync_vehicles(hass, entry, SimpleNamespace(get_vehicles=AsyncMock(return_value=[])))
    assert not [key for key in ir.async_get(hass).issues if key[0] == DOMAIN]
    assert entry.data[CONF_VEHICLES] == [car.to_dict()]


# --- 5. Configuración y token del MQTT, reutilizados -------------------------------------------------


async def test_mqtt_session_is_reused(monkeypatch: pytest.MonkeyPatch) -> None:
    fetched: list[str] = []
    fail = {"next": False}

    async def new_session(self, vehicle):  # noqa: ANN001, ANN202
        fetched.append(vehicle.vehicle_id)
        return SimpleNamespace(), f"token{len(fetched)}"

    async def read(connection, token, ssl_context):  # noqa: ANN001, ANN202
        if fail["next"]:
            fail["next"] = False
            raise ConnectionError("broker")
        return token

    monkeypatch.setattr(DeepalClient, "_new_mqtt_session", new_session)
    monkeypatch.setattr(client_module, "read_telemetry", read)
    client = DeepalClient(SimpleNamespace(session=SimpleNamespace(refresh_token=None)))
    car = VehicleInfo(vehicle_id="1")
    assert [await client.read_mqtt(car, None) for _ in range(3)] == ["token1"] * 3
    assert fetched == ["1"]  # dos peticiones menos en cada lectura
    # Si falla con ellos, se olvidan y la siguiente lectura los pide de nuevo.
    fail["next"] = True
    with pytest.raises(ConnectionError):
        await client.read_mqtt(car, None)
    assert await client.read_mqtt(car, None) == "token2" and fetched == ["1", "1"]
    # Pasado el tiempo, también se renuevan.
    monkeypatch.setattr(client_module, "MQTT_SESSION_TTL", 0)
    client._mqtt_sessions.clear()
    await client.read_mqtt(car, None)
    await client.read_mqtt(car, None)
    assert len(fetched) == 4


# --- 6. Mensajes MQTT rotos ----------------------------------------------------------------------------


def test_broken_publish_raises_value_error() -> None:
    """Lo que el bucle de lectura salta (en vez de cortar la lectura)."""
    with pytest.raises(ValueError):
        protocol.parse_publish(0x30, b"\x00")
    with pytest.raises(ValueError):
        protocol.parse_publish(0x30, b"\x00\x01a no-json")


async def test_read_skips_a_broken_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un mensaje roto en medio no corta la lectura: se salta y llega el bueno."""
    good_topic = "dev/x/properties/get/res"
    broken = (0x30, b"\x00\x01a no-json")  # PUBLISH con un payload que no es JSON
    topic = good_topic.encode()
    good = (0x30, len(topic).to_bytes(2, "big") + topic + b'{"data": 1}')
    # El primero bueno trae la clave (se piden los datos); el segundo, los datos.
    packets = iter([broken, good, broken, good])

    class Writer:
        def write(self, _data: bytes) -> None: ...
        async def drain(self) -> None: ...
        def close(self) -> None: ...
        async def wait_closed(self) -> None: ...

    async def open_connection(*_args, **_kwargs):  # noqa: ANN202
        return object(), Writer()

    async def read_packet(_reader):  # noqa: ANN001, ANN202
        try:
            return next(packets)
        except StopIteration:
            raise TimeoutError from None

    async def nothing(*_args, **_kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def extract(_payload, _key, reading):  # noqa: ANN001, ANN202
        reading.params.update({f"k{i}": i for i in range(11)})
        return True

    monkeypatch.setattr(mqtt_client.asyncio, "open_connection", open_connection)
    monkeypatch.setattr(mqtt_client, "_connect", nothing)
    monkeypatch.setattr(mqtt_client, "_subscribe", nothing)
    monkeypatch.setattr(mqtt_client, "_secret_key", lambda _payload: "clave")
    monkeypatch.setattr(mqtt_client, "_extract", extract)
    monkeypatch.setattr(protocol, "read_packet", read_packet)
    connection = SimpleNamespace(
        host="h", port=1, login_topic="t", login_device_id="d", vehicle_device_id="v", properties_topic="p"
    )
    monkeypatch.setattr(mqtt_client, "_condition_payload", lambda *_args: {})
    monkeypatch.setattr(mqtt_client, "_login_payload", lambda *_args: {})
    reading = await mqtt_client._read_telemetry(connection, "token", None)
    assert len(reading.params) == 11
    assert asyncio
