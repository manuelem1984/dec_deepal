"""Imágenes del vehículo: dos entidades separadas.

- **official_image** — "Imagen oficial": la foto que manda el servidor de
  Deepal en la lista de vehículos. Si el servidor no manda ninguna, la entidad
  aparece como no disponible.
- **dec_photo** — "Foto DEC": la foto del catálogo (``vehicles/photos``) que
  corresponde a la versión y el color elegidos en Configurar. Si no se han
  elegido, o falta esa foto, se usa la foto por defecto del modelo. Ver
  ``docs/imagenes.md``.

La imagen oficial se descarga aquí mismo (y no con el mecanismo estándar de
Home Assistant) por dos motivos:
- el servidor de imágenes puede no indicar bien el tipo (``Content-Type``),
  y HA descarta la imagen en ese caso; aquí se deduce por la extensión o por
  los primeros bytes;
- así se puede guardar el resultado de la última descarga (código HTTP,
  tipo, error) para verlo en los diagnósticos sin exponer la URL completa.
"""

from __future__ import annotations

import logging
import mimetypes
from datetime import UTC, datetime
from pathlib import Path
from typing import Final
from urllib.parse import urlparse

import aiohttp
from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import DecDeepalEntity
from .runtime import DecDeepalConfigEntry, DecDeepalRuntime, VehicleContext

_LOGGER = logging.getLogger(__name__)

#: Segundos máximos para descargar la imagen oficial.
DOWNLOAD_TIMEOUT: Final = 20

#: Firmas de los formatos de imagen más habituales (primeros bytes).
_MAGIC: Final = (
    (b"\x89PNG", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF8", "image/gif"),
    (b"RIFF", "image/webp"),
)


def _guess_content_type(url: str, header: str | None, data: bytes) -> str | None:
    """Tipo de imagen: cabecera si es de imagen; si no, bytes; si no, extensión."""
    if header and header.split(";")[0].strip().startswith("image/"):
        return header.split(";")[0].strip()
    for magic, content_type in _MAGIC:
        if data.startswith(magic):
            return content_type
    guessed = mimetypes.guess_type(urlparse(url).path)[0]
    return guessed if guessed and guessed.startswith("image/") else None


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
        # La URL no cambia mientras la integración está cargada.
        self._attr_image_last_updated = datetime.now(UTC)
        self._cached: bytes | None = None
        # Resultado de cada descarga: vehicle.official_image_status (lo
        # muestran los diagnósticos, sin la URL completa).
        self.vehicle.official_image_status = {
            "estado": "sin_descargar",
            "tiene_url": bool(vehicle.info.image_url),
        }

    @property
    def _url(self) -> str | None:
        return self.vehicle.info.image_url

    @property
    def available(self) -> bool:
        """Solo disponible si el servidor dio una URL."""
        return bool(self._url)

    async def async_image(self) -> bytes | None:
        """Descarga la imagen (una vez; luego se sirve de memoria)."""
        if self._cached is not None:
            return self._cached
        url = self._url
        if not url:
            self.vehicle.official_image_status = {"estado": "sin_url"}
            return None
        host = urlparse(url).netloc or "(URL relativa)"
        try:
            async with async_get_clientsession(self.hass).get(
                url, timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
            ) as response:
                data = await response.read()
                header = response.headers.get("Content-Type")
                status = response.status
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            self.vehicle.official_image_status = {"estado": "error", "servidor": host, "error": str(err)}
            _LOGGER.warning("Imagen oficial: no se pudo descargar de %s: %s", host, err)
            return None

        content_type = _guess_content_type(url, header, data)
        self.vehicle.official_image_status = {
            "estado": "ok" if status == 200 and content_type else "error",
            "servidor": host,
            "http": status,
            "content_type_servidor": header,
            "content_type_usado": content_type,
            "bytes": len(data),
        }
        if status != 200 or content_type is None:
            _LOGGER.warning(
                "Imagen oficial no válida (servidor %s, HTTP %s, tipo %s)", host, status, header
            )
            return None
        self._attr_content_type = content_type
        self._cached = data
        return data


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
