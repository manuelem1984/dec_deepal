"""Registro del paquete de iconos "dec:" en el navegador.

Se hace **una sola vez por arranque** (desde ``async_setup``), aunque haya
varias cuentas configuradas: registrar dos veces la misma ruta estática hace
que Home Assistant lance un error.

Qué se publica:

=====================================  ========================================
URL                                    Contenido
=====================================  ========================================
``/dec_deepal/icons/<nombre>.svg``     Cada archivo de ``icons/svg/``.
``/dec_deepal/frontend/dec-icons.js``  Script que enseña al navegador el
                                       prefijo ``dec:`` (se carga solo).
``/api/dec_deepal/icons``              Lista JSON de iconos disponibles.
``/api/dec_deepal/icons_bundle``       Todos los SVG en un solo JSON
                                       (``{nombre: svg}``); lo usa el script.
=====================================  ========================================

Nada de esto es información privada: son solo dibujos.

Por qué un paquete único (2.1.2): tras reiniciar Home Assistant, la app
vuelve a cargar la página antes de que esta integración termine de
arrancar. Con una petición por icono, las que caían en ese hueco fallaban
y el script recordaba el fallo: los iconos no salían hasta recargar. Ahora
el script pide un solo paquete y lo reintenta hasta que la integración
está lista (ver ``icons/dec-icons.js``).
"""

from __future__ import annotations

import logging

from aiohttp import web
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    ICONS_JS_FILE,
    ICONS_BUNDLE_API,
    ICONS_JS_URL,
    ICONS_LIST_API,
    ICONS_SVG_URL,
    INTEGRATION_DIR,
    VERSION,
)
from .registries.icons import IconRegistry

_LOGGER = logging.getLogger(__name__)

_REGISTERED_KEY = "frontend_registered"


class IconListView(HomeAssistantView):
    """``GET /api/dec_deepal/icons`` → ``["high_beam_on", ...]``."""

    url = ICONS_LIST_API
    name = "api:dec_deepal:icons"
    requires_auth = False

    def __init__(self, icons: IconRegistry) -> None:
        self._icons = icons

    async def get(self, request: web.Request) -> web.Response:
        """Devuelve los nombres de los SVG disponibles."""
        return self.json(sorted(self._icons.available))


class IconBundleView(HomeAssistantView):
    """``GET /api/dec_deepal/icons_bundle`` → ``{"high_beam": "<svg ...>", ...}``."""

    url = ICONS_BUNDLE_API
    name = "api:dec_deepal:icons_bundle"
    requires_auth = False

    def __init__(self, hass: HomeAssistant, icons: IconRegistry) -> None:
        self._hass = hass
        self._icons = icons

    async def get(self, request: web.Request) -> web.Response:
        """Devuelve todos los SVG (se leen del disco en un hilo aparte)."""
        bundle = await self._hass.async_add_executor_job(self._icons.bundle)
        response = self.json(bundle)
        response.headers["Cache-Control"] = "no-store"
        return response


async def async_register_frontend(hass: HomeAssistant, icons: IconRegistry) -> None:
    """Publica los SVG, el script y la lista de iconos (una sola vez)."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_REGISTERED_KEY):
        return
    try:
        await hass.http.async_register_static_paths(
            [
                # cache_headers=False: así un SVG nuevo se ve tras reiniciar
                # sin tener que vaciar la caché del navegador.
                StaticPathConfig(ICONS_SVG_URL, str(icons.svg_dir), False),
                StaticPathConfig(
                    f"{ICONS_JS_URL}/{ICONS_JS_FILE}",
                    str(INTEGRATION_DIR / "icons" / ICONS_JS_FILE),
                    False,
                ),
            ]
        )
    except RuntimeError as err:
        # Ruta ya registrada (no debería pasar, pero no es grave).
        _LOGGER.debug("Rutas de iconos ya registradas: %s", err)
    hass.http.register_view(IconListView(icons))
    hass.http.register_view(IconBundleView(hass, icons))
    # ?v=<versión> evita que el navegador use un script viejo tras actualizar.
    add_extra_js_url(hass, f"{ICONS_JS_URL}/{ICONS_JS_FILE}?v={VERSION}")
    domain_data[_REGISTERED_KEY] = True
