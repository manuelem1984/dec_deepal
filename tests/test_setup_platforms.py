"""La integración entera con un S05 falso: arranca, crea las entidades de cada plataforma y se descarga.

Hasta la 2.6.0b15 ninguna prueba montaba la cuenta completa, así que las
plataformas (sensor, number, lock, switch, cover, button, image...) no se
probaban nunca. Aquí se monta como lo hace Home Assistant, con el servidor de
Deepal sustituido: la lista de coches, la lectura MQTT y la REST son falsas.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dec_deepal.api.client import DeepalClient
from custom_components.dec_deepal.api.commands import DeepalCommands
from custom_components.dec_deepal.api.models import CommandResult, CommandStatus, VehicleInfo
from custom_components.dec_deepal.api.mqtt.client import MqttReading
from custom_components.dec_deepal.api.session import DeepalSession
from custom_components.dec_deepal.const import DOMAIN

VEHICLE = VehicleInfo(
    vehicle_id="car1",
    vin="LS5A3ABE0RA000001",
    model_name="Deepal S05",
    nickname="Changote",
    protocol_type="MQTT",
)
#: Una lectura MQTT como las de un S05 EV aparcado y enchufado en AC.
PARAMS = {
    "soc": 56,
    "remainedPowerMile": 276,
    "ChrgSts": 1,
    "totalOdometer": 3645,
    "vehicleTemperature": 21,
    "innerHumidity": 61.0,
    "powerStatus": 0,
    "driverDoorLockStatus": 1,
    # Un informe reciente: así las órdenes no despiertan el coche antes.
    "lastUpdatedTime": int(time.time() * 1000),
}


@pytest.fixture
def deepal() -> Iterator[None]:
    """El servidor de Deepal, falso (nada sale a internet)."""
    with (
        patch.object(DeepalClient, "get_vehicles", AsyncMock(return_value=[VEHICLE])),
        patch.object(DeepalClient, "get_capabilities", AsyncMock(return_value=None)),
        patch.object(DeepalClient, "read_mqtt", AsyncMock(return_value=MqttReading(params=dict(PARAMS), model_code="SC6464AAKBEV"))),
        patch.object(DeepalClient, "get_condition", AsyncMock(return_value={})),
        # El frontend de Home Assistant no está en el entorno de pruebas: el
        # registro de los ficheros y del panel se prueba aparte.
        patch("custom_components.dec_deepal.async_register_frontend", AsyncMock()),
        patch("custom_components.dec_deepal.async_register_panel", AsyncMock()),
        # Las órdenes: se mandan y el coche dice que bien.
        patch.object(DeepalCommands, "send", AsyncMock(return_value="cmd1")),
        patch.object(DeepalCommands, "result", AsyncMock(return_value=CommandResult(CommandStatus.SUCCESS, 0))),
        patch.object(DeepalCommands, "condition_inquiry", AsyncMock(return_value="cmd2")),
    ):
        yield


@pytest.mark.usefixtures("enable_custom_integrations", "deepal")
async def test_account_with_one_car(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=3,
        data={
            "country": "es",
            "session": DeepalSession(device_id="dev1", access_token="a", user_id="u1").to_dict(),
            "vehicles": [VEHICLE.to_dict()],
        },
        options={
            "appearance": {"car1": {"model": "s05_2024", "trim": "max", "color": "deep_space_black"}},
            # Con el control con PIN salen también el cierre y las ventanillas.
            "pin_enabled": True,
            "pin": "1234",
        },
    )
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, "http", {})
    # Dependencias del manifiesto que necesitan el paquete del frontend (no
    # instalado en las pruebas): se dan por cargadas.
    hass.config.components.update({"frontend", "panel_custom"})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    platforms = {item.domain for item in entities}
    assert {"sensor", "binary_sensor", "lock", "switch", "cover", "button", "number", "climate", "image"} <= platforms

    def state_of(domain: str, key: str) -> str | None:
        item = next((e for e in entities if e.domain == domain and e.translation_key == key), None)
        assert item is not None, (domain, key)
        state = hass.states.get(item.entity_id)
        return None if state is None else state.state

    # Lo que llega del coche se ve en las entidades.
    assert state_of("sensor", "battery_level") == "56"
    assert state_of("sensor", "charge_status") == "connected_ac"
    assert state_of("binary_sensor", "charging") == "off"
    # El Max tiene ventilación de asientos (number); el modelo elegido decide.
    assert any(e.domain == "number" and "vent" in (e.translation_key or "") for e in entities)

    # Órdenes desde las entidades: cada una llega a la API con lo esperado.
    def entity_id(domain: str, key: str) -> str:
        return next(e.entity_id for e in entities if e.domain == domain and e.translation_key == key)

    send = DeepalCommands.send
    for domain, service, key, data in (
        ("switch", "turn_on", "steering_wheel_heat", {}),
        ("lock", "unlock", "doors", {}),
        ("button", "press", "flash_lights", {}),
    ):
        calls = send.await_count
        await hass.services.async_call(domain, service, {"entity_id": entity_id(domain, key), **data}, blocking=True)
        assert send.await_count == calls + 1, (domain, key)
    # Optimista: el interruptor queda encendido sin esperar a la siguiente lectura.
    assert state_of("switch", "steering_wheel_heat") == "on"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
