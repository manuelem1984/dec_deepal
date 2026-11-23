"""2.6.0b18: conexión MQTT permanente (experimental, api/mqtt/live.py), con un broker falso."""

from __future__ import annotations

import asyncio
import contextlib
import json
import struct
from collections.abc import AsyncIterator
from typing import Any

import pytest

from custom_components.dec_deepal.api.crypto import mqtt_encrypt
from custom_components.dec_deepal.api.mqtt import live as live_module
from custom_components.dec_deepal.api.mqtt.client import MqttReading
from custom_components.dec_deepal.api.mqtt.live import LiveSession
from custom_components.dec_deepal.api.mqtt.topics import MqttConnection

CONNECTION = MqttConnection(
    host="broker",
    port=8883,
    login_device_id="phone",
    vehicle_device_id="car",
    login_topic="login",
    properties_topic="props",
    subscribe_topics=("sub",),
)


def _publish(topic: str, payload: dict[str, Any]) -> bytes:
    body = struct.pack("!H", len(topic)) + topic.encode() + json.dumps(payload).encode()
    length = bytearray()
    remaining = len(body)
    while True:
        byte, remaining = remaining % 128, remaining // 128
        length.append(byte | (0x80 if remaining else 0))
        if not remaining:
            break
    return bytes([0x30]) + bytes(length) + body


class FakeWriter:
    """Lo que la sesión escribe; al cerrarla, el broker "cuelga"."""

    def __init__(self, reader: asyncio.StreamReader) -> None:
        self.reader = reader
        self.sent: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.sent.append(data)

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        if not self.reader.at_eof():
            self.reader.feed_eof()


class Broker:
    """Abre sesiones falsas; ``self.current`` es la abierta."""

    def __init__(self) -> None:
        self.opened = 0
        self.fail = 0
        self.current: tuple[asyncio.StreamReader, FakeWriter] | None = None
        self.ready = asyncio.Event()

    @contextlib.asynccontextmanager
    async def open(self) -> AsyncIterator[tuple[asyncio.StreamReader, FakeWriter, MqttConnection]]:
        self.opened += 1
        if self.fail:
            self.fail -= 1
            raise ConnectionError("el broker no deja")
        reader = asyncio.StreamReader()
        writer = FakeWriter(reader)
        self.current = (reader, writer)
        self.ready.set()
        try:
            yield reader, writer, CONNECTION
        finally:
            self.current = None
            self.ready.clear()

    def send(self, payload: dict[str, Any], topic: str = "sub") -> None:
        assert self.current is not None
        self.current[0].feed_data(_publish(topic, payload))


async def _until(check) -> None:  # noqa: ANN001
    """Espera (como mucho 2 s) a que se cumpla algo que pasa en otra tarea."""
    async with asyncio.timeout(2):
        while not check():  # noqa: ASYNC110 - en las pruebas basta con mirar cada 10 ms
            await asyncio.sleep(0.01)


@pytest.fixture(autouse=True)
def fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live_module, "BACKOFF_FIRST", 0.01)
    monkeypatch.setattr(live_module, "KICKED_WAIT", 0.05)


async def test_receives_and_accumulates_reports() -> None:
    broker = Broker()
    received: list[dict[str, Any]] = []
    session = LiveSession(broker.open, lambda reading: received.append(dict(reading.params)))
    session.start()
    await asyncio.wait_for(broker.ready.wait(), 2)
    # Respuesta al login: con la clave, pide un estado completo por la misma conexión.
    broker.send({"rs": [{"params": {"secretKey": "0123456789abcdef"}}]})
    await _until(lambda: session.connected)
    writer = broker.current[1]
    assert any(b"props" in data for data in writer.sent)

    def report(params: dict[str, Any], request_id: str) -> dict[str, Any]:
        services = [{"service_code": "car_condition", "params": params}]
        return {"r": request_id, "rs": mqtt_encrypt(services, "0123456789abcdef", request_id)}

    broker.send(report({"soc": 56, "ChrgSts": 0}, "r1"))
    broker.send(report({"leftAnteriorWindowDegree": 10}, "r2"))  # un trocito: no borra lo demás
    await _until(lambda: len(received) == 2)
    assert received[-1] == {"soc": 56, "ChrgSts": 0, "leftAnteriorWindowDegree": 10}
    assert session.stats.as_dict()["mensajes"] == 3
    await session.stop()


async def test_pause_reconnect_and_kicks() -> None:
    broker = Broker()
    session = LiveSession(broker.open, lambda _reading: None)
    session.start()
    await asyncio.wait_for(broker.ready.wait(), 2)
    # Pausa: cierra para que otro use el MQTT y vuelve a abrir al acabar.
    async with session.paused():
        assert broker.current is None and not session.stats.connected
    await asyncio.wait_for(broker.ready.wait(), 2)
    assert broker.opened == 2
    # Se cae: reintenta. Echada varias veces seguidas: lo apunta y espera más.
    broker.fail = 3
    broker.current[1].close()
    await _until(lambda: broker.opened >= 6 and broker.current is not None)
    assert session.stats.kicked >= live_module.KICKS_BEFORE_PAUSE
    assert "ConnectionError" in session.stats.last_error
    await session.stop()
    assert broker.current is None


async def test_coordinator_publishes_live_reports(hass, hass_storage) -> None:  # noqa: ANN001
    from types import SimpleNamespace

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.dec_deepal.api.models import VehicleInfo
    from custom_components.dec_deepal.const import DOMAIN
    from custom_components.dec_deepal.coordinator import VehicleCoordinator
    from custom_components.dec_deepal.debug.recorder import DebugRecorder
    from custom_components.dec_deepal.telemetry import signals as s

    broker = Broker()
    sessions: dict[str, LiveSession] = {}

    def live_session(vehicle: VehicleInfo, _ssl: Any, on_params: Any) -> LiveSession:
        sessions[vehicle.vehicle_id] = LiveSession(broker.open, on_params)
        return sessions[vehicle.vehicle_id]

    async def get_condition(_vehicle_id: str) -> dict:
        return {"vehicleStatus": {"soc": 50}}

    async def read_mqtt(*_args: Any) -> MqttReading:
        return MqttReading(params={"soc": 51})

    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    client = SimpleNamespace(get_condition=get_condition, read_mqtt=read_mqtt, live_session=live_session, live=sessions)
    coordinator = VehicleCoordinator(
        hass,
        entry,
        account=SimpleNamespace(ensure_fresh=lambda: asyncio.sleep(0)),
        client=client,
        recorder=DebugRecorder(10).for_vehicle("Changote"),
        vehicle=VehicleInfo(vehicle_id="car1", nickname="Changote"),
        use_mqtt=True,
        scan_minutes=5,
        live=True,
    )
    coordinator.data = await coordinator._fetch()  # sin conexión todavía: la lectura de siempre
    assert coordinator.data.get(s.BATTERY_LEVEL) == 51
    await coordinator.async_start_live()
    await asyncio.wait_for(broker.ready.wait(), 2)
    live = sessions["car1"]
    live.reading.params.update({"soc": 60})
    live._secret = "0123456789abcdef"  # la sesión ya está lista
    coordinator._publish_live()
    assert coordinator.data.get(s.BATTERY_LEVEL) == 60
    # Con la conexión abierta, la lectura periódica usa sus datos.
    assert (await coordinator._fetch()).get(s.BATTERY_LEVEL) == 60
    await coordinator.async_stop_live()
    assert "car1" not in sessions
