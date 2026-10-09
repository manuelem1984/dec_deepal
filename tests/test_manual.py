"""Prueba del manual visto desde la tarjeta (Home Assistant como intermediario)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.const import DOMAIN, OPT_MANUAL_URLS
from custom_components.dec_deepal.manual import async_register_manual, is_valid_url
from custom_components.dec_deepal.registries import load_all

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "dec_deepal"
OTHER_URL = "https://example.com/otro-manual.pdf"


def test_valid_urls() -> None:
    assert is_valid_url("https://example.com/manual.pdf")
    assert not is_valid_url("example.com/manual.pdf")
    assert not is_valid_url("javascript:alert(1)")
    assert not is_valid_url("https://example.com/con espacio.pdf")


async def test_manual_is_read_from_the_link(hass: HomeAssistant, hass_client, aioclient_mock) -> None:  # noqa: ANN001
    registries = load_all(INTEGRATION)
    s05 = registries.vehicles.get("s05_2024")
    assert s05.manual_url.startswith("https://www.changaneurope.com/")
    assert registries.vehicles.generic.manual_url == ""

    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    entry.runtime_data = SimpleNamespace(
        vehicles={
            "car1": SimpleNamespace(info=VehicleInfo(vehicle_id="car1", nickname="Changote"), model=s05),
            "car2": SimpleNamespace(
                info=VehicleInfo(vehicle_id="car2", nickname="Otro"), model=registries.vehicles.generic
            ),
        }
    )
    devices = dr.async_get(hass)
    car1 = devices.async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, "car1")})
    car2 = devices.async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, "car2")})

    assert await async_setup_component(hass, "http", {})
    async_register_manual(hass)
    client = await hass_client()
    aioclient_mock.get(s05.manual_url, content=b"%PDF-1.7 manual oficial")
    aioclient_mock.get(OTHER_URL, content=b"%PDF-1.7 otro manual")

    # --- Coche con manual en el catálogo ------------------------------------------
    response = await client.get(f"/api/dec_deepal/manual_info/{car1.id}")
    assert response.status == 200 and await response.json() == {"available": True}
    response = await client.get(f"/api/dec_deepal/manual/{car1.id}")
    assert response.status == 200
    assert response.content_type == "application/pdf"
    assert response.headers["Content-Disposition"].startswith("inline")
    assert await response.read() == b"%PDF-1.7 manual oficial"

    # --- Enlace cambiado en Configurar → Avanzado ---------------------------------------
    hass.config_entries.async_update_entry(entry, options={OPT_MANUAL_URLS: {"s05_2024": OTHER_URL}})
    response = await client.get(f"/api/dec_deepal/manual/{car1.id}")
    assert await response.read() == b"%PDF-1.7 otro manual"

    # --- Sin manual (modelo genérico) y dispositivo desconocido -----------------------------
    response = await client.get(f"/api/dec_deepal/manual_info/{car2.id}")
    assert await response.json() == {"available": False}
    assert (await client.get(f"/api/dec_deepal/manual/{car2.id}")).status == 404
    assert (await client.get("/api/dec_deepal/manual/no-existe")).status == 404

    # --- El enlace no responde bien → error claro, no una página en blanco -------------------
    aioclient_mock.clear_requests()
    aioclient_mock.get(OTHER_URL, status=404)
    assert (await client.get(f"/api/dec_deepal/manual/{car1.id}")).status == 502
