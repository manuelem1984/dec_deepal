"""Cerraduras: cierre centralizado (con PIN) y candado de armado (Opción B).

Ninguna se crea si el bloque de PIN está desactivado en Configurar: una
cerradura que siempre se niega a funcionar solo confunde.

- **doors** — bloquear/desbloquear todas las puertas. ⚠️ Formato del comando
  tomado de Deepal Alternative; pendiente de confirmar en el S05 de España.
- **pin_arm** — "Desbloqueo acciones con PIN". No envía nada al coche: abre
  una ventana de N segundos en la que se permiten los comandos con PIN.
  Solo existe en la Opción B. Siempre arranca bloqueado.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import OPT_PIN_ENABLED, OPT_PIN_MODE, PIN_MODE_ARMED
from .entity import DecDeepalEntity
from .registries.vehicles import FEATURE_PIN_COMMANDS
from .runtime import DecDeepalConfigEntry, DecDeepalRuntime, VehicleContext
from .telemetry import signals as s


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea las cerraduras si el bloque de PIN está activo."""
    if not entry.options.get(OPT_PIN_ENABLED):
        return
    runtime = entry.runtime_data
    armed_mode = entry.options.get(OPT_PIN_MODE) == PIN_MODE_ARMED
    entities: list[DecDeepalEntity] = []
    for vehicle in runtime.vehicles.values():
        if not vehicle.has(FEATURE_PIN_COMMANDS):
            continue
        entities.append(DecDoorLock(runtime, vehicle))
        if armed_mode:
            entities.append(DecPinArmLock(runtime, vehicle))
    async_add_entities(entities)


class DecDoorLock(DecDeepalEntity, LockEntity):
    """Cierre centralizado del coche (todas las puertas a la vez)."""

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "lock", "doors")

    @property
    def is_locked(self) -> bool | None:
        """Bloqueado si las dos cerraduras delanteras lo están."""
        return self.signal(s.CENTRAL_LOCKED)

    def icon_state(self) -> str | None:
        locked = self.is_locked
        return None if locked is None else ("locked" if locked else "unlocked")

    async def async_lock(self, **kwargs: Any) -> None:
        """Bloquear."""
        await self._set(locked=True)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Desbloquear."""
        await self._set(locked=False)

    async def _set(self, *, locked: bool) -> None:
        vehicle_id = self.vehicle.info.vehicle_id
        await self.vehicle.runner.run(
            "doors",
            lambda: self.runtime.commands.doors(vehicle_id, unlock=not locked),
            optimistic={s.LOCKED_DRIVER: locked, s.LOCKED_PASSENGER: locked},
            needs_arming=True,
        )


class DecPinArmLock(DecDeepalEntity, LockEntity):
    """"Desbloqueo acciones con PIN" (Opción B)."""

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "lock", "pin_arm")

    @property
    def available(self) -> bool:
        """Siempre disponible: no depende de que el coche responda."""
        return True

    @property
    def is_locked(self) -> bool:
        """Bloqueado = comandos con PIN no permitidos."""
        return not self.vehicle.runner.is_armed

    def icon_state(self) -> str | None:
        return "locked" if self.is_locked else "unlocked"

    async def async_lock(self, **kwargs: Any) -> None:
        """Volver a bloquear ya."""
        self.vehicle.runner.disarm()

    async def async_unlock(self, **kwargs: Any) -> None:
        """Permitir comandos con PIN durante la ventana configurada."""
        self.vehicle.runner.arm()
