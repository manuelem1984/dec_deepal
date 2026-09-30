"""Interruptores: volante calefactado y desempañado delantero. ⚠️

Su estado se lee del REST (el MQTT no es fiable para ellos, ver
``telemetry/state.py``) y se conserva el último valor si el coche no lo
informa, para que encender el clima no los "apague" en pantalla (fallo
corregido en Deepal Alternative v1.3.1).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api.commands import DeepalCommands
from .entity import DecDeepalEntity
from .registries.vehicles import FEATURE_DEFROST, FEATURE_WHEEL_HEAT
from .runtime import DecDeepalConfigEntry, DecDeepalRuntime, VehicleContext
from .telemetry import signals as s


@dataclass(frozen=True, kw_only=True)
class DecSwitchDescription(SwitchEntityDescription):
    """Descripción de un interruptor."""

    signal: str
    feature: str
    #: Devuelve la función del cliente que envía el comando (id, on/off).
    command: Callable[[DeepalCommands], Callable[[str, bool], Awaitable[str]]]


SWITCHES: tuple[DecSwitchDescription, ...] = (
    DecSwitchDescription(
        key="steering_wheel_heat",
        signal=s.STEERING_WHEEL_HEAT,
        feature=FEATURE_WHEEL_HEAT,
        command=lambda commands: commands.steering_wheel_heat,
    ),
    DecSwitchDescription(
        key="front_defrost",
        signal=s.FRONT_DEFROST,
        feature=FEATURE_DEFROST,
        command=lambda commands: commands.defrost,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea los interruptores de cada coche."""
    runtime = entry.runtime_data
    async_add_entities(
        DecSwitch(runtime, vehicle, description)
        for vehicle in runtime.vehicles.values()
        for description in SWITCHES
        if vehicle.has(description.feature)
    )


class DecSwitch(DecDeepalEntity, SwitchEntity):
    """Un interruptor de confort."""

    entity_description: DecSwitchDescription

    def __init__(
        self,
        runtime: DecDeepalRuntime,
        vehicle: VehicleContext,
        description: DecSwitchDescription,
    ) -> None:
        super().__init__(runtime, vehicle, "switch", description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Estado actual."""
        return self.signal(self.entity_description.signal)

    def icon_state(self) -> str | None:
        """``"on"`` / ``"off"`` para el icono."""
        is_on = self.is_on
        return None if is_on is None else ("on" if is_on else "off")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Encender."""
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Apagar."""
        await self._set(False)

    async def _set(self, enabled: bool) -> None:
        description = self.entity_description
        send = description.command(self.runtime.commands)
        vehicle_id = self.vehicle.info.vehicle_id
        await self.vehicle.runner.run(
            description.key,
            lambda: send(vehicle_id, enabled),
            optimistic={description.signal: enabled},
        )
