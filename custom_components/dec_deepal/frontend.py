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
``/dec_deepal/frontend/dec-deepal-card.js``  Tarjeta para los paneles
                                       (``custom:dec-deepal-card``, 2.2.0).
``/api/dec_deepal/icons``              Lista JSON de iconos disponibles.
``/api/dec_deepal/icons_bundle``       Todos los SVG en un solo JSON
                                       (``{nombre: svg}``); lo usa el script.
=====================================  ========================================

Nada de esto es información privada: son solo dibujos.

La tarjeta (2.2.0)
------------------
``frontend_card/dec-deepal-card.js`` es la tarjeta ``custom:dec-deepal-card``.
No se registra aparte: la carga ``dec-icons.js`` al terminar, así llega por
los mismos dos caminos que los iconos (la página de Home Assistant y el
cargador temprano). Si llega tarde tras un reinicio, Home Assistant vuelve a
pintar la tarjeta en cuanto queda definida.

Cargador temprano (2.1.3)
-------------------------
Home Assistant decide qué scripts lleva la página al servirla, y una
integración de HACS arranca unos segundos después de que la web ya
responda. Tras un reinicio, la app recarga en ese hueco: la página sale sin
``dec-icons.js`` y los iconos ``dec:`` quedan en blanco hasta recargar.

Lo único que está disponible desde el primer instante y que una integración
puede preparar sola es la carpeta ``www`` (``/local/``) y los **recursos de
los paneles** (guardados en disco). Por eso, al arrancar:

1. se copia ``dec-icons-loader.js`` a ``<config>/www/dec_deepal/``;
2. se registra ``/local/dec_deepal/dec-icons-loader.js`` como recurso
   (una sola vez; su contenido no cambia entre versiones).

El cargador reintenta cargar ``dec-icons.js`` hasta que la integración lo
publica, y este repinta los iconos que ya estaban dibujados. Límites: los
recursos solo se cargan al abrir un panel (no en Ajustes), no se pueden
registrar si los recursos están en modo YAML, y ``/local/`` solo existe si
la carpeta ``www`` ya estaba al arrancar (la primera vez, tras otro
reinicio). Nada de esto puede impedir que la integración arranque.

Por qué un paquete único (2.1.2): tras reiniciar Home Assistant, la app
vuelve a cargar la página antes de que esta integración termine de
arrancar. Con una petición por icono, las que caían en ese hueco fallaban
y el script recordaba el fallo: los iconos no salían hasta recargar. Ahora
el script pide un solo paquete y lo reintenta hasta que la integración
está lista (ver ``icons/dec-icons.js``).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from aiohttp import web
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import (
    CARD_JS_DIR,
    CARD_JS_FILE,
    DOMAIN,
    ICONS_JS_FILE,
    ICONS_BUNDLE_API,
    ICONS_JS_URL,
    ICONS_LIST_API,
    ICONS_LOADER_FILE,
    ICONS_LOADER_URL,
    ICONS_LOADER_WWW_DIR,
    ICONS_SVG_URL,
    INTEGRATION_DIR,
    VERSION,
)
from .registries.icons import IconRegistry

_LOGGER = logging.getLogger(__name__)

_REGISTERED_KEY = "frontend_registered"
#: Resultado de preparar el cargador temprano (lo muestran los diagnósticos).
LOADER_STATUS_KEY = "icon_loader_status"


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
                StaticPathConfig(
                    f"{ICONS_JS_URL}/{CARD_JS_FILE}",
                    str(INTEGRATION_DIR / CARD_JS_DIR / CARD_JS_FILE),
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
    domain_data[LOADER_STATUS_KEY] = await async_install_early_loader(hass)


# ---------------------------------------------------------------------------
# Cargador temprano (ver el docstring del módulo)
# ---------------------------------------------------------------------------


def _copy_loader(www_dir: Path) -> bool:
    """Copia el cargador a ``www/dec_deepal/`` si falta o ha cambiado. Bloqueante.

    Returns:
        ``True`` si la carpeta ``www`` ya existía (y por tanto ``/local/`` se
        está sirviendo); ``False`` si se acaba de crear: hará falta otro
        reinicio de Home Assistant para que ``/local/`` exista.
    """
    www_existed = www_dir.is_dir()
    source = INTEGRATION_DIR / "icons" / ICONS_LOADER_FILE
    target = www_dir / ICONS_LOADER_WWW_DIR / ICONS_LOADER_FILE
    data = source.read_bytes()
    if not target.is_file() or target.read_bytes() != data:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return www_existed


def _resource_collection(hass: HomeAssistant):  # noqa: ANN202 - tipo interno de HA
    """Colección de recursos de los paneles, o ``None`` si no se puede escribir."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA  # noqa: PLC0415
    except ImportError:
        return None
    data = hass.data.get(LOVELACE_DATA)
    resources = getattr(data, "resources", None)
    # En modo YAML la colección no tiene ``async_create_item``.
    if resources is None or not hasattr(resources, "async_create_item"):
        return None
    return resources


async def _loader_resources(resources) -> list[dict]:  # noqa: ANN001
    """Recursos ya registrados que apuntan a nuestro cargador."""
    await resources.async_get_info()  # asegura que están leídos del disco
    return [
        item
        for item in resources.async_items()
        if str(item.get("url", "")).split("?")[0] == ICONS_LOADER_URL
    ]


async def async_install_early_loader(hass: HomeAssistant) -> str:
    """Copia el cargador a ``www`` y lo registra como recurso. Nunca falla.

    Returns:
        Texto corto con el resultado, para los diagnósticos.
    """
    try:
        www_existed = await hass.async_add_executor_job(
            _copy_loader, Path(hass.config.path("www"))
        )
        resources = _resource_collection(hass)
        if resources is None:
            return "recursos en modo YAML o no disponibles: no se registra"
        if not await _loader_resources(resources):
            await resources.async_create_item({"res_type": "module", "url": ICONS_LOADER_URL})
            status = "recurso registrado"
        else:
            status = "recurso ya registrado"
        if not www_existed:
            status += "; carpeta www recién creada (activo tras el próximo reinicio)"
    except Exception as err:  # noqa: BLE001 - los iconos nunca deben impedir arrancar
        _LOGGER.warning("No se pudo preparar el cargador temprano de iconos: %s", err)
        return f"error: {err}"
    _LOGGER.debug("Cargador temprano de iconos: %s", status)
    return status


async def async_remove_early_loader(hass: HomeAssistant) -> None:
    """Quita el recurso y la copia de ``www`` (al desinstalar). Nunca falla."""
    try:
        resources = _resource_collection(hass)
        if resources is not None:
            for item in await _loader_resources(resources):
                await resources.async_delete_item(item["id"])
        target = Path(hass.config.path("www")) / ICONS_LOADER_WWW_DIR
        await hass.async_add_executor_job(shutil.rmtree, target, True)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("No se pudo quitar el cargador temprano de iconos: %s", err)
