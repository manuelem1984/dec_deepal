"""Aperturas con PIN: todas las ventanillas y el maletero. ⚠️

Solo se crean con el bloque de PIN activo en Configurar.

- **windows** — abre o cierra **todas** las ventanillas a la vez. No se
  conoce ningún comando para una sola ventanilla: la versión anterior lo
  intentaba con un formato inventado que nunca se verificó. El estado se
  considera "abierto" si cualquiera de las cuatro lo está.
- **trunk_control** — abre o cierra el maletero.

Las lecturas individuales (cada ventanilla, maletero) siguen existiendo como
sensores binarios.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import CoverDeviceClass, CoverEntity, CoverEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import OPT_PIN_ENABLED
from .entity import DecDeepalEntity
from .registries.vehicles import FEATURE_PIN_COMMANDS
from .runtime import DecDeepalConfigEntry, DecDeepalRuntime, VehicleContext
from .telemetry import signals as s

_WINDOW_SIGNALS = (
    s.WINDOW_FRONT_LEFT,
    s.WINDOW_FRONT_RIGHT,
    s.WINDOW_REAR_LEFT,
    s.WINDOW_REAR_RIGHT,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea ventanillas y maletero si el bloque de PIN está activo."""
    if not entry.options.get(OPT_PIN_ENABLED):
        return
    runtime = entry.runtime_data
    entities: list[DecDeepalEntity] = []
    for vehicle in runtime.vehicles.values():
        if vehicle.has(FEATURE_PIN_COMMANDS):
            entities.append(DecWindowsCover(runtime, vehicle))
            entities.append(DecTrunkCover(runtime, vehicle))
    async_add_entities(entities)


class _DecCover(DecDeepalEntity, CoverEntity):
    """Base común: estado para el icono."""

    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def icon_state(self) -> str | None:
        closed = self.is_closed
        return None if closed is None else ("closed" if closed else "open")


class DecWindowsCover(_DecCover):
    """Todas las ventanillas."""

    _attr_device_class = CoverDeviceClass.WINDOW

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "cover", "windows")

    @property
    def is_closed(self) -> bool | None:
        """Cerrado solo si se sabe que las cuatro están cerradas."""
        values = [self.signal(signal) for signal in _WINDOW_SIGNALS]
        if any(value is True for value in values):
            return False
        if any(value is None for value in values):
            return None
        return True

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Bajar todas."""
        await self._set(open_windows=True)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Subir todas."""
        await self._set(open_windows=False)

    async def _set(self, *, open_windows: bool) -> None:
        vehicle_id = self.vehicle.info.vehicle_id
        await self.vehicle.runner.run(
            "windows",
            lambda: self.runtime.commands.windows(vehicle_id, open_windows=open_windows),
            optimistic={signal: open_windows for signal in _WINDOW_SIGNALS},
            needs_arming=True,
        )


class DecTrunkCover(_DecCover):
    """Maletero."""

    _attr_device_class = CoverDeviceClass.DOOR

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "cover", "trunk_control")

    @property
    def is_closed(self) -> bool | None:
        """Estado del maletero."""
        is_open = self.signal(s.TRUNK_OPEN)
        return None if is_open is None else not is_open

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Abrir."""
        await self._set(open_trunk=True)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Cerrar."""
        await self._set(open_trunk=False)

    async def _set(self, *, open_trunk: bool) -> None:
        vehicle_id = self.vehicle.info.vehicle_id
        await self.vehicle.runner.run(
            "trunk",
            lambda: self.runtime.commands.trunk(vehicle_id, open_trunk=open_trunk),
            optimistic={s.TRUNK_OPEN: open_trunk},
            needs_arming=True,
        )
