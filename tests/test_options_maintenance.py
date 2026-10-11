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

from custom_components.dec_deepal.alert_rules import CAR_ALERT_TYPES, NO_ROUTE, route_for
from custom_components.dec_deepal.alerts import AlertManager
from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.const import DOMAIN, OPT_ALERTS, OPT_MANUAL_URLS
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
        configured=True,
    )


@pytest.mark.usefixtures("enable_custom_integrations", "hass_storage")
async def test_alerts_and_maintenance_steps(hass: HomeAssistant, freezer) -> None:  # noqa: ANN001
    freezer.move_to("2027-01-22 20:00:00+00:00")
    async_mock_service(hass, "notify", "mobile_app_test")
    # Un móvil con la app: su servicio sale del nombre con que se registró.
    async_mock_service(hass, "notify", "mobile_app_iphone_de_manuel")
    MockConfigEntry(
        domain="mobile_app", title="iPhone de Manuel", data={"device_name": "iPhone de Manuel"}
    ).add_to_hass(hass)
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

    # --- Avisos: por coche, con sus destinos para cada grupo -------------------------
    flow = new_flow()
    result = await flow.async_step_alerts()
    assert result["type"] == "form" and result["step_id"] == "alerts", result  # qué coche
    _serialize(result)
    result = await flow.async_step_alerts({"vehicle": "car2"})
    assert result["type"] == "form" and result["step_id"] == "alerts_setup", result
    _serialize(result)
    assert result["description_placeholders"] == {"vehicle": "Changuito"}
    fields = {str(key): value for key, value in result["data_schema"].schema.items()}
    assert list(fields) == ["car", "car_types", "maintenance", "itv", "insurance", "all_vehicles"]
    # Se enseña el nombre del dispositivo; lo que se guarda sigue siendo el servicio.
    assert {option["value"]: option["label"] for option in fields["car"].config["options"]} == {
        "mobile_app_iphone_de_manuel": "iPhone de Manuel",
        "mobile_app_test": "notify.mobile_app_test",
        "persistent_notification": "Home Assistant notifications",
    }
    assert fields["car_types"].config["options"] == list(CAR_ALERT_TYPES)
    hers = {
        "car": ["mobile_app_test"],
        "car_types": ["charge_finished"],
        "maintenance": ["mobile_app_iphone_de_manuel", "persistent_notification"],
        "itv": ["mobile_app_iphone_de_manuel"],
        "insurance": [],
        "all_vehicles": False,
    }
    result = await flow.async_step_alerts_setup(hers)
    assert result["type"] == "create_entry"
    # Se guarda aviso a aviso (el formato del panel): cada aviso de un grupo
    # recibe los destinos de su grupo. El otro coche se escribe como estaba.
    saved = result["data"][OPT_ALERTS]["vehicles"]
    assert saved["car1"] == NO_ROUTE.to_dict()
    assert saved["car2"]["thresholds"] == {}
    notices = saved["car2"]["notices"]
    assert notices["charge_finished"] == ["mobile_app_test"] and notices["charge_started"] == []
    assert notices["maintenance_t1"] == notices["maintenance_overdue"] == hers["maintenance"]
    assert notices["itv_t2"] == hers["itv"] and notices["insurance_c1"] == []
    # Lo guardado se vuelve a leer igual en el formulario por grupos.
    route = route_for({"vehicles": saved}, "car2")
    assert list(route.group_targets("maintenance")) == hers["maintenance"]
    assert route.car_types == {"charge_finished"}
    # "Usar lo mismo en los demás coches".
    flow = new_flow()
    await flow.async_step_alerts({"vehicle": "car2"})
    result = await flow.async_step_alerts_setup({**hers, "all_vehicles": True})
    assert result["data"][OPT_ALERTS]["vehicles"]["car1"] == result["data"][OPT_ALERTS]["vehicles"]["car2"]

    # --- Avanzado: enlace del manual ------------------------------------------------
    advanced = {"scan_minutes": 5, "wake": True, "debug": False}
    flow = new_flow()
    result = await flow.async_step_advanced()
    assert result["type"] == "form" and result["step_id"] == "advanced", result
    _serialize(result)
    result = await flow.async_step_advanced({**advanced, "manual_url": "sin-protocolo.pdf"})
    assert result["errors"] == {"manual_url": "invalid_url"}
    result = await flow.async_step_advanced({**advanced, "manual_url": "https://example.com/m.pdf"})
    assert result["data"][OPT_MANUAL_URLS] == {"s05_2024": "https://example.com/m.pdf"}
    # El del catálogo, o vacío, no se guarda (se sigue el catálogo).
    result = await new_flow().async_step_advanced({**advanced, "manual_url": model.manual_url})
    assert result["data"][OPT_MANUAL_URLS] == {}
    result = await new_flow().async_step_advanced(advanced)
    assert result["data"][OPT_MANUAL_URLS] == {}

    # --- ITV ------------------------------------------------------------------------
    flow = new_flow()
    result = await flow.async_step_itv()
    assert result["type"] == "form" and result["step_id"] == "itv", result
    _serialize(result)
    result = await flow.async_step_itv({"vehicle": "car1"})
    assert result["type"] == "form" and result["step_id"] == "itv_setup", result
    _serialize(result)
    with patch.object(hass.config_entries, "async_schedule_reload") as reload:
        result = await flow.async_step_itv_setup({"enabled": True, "registration_date": "2022-11-26"})
        assert result["type"] == "create_entry"
        reload.assert_called_once_with(entry.entry_id)
    assert manager.itv_status("car1").due_date.isoformat() == "2026-11-26"
    assert manager.itv_record("car2") is None
    # Fecha a mano distinta de la calculada: se respeta. Igual a la calculada: no se guarda.
    flow = new_flow()
    await flow.async_step_itv({"vehicle": "car1"})
    with patch.object(hass.config_entries, "async_schedule_reload") as reload:
        await flow.async_step_itv_setup(
            {"enabled": True, "registration_date": "2022-11-26", "next_itv_date": "2026-10-01"}
        )
        reload.assert_not_called()
    assert manager.itv_record("car1").next_override.isoformat() == "2026-10-01"
    flow = new_flow()
    await flow.async_step_itv({"vehicle": "car1"})
    result = await flow.async_step_itv_setup()
    _serialize(result)
    await flow.async_step_itv_setup(
        {"enabled": True, "registration_date": "2022-11-26", "next_itv_date": "2026-11-26"}
    )
    assert manager.itv_record("car1").next_override is None

    # --- Seguro ---------------------------------------------------------------------
    flow = new_flow()
    result = await flow.async_step_insurance({"vehicle": "car1"})
    assert result["type"] == "form" and result["step_id"] == "insurance_setup", result
    _serialize(result)
    with patch.object(hass.config_entries, "async_schedule_reload"):
        result = await flow.async_step_insurance_setup(
            {
                "enabled": True,
                "company": " Mutua Ejemplo ",
                "policy": "0123 4567 89",
                "insurance_kind": "comprehensive_excess",
                "renewal_date": "2027-03-14",
                "notice_days": 30,
                "phone_assistance": "900 000 000",
            }
        )
    assert result["type"] == "create_entry"
    insurance = manager.insurance_record("car1")
    assert (insurance.company, insurance.policy, insurance.phone_company) == ("Mutua Ejemplo", "0123 4567 89", "")
    assert manager.insurance_status("car1").cancel_deadline.isoformat() == "2027-02-12"
    # La póliza no sale en los diagnósticos.
    assert "0123" not in str(manager.diagnostics("car1"))
    flow = new_flow()
    await flow.async_step_insurance({"vehicle": "car1"})
    result = await flow.async_step_insurance_setup()
    _serialize(result)

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
