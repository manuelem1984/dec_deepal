"""Sensores binarios (sí/no): puertas, ventanillas, luces, carga, testigos...

Añadidos en la 2.1.0 a partir de claves del informe MQTT: antiniebla
trasera y recirculación (✅ probadas con el coche), pila del mando y
testigos del cuadro (⚠️ no se pueden provocar; sin falsas alarmas).
Retirados tras probarlos (05-10-2026): tapa de carga (el coche no informa)
y antiniebla delantera (el S05 no tiene).

Ojo con las cerraduras: en Home Assistant, un sensor binario de tipo
``LOCK`` está **encendido cuando está desbloqueado**. Las señales de cierre
son ``True`` = bloqueado, así que esas filas llevan ``invert=True``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
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
    """Aviso de un neumático: problema, en "Diagnóstico" (desde la 2.1.1)."""
    return DecBinaryDescription(
        key=key,
        signal=signal,
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    )


def _light(key: str, signal: str) -> DecBinaryDescription:
    return DecBinaryDescription(key=key, signal=signal, device_class=BinarySensorDeviceClass.LIGHT)


def _warning(key: str, signal: str) -> DecBinaryDescription:
    """Testigo del cuadro: encendido = problema. Va en "Diagnóstico"."""
    return DecBinaryDescription(
        key=key,
        signal=signal,
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    )


#: Sensores que existieron en alguna beta y se retiraron: se borran del
#: registro al arrancar para que no queden como "no disponible".
REMOVED_KEYS: Final = ("charge_cover", "front_fog_lamp")


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
    _light("rear_fog_lamp", s.REAR_FOG_LAMP),
    DecBinaryDescription(key="climate_on", signal=s.CLIMATE_ON, feature=FEATURE_CLIMATE),
    DecBinaryDescription(
        key="air_recirculation", signal=s.AIR_RECIRCULATION, feature=FEATURE_CLIMATE
    ),
    DecBinaryDescription(
        key="key_battery_low",
        signal=s.KEY_BATTERY_LOW,
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # --- Testigos del cuadro (encendido = problema) ---------------------------
    _warning("warning_12v_battery", s.WARNING_12V_BATTERY),
    _warning("warning_tpms", s.WARNING_TPMS),
    _warning("warning_abs", s.WARNING_ABS),
    _warning("warning_airbag", s.WARNING_AIRBAG),
    _warning("warning_brake_fluid", s.WARNING_BRAKE_FLUID),
    _warning("warning_brake", s.WARNING_BRAKE),
    _warning("warning_eps", s.WARNING_EPS),
    _warning("warning_power_limit", s.WARNING_POWER_LIMIT),
    _warning("warning_power_system", s.WARNING_POWER_SYSTEM),
    _warning("warning_traction_battery_low", s.WARNING_TRACTION_BATTERY_LOW),
    _warning("warning_coolant_temperature", s.WARNING_COOLANT_TEMPERATURE),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea los sensores binarios de cada coche."""
    runtime = entry.runtime_data
    registry = er.async_get(hass)
    for vehicle in runtime.vehicles.values():
        for key in REMOVED_KEYS:
            unique_id = f"{vehicle.info.vehicle_id}_binary_sensor_{key}"
            if entity_id := registry.async_get_entity_id("binary_sensor", DOMAIN, unique_id):
                registry.async_remove(entity_id)
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
