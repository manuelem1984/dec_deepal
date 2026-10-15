"""Coches nuevos y retirados de la cuenta: avisos en Reparaciones y sus asistentes."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import voluptuous_serialize
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dec_deepal import repairs
from custom_components.dec_deepal.api.errors import DeepalConnectionError
from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.const import CONF_VEHICLES, DOMAIN
from custom_components.dec_deepal.vehicle_sync import (
    added_issue_id,
    async_sync_vehicles,
    delete_issues,
    removed_issue_id,
)

CHANGOTE = VehicleInfo(vehicle_id="car1", nickname="Changote", vin="LS5A3ABE0RA000001")
CHANGUITO = VehicleInfo(vehicle_id="car2", nickname="Changuito", vin="LS5A3ABE0RA000002")
NUEVO = VehicleInfo(vehicle_id="car3", nickname="Nuevo", vin="LS5A3ABE0RA000003", license_plate="1234 ABC")


def _client(*vehicles: VehicleInfo) -> SimpleNamespace:
    return SimpleNamespace(get_vehicles=AsyncMock(return_value=list(vehicles)))


async def _run_fix(hass: HomeAssistant, issue_id: str) -> dict:
    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
    flow = await repairs.async_create_fix_flow(hass, issue_id, issue.data)
    flow.hass, flow.handler, flow.flow_id = hass, DOMAIN, "test"
    result = await flow.async_step_init({"issue_id": issue_id})
    assert result["type"] == "form" and result["step_id"] == "confirm", result
    voluptuous_serialize.convert(result["data_schema"], custom_serializer=cv.custom_serializer)
    return result, flow


async def test_new_and_removed_cars(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_VEHICLES: [CHANGOTE.to_dict(), CHANGUITO.to_dict()]}, options={}
    )
    entry.add_to_hass(hass)
    issues = ir.async_get(hass)

    # La cuenta ahora tiene Changote y uno nuevo; Changuito ya no está.
    await async_sync_vehicles(hass, entry, _client(CHANGOTE, NUEVO))
    added = issues.async_get_issue(DOMAIN, added_issue_id("car3"))
    removed = issues.async_get_issue(DOMAIN, removed_issue_id("car2"))
    assert added.translation_key == "vehicle_added" and added.is_fixable
    assert added.translation_placeholders == {"vehicle": "Nuevo"}
    assert removed.translation_key == "vehicle_removed"
    assert removed.translation_placeholders == {"vehicle": "Changuito"}
    assert issues.async_get_issue(DOMAIN, added_issue_id("car1")) is None
    assert issues.async_get_issue(DOMAIN, removed_issue_id("car1")) is None

    # Sin red no cambia nada (ni se borran los avisos).
    await async_sync_vehicles(hass, entry, SimpleNamespace(get_vehicles=AsyncMock(side_effect=DeepalConnectionError("x"))))
    assert issues.async_get_issue(DOMAIN, added_issue_id("car3")) is not None

    # Añadir el nuevo: entra en la cuenta y la integración se recarga.
    result, flow = await _run_fix(hass, added_issue_id("car3"))
    assert result["description_placeholders"] == {"vehicle": "Nuevo"}
    with patch.object(hass.config_entries, "async_schedule_reload") as reload:
        assert (await flow.async_step_confirm({}))["type"] == "create_entry"
        reload.assert_called_once_with(entry.entry_id)
    assert [item["vehicle_id"] for item in entry.data[CONF_VEHICLES]] == ["car1", "car2", "car3"]
    assert entry.data[CONF_VEHICLES][2]["license_plate"] == "1234 ABC"

    # Quitar el retirado: sale de la cuenta, con su dispositivo.
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "car2")}, name="Changuito"
    )
    result, flow = await _run_fix(hass, removed_issue_id("car2"))
    assert result["description_placeholders"] == {"vehicle": "Changuito"}
    with patch.object(hass.config_entries, "async_schedule_reload") as reload:
        await flow.async_step_confirm({})
        reload.assert_called_once_with(entry.entry_id)
    assert [item["vehicle_id"] for item in entry.data[CONF_VEHICLES]] == ["car1", "car3"]
    assert dr.async_get(hass).async_get(device.id) is None

    # La siguiente comprobación ve todo en orden: no queda ningún aviso.
    await async_sync_vehicles(hass, entry, _client(CHANGOTE, NUEVO))
    assert issues.async_get_issue(DOMAIN, added_issue_id("car3")) is None
    assert issues.async_get_issue(DOMAIN, removed_issue_id("car2")) is None


async def test_car_of_another_account_is_not_offered(hass: HomeAssistant) -> None:
    """Un coche que ya tiene otra cuenta de la integración no se ofrece dos veces."""
    other = MockConfigEntry(domain=DOMAIN, data={CONF_VEHICLES: [NUEVO.to_dict()]}, options={})
    other.add_to_hass(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_VEHICLES: [CHANGOTE.to_dict()]}, options={})
    entry.add_to_hass(hass)
    await async_sync_vehicles(hass, entry, _client(CHANGOTE, NUEVO))
    assert ir.async_get(hass).async_get_issue(DOMAIN, added_issue_id("car3")) is None


async def test_issues_go_away_with_the_account(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_VEHICLES: [CHANGOTE.to_dict()]}, options={})
    entry.add_to_hass(hass)
    await async_sync_vehicles(hass, entry, _client(NUEVO))
    delete_issues(hass, entry)
    assert not [key for key in ir.async_get(hass).issues if key[0] == DOMAIN]
