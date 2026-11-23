"""Entidades de la climatización programada (ver ``climate_schedule.py``).

No leen del coche: enseñan y cambian la programación guardada en Home
Assistant. Las crean ``switch.py``, ``time.py``, ``select.py`` y
``number.py`` en los coches con climatización.
"""

from __future__ import annotations

from datetime import time as dt_time
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.select import SelectEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.time import TimeEntity
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature

from .climate import MAX_TEMP_C, MIN_TEMP_C
from .climate_schedule import DAYS_OPTIONS, MIN_BATTERY_LIMITS, ClimateSchedule
from .entity import DecDeepalEntity
from .registries.vehicles import FEATURE_CLIMATE
from .runtime import DecDeepalRuntime, VehicleContext


def schedule_vehicles(runtime: DecDeepalRuntime) -> list[VehicleContext]:
    """Coches que tienen climatización programada."""
    if runtime.climate_schedule is None:
        return []
    return [vehicle for vehicle in runtime.vehicles.values() if vehicle.has(FEATURE_CLIMATE)]


class _ScheduleEntity(DecDeepalEntity):
    """Base: lee y cambia la programación del coche."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext, platform: str, key: str) -> None:
        super().__init__(runtime, vehicle, platform, key)

    @property
    def schedule(self) -> ClimateSchedule:
        """La programación actual."""
        return self.runtime.climate_schedule.get(self.vehicle.info.vehicle_id)

    async def _update(self, **changes: Any) -> None:
        await self.runtime.climate_schedule.async_update(self.vehicle.info.vehicle_id, **changes)

    async def async_added_to_hass(self) -> None:
        """Se pone al día cuando cambia la programación."""
        await super().async_added_to_hass()
        self.async_on_remove(self.runtime.climate_schedule.async_add_listener(self.async_write_ha_state))


class ScheduleSwitch(_ScheduleEntity, SwitchEntity):
    """«Climatización programada»: activa o no."""

    _attr_entity_category = None  # se ve con los controles, no en Configuración

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "switch", "climate_schedule")

    @property
    def is_on(self) -> bool:
        """¿Activa?"""
        return self.schedule.enabled

    def icon_state(self) -> str | None:
        """``"on"`` / ``"off"`` para el icono."""
        return "on" if self.is_on else "off"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activar."""
        await self._update(enabled=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Desactivar."""
        await self._update(enabled=False)


class ScheduleTime(_ScheduleEntity, TimeEntity):
    """Hora a la que se enciende."""

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "time", "climate_schedule_time")

    @property
    def native_value(self) -> dt_time:
        """La hora."""
        hours, minutes = self.schedule.time.split(":")
        return dt_time(int(hours), int(minutes))

    async def async_set_value(self, value: dt_time) -> None:
        """Cambiar la hora."""
        await self._update(time=f"{value.hour:02d}:{value.minute:02d}", last_run=None)


class ScheduleDays(_ScheduleEntity, SelectEntity):
    """Qué días: todos, laborables o fin de semana."""

    _attr_options = list(DAYS_OPTIONS)

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "select", "climate_schedule_days")

    @property
    def current_option(self) -> str:
        """Los días elegidos."""
        return self.schedule.days

    async def async_select_option(self, option: str) -> None:
        """Cambiar los días."""
        await self._update(days=option)


class ScheduleTemperature(_ScheduleEntity, NumberEntity):
    """Temperatura a la que se enciende."""

    _attr_native_min_value = MIN_TEMP_C
    _attr_native_max_value = MAX_TEMP_C
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "number", "climate_schedule_temperature")

    @property
    def native_value(self) -> float:
        """La temperatura."""
        return self.schedule.temperature

    async def async_set_native_value(self, value: float) -> None:
        """Cambiar la temperatura."""
        await self._update(temperature=value)


class ScheduleMinBattery(_ScheduleEntity, NumberEntity):
    """Batería mínima para encender (0 = siempre)."""

    _attr_native_min_value = MIN_BATTERY_LIMITS[0]
    _attr_native_max_value = MIN_BATTERY_LIMITS[1]
    _attr_native_step = 5
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "number", "climate_schedule_min_battery")

    @property
    def native_value(self) -> int:
        """El mínimo."""
        return self.schedule.min_battery

    async def async_set_native_value(self, value: float) -> None:
        """Cambiar el mínimo."""
        await self._update(min_battery=round(value))
