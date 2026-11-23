"""2.6.0b17: datos falsos al despertar el coche, tope del PHEV, espera de los
testigos al encender, testigos del REST, último estado tras reiniciar y la
API nativa de temperatura de Home Assistant 2026.11."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.climate import DecClimate
from custom_components.dec_deepal.const import DOMAIN
from custom_components.dec_deepal.coordinator import VehicleCoordinator
from custom_components.dec_deepal.debug.recorder import DebugRecorder
from custom_components.dec_deepal.last_state import LastStateStore
from custom_components.dec_deepal.telemetry import converters as c
from custom_components.dec_deepal.telemetry import signals as s
from custom_components.dec_deepal.telemetry.mqtt_map import map_mqtt
from custom_components.dec_deepal.telemetry.rest_map import map_rest
from custom_components.dec_deepal.telemetry.state import SOURCE_PREVIOUS, build_state

T0 = datetime(2026, 11, 23, 10, 0, tzinfo=UTC)


# --- Valores de arranque de los módulos ----------------------------------------------------------


def test_zero_tire_pressure_is_not_a_reading() -> None:
    assert c.tire_pressure(0) is None
    assert c.tire_pressure("0.0") is None
    assert c.tire_pressure(250) == 250.0
    assert s.TIRE_PRESSURE_FRONT_LEFT not in map_mqtt({"lfTyrePressure": 0})
    assert map_rest({"tire": {"leftFront": {"pressure": 0}}}).get(s.TIRE_PRESSURE_FRONT_LEFT) is None


def test_tire_pressure_kept_while_the_module_wakes() -> None:
    before = build_state(mqtt_params={"lfTyrePressure": 250}, rest_raw=None, previous=None)
    woken = build_state(mqtt_params={"lfTyrePressure": 0}, rest_raw=None, previous=before)
    assert woken.get(s.TIRE_PRESSURE_FRONT_LEFT) == 250.0
    assert woken.source(s.TIRE_PRESSURE_FRONT_LEFT) == SOURCE_PREVIOUS


def test_impossible_climate_target_is_dropped() -> None:
    assert c.target_temp(22) == 22.0
    assert c.target_temp(0) is None
    assert c.target_temp(127) is None
    assert s.CLIMATE_TARGET_C not in map_mqtt({"airConditioningSetTemperature": 0})
    # El REST la da en décimas.
    assert map_rest({"hvac": {"remoteTemp": 225}})[s.CLIMATE_TARGET_C] == 22.5
    assert map_rest({"hvac": {"remoteTemp": 1270}}).get(s.CLIMATE_TARGET_C) is None


def test_dc_wake_sentinel_is_dropped() -> None:
    # Sin estado de carga: -400 A en DC no es una corriente (saldría 400 A).
    values = map_mqtt({"BattDCChrgInCurr": -400, "BattACChrgInCurr": 0})
    assert s.DC_CHARGE_CURRENT not in values
    assert values[s.CHARGE_CURRENT] == 0.0
    # Cargando en AC: la de DC se descarta del todo (no 0 A, no la mandó de verdad).
    values = map_mqtt({"ChrgSts": 3, "BattDCChrgInCurr": -400, "BattACChrgInCurr": -16})
    assert s.DC_CHARGE_CURRENT not in values
    assert values[s.CHARGE_CURRENT] == 16.0
    # Cargando en DC, -400 A sí es la corriente.
    assert map_mqtt({"ChrgSts": 4, "BattDCChrgInCurr": -400})[s.CHARGE_CURRENT] == 400.0


def test_zero_minutes_without_charging_is_unknown() -> None:
    idle = build_state(mqtt_params={"ChrgSts": 0, "chargDeltMins": 0}, rest_raw=None, previous=None)
    assert idle.get(s.REMAINING_CHARGE_MIN) is None
    charging = build_state(mqtt_params={"ChrgSts": 3, "chargDeltMins": 0}, rest_raw=None, previous=None)
    assert charging.get(s.REMAINING_CHARGE_MIN) == 0
    busy = build_state(mqtt_params={"ChrgSts": 3, "chargDeltMins": 45}, rest_raw=None, previous=None)
    assert busy.get(s.REMAINING_CHARGE_MIN) == 45


# --- Testigos: espera de arranque y registros del REST -------------------------------------------


def test_ready_window_after_power_on() -> None:
    off = build_state(mqtt_params={"powerStatusFeedBack": 0}, rest_raw=None, previous=None, now=T0)
    assert off.power_on_since is None
    first = build_state(
        mqtt_params={"powerStatusFeedBack": 2, "brakeLightStatus": 1}, rest_raw=None, previous=off, now=T0
    )
    assert first.power_on_since == T0
    assert first.get(s.WARNING_BRAKE) is None  # comprobación de arranque
    later = build_state(
        mqtt_params={"powerStatusFeedBack": 2, "brakeLightStatus": 1},
        rest_raw=None,
        previous=first,
        now=T0 + timedelta(seconds=60),
    )
    assert later.power_on_since == T0  # se mantiene mientras siga encendido
    assert later.get(s.WARNING_BRAKE) is True


def test_rest_subsystem_registers_drive_airbag_abs_eps() -> None:
    values = map_rest(
        {"vehicleStatus": {"airBagSysStatus": 0, "absAntiLockBrakingSysStatus": 1, "powerSteeringSysStatus": 0}}
    )
    assert values[s.WARNING_AIRBAG] is False
    assert values[s.WARNING_ABS] is True
    assert values[s.WARNING_EPS] is False
    # El REST manda sobre el bit del MQTT (que se enciende sin motivo en un coche sano).
    started = build_state(mqtt_params={"powerStatusFeedBack": 2}, rest_raw=None, previous=None, now=T0)
    state = build_state(
        mqtt_params={"powerStatusFeedBack": 2, "airBagLightStatus": 1},
        rest_raw={"vehicleStatus": {"airBagSysStatus": 0}},
        previous=started,
        now=T0 + timedelta(minutes=2),
    )
    assert state.get(s.WARNING_AIRBAG) is False


# --- Coordinador: tope del PHEV y último estado guardado -----------------------------------------


def _coordinator(hass: HomeAssistant, rest: dict, **kwargs: Any) -> VehicleCoordinator:
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)

    async def get_condition(_vehicle_id: str) -> dict:
        return rest

    async def ensure_fresh() -> None:
        return None

    return VehicleCoordinator(
        hass,
        entry,
        account=SimpleNamespace(ensure_fresh=ensure_fresh),
        client=SimpleNamespace(get_condition=get_condition),
        recorder=DebugRecorder(10).for_vehicle("Changote"),
        vehicle=VehicleInfo(vehicle_id="car1", nickname="Changote"),
        use_mqtt=False,
        scan_minutes=5,
        **kwargs,
    )


async def test_phev_rejects_impossible_currents(hass: HomeAssistant) -> None:
    rest = {"charge": {"chargeStatus": 1}}
    coordinator = _coordinator(hass, rest, max_charge_current=c.PHEV_MAX_CHARGE_CURRENT_A)
    state = await coordinator._fetch()
    state.values[s.DC_CHARGE_CURRENT] = 300.0
    coordinator._drop_impossible_currents(state)
    assert s.DC_CHARGE_CURRENT not in state.values
    state.values[s.AC_CHARGE_CURRENT] = 16.0
    coordinator._drop_impossible_currents(state)
    assert state.values[s.AC_CHARGE_CURRENT] == 16.0


async def test_last_state_survives_a_restart(hass: HomeAssistant, hass_storage: dict) -> None:
    store = LastStateStore(hass)
    await store.async_load()
    before = build_state(
        mqtt_params={"lfTyrePressure": 250, "steeringWheelHeating": 1, "soc": 80},
        rest_raw=None,
        previous=None,
    )
    store.remember("car1", before)
    assert store.restored("car1").values[s.TIRE_PRESSURE_FRONT_LEFT] == 250.0
    assert s.BATTERY_LEVEL not in store.restored("car1").values  # solo lo que se conserva

    # "Reinicio": almacén nuevo con lo escrito en disco; el coche, dormido, no manda las ruedas.
    await hass.async_block_till_done()
    hass_storage["dec_deepal.last_state"] = {
        "version": 1,
        "minor_version": 1,
        "key": "dec_deepal.last_state",
        "data": {"car1": store.restored("car1").values},
    }
    fresh = LastStateStore(hass)
    await fresh.async_load()
    coordinator = _coordinator(hass, {"vehicleStatus": {"soc": 70}}, last_states=fresh)
    state = await coordinator._fetch()
    assert state.get(s.TIRE_PRESSURE_FRONT_LEFT) == 250.0
    assert state.get(s.STEERING_WHEEL_HEAT) is True
    assert state.source(s.TIRE_PRESSURE_FRONT_LEFT) == SOURCE_PREVIOUS
    assert state.get(s.BATTERY_LEVEL) == 70


async def test_last_state_ignores_garbage(hass: HomeAssistant, hass_storage: dict) -> None:
    hass_storage["dec_deepal.last_state"] = {
        "version": 1,
        "minor_version": 1,
        "key": "dec_deepal.last_state",
        "data": {"car1": {"unknown_signal": 1, s.ODOMETER_KM: [1, 2]}, "car2": "x"},
    }
    store = LastStateStore(hass)
    await store.async_load()
    assert store.restored("car1") is None
    assert store.restored("car2") is None
    assert store.restored("car3") is None


# --- Clima: los dos juegos de nombres ------------------------------------------------------------


def test_climate_exposes_native_and_legacy_temperatures() -> None:
    climate = DecClimate.__new__(DecClimate)
    climate.signal = {s.INSIDE_TEMP_C: 21.0, s.CLIMATE_TARGET_C: 22.5}.get
    assert climate.native_current_temperature == climate.current_temperature == 21.0
    assert climate.native_target_temperature == climate.target_temperature == 22.5
    # La 2026.11 lee el ``_attr_native_*``; hasta la 2026.10, ``temperature_unit``.
    assert climate._attr_native_temperature_unit == climate.temperature_unit == "°C"
