"""Climatización del habitáculo: encender/apagar y temperatura objetivo. ✅

Verificado con la app oficial. El ventilador sigue siendo solo lectura
(sensor ``fan_level``): cambiarlo exigiría conocer los valores de
``windMode``, que no se han investigado.
"""

from __future__ import annotations

from typing import Any, Final

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import DecDeepalEntity
from .registries.vehicles import FEATURE_CLIMATE
from .runtime import DecDeepalConfigEntry, DecDeepalRuntime, VehicleContext
from .telemetry import signals as s

#: Límites razonables; los reales del coche no se han confirmado.
MIN_TEMP_C: Final = 16.0
MAX_TEMP_C: Final = 32.0
DEFAULT_TEMP_C: Final = 22.0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea la climatización de cada coche que la tenga."""
    runtime = entry.runtime_data
    async_add_entities(
        DecClimate(runtime, vehicle)
        for vehicle in runtime.vehicles.values()
        if vehicle.has(FEATURE_CLIMATE)
    )


class DecClimate(DecDeepalEntity, ClimateEntity):
    """Climatización: modo apagado / automático y temperatura."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT_COOL]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_min_temp = MIN_TEMP_C
    _attr_max_temp = MAX_TEMP_C
    _attr_target_temperature_step = 0.5

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "climate", "cabin_climate")

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Encendido → ``heat_cool``; apagado → ``off``."""
        on = self.signal(s.CLIMATE_ON)
        if on is None:
            return None
        return HVACMode.HEAT_COOL if on else HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        """Temperatura interior actual."""
        return self.signal(s.INSIDE_TEMP_C)

    @property
    def target_temperature(self) -> float | None:
        """Temperatura objetivo."""
        return self.signal(s.CLIMATE_TARGET_C)

    def icon_state(self) -> str | None:
        """El modo HVAC como estado para el icono."""
        mode = self.hvac_mode
        return None if mode is None else str(mode)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Encender o apagar."""
        await self._send(on=hvac_mode != HVACMode.OFF, target=self.target_temperature)

    async def async_turn_on(self) -> None:
        """Encender."""
        await self._send(on=True, target=self.target_temperature)

    async def async_turn_off(self) -> None:
        """Apagar."""
        await self._send(on=False, target=self.target_temperature)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Fijar temperatura (y encender, como hace la app)."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self._send(on=True, target=float(temperature))

    async def _send(self, *, on: bool, target: float | None) -> None:
        """Envía el comando con valor optimista."""
        target_c = target or DEFAULT_TEMP_C
        vehicle_id = self.vehicle.info.vehicle_id
        optimistic: dict[str, Any] = {s.CLIMATE_ON: on}
        if on:
            optimistic[s.CLIMATE_TARGET_C] = target_c
        await self.vehicle.runner.run(
            "climate",
            lambda: self.runtime.commands.air_conditioner(
                vehicle_id, enabled=on, target_c=target_c
            ),
            optimistic=optimistic,
        )
