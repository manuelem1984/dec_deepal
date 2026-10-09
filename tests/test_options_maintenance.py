"""Prueba de los apartados "Avisos" y "Mantenimiento" de Configurar.

Recorre los pasos como lo hace Home Assistant (incluida la serialización de
cada formulario para el navegador), con coches falsos y el gestor real.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import voluptuous_serialize
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.dec_deepal.alerts import AlertManager
from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.const import DOMAIN, OPT_ALERTS
from custom_components.dec_deepal.options_flow import DecDeepalOptionsFlow
from custom_components.dec_deepal.registries import load_all
from custom_components.dec_deepal.telemetry import signals as s

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "dec_deepal"


def _serialize(result: dict) -> None:
    """Lo mismo que hace HA antes de mandar el formulario al navegador."""
    if result.get("data_schema") is not None:
        voluptuous_serialize.convert(result["data_schema"], custom_serializer=cv.custom_serializer)


def _vehicle(model, vehicle_id: str, name: str):  # noqa: ANN001, ANN202
    values = {s.ODOMETER_KM: 37500}
    return SimpleNamespace(
        info=VehicleInfo(vehicle_id=vehicle_id, nickname=name),
        coordinator=SimpleNamespace(
            data=SimpleNamespace(get=values.get), async_add_listener=lambda _cb: lambda: None
        ),
        model=model,
        trim="max",
    )


@pytest.mark.usefixtures("enable_custom_integrations", "hass_storage")
async def test_alerts_and_maintenance_steps(hass: HomeAssistant, freezer) -> None:  # noqa: ANN001
    freezer.move_to("2027-01-22 20:00:00+00:00")
    async_mock_service(hass, "notify", "mobile_app_test")
    model = load_all(INTEGRATION).vehicles.get("s05_2024")
    vehicles = {"car1": _vehicle(model, "car1", "Changote"), "car2": _vehicle(model, "car2", "Changuito")}
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    manager = AlertManager(hass, entry.entry_id, {}, vehicles)
    await manager.async_load()
    manager.async_start()
    entry.runtime_data = SimpleNamespace(vehicles=vehicles, alerts=manager)

    def new_flow() -> DecDeepalOptionsFlow:
        flow = DecDeepalOptionsFlow()
        flow.hass = hass
        flow.handler = entry.entry_id
        flow.flow_id = "test"
        return flow

    # --- Avisos ------------------------------------------------------------------
    flow = new_flow()
    result = await flow.async_step_alerts()
    assert result["type"] == "form" and result["step_id"] == "alerts", result
    _serialize(result)
    result = await flow.async_step_alerts(
        {"targets": ["mobile_app_test"], "types": ["charge_finished"], "persistent": False}
    )
    assert result["type"] == "create_entry"
    assert result["data"][OPT_ALERTS] == {
        "targets": ["mobile_app_test"],
        "types": ["charge_finished"],
        "persistent": False,
    }

    # --- Mantenimiento: elegir coche → ficha (aún sin configurar) --------------------
    flow = new_flow()
    result = await flow.async_step_maintenance()
    assert result["type"] == "form" and result["step_id"] == "maintenance", result
    _serialize(result)
    result = await flow.async_step_maintenance({"vehicle": "car2"})
    assert result["type"] == "form" and result["step_id"] == "maintenance_setup", result
    _serialize(result)
    with patch.object(hass.config_entries, "async_schedule_reload") as reload:
        result = await flow.async_step_maintenance_setup(
            {
                "maintenance_enabled": True,
                "services_done": 1,
                "last_date": "2026-03-10",
                "last_km": 19500,
                "interval_km": 20000,
                "interval_months": 12,
            }
        )
    assert result["type"] == "create_entry"
    reload.assert_called_once_with(entry.entry_id)  # hay que crear las entidades
    assert manager.record("car1") is None
    assert manager.status("car2").days_left == 47 and manager.status("car2").km_left == 2000

    # --- Coche ya configurado: menú → registrar ---------------------------------------
    flow = new_flow()
    result = await flow.async_step_maintenance({"vehicle": "car2"})
    assert result["type"] == "menu" and result["step_id"] == "maintenance_menu", result
    assert "2ª" in result["description_placeholders"]["summary"] or "2nd" in result[
        "description_placeholders"
    ]["summary"]
    result = await flow.async_step_maintenance_register()
    assert result["type"] == "form" and result["step_id"] == "maintenance_register", result
    _serialize(result)
    result = await flow.async_step_maintenance_register(
        {"service_date": "2027-01-20", "service_km": 37400}
    )
    assert result["type"] == "create_entry"
    assert manager.record("car2").services_done == 2
    assert manager.status("car2").number == 3

    # --- Corregir (sin recargar) y desactivar (recarga) ---------------------------------
    flow = new_flow()
    await flow.async_step_maintenance({"vehicle": "car2"})
    result = await flow.async_step_maintenance_setup()
    assert result["type"] == "form", result
    _serialize(result)
    with patch.object(hass.config_entries, "async_schedule_reload") as reload:
        await flow.async_step_maintenance_setup(
            {
                "maintenance_enabled": True,
                "services_done": 2,
                "last_date": "2027-01-21",
                "last_km": 37450,
                "interval_km": 15000,
                "interval_months": 12,
            }
        )
        reload.assert_not_called()
        assert manager.record("car2").interval_km == 15000
        assert manager.record("car2").history[-1]["number"] == 2
        flow = new_flow()
        await flow.async_step_maintenance({"vehicle": "car2"})
        await flow.async_step_maintenance_setup(
            {
                "maintenance_enabled": False,
                "services_done": 2,
                "last_date": "2027-01-21",
                "last_km": 37450,
                "interval_km": 15000,
                "interval_months": 12,
            }
        )
        reload.assert_called_once_with(entry.entry_id)
    assert manager.record("car2") is None
    await manager.async_stop()
