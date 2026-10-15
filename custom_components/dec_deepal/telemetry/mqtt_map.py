"""Tabla de mapeo MQTT → señal.

Cada fila dice: "la señal X se saca de la primera de estas claves MQTT que
llegue, pasada por este conversor". Las claves son las que manda el Deepal S05
(con sus erratas originales: ``diverWindow``, ``turnLndicatorLeft``...).

Estado de verificación (✅ / ⚠️) de cada fila: ver
``docs/correlacion_endpoints_entidades.csv`` (columna "Verificado").

Para añadir un dato nuevo que ya llega por MQTT:
1. Añadir la señal en ``signals.py``.
2. Añadir aquí una fila ``MqttField(...)``.
3. Crear la entidad que la use y añadir la fila en el CSV de correlación.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from . import converters as c
from . import signals as s


@dataclass(frozen=True, slots=True)
class MqttField:
    """Una fila de la tabla: señal ← primera clave presente → conversor."""

    signal: str
    keys: tuple[str, ...]
    convert: Callable[[Any], Any]


CHARGE_STATE_KEYS: Final = ("ChrgSts",)
AC_CURRENT_KEYS: Final = ("BattACChrgInCurr", "battACChrgInCurr")
DC_CURRENT_KEYS: Final = ("BattDCChrgInCurr", "battDCChrgInCurr")

MQTT_FIELDS: Final[tuple[MqttField, ...]] = (
    # --- Batería y carga ----------------------------------------------------
    MqttField(s.BATTERY_LEVEL, ("soc", "socDsp", "remainPower"), c.to_int),
    MqttField(s.RANGE_KM, ("remainedPowerMile", "totalResidualMileage"), c.to_int),
    # ChrgSts es un estado (0-4), no un sí/no: ver converters.charge_state.
    MqttField(s.CHARGE_STATE, CHARGE_STATE_KEYS, c.charge_state),
    MqttField(s.CHARGING, CHARGE_STATE_KEYS, c.charging_from_state),
    MqttField(s.AC_CONNECTOR, ("acChargeGunConnectionState",), c.connector),
    # "dcDhargeGunConnectionState" (sic) aparece en algunas versiones del coche.
    MqttField(
        s.DC_CONNECTOR,
        ("dcChargeGunConnectionState", "dcDhargeGunConnectionState"),
        c.connector,
    ),
    # Corrientes: el coche usa dos grafías (mayúscula y minúscula inicial). La
    # corriente "activa" (CHARGE_CURRENT) se elige en map_mqtt según ChrgSts.
    MqttField(s.AC_CHARGE_CURRENT, AC_CURRENT_KEYS, c.charge_current),
    MqttField(s.DC_CHARGE_CURRENT, DC_CURRENT_KEYS, c.charge_current),
    MqttField(s.REMAINING_CHARGE_MIN, ("chargDeltMins",), c.charge_minutes),
    # --- Estado general -----------------------------------------------------
    MqttField(s.REPORT_TIME, ("latestDate", "lastUpdatedAt", "lastUpdatedTime"), c.timestamp),
    MqttField(s.ENGINE_ON, ("engineStatus",), c.to_bool),
    MqttField(s.POWER_STATUS, ("powerStatusFeedBack",), c.to_int),
    MqttField(s.ODOMETER_KM, ("totalOdometer",), c.to_float),
    MqttField(s.MILEAGE_YESTERDAY_KM, ("totalMeterYesterday",), c.to_float),
    MqttField(s.TRIP_KM, ("igniteCumulativeMileage",), c.to_float),
    MqttField(s.SPEED_KMH, ("vehicleSpeed", "speed"), c.to_float),
    MqttField(s.PARKING_BRAKE, ("electronichandbrakeStatus",), c.to_int),
    # --- Clima --------------------------------------------------------------
    MqttField(s.INSIDE_TEMP_C, ("vehicleTemperature",), c.to_float),
    MqttField(s.OUTSIDE_TEMP_C, ("outsideTemperature", "externalTemperature"), c.to_float),
    MqttField(s.CABIN_HUMIDITY, ("innerHumidity",), c.humidity),
    MqttField(s.CLIMATE_ON, ("airStatus",), c.to_bool),
    MqttField(s.FAN_LEVEL, ("airConditioningHairRatings",), c.to_int),
    MqttField(s.CLIMATE_TARGET_C, ("airConditioningSetTemperature",), c.to_float),
    # --- Confort (el REST tiene prioridad para estas, ver state.py) ---------
    MqttField(s.SEAT_HEAT_DRIVER, ("driverSeatHeatStatus",), c.seat_level),
    MqttField(s.SEAT_HEAT_PASSENGER, ("passengerSeatHeatStatus",), c.seat_level),
    MqttField(s.SEAT_VENT_DRIVER, ("driverSeatAirStatus",), c.seat_level),
    MqttField(s.SEAT_VENT_PASSENGER, ("passengerSeatAirStatus",), c.seat_level),
    MqttField(s.STEERING_WHEEL_HEAT, ("steeringWheelHeating",), c.to_bool),
    MqttField(s.FRONT_DEFROST, ("frontDefrostStatus",), c.to_bool),
    # --- Carrocería ---------------------------------------------------------
    MqttField(s.DOOR_FRONT_LEFT, ("driverDoor",), c.to_bool),
    MqttField(s.DOOR_FRONT_RIGHT, ("passengerDoor",), c.to_bool),
    MqttField(s.DOOR_REAR_LEFT, ("leftRearDoor",), c.to_bool),
    MqttField(s.DOOR_REAR_RIGHT, ("rightRearDoor",), c.to_bool),
    MqttField(s.TRUNK_OPEN, ("trunk",), c.to_bool),
    MqttField(s.HOOD_OPEN, ("hoodStatus", "hood"), c.to_bool),
    # "diverWindow" (sic): errata del propio coche.
    MqttField(s.WINDOW_FRONT_LEFT, ("diverWindow",), c.to_bool),
    MqttField(s.WINDOW_FRONT_RIGHT, ("passengerWindow",), c.to_bool),
    MqttField(s.WINDOW_REAR_LEFT, ("leftRearWindow",), c.to_bool),
    MqttField(s.WINDOW_REAR_RIGHT, ("rightRearWindow",), c.to_bool),
    MqttField(s.LOCKED_DRIVER, ("driverDoorLock",), c.locked_if_zero),
    MqttField(s.LOCKED_PASSENGER, ("passengerDoorLock",), c.locked_if_zero),
    # --- Neumáticos (llegan en kPa) -----------------------------------------
    MqttField(s.TIRE_PRESSURE_FRONT_LEFT, ("lfTyrePressure",), c.to_float),
    MqttField(s.TIRE_PRESSURE_FRONT_RIGHT, ("rfTyrePressure",), c.to_float),
    MqttField(s.TIRE_PRESSURE_REAR_LEFT, ("lrTyrePressure",), c.to_float),
    MqttField(s.TIRE_PRESSURE_REAR_RIGHT, ("rrTyrePressure",), c.to_float),
    MqttField(s.TIRE_ALARM_FRONT_LEFT, ("lfPressureWarning",), c.to_bool),
    MqttField(s.TIRE_ALARM_FRONT_RIGHT, ("rfPressureWarning",), c.to_bool),
    MqttField(s.TIRE_ALARM_REAR_LEFT, ("lrPressureWarning",), c.to_bool),
    MqttField(s.TIRE_ALARM_REAR_RIGHT, ("rrPressureWarning",), c.to_bool),
    # --- Luces ("Lndicator" (sic): errata del coche) ------------------------
    MqttField(s.HIGH_BEAM, ("highBeam",), c.to_bool),
    MqttField(s.LOW_BEAM, ("lowBeam",), c.to_bool),
    MqttField(s.POSITION_LAMP, ("positionLamp",), c.to_bool),
    MqttField(s.INDICATOR_LEFT, ("turnLndicatorLeft",), c.to_bool),
    MqttField(s.INDICATOR_RIGHT, ("turnLndicatorRight",), c.to_bool),
    MqttField(s.REAR_FOG_LAMP, ("rearFoglamp",), c.to_bool),
    # --- Extras (2.1.0). Probados con el coche el 05-10-2026 -----------------
    # NO se usan (el S05 los manda siempre a 0): frontFoglamp (no tiene
    # antiniebla delantera) y chargeCoverStatus (no cambia al abrir la tapa).
    MqttField(s.KEY_BATTERY_LOW, ("keyLowPower",), c.to_bool),
    MqttField(s.AIR_RECIRCULATION, ("airRecycleStatus",), c.to_bool),
    # "Anterior" = delantera.
    MqttField(s.WINDOW_OPENING_FRONT_LEFT, ("leftAnteriorWindowDegree",), c.to_int),
    MqttField(s.WINDOW_OPENING_FRONT_RIGHT, ("rightAnteriorWindowDegree",), c.to_int),
    MqttField(s.WINDOW_OPENING_REAR_LEFT, ("leftRearWindowDegree",), c.to_int),
    MqttField(s.WINDOW_OPENING_REAR_RIGHT, ("rightRearWindowDegree",), c.to_int),
    # Testigos del cuadro. NO se exponen accLightStatus, aebLightStatus,
    # lwdLightStatus ni oilFuelLightStatus (valen "1" con el coche sano; el
    # último, en un eléctrico) ni espLightStatus (cambia entre lecturas sin
    # avería): darían falsas alarmas.
    MqttField(s.WARNING_12V_BATTERY, ("batt12VLightStatus",), c.to_bool),
    MqttField(s.WARNING_TPMS, ("tpmsLightStatus",), c.to_bool),
    MqttField(s.WARNING_ABS, ("absLightStatus",), c.to_bool),
    MqttField(s.WARNING_AIRBAG, ("airBagLightStatus",), c.to_bool),
    MqttField(s.WARNING_BRAKE_FLUID, ("brakeFluidLightStatus",), c.to_bool),
    MqttField(s.WARNING_BRAKE, ("brakeLightStatus",), c.to_bool),
    MqttField(s.WARNING_EPS, ("epsLightStatus",), c.to_bool),
    MqttField(s.WARNING_POWER_LIMIT, ("powerLimitLightStatus",), c.to_bool),
    MqttField(s.WARNING_POWER_SYSTEM, ("powerSystemLightStatus",), c.to_bool),
    MqttField(s.WARNING_TRACTION_BATTERY_LOW, ("bcuBattSocLightStatus",), c.to_bool),
    MqttField(s.WARNING_COOLANT_TEMPERATURE, ("coolanTemperatureLightStatus",), c.to_bool),
)

#: Todas las claves MQTT que se leen. Diagnóstico usa esto para listar las
#: claves que llegan pero ninguna señal usa todavía ("sin mapear").
MAPPED_MQTT_KEYS: Final[frozenset[str]] = frozenset(
    key for field in MQTT_FIELDS for key in field.keys
)


def first_present(params: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Valor de la primera clave presente (no ``None``) en ``params``."""
    for key in keys:
        value = params.get(key)
        if value is not None:
            return value
    return None


def map_mqtt(params: dict[str, Any]) -> dict[str, Any]:
    """Convierte los parámetros MQTT en ``{señal: valor}``.

    Solo incluye señales con valor (las ``None`` se omiten), para que la
    fusión con REST pueda distinguir "no llegó" de "llegó".
    """
    values: dict[str, Any] = {}
    for field in MQTT_FIELDS:
        value = field.convert(first_present(params, field.keys))
        if value is not None:
            values[field.signal] = value
    _resolve_charge_currents(params, values)
    return values


def _resolve_charge_currents(params: dict[str, Any], values: dict[str, Any]) -> None:
    """Ajusta las corrientes de carga según el estado (``ChrgSts``).

    El coche sigue mandando la corriente del cargador que **no** usa, y antes
    se cogía primero la de AC: un ``0`` en AC escondía la corriente real de
    DC. Ahora:

    - Cargando en DC (4): la activa es la de DC; la de AC, 0.
    - Cargando en AC (3): la activa es la de AC; la de DC, 0.
    - Sin cargar (0, 1, 2): todas a 0 (no un valor viejo ni el falso de
      después de una carga).
    - Estado desconocido: la que no sea 0, preferiblemente la de AC.

    Solo se pone 0 en una corriente que el coche haya mandado.
    """
    state = values.get(s.CHARGE_STATE)
    ac_sent = c.to_float(first_present(params, AC_CURRENT_KEYS)) is not None
    dc_sent = c.to_float(first_present(params, DC_CURRENT_KEYS)) is not None
    ac = values.get(s.AC_CHARGE_CURRENT)
    dc = values.get(s.DC_CHARGE_CURRENT)

    if state == c.CHARGE_STATE_DC_CHARGING:
        ac, active = (0.0 if ac_sent else None), dc
    elif state == c.CHARGE_STATE_AC_CHARGING:
        dc, active = (0.0 if dc_sent else None), ac
    elif state is not None:
        ac = 0.0 if ac_sent else None
        dc = 0.0 if dc_sent else None
        active = 0.0 if (ac_sent or dc_sent) else None
    else:
        active = ac if ac else dc
        if active is None and ac is not None:
            active = 0.0

    for signal, value in (
        (s.AC_CHARGE_CURRENT, ac),
        (s.DC_CHARGE_CURRENT, dc),
        (s.CHARGE_CURRENT, active),
    ):
        if value is None:
            values.pop(signal, None)
        else:
            values[signal] = value
