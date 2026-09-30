"""Botones: actualizar datos, parpadear luces, claxon, luces + claxon.

Los tres de luces/claxon tienen **espera física** (ver
``command_runner.COOLDOWN_SECONDS``): repetirlos antes de tiempo muestra los
segundos que faltan.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api.commands import FLASH_HONK_BOTH, FLASH_HONK_FLASH, FLASH_HONK_HORN
from .api.errors import DeepalError
from .entity import DecDeepalEntity
from .registries.vehicles import FEATURE_LIGHTS_HORN
from .runtime import DecDeepalConfigEntry, DecDeepalRuntime, VehicleContext


@dataclass(frozen=True, kw_only=True)
class DecButtonDescription(ButtonEntityDescription):
    """Descripción de un botón DEC Deepal."""

    #: Acción de flashing-honking, o ``None`` para el botón de actualizar.
    flash_honk_action: int | None = None
    feature: str | None = None


BUTTONS: tuple[DecButtonDescription, ...] = (
    DecButtonDescription(key="refresh"),
    DecButtonDescription(
        key="flash_lights", flash_honk_action=FLASH_HONK_FLASH, feature=FEATURE_LIGHTS_HORN
    ),
    DecButtonDescription(
        key="honk_horn", flash_honk_action=FLASH_HONK_HORN, feature=FEATURE_LIGHTS_HORN
    ),
    DecButtonDescription(
        key="flash_and_honk", flash_honk_action=FLASH_HONK_BOTH, feature=FEATURE_LIGHTS_HORN
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea los botones de cada coche."""
    runtime = entry.runtime_data
    async_add_entities(
        DecButton(runtime, vehicle, description)
        for vehicle in runtime.vehicles.values()
        for description in BUTTONS
        if description.feature is None or vehicle.has(description.feature)
    )


class DecButton(DecDeepalEntity, ButtonEntity):
    """Un botón."""

    entity_description: DecButtonDescription

    def __init__(
        self,
        runtime: DecDeepalRuntime,
        vehicle: VehicleContext,
        description: DecButtonDescription,
    ) -> None:
        super().__init__(runtime, vehicle, "button", description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Pulsación del botón."""
        action = self.entity_description.flash_honk_action
        if action is None:
            await self._refresh()
            return
        vehicle_id = self.vehicle.info.vehicle_id
        send: Callable[[], Awaitable[str]] = lambda: self.runtime.commands.flash_honk(  # noqa: E731
            vehicle_id, action
        )
        # Luces y claxon no cambian ningún dato: no hace falta releer.
        await self.vehicle.runner.run(self.entity_description.key, send, refresh_after=False)

    async def _refresh(self) -> None:
        """Pide al coche datos frescos y relee.

        El aviso al coche (``condition-inquiry``) es un comando firmado; si
        falla (p. ej. falta la clave de firma), se hace igualmente una lectura
        normal: el botón nunca debe quedarse sin hacer nada.
        """
        try:
            await self.runtime.commands.condition_inquiry(self.vehicle.info.vehicle_id)
        except DeepalError:
            pass
        await self.coordinator.async_request_refresh()
