"""Puesta al día de una cuenta añadida con una versión anterior."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dec_deepal import async_migrate_entry
from custom_components.dec_deepal.const import DOMAIN


async def test_connectors_are_disabled_once(hass: HomeAssistant) -> None:
    """Versión menor 2: los conectores AC y DC pasan a desactivados, una sola vez."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, version=1, minor_version=1)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)

    def create(key: str) -> str:
        return registry.async_get_or_create(
            "binary_sensor", DOMAIN, f"car1_binary_sensor_{key}", config_entry=entry
        ).entity_id

    ac, dc, charging = create("ac_connector"), create("dc_connector"), create("charging")
    assert await async_migrate_entry(hass, entry)
    assert entry.minor_version == 2
    assert registry.async_get(ac).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert registry.async_get(dc).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert registry.async_get(charging).disabled_by is None

    # Quien los vuelva a activar a mano se los queda: ya no se tocan.
    registry.async_update_entity(ac, disabled_by=None)
    assert await async_migrate_entry(hass, entry)
    assert registry.async_get(ac).disabled_by is None
