"""Puesta al día de una cuenta añadida con una versión anterior."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dec_deepal import async_migrate_entry
from custom_components.dec_deepal.const import DOMAIN


async def test_connectors_are_enabled_again_once(hass: HomeAssistant) -> None:
    """Versión menor 3: los conectores vuelven a estar activos, una sola vez.

    Solo los que desactivó la integración (2.5.0b7); si alguien los desactivó
    a mano, se respeta.
    """
    entry = MockConfigEntry(domain=DOMAIN, data={}, version=1, minor_version=2)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)

    def create(key: str, disabled_by: er.RegistryEntryDisabler | None) -> str:
        return registry.async_get_or_create(
            "binary_sensor",
            DOMAIN,
            f"car1_binary_sensor_{key}",
            config_entry=entry,
            disabled_by=disabled_by,
        ).entity_id

    ac = create("ac_connector", er.RegistryEntryDisabler.INTEGRATION)
    dc = create("dc_connector", er.RegistryEntryDisabler.USER)
    speed = create("speed", er.RegistryEntryDisabler.INTEGRATION)
    assert await async_migrate_entry(hass, entry)
    assert entry.minor_version == 3
    assert registry.async_get(ac).disabled_by is None
    assert registry.async_get(dc).disabled_by is er.RegistryEntryDisabler.USER
    assert registry.async_get(speed).disabled_by is er.RegistryEntryDisabler.INTEGRATION

    # Ya migrada: si después se desactiva, no se vuelve a tocar.
    registry.async_update_entity(ac, disabled_by=er.RegistryEntryDisabler.INTEGRATION)
    assert await async_migrate_entry(hass, entry)
    assert registry.async_get(ac).disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_old_accounts_keep_connectors_enabled(hass: HomeAssistant) -> None:
    """Una cuenta de antes de la 2.5.0b7 (menor 1) pasa a la 3 sin desactivarlos."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, version=1, minor_version=1)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    ac = registry.async_get_or_create(
        "binary_sensor", DOMAIN, "car1_binary_sensor_ac_connector", config_entry=entry
    ).entity_id
    assert await async_migrate_entry(hass, entry)
    assert entry.minor_version == 3
    assert registry.async_get(ac).disabled_by is None
