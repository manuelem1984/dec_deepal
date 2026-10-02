"""Imágenes del vehículo: tres entidades separadas.

- **official_image** — "Imagen oficial": la foto que manda el servidor de
  Deepal en la lista de vehículos. Si el servidor no manda ninguna, la entidad
  aparece como no disponible.
- **dec_photo** — "Imagen DEC": la foto del catálogo (``vehicles/photos``) que
  corresponde a la versión y el color elegidos en Configurar. Si no se han
  elegido, o falta esa foto, se usa la foto por defecto del modelo. Ver
  ``docs/imagenes.md``.
- **top_view** — "Vista de planta": el coche visto desde arriba, montado con
  capas según su estado (puertas, capó, maletero, ventanillas, luces). Las
  capas están en ``vehicles/vista_planta/<carpeta>/capas.yaml``; el dibujo,
  en ``top_view.py``.

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
from typing import Any, Final
from urllib.parse import urlparse

import aiohttp
from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import DecDeepalEntity
from .registries.top_view import Selection, TopViewLayers
from .runtime import DecDeepalConfigEntry, DecDeepalRuntime, VehicleContext
from .top_view import TopViewRenderer

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


async def fetch_official_image(
    hass: HomeAssistant, vehicle: VehicleContext
) -> tuple[bytes, str] | None:
    """Descarga la imagen oficial del coche (una vez; luego, de memoria).

    La usan las dos entidades: "Imagen oficial" siempre, e "Imagen DEC" cuando
    el catálogo no tiene foto para el coche. El resultado de cada intento se
    guarda en ``vehicle.official_image_status`` (lo muestran los diagnósticos,
    sin la URL completa).

    Returns:
        ``(bytes, content_type)`` o ``None`` si no hay URL o la descarga falla.
    """
    if vehicle.official_image_cache is not None:
        return vehicle.official_image_cache
    url = vehicle.info.image_url
    if not url:
        vehicle.official_image_status = {"estado": "sin_url"}
        return None
    host = urlparse(url).netloc or "(URL relativa)"
    try:
        async with async_get_clientsession(hass).get(
            url, timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
        ) as response:
            data = await response.read()
            header = response.headers.get("Content-Type")
            status = response.status
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        vehicle.official_image_status = {"estado": "error", "servidor": host, "error": str(err)}
        _LOGGER.warning("Imagen oficial: no se pudo descargar de %s: %s", host, err)
        return None

    content_type = _guess_content_type(url, header, data)
    vehicle.official_image_status = {
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
    vehicle.official_image_cache = (data, content_type)
    return vehicle.official_image_cache


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea las imágenes de cada coche."""
    runtime = entry.runtime_data
    entities: list[ImageEntity] = []
    for vehicle in runtime.vehicles.values():
        vehicle.official_image_status = {
            "estado": "sin_descargar",
            "tiene_url": bool(vehicle.info.image_url),
        }
        entities.append(DecOfficialImage(hass, runtime, vehicle))
        entities.append(DecImage(hass, runtime, vehicle))
        layers = top_view_layers(vehicle)
        if layers is not None:
            entities.append(DecTopView(hass, runtime, vehicle, layers))
    async_add_entities(entities)


def top_view_layers(vehicle: VehicleContext) -> TopViewLayers | None:
    """Capas de la vista de planta del coche.

    Las del modelo elegido; si aún no se ha elegido (modelo genérico), las del
    modelo reconocido por el nombre. ``None`` si ninguno tiene.
    """
    if vehicle.model.top_view is not None:
        return vehicle.model.top_view
    if vehicle.suggested_model is not None:
        return vehicle.suggested_model.top_view
    return None


class DecOfficialImage(DecDeepalEntity, ImageEntity):
    """"Imagen oficial": la que devuelve el servidor (``vehicleImageUrl``...)."""

    def __init__(
        self, hass: HomeAssistant, runtime: DecDeepalRuntime, vehicle: VehicleContext
    ) -> None:
        DecDeepalEntity.__init__(self, runtime, vehicle, "image", "official_image")
        ImageEntity.__init__(self, hass)
        # La URL no cambia mientras la integración está cargada.
        self._attr_image_last_updated = datetime.now(UTC)

    @property
    def available(self) -> bool:
        """Solo disponible si el servidor dio una URL."""
        return bool(self.vehicle.info.image_url)

    async def async_image(self) -> bytes | None:
        """Imagen oficial (descargada una vez)."""
        result = await fetch_official_image(self.hass, self.vehicle)
        if result is None:
            return None
        data, self._attr_content_type = result
        return data


class DecImage(DecDeepalEntity, ImageEntity):
    """"Imagen DEC": foto del catálogo según versión y color.

    Si el catálogo no tiene foto para este coche (modelo genérico, o falta
    la foto y no hay foto por defecto), muestra la **imagen oficial** del
    servidor. Así la ficha del dispositivo siempre tiene imagen.

    La clave interna sigue siendo ``dec_photo`` (antes "Imagen DEC") para no
    cambiar el ``entity_id`` de quien ya la tiene.
    """

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
        """Disponible si hay foto del catálogo o, en su defecto, imagen oficial."""
        return self._path is not None or bool(self.vehicle.info.image_url)

    async def async_image(self) -> bytes | None:
        """Foto del catálogo (leída del disco) o, si no hay, la imagen oficial."""
        if self._path is not None:
            return await self.hass.async_add_executor_job(self._path.read_bytes)
        result = await fetch_official_image(self.hass, self.vehicle)
        if result is None:
            return None
        data, self._attr_content_type = result
        return data


class DecTopView(DecDeepalEntity, ImageEntity):
    """"Vista de planta": el coche desde arriba según su estado.

    Cada vez que llegan datos se decide qué capas tocan (puerta abierta,
    capó cerrado...). Solo si cambian se marca la imagen como nueva, y Home
    Assistant la vuelve a pedir; la imagen se monta al pedirla.

    Dato desconocido: se usa el **último valor conocido** de esa señal (desde
    que arrancó la integración); si nunca se ha conocido, se dibuja cerrado /
    apagado. Los atributos dicen qué está activo y qué no tiene dato.
    """

    _attr_content_type = "image/png"

    def __init__(
        self,
        hass: HomeAssistant,
        runtime: DecDeepalRuntime,
        vehicle: VehicleContext,
        layers: TopViewLayers,
    ) -> None:
        DecDeepalEntity.__init__(self, runtime, vehicle, "image", "top_view")
        ImageEntity.__init__(self, hass)
        self._layers = layers
        # Se decide una vez: cambiar el color en Configurar recarga la
        # integración y vuelve a crear esta entidad.
        self._renderer = TopViewRenderer(layers, vehicle.color)
        self._last_known: dict[str, bool] = {}
        self._unknown: tuple[str, ...] = ()
        self._selection = self._select()
        self._attr_image_last_updated = datetime.now(UTC)

    def _select(self) -> Selection:
        """Capas que tocan con los datos actuales (y apunta los desconocidos)."""
        values: dict[str, bool | None] = {}
        unknown: list[str] = []
        for name in self._layers.signals:
            raw = self.signal(name)
            if raw is None:
                unknown.append(name)
                values[name] = self._last_known.get(name)
            else:
                values[name] = self._last_known[name] = bool(raw)
        self._unknown = tuple(unknown)
        return self._layers.select(values.get)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Datos nuevos: si cambian las capas, la imagen es nueva."""
        selection = self._select()
        if selection.images != self._selection.images:
            self._attr_image_last_updated = datetime.now(UTC)
        self._selection = selection
        super()._handle_coordinator_update()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Qué está abierto / encendido y qué señales no tienen dato."""
        return {
            "activo": list(self._selection.active),
            "sin_dato": list(self._unknown),
        }

    async def async_image(self) -> bytes | None:
        """PNG montado con las capas actuales."""
        return await self.hass.async_add_executor_job(
            self._renderer.render, self._selection.images
        )
