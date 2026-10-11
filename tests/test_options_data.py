"""Prueba del apartado "Datos de los coches" de Configurar: copia y borrado."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import voluptuous_serialize
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dec_deepal import vehicle_data as vd
from custom_components.dec_deepal.alerts import AlertManager
from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.const import DOMAIN, EXPORT_API
from custom_components.dec_deepal.documents import InsuranceRecord
from custom_components.dec_deepal.maintenance import MaintenanceRecord
from custom_components.dec_deepal.options_flow import DecDeepalOptionsFlow
from custom_components.dec_deepal.registries import load_all
from custom_components.dec_deepal.telemetry import signals as s
from custom_components.dec_deepal.vehicle_store import async_get_store, async_register_export

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "dec_deepal"
VIN = "LS5A3ABE0RA000001"
READ = "custom_components.dec_deepal.options_flow._read_upload"


def _vehicle(model, vehicle_id: str, name: str, vin: str):  # noqa: ANN001, ANN202
    values = {s.ODOMETER_KM: 37500}
    return SimpleNamespace(
        info=VehicleInfo(vehicle_id=vehicle_id, nickname=name, vin=vin),
        coordinator=SimpleNamespace(
            data=SimpleNamespace(get=values.get), async_add_listener=lambda _cb: lambda: None
        ),
        model=model,
        trim="max",
        color=None,
        wheels=None,
        # Sin modelo elegido todavía: no hay apariencia que guardar.
        configured=False,
    )


@pytest.mark.usefixtures("enable_custom_integrations", "hass_storage")
async def test_backup_and_delete(
    hass: HomeAssistant, hass_client_no_auth, freezer  # noqa: ANN001
) -> None:
    freezer.move_to("2027-01-22 20:00:00+00:00")
    assert await async_setup_component(hass, "http", {})
    async_register_export(hass)
    model = load_all(INTEGRATION).vehicles.get("s05_2024")
    color = next(iter(model.colors))
    vehicles = {"car1": _vehicle(model, "car1", "Changote", VIN)}
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    manager = AlertManager(hass, entry.entry_id, {}, vehicles)
    await manager.async_load()
    registries = load_all(INTEGRATION)
    entry.runtime_data = SimpleNamespace(vehicles=vehicles, alerts=manager, registries=registries)

    def new_flow() -> DecDeepalOptionsFlow:
        flow = DecDeepalOptionsFlow()
        flow.hass = hass
        flow.handler = entry.entry_id
        flow.flow_id = "test"
        return flow

    result = await new_flow().async_step_data()
    assert result["type"] == "menu"
    assert result["menu_options"] == ["data_export", "data_import", "data_delete"]
    # Sin nada guardado no hay copia que descargar ni datos que borrar.
    assert (await new_flow().async_step_data_export())["reason"] == "no_data"
    assert (await new_flow().async_step_data_delete())["reason"] == "no_data"

    await manager.async_set_record(
        "car1", MaintenanceRecord(services_done=1, last_date=date(2026, 3, 10), last_km=19500)
    )
    await manager.async_set_insurance(
        "car1", InsuranceRecord(renewal_date=date(2027, 6, 1), company="Mutua", policy="0123")
    )

    # --- Descargar --------------------------------------------------------------
    result = await new_flow().async_step_data_export()
    assert result["type"] == "form" and result["step_id"] == "data_export", result
    voluptuous_serialize.convert(result["data_schema"], custom_serializer=cv.custom_serializer)
    assert result["description_placeholders"]["cars"] == "Changote (…000001)"
    url = result["description_placeholders"]["url"]
    # El enlace va firmado: se descarga sin iniciar sesión (y caduca).
    assert url.startswith(f"{EXPORT_API}?authSig=")
    anonymous = await hass_client_no_auth()
    response = await anonymous.get(url)
    assert response.status == 200
    assert "attachment" in response.headers["Content-Disposition"]
    backup = await response.json()
    assert backup["formato"] == vd.EXPORT_FORMAT
    assert backup["coches"][VIN]["insurance"]["policy"] == "0123"
    # Sin la firma (o con una firma tocada) no se descarga nada.
    assert (await anonymous.get(EXPORT_API)).status == 401
    assert (await anonymous.get(url[:-4] + "xxxx")).status == 401

    with patch.object(hass.config_entries, "async_schedule_reload") as reload:
        # --- Borrar: hay que elegir y confirmar -------------------------------------
        flow = new_flow()
        result = await flow.async_step_data_delete()
        assert result["type"] == "form", result
        voluptuous_serialize.convert(result["data_schema"], custom_serializer=cv.custom_serializer)
        result = await flow.async_step_data_delete({"cars": [], "confirm": True})
        assert result["errors"] == {"cars": "no_selection"}
        result = await flow.async_step_data_delete({"cars": [VIN], "confirm": False})
        assert result["errors"] == {"confirm": "confirm_required"}
        assert manager.record("car1") is not None
        result = await flow.async_step_data_delete({"cars": [VIN], "confirm": True})
        assert result["type"] == "abort" and result["reason"] == "data_deleted"
        assert result["description_placeholders"] == {"cars": "Changote (…000001)"}
        assert manager.record("car1") is None and manager.insurance_record("car1") is None
        assert VIN not in async_get_store(hass).cars()
        reload.assert_called_once_with(entry.entry_id)

        # --- Cargar: un fichero malo no cambia nada; la copia lo devuelve todo -------
        flow = new_flow()
        result = await flow.async_step_data_import()
        assert result["type"] == "form" and result["step_id"] == "data_import", result
        voluptuous_serialize.convert(result["data_schema"], custom_serializer=cv.custom_serializer)
        with patch(READ, return_value={"otra": "cosa"}):
            result = await flow.async_step_data_import({"file": "id"})
        assert result["errors"] == {"file": "invalid_file"}
        with patch(READ, return_value={**backup, "version": 99}):
            result = await flow.async_step_data_import({"file": "id"})
        assert result["errors"] == {"file": "newer_file"}
        assert manager.record("car1") is None
        with patch(READ, return_value=backup):
            result = await flow.async_step_data_import({"file": "id"})
        assert result["type"] == "abort" and result["reason"] == "data_imported"
        assert manager.record("car1").last_km == 19500
        assert manager.insurance_record("car1").policy == "0123"
        assert reload.call_count == 2

        # --- La apariencia viaja en la copia y vuelve a las opciones de la cuenta ---
        vehicles["car1"].configured = True
        vehicles["car1"].color = color
        await new_flow().async_step_data_export()  # vuelca lo pendiente al almacén
        saved = async_get_store(hass).export()["coches"][VIN]["appearance"]
        assert saved == {"model": "s05_2024", "trim": "max", "color": color}
        other = {"model": "s05_2024", "trim": "pro", "color": "no-existe"}
        with patch(READ, return_value={**backup, "coches": {VIN: {"appearance": other}}}):
            result = await new_flow().async_step_data_import({"file": "id"})
        assert result["reason"] == "data_imported"
        # Lo que el catálogo no tiene (ese color) se descarta; el resto se aplica.
        assert entry.options["appearance"] == {
            "car1": {"model": "s05_2024", "trim": "pro", "color": None}
        }
        # Las opciones han cambiado: la cuenta se recarga sola, no hace falta pedirlo.
        assert reload.call_count == 2
        # La copia manda: el coche queda como en el fichero (aquí, sin fichas).
        assert manager.record("car1") is None
    await manager.async_stop()

