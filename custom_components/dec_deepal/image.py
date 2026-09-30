"""Imágenes del vehículo: dos entidades separadas.

- **official_image** — "Imagen oficial": la foto que manda el servidor de
  Deepal en la lista de vehículos. Si el servidor no manda ninguna, la entidad
  aparece como no disponible.
- **dec_photo** — "Foto DEC": la foto del catálogo (``vehicles/photos``) que
  corresponde a la versión y el color elegidos en Configurar. Si no se han
  elegido, o falta esa foto, se usa la foto por defecto del modelo. Ver
  ``docs/imagenes.md``.
"""

from __future__ import annotations

import mimetypes
from datetime import UTC, datetime
from pathlib import Path

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import DecDeepalEntity
from .runtime import DecDeepalConfigEntry, DecDeepalRuntime, VehicleContext


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea las dos imágenes de cada coche."""
    runtime = entry.runtime_data
    entities: list[ImageEntity] = []
    for vehicle in runtime.vehicles.values():
        entities.append(DecOfficialImage(hass, runtime, vehicle))
        entities.append(DecPhoto(hass, runtime, vehicle))
    async_add_entities(entities)


class DecOfficialImage(DecDeepalEntity, ImageEntity):
    """Foto oficial que devuelve el servidor (``vehicleImageUrl``...)."""

    def __init__(
        self, hass: HomeAssistant, runtime: DecDeepalRuntime, vehicle: VehicleContext
    ) -> None:
        DecDeepalEntity.__init__(self, runtime, vehicle, "image", "official_image")
        ImageEntity.__init__(self, hass)
        self._attr_image_url = vehicle.info.image_url
        # La URL no cambia mientras la integración está cargada.
        self._attr_image_last_updated = datetime.now(UTC)

    @property
    def available(self) -> bool:
        """Solo disponible si el servidor dio una URL."""
        return bool(self.vehicle.info.image_url)


class DecPhoto(DecDeepalEntity, ImageEntity):
    """Foto del catálogo DEC según versión y color."""

    def __init__(
        self, hass: HomeAssistant, runtime: DecDeepalRuntime, vehicle: VehicleContext
    ) -> None:
        DecDeepalEntity.__init__(self, runtime, vehicle, "image", "dec_photo")
        ImageEntity.__init__(self, hass)
        # Se decide una vez: cambiar versión/color en Configurar recarga la
        # integración y vuelve a crear esta entidad con la foto nueva.
        self._path: Path | None = vehicle.model.photo_for(vehicle.trim, vehicle.color)
        if self._path is not None:
            self._attr_content_type = mimetypes.guess_type(self._path.name)[0] or "image/png"
        self._attr_image_last_updated = datetime.now(UTC)

    @property
    def available(self) -> bool:
        """Disponible si el catálogo tiene foto para este coche."""
        return self._path is not None

    async def async_image(self) -> bytes | None:
        """Lee la foto del disco (en un hilo aparte: es bloqueante)."""
        if self._path is None:
            return None
        return await self.hass.async_add_executor_job(self._path.read_bytes)
