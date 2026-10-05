"""Pruebas de telemetry/ (conversores, mapeos, fusión, derivadas)."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.dec_deepal.telemetry import converters as c
from custom_components.dec_deepal.telemetry import signals as s
from custom_components.dec_deepal.telemetry.mqtt_map import map_mqtt
from custom_components.dec_deepal.telemetry.rest_map import map_rest, value_at
from custom_components.dec_deepal.telemetry.state import (
    SOURCE_OPTIMISTIC,
    SOURCE_PREVIOUS,
    SOURCE_REST,
    OptimisticHold,
    apply_holds,
    build_state,
)


def test_connector_threshold() -> None:
    assert c.connector(0) is False
    assert c.connector(1) is False  # desenchufado aunque sea 1
    assert c.connector(3) is True
    assert c.connector(None) is None


def test_seat_level_one_to_one_and_sleep() -> None:
    assert c.seat_level(2) == 2
    assert c.seat_level(6) is None  # módulo dormido


def test_charge_minutes_sentinel() -> None:
    assert c.charge_minutes(8191) is None
    assert c.charge_minutes(45) == 45


def test_timestamp_formats() -> None:
    expected = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)
    assert c.timestamp("2026-09-30T10:00:00Z") == expected
    assert c.timestamp(int(expected.timestamp() * 1000)) == expected


def test_map_mqtt_typos_and_units() -> None:
    values = map_mqtt(
        {
            "soc": "80",
            "diverWindow": 1,
            "turnLndicatorLeft": 0,
            "innerHumidity": 453,
            "driverDoorLock": 0,
            "chargDeltMins": 8191,
        }
    )
    assert values[s.BATTERY_LEVEL] == 80
    assert values[s.WINDOW_FRONT_LEFT] is True
    assert values[s.INDICATOR_LEFT] is False
    assert values[s.CABIN_HUMIDITY] == 45.3
    assert values[s.LOCKED_DRIVER] is True
    assert s.REMAINING_CHARGE_MIN not in values


def test_map_rest_nested_and_lists() -> None:
    raw = {
        "hvac": {"outsideTemp": 215, "defrostStatus": 1},
        "door": {"doors": [0, 1, 0, 0]},
        "seat": {"leftFront": {"level": 3}},
    }
    values = map_rest(raw)
    assert values[s.OUTSIDE_TEMP_C] == 21.5
    assert values[s.DOOR_FRONT_RIGHT] is True
    assert values[s.SEAT_HEAT_DRIVER] == 3
    assert value_at(raw, ("door", "doors", 9)) is None


def test_build_state_rules() -> None:
    previous = build_state(mqtt_params={"steeringWheelHeating": 1}, rest_raw=None, previous=None)
    state = build_state(
        mqtt_params={"soc": 50, "driverSeatHeatStatus": 1},
        rest_raw={
            "vehicleStatus": {"soc": 99},
            "seat": {"leftFront": {"heatStatus": 3}},
            "hvac": {"outsideTemp": 100},
        },
        previous=previous,
    )
    assert state.get(s.BATTERY_LEVEL) == 50  # MQTT manda
    assert state.get(s.SEAT_HEAT_DRIVER) == 3  # REST manda en confort
    assert state.source(s.SEAT_HEAT_DRIVER) == SOURCE_REST
    assert state.get(s.OUTSIDE_TEMP_C) == 10.0  # REST rellena huecos
    assert state.get(s.STEERING_WHEEL_HEAT) is True  # último valor conservado
    assert state.source(s.STEERING_WHEEL_HEAT) == SOURCE_PREVIOUS
    assert state.get(s.CLOUD_CONNECTED) is True


def test_stale_rest_does_not_override() -> None:
    state = build_state(
        mqtt_params={"latestDate": "2026-09-30T10:00:00Z", "driverSeatHeatStatus": 1},
        rest_raw={"lastUpdatedAt": "2026-09-30T09:00:00Z", "seat": {"leftFront": {"heatStatus": 3}}},
        previous=None,
    )
    assert state.get(s.SEAT_HEAT_DRIVER) == 1


def test_apply_holds_confirm_and_expire() -> None:
    state = build_state(mqtt_params={"airStatus": 0}, rest_raw=None, previous=None)
    holds = {s.CLIMATE_ON: OptimisticHold(True, expires_at=100.0)}
    apply_holds(state, holds, now=10.0)
    assert state.get(s.CLIMATE_ON) is True
    assert state.source(s.CLIMATE_ON) == SOURCE_OPTIMISTIC
    apply_holds(state, holds, now=10.0)  # ya coincide → se confirma
    assert holds == {}


def test_derived_signals() -> None:
    state = build_state(
        mqtt_params={
            "acChargeGunConnectionState": 3,
            "dcChargeGunConnectionState": 0,
            "ChrgSts": 1,
            "chargDeltMins": 125,
            "driverDoorLock": 0,
            "passengerDoorLock": 1,
        },
        rest_raw=None,
        previous=None,
    )
    assert state.get(s.CHARGE_STATUS) == "charging_ac"
    assert state.get(s.REMAINING_CHARGE_HHMM) == "2:05"
    assert state.get(s.CENTRAL_LOCKED) is False


def test_power_on_from_power_status() -> None:
    """Encendido = estado de alimentación distinto de 0 (S05 real: 0 apagado, 2 en marcha)."""
    assert build_state(mqtt_params={"powerStatusFeedBack": "2", "engineStatus": "0"}, rest_raw=None, previous=None).get(s.POWER_ON) is True
    assert build_state(mqtt_params={"powerStatusFeedBack": "0"}, rest_raw=None, previous=None).get(s.POWER_ON) is False
    assert build_state(mqtt_params={}, rest_raw=None, previous=None).get(s.POWER_ON) is None


def test_charger_plugged() -> None:
    from custom_components.dec_deepal.telemetry.derived import charger_plugged

    assert charger_plugged({}) is None
    assert charger_plugged({s.AC_CONNECTOR: False, s.DC_CONNECTOR: None}) is False
    assert charger_plugged({s.AC_CONNECTOR: False, s.DC_CONNECTOR: True}) is True
    assert charger_plugged({s.AC_CONNECTOR: True}) is True


def test_extras_2_1_0() -> None:
    """Claves nuevas del informe MQTT: tipos tal como los manda el coche."""
    values = map_mqtt(
        {
            "chargeCoverStatus": 1,
            "frontFoglamp": 0,
            "rearFoglamp": 1,
            "keyLowPower": 0.0,
            "airRecycleStatus": 1,
            "leftAnteriorWindowDegree": "35",
            "rightRearWindowDegree": "0",
            "batt12VLightStatus": "1",
            "tpmsLightStatus": "0",
            # Testigos descartados: no deben crear ninguna señal.
            "oilFuelLightStatus": "1",
            "accLightStatus": "1",
        }
    )
    assert values[s.CHARGE_COVER_OPEN] is True
    assert values[s.FRONT_FOG_LAMP] is False and values[s.REAR_FOG_LAMP] is True
    assert values[s.KEY_BATTERY_LOW] is False
    assert values[s.AIR_RECIRCULATION] is True
    assert values[s.WINDOW_OPENING_FRONT_LEFT] == 35
    assert values[s.WINDOW_OPENING_REAR_RIGHT] == 0
    assert values[s.WARNING_12V_BATTERY] is True and values[s.WARNING_TPMS] is False
    assert len([key for key in values if key.startswith("warning_")]) == 2
