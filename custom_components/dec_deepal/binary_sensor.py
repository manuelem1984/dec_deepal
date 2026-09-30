"""Sensores binarios (sí/no): puertas, ventanillas, luces, carga...

Ojo con las cerraduras: en Home Assistant, un sensor binario de tipo
``LOCK`` está **encendido cuando está desbloqueado**. Las señales de cierre
son ``True`` = bloqueado, así que esas filas llevan ``invert=True``.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import DecDeepalEntity
from .registries.vehicles import FEATURE_CLIMATE
from .runtime import DecDeepalConfigEntry, DecDeepalRuntime, VehicleContext
from .telemetry import signals as s


@dataclass(frozen=True, kw_only=True)
class DecBinaryDescription(BinarySensorEntityDescription):
    """Descripción de un sensor binario DEC Deepal."""

    signal: str
    #: Invertir el valor (cerraduras: señal True = bloqueada → sensor off).
    invert: bool = False
    feature: str | None = None


def _door(key: str, signal: str) -> DecBinaryDescription:
    return DecBinaryDescription(key=key, signal=signal, device_class=BinarySensorDeviceClass.DOOR)


def _window(key: str, signal: str) -> DecBinaryDescription:
    return DecBinaryDescription(key=key, signal=signal, device_class=BinarySensorDeviceClass.WINDOW)


def _tire(key: str, signal: str) -> DecBinaryDescription:
    return DecBinaryDescription(key=key, signal=signal, device_class=BinarySensorDeviceClass.PROBLEM)


def _light(key: str, signal: str) -> DecBinaryDescription:
    return DecBinaryDescription(key=key, signal=signal, device_class=BinarySensorDeviceClass.LIGHT)


BINARY_SENSORS: tuple[DecBinaryDescription, ...] = (
    DecBinaryDescription(
        key="cloud_connected",
        signal=s.CLOUD_CONNECTED,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DecBinaryDescription(
        key="engine", signal=s.POWER_ON, device_class=BinarySensorDeviceClass.RUNNING
    ),
    DecBinaryDescription(
        key="charging", signal=s.CHARGING, device_class=BinarySensorDeviceClass.BATTERY_CHARGING
    ),
    DecBinaryDescription(
        key="ac_connector", signal=s.AC_CONNECTOR, device_class=BinarySensorDeviceClass.PLUG
    ),
    DecBinaryDescription(
        key="dc_connector", signal=s.DC_CONNECTOR, device_class=BinarySensorDeviceClass.PLUG
    ),
    _door("door_front_left", s.DOOR_FRONT_LEFT),
    _door("door_front_right", s.DOOR_FRONT_RIGHT),
    _door("door_rear_left", s.DOOR_REAR_LEFT),
    _door("door_rear_right", s.DOOR_REAR_RIGHT),
    _door("trunk", s.TRUNK_OPEN),
    DecBinaryDescription(
        key="hood", signal=s.HOOD_OPEN, device_class=BinarySensorDeviceClass.OPENING
    ),
    _door("any_door_open", s.ANY_DOOR_OPEN),
    _window("window_front_left", s.WINDOW_FRONT_LEFT),
    _window("window_front_right", s.WINDOW_FRONT_RIGHT),
    _window("window_rear_left", s.WINDOW_REAR_LEFT),
    _window("window_rear_right", s.WINDOW_REAR_RIGHT),
    DecBinaryDescription(
        key="lock_driver",
        signal=s.LOCKED_DRIVER,
        invert=True,
        device_class=BinarySensorDeviceClass.LOCK,
    ),
    DecBinaryDescription(
        key="lock_passenger",
        signal=s.LOCKED_PASSENGER,
        invert=True,
        device_class=BinarySensorDeviceClass.LOCK,
    ),
    DecBinaryDescription(
        key="central_locking",
        signal=s.CENTRAL_LOCKED,
        invert=True,
        device_class=BinarySensorDeviceClass.LOCK,
    ),
    _tire("tire_alarm_front_left", s.TIRE_ALARM_FRONT_LEFT),
    _tire("tire_alarm_front_right", s.TIRE_ALARM_FRONT_RIGHT),
    _tire("tire_alarm_rear_left", s.TIRE_ALARM_REAR_LEFT),
    _tire("tire_alarm_rear_right", s.TIRE_ALARM_REAR_RIGHT),
    _light("high_beam", s.HIGH_BEAM),
    _light("low_beam", s.LOW_BEAM),
    _light("position_lamp", s.POSITION_LAMP),
    _light("indicator_left", s.INDICATOR_LEFT),
    _light("indicator_right", s.INDICATOR_RIGHT),
    DecBinaryDescription(key="climate_on", signal=s.CLIMATE_ON, feature=FEATURE_CLIMATE),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea los sensores binarios de cada coche."""
    runtime = entry.runtime_data
    async_add_entities(
        DecBinarySensor(runtime, vehicle, description)
        for vehicle in runtime.vehicles.values()
        for description in BINARY_SENSORS
        if description.feature is None or vehicle.has(description.feature)
    )


class DecBinarySensor(DecDeepalEntity, BinarySensorEntity):
    """Un sensor binario que muestra una señal booleana."""

    entity_description: DecBinaryDescription

    def __init__(
        self,
        runtime: DecDeepalRuntime,
        vehicle: VehicleContext,
        description: DecBinaryDescription,
    ) -> None:
        super().__init__(runtime, vehicle, "binary_sensor", description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Estado actual (invertido en las cerraduras)."""
        value = self.signal(self.entity_description.signal)
        if value is None:
            return None
        return not value if self.entity_description.invert else bool(value)

    def icon_state(self) -> str | None:
        """``"on"`` / ``"off"`` para elegir el icono."""
        is_on = self.is_on
        return None if is_on is None else ("on" if is_on else "off")
