"""Tabla de mapeo REST (``vehicle/condition``) → señal.

El JSON del REST está anidado; cada fila indica una o varias **rutas** (la
primera que tenga valor gana). Una ruta es una tupla de claves y/o índices:
``("seat", "leftFront", "heatStatus")`` o ``("door", "doors", 0)``.

Interpretaciones tomadas de Deepal Alternative (MIT, ver NOTICE.md), salvo
asientos/volante/desempañado, verificados ✅ por el proyecto anterior:

- Temperaturas del REST en **décimas** de grado.
- Presión de neumáticos en kPa (igual que MQTT).
- ``door.doors`` y ``window.windows`` son listas de 4: [conductor, acompañante,
  trasera izquierda, trasera derecha]; distinto de 0 = abierta.
- ``door.driverLock == 0`` → bloqueada.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from . import converters as c
from . import signals as s

Path = tuple[str | int, ...]


@dataclass(frozen=True, slots=True)
class RestField:
    """Una fila: señal ← primera ruta con valor → conversor."""

    signal: str
    paths: tuple[Path, ...]
    convert: Callable[[Any], Any]


def _seat(position: str, *keys: str) -> tuple[Path, ...]:
    """Rutas de un asiento: ``seat.<posición>.<clave>`` para cada clave."""
    return tuple(("seat", position, key) for key in keys)


REST_FIELDS: Final[tuple[RestField, ...]] = (
    # --- Batería y carga ----------------------------------------------------
    RestField(s.BATTERY_LEVEL, (("vehicleStatus", "soc"),), c.to_int),
    RestField(s.RANGE_KM, (("vehicleStatus", "drvMileage"),), c.to_int),
    RestField(s.CHARGING, (("charge", "chargeStatus"),), c.to_bool),
    RestField(s.DC_CONNECTOR, (("charge", "dcChargeGunConnectStatus"),), c.connector),
    RestField(s.CHARGE_CURRENT, (("charge", "chargeCurrent"),), c.to_float),
    RestField(s.AC_CHARGE_CURRENT, (("charge", "acChargeCurrent"),), c.to_float),
    RestField(s.DC_CHARGE_CURRENT, (("charge", "dcChargeCurrent"),), c.to_float),
    RestField(s.REMAINING_CHARGE_MIN, (("charge", "remainChargeTime"),), c.charge_minutes),
    # --- Estado general -----------------------------------------------------
    RestField(
        s.REPORT_TIME, (("lastUpdatedAt",), ("vehicleStatus", "lastUpdatedAt")), c.timestamp
    ),
    RestField(s.ENGINE_ON, (("vehicleStatus", "engineSts"),), c.to_bool),
    RestField(s.POWER_STATUS, (("vehicleStatus", "powerStatus"),), c.to_int),
    RestField(s.ODOMETER_KM, (("vehicleStatus", "totalMileage"),), c.to_float),
    RestField(s.MILEAGE_YESTERDAY_KM, (("vehicleStatus", "totalMeterYesterday"),), c.to_float),
    RestField(s.TRIP_KM, (("vehicleStatus", "igniteCumulativeMileage"),), c.to_float),
    RestField(s.SPEED_KMH, (("vehicleStatus", "speed"),), c.to_float),
    RestField(s.PARKING_BRAKE, (("vehicleStatus", "epbSts"),), c.to_int),
    # --- Clima (décimas de grado) -------------------------------------------
    RestField(s.INSIDE_TEMP_C, (("hvac", "insideTemp"),), c.tenths),
    RestField(s.OUTSIDE_TEMP_C, (("hvac", "outsideTemp"),), c.tenths),
    RestField(s.CLIMATE_ON, (("hvac", "acStatus"),), c.to_bool),
    RestField(s.FAN_LEVEL, (("hvac", "fanLevel"),), c.to_int),
    RestField(s.CLIMATE_TARGET_C, (("hvac", "remoteTemp"),), c.tenths),
    # --- Confort (prioritario sobre MQTT) ✅ ---------------------------------
    RestField(s.SEAT_HEAT_DRIVER, _seat("leftFront", "heatStatus", "level"), c.seat_level),
    RestField(s.SEAT_HEAT_PASSENGER, _seat("rightFront", "heatStatus", "level"), c.seat_level),
    RestField(s.SEAT_VENT_DRIVER, _seat("leftFront", "ventStatus"), c.seat_level),
    RestField(s.SEAT_VENT_PASSENGER, _seat("rightFront", "ventStatus"), c.seat_level),
    RestField(s.STEERING_WHEEL_HEAT, (("vehicleStatus", "steeringWheelHeater"),), c.to_bool),
    RestField(s.FRONT_DEFROST, (("hvac", "defrostStatus"),), c.to_bool),
    # --- Carrocería ---------------------------------------------------------
    RestField(s.DOOR_FRONT_LEFT, (("door", "doors", 0),), c.to_bool),
    RestField(s.DOOR_FRONT_RIGHT, (("door", "doors", 1),), c.to_bool),
    RestField(s.DOOR_REAR_LEFT, (("door", "doors", 2),), c.to_bool),
    RestField(s.DOOR_REAR_RIGHT, (("door", "doors", 3),), c.to_bool),
    RestField(s.TRUNK_OPEN, (("door", "trunk"),), c.to_bool),
    RestField(s.HOOD_OPEN, (("door", "hood"),), c.to_bool),
    RestField(s.WINDOW_FRONT_LEFT, (("window", "windows", 0),), c.to_bool),
    RestField(s.WINDOW_FRONT_RIGHT, (("window", "windows", 1),), c.to_bool),
    RestField(s.WINDOW_REAR_LEFT, (("window", "windows", 2),), c.to_bool),
    RestField(s.WINDOW_REAR_RIGHT, (("window", "windows", 3),), c.to_bool),
    RestField(s.LOCKED_DRIVER, (("door", "driverLock"),), c.locked_if_zero),
    RestField(s.LOCKED_PASSENGER, (("door", "passengerLock"),), c.locked_if_zero),
    # --- Neumáticos ---------------------------------------------------------
    RestField(s.TIRE_PRESSURE_FRONT_LEFT, (("tire", "leftFront", "pressure"),), c.to_float),
    RestField(s.TIRE_PRESSURE_FRONT_RIGHT, (("tire", "rightFront", "pressure"),), c.to_float),
    RestField(s.TIRE_PRESSURE_REAR_LEFT, (("tire", "leftBack", "pressure"),), c.to_float),
    RestField(s.TIRE_PRESSURE_REAR_RIGHT, (("tire", "rightBack", "pressure"),), c.to_float),
    # --- Luces --------------------------------------------------------------
    RestField(s.HIGH_BEAM, (("lamp", "highBeam"),), c.to_bool),
    RestField(s.LOW_BEAM, (("lamp", "lowBeam"),), c.to_bool),
    RestField(s.POSITION_LAMP, (("lamp", "positionLamp"),), c.to_bool),
    RestField(s.INDICATOR_LEFT, (("lamp", "leftTurn"),), c.to_bool),
    RestField(s.INDICATOR_RIGHT, (("lamp", "rightTurn"),), c.to_bool),
)


def value_at(data: Any, path: Path) -> Any:
    """Sigue una ruta dentro del JSON. ``None`` si algún paso no existe."""
    current = data
    for step in path:
        if isinstance(step, int):
            if not isinstance(current, list) or len(current) <= step:
                return None
            current = current[step]
        else:
            if not isinstance(current, dict):
                return None
            current = current.get(step)
        if current is None:
            return None
    return current


def map_rest(raw: dict[str, Any]) -> dict[str, Any]:
    """Convierte el JSON REST en ``{señal: valor}`` (solo las que tienen valor)."""
    values: dict[str, Any] = {}
    for field in REST_FIELDS:
        for path in field.paths:
            value = field.convert(value_at(raw, path))
            if value is not None:
                values[field.signal] = value
                break
    return values
