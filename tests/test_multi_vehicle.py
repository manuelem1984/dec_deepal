"""Pruebas de rc5: dos coches en la misma cuenta y cierre de conexión del broker.

Caso real (01-10-2026): con dos S05 en la misma cuenta, las dos lecturas MQTT
se hacían a la vez con el mismo identificador de cliente; el broker cerraba
una de las dos conexiones (``IncompleteReadError``) y la integración no
arrancaba porque ese error no se trataba como recuperable.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from custom_components.dec_deepal.api import client as client_module
from custom_components.dec_deepal.api.client import DeepalClient
from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.api.mqtt import client as mqtt_client


async def test_broker_disconnect_becomes_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _dropped(*_args):  # noqa: ANN202
        raise asyncio.IncompleteReadError(b"", 1)

    monkeypatch.setattr(mqtt_client, "_read_telemetry", _dropped)
    monkeypatch.setattr(mqtt_client, "_wake_vehicle", _dropped)
    with pytest.raises(ConnectionError):
        await mqtt_client.read_telemetry(None, "token", None)
    with pytest.raises(ConnectionError):
        await mqtt_client.wake_vehicle(None, "token", None)


async def test_mqtt_sessions_of_one_account_run_one_at_a_time(monkeypatch: pytest.MonkeyPatch) -> None:
    active = 0
    max_active = 0

    async def _fake_session(self, vehicle):  # noqa: ANN001, ANN202
        return SimpleNamespace(), "token"

    async def _fake_read(connection, token, ssl_context):  # noqa: ANN001, ANN202
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.05)
        active -= 1
        return "lectura"

    monkeypatch.setattr(DeepalClient, "_mqtt_session", _fake_session)
    monkeypatch.setattr(client_module, "read_telemetry", _fake_read)
    monkeypatch.setattr(client_module, "wake_vehicle", _fake_read)

    client = DeepalClient(SimpleNamespace(session=SimpleNamespace(refresh_token=None)))
    car1 = VehicleInfo(vehicle_id="1")
    car2 = VehicleInfo(vehicle_id="2")
    results = await asyncio.gather(
        client.read_mqtt(car1, None), client.read_mqtt(car2, None), client.wake(car1, None)
    )
    assert results == ["lectura", "lectura", "lectura"]
    assert max_active == 1  # nunca dos conexiones MQTT a la vez
