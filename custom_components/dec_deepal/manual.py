"""Manual de usuario del coche, visto dentro de la tarjeta.

El manual es un PDF en la web del fabricante. Su servidor no deja mostrarlo
incrustado en otras páginas (``X-Frame-Options: SAMEORIGIN``), así que Home
Assistant hace de **intermediario**: la tarjeta lo pide aquí y esta vista lo
lee del enlace en ese momento y lo va pasando. No se guarda ninguna copia.

Qué enlace se usa (:func:`manual_url`):

1. El que el usuario haya puesto en Configurar → Avanzado para ese modelo.
2. Si no, el del catálogo (``manual:`` del modelo en ``vehicles.yaml``).
3. Si el modelo no tiene, no hay manual (la tarjeta no enseña la opción).

Dos vistas, las dos solo para usuarios con sesión en Home Assistant:

- ``GET /api/dec_deepal/manual_info/<device_id>`` → ``{"available": bool}``.
- ``GET /api/dec_deepal/manual/<device_id>`` → el PDF. La tarjeta la abre en
  un ``<iframe>`` con una dirección firmada (``auth/sign_path``), porque un
  ``<iframe>`` no puede enviar la cabecera de sesión.

Solo se sirve el enlace configurado: la dirección no admite parámetros.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Final

from aiohttp import ClientError, ClientTimeout, hdrs, web
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, MANUAL_API, MANUAL_INFO_API, OPT_MANUAL_URLS
from .runtime import VehicleContext

_LOGGER = logging.getLogger(__name__)

#: Cabeceras del servidor del manual que se pasan tal cual al navegador
#: (las de rango permiten al visor pedir el PDF por trozos).
_PASS_HEADERS: Final = (
    hdrs.CONTENT_LENGTH,
    hdrs.CONTENT_RANGE,
    hdrs.ACCEPT_RANGES,
    hdrs.LAST_MODIFIED,
    hdrs.ETAG,
)
_CHUNK_BYTES: Final = 64 * 1024
#: Sin límite total (son decenas de MB), pero sí si el servidor se queda mudo.
_TIMEOUT: Final = ClientTimeout(total=None, connect=20, sock_read=60)


def is_valid_url(url: str) -> bool:
    """¿Es una dirección web (http o https)?"""
    return url.startswith(("http://", "https://")) and len(url) > 10 and " " not in url


def manual_url(options: Mapping[str, Any], vehicle: VehicleContext) -> str | None:
    """Enlace del manual de un coche (``None`` = no tiene)."""
    custom = str(options.get(OPT_MANUAL_URLS, {}).get(vehicle.model.id) or "").strip()
    if custom and is_valid_url(custom):
        return custom
    return vehicle.model.manual_url or None


def _vehicle_and_url(hass: HomeAssistant, device_id: str) -> tuple[VehicleContext, str | None]:
    """Coche de un dispositivo y su enlace del manual.

    Raises:
        web.HTTPNotFound: el dispositivo no es un coche de DEC Deepal.
    """
    device = dr.async_get(hass).async_get(device_id)
    if device is not None:
        vehicle_ids = [ident for domain, ident in device.identifiers if domain == DOMAIN]
        for entry_id in device.config_entries:
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
                continue
            for vehicle_id in vehicle_ids:
                if vehicle := entry.runtime_data.vehicles.get(vehicle_id):
                    return vehicle, manual_url(entry.options, vehicle)
    raise web.HTTPNotFound


class ManualInfoView(HomeAssistantView):
    """``GET /api/dec_deepal/manual_info/<device_id>`` → ¿tiene manual?"""

    url = MANUAL_INFO_API
    name = "api:dec_deepal:manual_info"

    async def get(self, request: web.Request, device_id: str) -> web.Response:
        """Dice a la tarjeta si debe enseñar la opción "Manual"."""
        _vehicle, url = _vehicle_and_url(request.app[KEY_HASS], device_id)
        return self.json({"available": url is not None})


class ManualView(HomeAssistantView):
    """``GET /api/dec_deepal/manual/<device_id>`` → el PDF, leído del enlace."""

    url = MANUAL_API
    name = "api:dec_deepal:manual"

    async def get(self, request: web.Request, device_id: str) -> web.StreamResponse:
        """Lee el manual de su enlace y lo va pasando al navegador."""
        hass = request.app[KEY_HASS]
        vehicle, url = _vehicle_and_url(hass, device_id)
        if url is None:
            raise web.HTTPNotFound

        headers = {}
        if range_header := request.headers.get(hdrs.RANGE):
            headers[hdrs.RANGE] = range_header
        try:
            upstream = await async_get_clientsession(hass).get(
                url, headers=headers, timeout=_TIMEOUT
            )
        except (ClientError, TimeoutError) as err:
            _LOGGER.warning("No se pudo abrir el manual (%s): %s", url, err)
            raise web.HTTPBadGateway from err

        try:
            if upstream.status not in (200, 206):
                _LOGGER.warning("El enlace del manual respondió %s (%s)", upstream.status, url)
                raise web.HTTPBadGateway
            response = web.StreamResponse(status=upstream.status)
            for header in _PASS_HEADERS:
                if header in upstream.headers:
                    response.headers[header] = upstream.headers[header]
            response.content_type = "application/pdf"
            # "inline": que el navegador lo enseñe en vez de descargarlo.
            response.headers[hdrs.CONTENT_DISPOSITION] = 'inline; filename="manual.pdf"'
            response.headers[hdrs.CACHE_CONTROL] = "private, max-age=3600"
            await response.prepare(request)
            try:
                async for chunk in upstream.content.iter_chunked(_CHUNK_BYTES):
                    await response.write(chunk)
                await response.write_eof()
            except (ClientError, TimeoutError, ConnectionError) as err:
                # El usuario cerró la ventana, o se cortó la lectura: no es un error.
                _LOGGER.debug("Manual de %s interrumpido: %s", vehicle.info.display_name, err)
            return response
        finally:
            upstream.release()


def async_register_manual(hass: HomeAssistant) -> None:
    """Registra las dos vistas (una vez por arranque)."""
    hass.http.register_view(ManualInfoView())
    hass.http.register_view(ManualView())
