"""2.6.0b17: diario del coche (viajes y cargas con energía y coste), Registro y estadísticas."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.dec_deepal import car_log
from custom_components.dec_deepal.const import DOMAIN
from custom_components.dec_deepal.logbook import describe
from custom_components.dec_deepal.telemetry import signals as s

from .test_plan_carga import _setup, server  # noqa: F401 - fixture

T0 = datetime.fromisoformat("2027-01-25T08:00:00+01:00")


def _read(log: dict, minutes: int, **values: object) -> list[dict]:
    return car_log.update(log, values, T0 + timedelta(minutes=minutes), 68.8)


def test_trips_are_logged_from_power_on_to_off() -> None:
    log = car_log.empty()
    assert _read(log, 0, power_on=True, odometer_km=1000.0, battery_level=80) == []
    assert "trip" in log
    done = _read(log, 40, power_on=False, odometer_km=1042.4, battery_level=72)
    assert done == [
        {
            "kind": "trip", "start": "2027-01-25T08:00:00+01:00", "end": "2027-01-25T08:40:00+01:00",
            "km": 42.4, "start_level": 80, "end_level": 72, "kwh": 5.5,
        }
    ]  # fmt: skip
    assert log["totals"]["trip_km"] == 42.4
    # Encender para climatizar sin moverse: no es un viaje.
    _read(log, 60, power_on=True, odometer_km=1042.4)
    assert _read(log, 70, power_on=False, odometer_km=1042.4) == []
    # Sin saber si está encendido, no se toca nada.
    assert _read(log, 80, odometer_km=1100.0) == [] and "trip" not in log


def test_charges_with_cost_and_without_a_charger() -> None:
    log = car_log.empty()
    log["prices"] = {"ac": 0.15, "dc": 0.45}
    _read(log, 0, charging=True, battery_level=40)
    done = _read(log, 300, charging=False, battery_level=80)
    assert done[0]["type"] == "ac" and done[0]["kwh"] == 27.52 and done[0]["cost"] == 4.13
    # Carga rápida: el precio de la rápida.
    _read(log, 400, charging=True, battery_level=20, dc=True)
    done = _read(log, 430, charging=False, battery_level=70)
    assert done[0]["type"] == "dc" and done[0]["cost"] == round(34.4 * 0.45, 2)
    assert log["totals"] == {"trip_km": 0.0, "charge_kwh": 61.92, "charge_cost": 19.61}
    # El coche dudando al enchufar (segundos, sin ganar batería): no cuenta.
    _read(log, 500, charging=True, battery_level=70)
    assert _read(log, 501, charging=False, battery_level=70) == []
    assert car_log.month_summary(log, 2027, 1) == {"viajes": 0, "km": 0.0, "cargas": 2, "kwh": 61.92, "coste": 19.61}


def test_consumption_and_cleaning() -> None:
    log = car_log.empty()
    for i in range(3):
        _read(log, i * 100, power_on=True, odometer_km=1000.0 + i * 100, battery_level=80)
        _read(log, i * 100 + 50, power_on=False, odometer_km=1050.0 + i * 100, battery_level=70)
    assert car_log.consumption(log) == 13.8  # 6,88 kWh cada 50 km
    assert car_log.last(log, car_log.KIND_TRIP)["km"] == 50.0
    # Lo guardado roto no rompe nada.
    assert car_log.clean({"entries": [{"kind": "x"}, "y"], "totals": {"trip_km": -5}, "prices": {"ac": "z"}}) == car_log.empty()


def test_logbook_text() -> None:
    trip = {"kind": "trip", "km": 42.4, "start_level": 80, "end_level": 72, "kwh": 5.5}
    assert describe(trip, "es") == "Viaje de 42,4 km (batería del 80 % al 72 %) · 5,5 kWh."
    charge = {"kind": "charge", "type": "dc", "start_level": 20, "end_level": 70, "kwh": 34.4, "cost": 15.48}
    assert describe(charge, "en", "EUR") == "Fast charge from 20 % to 70 % · 34.4 kWh · 15.48 EUR."


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_car_log_in_home_assistant(hass: HomeAssistant, server: dict) -> None:  # noqa: F811
    hass.config.currency = "EUR"
    await _setup(hass)
    registry = er.async_get(hass)
    ids = {
        e.translation_key: e.entity_id
        for e in registry.entities.values()
        if e.platform == DOMAIN
        and e.translation_key in ("charged_energy", "charging_cost", "average_consumption", "last_trip", "charge_price_home", "charge_price_fast")
    }
    assert len(ids) == 6
    assert hass.states.get(ids["charged_energy"]).state == "0.0"
    assert hass.states.get(ids["charged_energy"]).attributes["state_class"] == "total_increasing"

    await hass.services.async_call("number", "set_value", {"entity_id": ids["charge_price_home"], "value": 0.2}, blocking=True)
    assert float(hass.states.get(ids["charge_price_home"]).state) == 0.2

    # Una carga, contada desde las lecturas del coche.
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    vehicle = entry.runtime_data.vehicles["car1"]
    events = []
    hass.bus.async_listen(f"{DOMAIN}_car_log", events.append)
    manager = entry.runtime_data.car_log
    coordinator = vehicle.coordinator

    def push(minutes: int, **values: object) -> None:
        state = coordinator.data
        coordinator.async_set_updated_data(
            type(state)(values={**state.values, **values}, sources=dict(state.sources))
        )
        manager._on_update("car1", T0 + timedelta(minutes=minutes))

    push(0, **{s.CHARGING: True, s.BATTERY_LEVEL: 40})
    push(240, **{s.CHARGING: False, s.BATTERY_LEVEL: 80})
    await hass.async_block_till_done()
    assert events and events[-1].data["kind"] == "charge" and events[-1].data["cost"] == 5.5  # 27,52 kWh x 0,2
    assert float(hass.states.get(ids["charged_energy"]).state) == 27.52
    assert float(hass.states.get(ids["charging_cost"]).state) == 5.5

    # Exportar el diario.
    device_id = registry.async_get(ids["charged_energy"]).device_id
    response = await hass.services.async_call(
        DOMAIN, "export_car_log", {"device_id": device_id}, blocking=True, return_response=True
    )
    assert response["totales"]["charge_kwh"] == 27.52 and response["entradas"][-1]["type"] == "ac"
