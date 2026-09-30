"""Niveles de asientos delanteros: calefacción y ventilación (0 = apagado, 1-3). ⚠️

La ventilación solo se crea si el modelo/versión la tiene (en el S05, el Max).
El icono puede cambiar con el nivel: ``icons/svg/seat_heat_driver_2.svg``...
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import DecDeepalEntity
from .registries.vehicles import FEATURE_SEAT_HEAT, FEATURE_SEAT_VENT
from .runtime import DecDeepalConfigEntry, DecDeepalRuntime, VehicleContext
from .telemetry import signals as s


@dataclass(frozen=True, kw_only=True)
class DecSeatDescription(NumberEntityDescription):
    """Descripción de un nivel de asiento."""

    signal: str
    feature: str
    driver: bool  # True = conductor ("master"); False = acompañante ("copilot")
    ventilation: bool  # True = ventilación; False = calefacción


def _seat(key: str, signal: str, *, driver: bool, ventilation: bool) -> DecSeatDescription:
    return DecSeatDescription(
        key=key,
        signal=signal,
        feature=FEATURE_SEAT_VENT if ventilation else FEATURE_SEAT_HEAT,
        driver=driver,
        ventilation=ventilation,
        native_min_value=0,
        native_max_value=3,
        native_step=1,
        mode=NumberMode.SLIDER,
    )


SEATS: tuple[DecSeatDescription, ...] = (
    _seat("seat_heat_driver", s.SEAT_HEAT_DRIVER, driver=True, ventilation=False),
    _seat("seat_heat_passenger", s.SEAT_HEAT_PASSENGER, driver=False, ventilation=False),
    _seat("seat_vent_driver", s.SEAT_VENT_DRIVER, driver=True, ventilation=True),
    _seat("seat_vent_passenger", s.SEAT_VENT_PASSENGER, driver=False, ventilation=True),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea los niveles de asiento de cada coche."""
    runtime = entry.runtime_data
    async_add_entities(
        DecSeatLevel(runtime, vehicle, description)
        for vehicle in runtime.vehicles.values()
        for description in SEATS
        if vehicle.has(description.feature)
    )


class DecSeatLevel(DecDeepalEntity, NumberEntity):
    """Nivel de calefacción o ventilación de un asiento."""

    entity_description: DecSeatDescription

    def __init__(
        self,
        runtime: DecDeepalRuntime,
        vehicle: VehicleContext,
        description: DecSeatDescription,
    ) -> None:
        super().__init__(runtime, vehicle, "number", description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Nivel actual (0-3)."""
        value = self.signal(self.entity_description.signal)
        return None if value is None else float(value)

    def icon_state(self) -> str | None:
        """El nivel como estado para el icono ("0".."3")."""
        value = self.native_value
        return None if value is None else str(int(value))

    async def async_set_native_value(self, value: float) -> None:
        """Cambia el nivel (0 apaga)."""
        level = max(0, min(3, int(value)))
        description = self.entity_description
        vehicle_id = self.vehicle.info.vehicle_id
        commands = self.runtime.commands
        send = commands.seat_vent if description.ventilation else commands.seat_heat
        await self.vehicle.runner.run(
            description.key,
            lambda: send(vehicle_id, driver=description.driver, level=level),
            optimistic={description.signal: level},
        )
