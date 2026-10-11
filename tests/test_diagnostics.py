"""Prueba del informe de diagnóstico (lo que un usuario descarga y adjunta)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.const import DOMAIN
from custom_components.dec_deepal.debug.recorder import DebugRecorder
from custom_components.dec_deepal.debug.redact import REDACTED
from custom_components.dec_deepal.diagnostics import async_get_config_entry_diagnostics
from custom_components.dec_deepal.registries import load_all
from custom_components.dec_deepal.telemetry.state import build_state

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "dec_deepal"
VIN = "LS5A3ABE0RA000001"


async def test_diagnostics_report(hass: HomeAssistant) -> None:
    registries = load_all(INTEGRATION)
    model = registries.vehicles.get("s05_2024")
    recorder = DebugRecorder(50)
    car = recorder.for_vehicle("Changote")
    car.record("command", name="climate_on", stage="rechazado", code=1032, error="Power is not off")
    car.record("change", changes=["charging: False → True", "pin_arm: locked → unlocked"])
    recorder.record("alert", vehicle="Changote", type="charge_started", targets=1, sent=1)

    state = build_state(mqtt_params={"soc": 56, "innerHumidity": 61.0}, rest_raw=None, previous=None)
    vehicle = SimpleNamespace(
        info=VehicleInfo(vehicle_id="car1", nickname="Changote", vin=VIN),
        model=model,
        trim="pro",
        color=None,
        configured=True,
        suggested_model=model,
        capabilities=None,
        official_image_status={"estado": "sin_descargar"},
        coordinator=SimpleNamespace(data=state, use_mqtt=True, last_update_success=True),
        runner=SimpleNamespace(is_armed=False),
    )
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={"pin": "pin-secreto", "pin_enabled": True})
    entry.add_to_hass(hass)
    entry.runtime_data = SimpleNamespace(
        vehicles={"car1": vehicle},
        alerts=None,
        country=SimpleNamespace(id="es"),
        recorder=recorder,
        registries=registries,
        captures={},
    )
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "car1")}
    )
    entities = er.async_get(hass)
    for domain, key, disabled in (
        ("lock", "pin_arm", None),
        ("sensor", "range", None),
        ("sensor", "cabin_humidity", er.RegistryEntryDisabler.USER),
    ):
        entities.async_get_or_create(
            domain,
            DOMAIN,
            f"car1_{domain}_{key}",
            config_entry=entry,
            device_id=device.id,
            translation_key=key,
            disabled_by=disabled,
        )
    hass.states.async_set(entities.async_get_entity_id("sensor", DOMAIN, "car1_sensor_range"), "276")

    report = await async_get_config_entry_diagnostics(hass, entry)
    json.dumps(report)  # tiene que poder guardarse tal cual

    data = report["vehiculos"]["Changote"]
    # Datos personales ocultos; el PIN no aparece por ningún lado.
    assert data["info"]["vin"] == REDACTED and VIN not in json.dumps(report)
    assert "pin-secreto" not in json.dumps(report)
    assert report["integracion"]["opciones"] == {"pin_enabled": True}

    # Qué ficha del catálogo se le aplica (un Pro: sin verificar, sin ventilación).
    assert data["ficha"]["modelo"] == "s05_2024" and data["ficha"]["version"] == "pro"
    assert data["ficha"]["verificada"] is False
    assert data["ficha"]["funciones"]["asientos_ventilacion"] is False
    assert data["ficha"]["funciones"]["porton_electrico"] is False
    assert data["ficha"]["testigos_sin_aviso"] == ["warning_airbag"]
    assert data["senales"]["cabin_humidity"] == 61.0

    # Sus entidades, por su clave interna (aunque contenga "pin", no se oculta).
    assert data["entidades"] == {
        "lock.pin_arm": "sin estado",
        "sensor.cabin_humidity": "desactivada",
        "sensor.range": "276",
    }

    # Lo que pasó: órdenes con la respuesta del servidor, cambios y avisos.
    history = report["historial"]
    assert history["ordenes"][0]["code"] == 1032 and history["ordenes"][0]["vehicle"] == "Changote"
    assert history["cambios"][0]["changes"] == ["charging: False → True", "pin_arm: locked → unlocked"]
    assert history["avisos"][0]["type"] == "charge_started"
    assert [event["kind"] for event in history["errores"]] == ["command"]
    assert len(report["registro_depuracion"]) == 3
