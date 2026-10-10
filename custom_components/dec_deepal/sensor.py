"""Sensores (valores numéricos, fechas y estados de texto).

Cada sensor es una fila de :data:`SENSORS`: clave, señal que muestra, unidad
y tipo. El nombre visible está en ``translations/<idioma>.json``; el icono en
``icons/icons.yaml``. Estado de verificación de cada uno:
``docs/correlacion_endpoints_entidades.csv``.

Los sensores cuya fuente no está confirmada en el S05 se crean
**desactivados** (``entity_registry_enabled_default=False``): el usuario puede
activarlos desde la ficha de la entidad si quiere probarlos.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api.models import VehicleInfo
from .entity import DecDeepalEntity, DecMaintenanceEntity, remove_entities
from .maintenance import MaintenanceStatus
from .runtime import DecDeepalConfigEntry, DecDeepalRuntime, VehicleContext
from .telemetry import signals as s
from .telemetry.derived import CHARGE_STATUS_OPTIONS


@dataclass(frozen=True, kw_only=True)
class DecSensorDescription(SensorEntityDescription):
    """Descripción de un sensor DEC Deepal."""

    signal: str
    #: Función del catálogo necesaria (``None`` = siempre).
    feature: str | None = None
    #: Si se indica, el valor sale de los datos fijos del coche (lista de
    #: vehículos del servidor) en vez de una señal de telemetría.
    info_value: Callable[[VehicleInfo], Any] | None = None


def _pressure(key: str, signal: str) -> DecSensorDescription:
    """Sensor de presión de neumático: llega en kPa, se muestra en bar."""
    return DecSensorDescription(
        key=key,
        signal=signal,
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.KPA,
        suggested_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
    )


def _window_opening(key: str, signal: str) -> DecSensorDescription:
    """Apertura de una ventanilla. ⚠️ Desactivada: la escala no está clara.

    Prueba con el coche (05-10-2026): modo ventilación → 19-20; bajada a la
    mitad → 92; bajada del todo → 97; cerrada → 0 en los diagnósticos, pero
    en pantalla se llegó a ver 100. No es un porcentaje lineal fiable, así
    que se crea desactivada hasta entenderla.
    """
    return DecSensorDescription(
        key=key,
        signal=signal,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    )


SENSORS: tuple[DecSensorDescription, ...] = (
    # --- Batería y carga ----------------------------------------------------
    DecSensorDescription(
        key="battery_level",
        signal=s.BATTERY_LEVEL,
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DecSensorDescription(
        key="range",
        signal=s.RANGE_KM,
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DecSensorDescription(
        key="charge_status",
        signal=s.CHARGE_STATUS,
        device_class=SensorDeviceClass.ENUM,
        options=list(CHARGE_STATUS_OPTIONS),
    ),
    DecSensorDescription(
        key="charge_current",
        signal=s.CHARGE_CURRENT,
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DecSensorDescription(
        key="ac_charge_current",
        signal=s.AC_CHARGE_CURRENT,
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DecSensorDescription(
        key="dc_charge_current",
        signal=s.DC_CHARGE_CURRENT,
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DecSensorDescription(
        key="remaining_charge_time",
        signal=s.REMAINING_CHARGE_MIN,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    DecSensorDescription(
        key="remaining_charge_time_hhmm",
        signal=s.REMAINING_CHARGE_HHMM,
    ),
    # --- Estado general -----------------------------------------------------
    DecSensorDescription(
        key="odometer",
        signal=s.ODOMETER_KM,
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    DecSensorDescription(
        key="last_update",
        signal=s.REPORT_TIME,
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    DecSensorDescription(
        key="power_status",
        signal=s.POWER_STATUS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DecSensorDescription(
        key="speed",
        signal=s.SPEED_KMH,
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    DecSensorDescription(
        key="trip_mileage",
        signal=s.TRIP_KM,
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        entity_registry_enabled_default=False,
    ),
    DecSensorDescription(
        key="mileage_yesterday",
        signal=s.MILEAGE_YESTERDAY_KM,
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        entity_registry_enabled_default=False,
    ),
    # --- Clima --------------------------------------------------------------
    DecSensorDescription(
        key="inside_temperature",
        signal=s.INSIDE_TEMP_C,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DecSensorDescription(
        key="outside_temperature",
        signal=s.OUTSIDE_TEMP_C,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    DecSensorDescription(
        key="cabin_humidity",
        signal=s.CABIN_HUMIDITY,
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DecSensorDescription(
        key="climate_target_temperature",
        signal=s.CLIMATE_TARGET_C,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    DecSensorDescription(
        key="fan_level",
        signal=s.FAN_LEVEL,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # --- Neumáticos ---------------------------------------------------------
    _pressure("tire_pressure_front_left", s.TIRE_PRESSURE_FRONT_LEFT),
    _pressure("tire_pressure_front_right", s.TIRE_PRESSURE_FRONT_RIGHT),
    _pressure("tire_pressure_rear_left", s.TIRE_PRESSURE_REAR_LEFT),
    _pressure("tire_pressure_rear_right", s.TIRE_PRESSURE_REAR_RIGHT),
    # --- Apertura de ventanillas (⚠️ escala dudosa: desactivadas) -------------
    _window_opening("window_opening_front_left", s.WINDOW_OPENING_FRONT_LEFT),
    _window_opening("window_opening_front_right", s.WINDOW_OPENING_FRONT_RIGHT),
    _window_opening("window_opening_rear_left", s.WINDOW_OPENING_REAR_LEFT),
    _window_opening("window_opening_rear_right", s.WINDOW_OPENING_REAR_RIGHT),
    # --- Datos fijos del coche ----------------------------------------------
    # Matrícula: la lista de vehículos del servidor la trae en "plateNumber"
    # (✅ visto con dos S05 de España, 01-10-2026). Se actualiza al arrancar.
    DecSensorDescription(
        key="license_plate",
        signal="",
        info_value=lambda info: info.license_plate,
    ),
)


@dataclass(frozen=True, kw_only=True)
class DecMaintenanceDescription(SensorEntityDescription):
    """Sensor de mantenimiento: un dato de la próxima revisión."""

    value: Callable[[MaintenanceStatus], int | date | None]


#: Días y kilómetros que quedan (negativos si la revisión está vencida) y
#: fecha prevista. Ver ``maintenance.py``.
MAINTENANCE_SENSORS: Final[tuple[DecMaintenanceDescription, ...]] = (
    DecMaintenanceDescription(
        key="maintenance_days",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        suggested_display_precision=0,
        value=lambda current: current.days_left,
    ),
    DecMaintenanceDescription(
        key="maintenance_km",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        value=lambda current: current.km_left,
    ),
    DecMaintenanceDescription(
        key="maintenance_date",
        device_class=SensorDeviceClass.DATE,
        value=lambda current: current.due_date,
    ),
)


@dataclass(frozen=True, kw_only=True)
class DecDocumentDescription(SensorEntityDescription):
    """Sensor de ITV o de seguro: un dato sacado del gestor de avisos."""

    value: Callable[[Any, str], int | date | None]


def _itv(field: str) -> Callable[[Any, str], int | date | None]:
    return lambda alerts, vehicle_id: getattr(alerts.itv_status(vehicle_id), field, None)


def _insurance(field: str) -> Callable[[Any, str], int | date | None]:
    return lambda alerts, vehicle_id: getattr(alerts.insurance_status(vehicle_id), field, None)


def _days(key: str, value: Callable[[Any, str], int | date | None]) -> DecDocumentDescription:
    return DecDocumentDescription(
        key=key,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        suggested_display_precision=0,
        value=value,
    )


def _date(key: str, value: Callable[[Any, str], int | date | None]) -> DecDocumentDescription:
    return DecDocumentDescription(key=key, device_class=SensorDeviceClass.DATE, value=value)


#: ITV: fecha límite y días que quedan (negativos si está vencida).
ITV_SENSORS: Final = (_date("itv_date", _itv("due_date")), _days("itv_days", _itv("days_left")))
#: Seguro: renovación, días que faltan y último día para desistir.
INSURANCE_SENSORS: Final = (
    _date("insurance_renewal_date", _insurance("renewal_date")),
    _days("insurance_days", _insurance("days_to_renewal")),
    _date("insurance_cancel_date", _insurance("cancel_deadline")),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea los sensores de cada coche de la cuenta."""
    runtime = entry.runtime_data
    entities: list[SensorEntity] = [
        DecSensor(runtime, vehicle, description)
        for vehicle in runtime.vehicles.values()
        for description in SENSORS
        if description.feature is None or vehicle.has(description.feature)
    ]
    # Mantenimiento: solo en los coches que lo tienen activado.
    keys = tuple(description.key for description in MAINTENANCE_SENSORS)
    for vehicle in runtime.vehicles.values():
        if runtime.alerts.record(vehicle.info.vehicle_id) is None:
            remove_entities(hass, "sensor", vehicle.info.vehicle_id, keys)
            continue
        entities.extend(
            DecMaintenanceSensor(runtime, vehicle, description)
            for description in MAINTENANCE_SENSORS
        )
    # ITV y seguro: solo en los coches que los tienen activados.
    for descriptions, record_of in (
        (ITV_SENSORS, runtime.alerts.itv_record),
        (INSURANCE_SENSORS, runtime.alerts.insurance_record),
    ):
        keys = tuple(description.key for description in descriptions)
        for vehicle in runtime.vehicles.values():
            if record_of(vehicle.info.vehicle_id) is None:
                remove_entities(hass, "sensor", vehicle.info.vehicle_id, keys)
                continue
            entities.extend(
                DecDocumentSensor(runtime, vehicle, description) for description in descriptions
            )
    async_add_entities(entities)


class DecSensor(DecDeepalEntity, SensorEntity):
    """Un sensor que muestra una señal."""

    entity_description: DecSensorDescription

    def __init__(
        self,
        runtime: DecDeepalRuntime,
        vehicle: VehicleContext,
        description: DecSensorDescription,
    ) -> None:
        super().__init__(runtime, vehicle, "sensor", description.key)
        self.entity_description = description

    @property
    def native_value(self):  # noqa: ANN201 - el tipo depende del sensor
        """Valor actual de la señal (o del dato fijo del coche)."""
        if self.entity_description.info_value is not None:
            return self.entity_description.info_value(self.vehicle.info)
        return self.signal(self.entity_description.signal)

    def icon_state(self) -> str | None:
        """Los sensores de tipo lista usan su opción para el icono."""
        if self.entity_description.device_class == SensorDeviceClass.ENUM:
            value = self.native_value
            return None if value is None else str(value)
        return None


class DecMaintenanceSensor(DecMaintenanceEntity, SensorEntity):
    """Un dato de la próxima revisión (días, kilómetros o fecha)."""

    entity_description: DecMaintenanceDescription

    def __init__(
        self,
        runtime: DecDeepalRuntime,
        vehicle: VehicleContext,
        description: DecMaintenanceDescription,
    ) -> None:
        super().__init__(runtime, vehicle, "sensor", description.key)
        self.entity_description = description

    @property
    def native_value(self) -> int | date | None:
        """Valor actual (``None`` si falta el cuentakilómetros, en los km)."""
        current = self.maintenance
        return None if current is None else self.entity_description.value(current)


class DecDocumentSensor(DecMaintenanceEntity, SensorEntity):
    """Un dato de la ITV o del seguro (fecha o días)."""

    entity_description: DecDocumentDescription

    def __init__(
        self,
        runtime: DecDeepalRuntime,
        vehicle: VehicleContext,
        description: DecDocumentDescription,
    ) -> None:
        super().__init__(runtime, vehicle, "sensor", description.key)
        self.entity_description = description

    @property
    def native_value(self) -> int | date | None:
        """Valor actual."""
        return self.entity_description.value(self.runtime.alerts, self.vehicle.info.vehicle_id)
