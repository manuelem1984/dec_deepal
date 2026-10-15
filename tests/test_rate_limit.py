"""El servidor pide esperar (HTTP 429): se respeta su ``Retry-After``."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dec_deepal.api.errors import DeepalRateLimitError
from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.api.session import DeepalSession
from custom_components.dec_deepal.api.transport import (
    CountryProfile,
    DeepalTransport,
    retry_after_seconds,
)
from custom_components.dec_deepal.const import DOMAIN
from custom_components.dec_deepal.coordinator import VehicleCoordinator
from custom_components.dec_deepal.debug.recorder import DebugRecorder

PROFILE = CountryProfile("es", "ES", "en_US", "https://intl", "https://ca", "https://sda")


def test_retry_after_header() -> None:
    assert retry_after_seconds("120") == 120.0
    assert retry_after_seconds(None) is None and retry_after_seconds("pronto") is None
    later = format_datetime(datetime.now(UTC) + timedelta(minutes=10), usegmt=True)
    assert 590 <= retry_after_seconds(later) <= 600
    assert retry_after_seconds("-5") == 0.0


class _Response:
    def __init__(self, status: int, headers: dict[str, str], body: Any) -> None:
        self.status, self.headers, self._body = status, headers, body

    async def json(self, content_type: Any = None) -> Any:
        return self._body

    async def __aenter__(self) -> _Response:
        return self

    async def __aexit__(self, *_args: Any) -> None:
        return None


class _Http:
    def __init__(self, response: _Response) -> None:
        self.response = response

    def post(self, *_args: Any, **_kwargs: Any) -> _Response:
        return self.response


async def test_transport_raises_with_the_wait() -> None:
    http = _Http(_Response(429, {"Retry-After": "900"}, None))
    transport = DeepalTransport(http, PROFILE, DeepalSession(device_id="dev"))
    with pytest.raises(DeepalRateLimitError) as caught:
        await transport.post("/condition", {})
    assert caught.value.status == 429 and caught.value.retry_after == 900.0


async def test_coordinator_waits_what_the_server_asks(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    waits = iter((900.0, 10.0, None))

    async def get_condition(_vehicle_id: str) -> dict:
        raise DeepalRateLimitError("HTTP 429", status=429, retry_after=next(waits))

    async def ensure_fresh() -> None:
        return None

    coordinator = VehicleCoordinator(
        hass,
        entry,
        account=SimpleNamespace(ensure_fresh=ensure_fresh),
        client=SimpleNamespace(get_condition=get_condition),
        recorder=DebugRecorder(10).for_vehicle("Changote"),
        vehicle=VehicleInfo(vehicle_id="car1", nickname="Changote"),
        use_mqtt=False,
        scan_minutes=5,
    )
    # Lo que pide el servidor, si es más que el intervalo normal...
    with pytest.raises(UpdateFailed) as caught:
        await coordinator._async_update_data()
    assert caught.value.retry_after == 900.0
    # ...y nunca menos que el intervalo normal (5 min), lo diga o no.
    for _ in range(2):
        with pytest.raises(UpdateFailed) as caught:
            await coordinator._async_update_data()
        assert caught.value.retry_after == 300.0
