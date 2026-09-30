"""Prueba del asistente de Reparaciones "Configura tu vehículo".

Ejecuta el flujo como lo hace Home Assistant (crear el flujo, paso ``init``,
serializar el formulario para el navegador, paso ``details`` y guardar), con
un "runtime" falso en vez de la integración completa.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import voluptuous_serialize
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dec_deepal import repairs
from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.const import DOMAIN, OPT_APPEARANCE
from custom_components.dec_deepal.registries import load_all

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "dec_deepal"


def _serialize(result: dict) -> None:
    """Lo mismo que hace HA antes de mandar el formulario al navegador."""
    if result.get("data_schema") is not None:
        voluptuous_serialize.convert(result["data_schema"], custom_serializer=cv.custom_serializer)


async def test_vehicle_setup_fix_flow(hass: HomeAssistant) -> None:
    registries = load_all(INTEGRATION)
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    entry.runtime_data = SimpleNamespace(
        country=SimpleNamespace(id="es"),
        vehicles={
            "car1": SimpleNamespace(
                info=VehicleInfo(vehicle_id="car1", nickname="Changote", series_name="S05"),
                suggested_model=registries.vehicles.get("s05_2024"),
                capabilities=None,
            )
        },
    )

    flow = await repairs.async_create_fix_flow(
        hass, "vehicle_not_configured_car1", {"entry_id": entry.entry_id, "vehicle_id": "car1"}
    )
    flow.hass = hass
    flow.handler = DOMAIN
    flow.flow_id = "test"

    result = await flow.async_step_init()
    assert result["type"] == "form", result
    _serialize(result)

    result = await flow.async_step_init({"model": "s05_2024"})
    assert result["type"] == "form" and result["step_id"] == "details", result
    _serialize(result)

    result = await flow.async_step_details({"trim": "max", "color": "ganymade_grey"})
    assert result["type"] == "create_entry", result
    assert entry.options[OPT_APPEARANCE]["car1"] == {
        "model": "s05_2024",
        "trim": "max",
        "color": "ganymade_grey",
    }
