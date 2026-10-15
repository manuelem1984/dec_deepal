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
    # El mismo dato llega a veces ya en % (visto el 11-10-2026): no se divide.
    assert map_mqtt({"innerHumidity": 61.0})[s.CABIN_HUMIDITY] == 61.0
    assert map_mqtt({"innerHumidity": 0.0})[s.CABIN_HUMIDITY] == 0.0
    assert s.CABIN_HUMIDITY not in map_mqtt({"innerHumidity": 1500})
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


def test_optimistic_value_is_not_kept_as_last_known() -> None:
    """Si el coche nunca confirma un comando, su valor no se queda para siempre."""
    state = build_state(mqtt_params={"steeringWheelHeating": 0}, rest_raw=None, previous=None)
    holds = {s.STEERING_WHEEL_HEAT: OptimisticHold(True, expires_at=100.0)}
    apply_holds(state, holds, now=10.0)
    assert state.get(s.STEERING_WHEEL_HEAT) is True
    # Lectura sin el dato (módulo dormido) cuando el valor optimista ya caducó.
    after = build_state(mqtt_params={"soc": 50}, rest_raw=None, previous=state)
    apply_holds(after, holds, now=200.0)
    assert after.get(s.STEERING_WHEEL_HEAT) is None
    # Un valor real sí se conserva.
    real = build_state(mqtt_params={"steeringWheelHeating": 1}, rest_raw=None, previous=None)
    assert build_state(mqtt_params={"soc": 50}, rest_raw=None, previous=real).get(s.STEERING_WHEEL_HEAT) is True


def test_derived_signals() -> None:
    state = build_state(
        mqtt_params={
            "acChargeGunConnectionState": 3,
            "dcChargeGunConnectionState": 0,
            "ChrgSts": 3,
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
    # Si carga, está enchufado, aunque los conectores digan que no (o no digan nada).
    assert charger_plugged({s.CHARGING: True, s.AC_CONNECTOR: False, s.DC_CONNECTOR: False}) is True
    assert charger_plugged({s.CHARGING: True}) is True
    assert charger_plugged({s.CHARGING: False}) is False


def test_charge_status_does_not_trust_the_connectors() -> None:
    """Manda "cargando": los conectores del S05 no son fiables (visto el 11-10-2026)."""
    from custom_components.dec_deepal.telemetry.derived import charge_status

    off = {s.AC_CONNECTOR: False, s.DC_CONNECTOR: False}
    # Cargando con "conector AC: no": antes quedaba sin valor.
    assert charge_status({**off, s.CHARGING: True}) == "charging_ac"
    # Un coche que no manda el conector AC (el segundo de la cuenta de pruebas).
    assert charge_status({s.CHARGING: True}) == "charging_ac"
    assert charge_status({s.CHARGING: False}) == "disconnected"
    # Continua: por el conector o por la corriente.
    assert charge_status({s.CHARGING: True, s.DC_CONNECTOR: True}) == "charging_dc"
    assert charge_status({**off, s.CHARGING: True, s.DC_CHARGE_CURRENT: 120.0}) == "charging_dc"
    assert charge_status({**off, s.CHARGING: True, s.DC_CHARGE_CURRENT: 0}) == "charging_ac"
    # Sin cargar: lo que digan los conectores, si dicen algo.
    assert charge_status({**off, s.CHARGING: False}) == "disconnected"
    assert charge_status({s.CHARGING: False, s.AC_CONNECTOR: True, s.DC_CONNECTOR: False}) == "connected_ac"
    assert charge_status({s.CHARGING: False, s.DC_CONNECTOR: True}) == "connected_dc"
    # Sin saber si carga, no se adivina.
    assert charge_status({s.AC_CONNECTOR: True}) is None and charge_status({}) is None


def test_charge_state_is_an_enum() -> None:
    """ChrgSts: 0 sin cargar, 1/2 manguera AC/DC puesta, 3/4 cargando AC/DC."""
    assert [c.charge_state(value) for value in (0, "1", 2.0, 3, 4)] == [0, 1, 2, 3, 4]
    assert c.charge_state(9) is None and c.charge_state(None) is None
    assert [c.charging_from_state(value) for value in (0, 1, 2, 3, 4)] == [
        False,
        False,
        False,
        True,
        True,
    ]
    assert c.charging_from_state(9) is None


def test_plugging_in_is_not_charging() -> None:
    """Enchufar la manguera (1 o 2) ya no cuenta como "cargando" (2.5.0b8)."""
    expected = {
        0: (False, "disconnected", False),
        1: (False, "connected_ac", True),
        2: (False, "connected_dc", True),
        3: (True, "charging_ac", True),
        4: (True, "charging_dc", True),
    }
    for chrg_sts, (charging, status, plugged) in expected.items():
        # Conectores en "no enchufado": manda el estado de carga.
        params = {"ChrgSts": chrg_sts, "acChargeGunConnectionState": 0}
        state = build_state(mqtt_params=params, rest_raw=None, previous=None)
        assert state.get(s.CHARGE_STATE) == chrg_sts
        assert state.get(s.CHARGING) is charging
        assert state.get(s.CHARGE_STATUS) == status
        assert state.get(s.CHARGER_PLUGGED) is plugged

    # Estado desconocido: no se adivina si carga.
    unknown = build_state(mqtt_params={"ChrgSts": 9}, rest_raw=None, previous=None)
    assert unknown.get(s.CHARGING) is None and unknown.get(s.CHARGE_STATE) is None
    # Sin cargar (0) con un conector que dice "enchufado": carga terminada.
    full = build_state(
        mqtt_params={"ChrgSts": 0, "acChargeGunConnectionState": 2}, rest_raw=None, previous=None
    )
    assert full.get(s.CHARGE_STATUS) == "connected_ac"


def test_plugging_in_does_not_open_a_charge_session() -> None:
    from custom_components.dec_deepal import charging as ch

    now = datetime(2026, 10, 15, 10, 0, tzinfo=UTC)
    plugged = map_mqtt({"ChrgSts": 1, "soc": 40})
    session, changed = ch.update(None, plugged[s.CHARGING], 40, 200, now)
    assert session == {} and changed is False


def test_charge_currents_follow_the_charge_state() -> None:
    """La corriente activa es la del cargador en uso (antes, un 0 en AC tapaba la de DC)."""
    dc = map_mqtt({"ChrgSts": 4, "BattACChrgInCurr": 0, "BattDCChrgInCurr": 120})
    assert (dc[s.AC_CHARGE_CURRENT], dc[s.DC_CHARGE_CURRENT], dc[s.CHARGE_CURRENT]) == (
        0.0,
        120.0,
        120.0,
    )
    ac = map_mqtt({"ChrgSts": 3, "battACChrgInCurr": 16, "battDCChrgInCurr": 5})
    assert (ac[s.AC_CHARGE_CURRENT], ac[s.DC_CHARGE_CURRENT], ac[s.CHARGE_CURRENT]) == (
        16.0,
        0.0,
        16.0,
    )
    # Sin cargar: 0, no un valor viejo.
    idle = map_mqtt({"ChrgSts": 2, "BattACChrgInCurr": 3, "BattDCChrgInCurr": 60})
    assert (idle[s.AC_CHARGE_CURRENT], idle[s.DC_CHARGE_CURRENT], idle[s.CHARGE_CURRENT]) == (
        0.0,
        0.0,
        0.0,
    )
    # Estado desconocido: la que no sea 0.
    unknown = map_mqtt({"BattACChrgInCurr": 0, "BattDCChrgInCurr": 60})
    assert unknown[s.CHARGE_CURRENT] == 60.0
    assert map_mqtt({"BattACChrgInCurr": 0})[s.CHARGE_CURRENT] == 0.0
    # Sin corrientes en el informe: no se inventan.
    assert s.CHARGE_CURRENT not in map_mqtt({"ChrgSts": 0})


def test_impossible_charge_current_is_dropped() -> None:
    """2538 A: valor falso que mandó un S05 aparcado tras una carga DC."""
    assert c.charge_current(2538) is None
    assert c.charge_current(-1) is None
    assert c.charge_current("480") == 480.0
    values = map_mqtt({"BattDCChrgInCurr": 2538})
    assert s.DC_CHARGE_CURRENT not in values and s.CHARGE_CURRENT not in values
    assert s.CHARGE_CURRENT not in map_rest({"charge": {"chargeCurrent": 2538}})


def test_extras_2_1_0() -> None:
    """Claves nuevas del informe MQTT: tipos tal como los manda el coche."""
    values = map_mqtt(
        {
            "chargeCoverStatus": 1,
            "frontFoglamp": 1,
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
    # Retiradas: el S05 no informa de la tapa ni tiene antiniebla delantera.
    assert "charge_cover_open" not in values and "front_fog_lamp" not in values
    assert values[s.REAR_FOG_LAMP] is True
    assert values[s.KEY_BATTERY_LOW] is False
    assert values[s.AIR_RECIRCULATION] is True
    assert values[s.WINDOW_OPENING_FRONT_LEFT] == 35
    assert values[s.WINDOW_OPENING_REAR_RIGHT] == 0
    assert values[s.WARNING_12V_BATTERY] is True and values[s.WARNING_TPMS] is False
    assert len([key for key in values if key.startswith("warning_")]) == 2
