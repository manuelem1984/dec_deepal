"""Entidades del diario del coche (ver ``car_log.py``): totales, consumo, último viaje y precios.

Las crean ``sensor.py`` y ``number.py`` en todos los coches. Los totales
tienen ``state_class`` total: Home Assistant guarda sus estadísticas y las
enseña por día, semana o mes (tarjeta de estadísticas, panel de Energía).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfEnergy, UnitOfEnergyDistance, UnitOfLength
from homeassistant.util import dt as dt_util

from . import car_log
from .entity import DecDeepalEntity
from .runtime import DecDeepalRuntime, VehicleContext


class _LogEntity(DecDeepalEntity):
    """Base: lee el diario del coche y se pone al día con él."""

    @property
    def log(self) -> dict[str, Any]:
        """El diario."""
        return self.runtime.car_log.log(self.vehicle.info.vehicle_id)

    async def async_added_to_hass(self) -> None:
        """Se pone al día cuando cambia el diario."""
        await super().async_added_to_hass()
        self.async_on_remove(self.runtime.car_log.async_add_listener(self.async_write_ha_state))


class ChargedEnergy(_LogEntity, SensorEntity):
    """kWh que han entrado en la batería en todas las cargas apuntadas."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 1

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "sensor", "charged_energy")

    @property
    def native_value(self) -> float:
        """El total."""
        return self.log["totals"]["charge_kwh"]


class ChargingCost(_LogEntity, SensorEntity):
    """Coste de todas las cargas apuntadas (con los precios elegidos)."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "sensor", "charging_cost")

    @property
    def native_unit_of_measurement(self) -> str:
        """La moneda de Home Assistant."""
        return self.hass.config.currency

    @property
    def native_value(self) -> float:
        """El total."""
        return self.log["totals"]["charge_cost"]


class AverageConsumption(_LogEntity, SensorEntity):
    """Consumo medio de los últimos viajes largos (kWh/100 km)."""

    _attr_device_class = SensorDeviceClass.ENERGY_DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfEnergyDistance.KILO_WATT_HOUR_PER_100_KM
    _attr_suggested_display_precision = 1

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "sensor", "average_consumption")

    @property
    def native_value(self) -> float | None:
        """El consumo (sin viajes suficientes, desconocido)."""
        return car_log.consumption(self.log)


class LastTrip(_LogEntity, SensorEntity):
    """Km del último viaje, con sus datos como atributos."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "sensor", "last_trip")

    @property
    def native_value(self) -> float | None:
        """Km del último viaje."""
        trip = car_log.last(self.log, car_log.KIND_TRIP)
        return None if trip is None else trip.get("km")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """El viaje y el resumen del mes (los lee la tarjeta)."""
        trip = car_log.last(self.log, car_log.KIND_TRIP) or {}
        now = dt_util.now()
        return {
            "inicio": trip.get("start"),
            "fin": trip.get("end"),
            "nivel_inicio": trip.get("start_level"),
            "nivel_fin": trip.get("end_level"),
            "kwh": trip.get("kwh"),
            "mes": car_log.month_summary(self.log, now.year, now.month),
        }


class ChargePrice(_LogEntity, NumberEntity):
    """Precio de la electricidad (por kWh) en casa (AC) o en carga rápida (DC)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 2
    _attr_native_step = 0.001
    _attr_mode = NumberMode.BOX

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext, kind: str) -> None:
        super().__init__(runtime, vehicle, "number", f"charge_price_{'home' if kind == 'ac' else 'fast'}")
        self._kind = kind

    @property
    def native_unit_of_measurement(self) -> str:
        """Moneda por kWh."""
        return f"{self.hass.config.currency}/kWh"

    @property
    def native_value(self) -> float:
        """El precio (0 = sin precio: las cargas no tendrán coste)."""
        return self.log["prices"].get(self._kind, 0.0)

    async def async_set_native_value(self, value: float) -> None:
        """Cambiar el precio (para las cargas que terminen desde ahora)."""
        await self.runtime.car_log.async_set_price(self.vehicle.info.vehicle_id, self._kind, value)


def log_sensors(runtime: DecDeepalRuntime) -> list[SensorEntity]:
    """Sensores del diario de todos los coches."""
    if runtime.car_log is None:
        return []
    return [
        cls(runtime, vehicle)
        for vehicle in runtime.vehicles.values()
        for cls in (ChargedEnergy, ChargingCost, AverageConsumption, LastTrip)
    ]


def log_numbers(runtime: DecDeepalRuntime) -> list[NumberEntity]:
    """Precios de la electricidad de todos los coches."""
    if runtime.car_log is None:
        return []
    return [ChargePrice(runtime, vehicle, kind) for vehicle in runtime.vehicles.values() for kind in car_log.PRICE_KINDS]
