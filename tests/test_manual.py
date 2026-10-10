"""Prueba del enlace del manual que abre la tarjeta."""

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


async def test_manual_link_for_the_card(hass: HomeAssistant, hass_client) -> None:  # noqa: ANN001
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

    # --- Coche con manual en el catálogo ------------------------------------------
    response = await client.get(f"/api/dec_deepal/manual_info/{car1.id}")
    assert response.status == 200
    assert await response.json() == {"available": True, "url": s05.manual_url, "itv": True}

    # --- Enlace cambiado en Configurar → Avanzado ---------------------------------------
    hass.config_entries.async_update_entry(entry, options={OPT_MANUAL_URLS: {"s05_2024": OTHER_URL}})
    response = await client.get(f"/api/dec_deepal/manual_info/{car1.id}")
    assert await response.json() == {"available": True, "url": OTHER_URL, "itv": True}

    # --- Sin manual (modelo genérico) y dispositivo desconocido -----------------------------
    response = await client.get(f"/api/dec_deepal/manual_info/{car2.id}")
    assert await response.json() == {"available": False, "url": None, "itv": True}
    # Un país sin módulo de ITV: la tarjeta lo sabe y oculta la opción.
    entry.runtime_data.alerts = SimpleNamespace(itv_available=False)
    response = await client.get(f"/api/dec_deepal/manual_info/{car1.id}")
    assert (await response.json())["itv"] is False
    assert (await client.get("/api/dec_deepal/manual_info/no-existe")).status == 404
