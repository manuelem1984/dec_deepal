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
``/dec_deepal/frontend/dec-icons-loader.js``  Cargador temprano (recurso
                                       de los paneles, ver abajo).
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

Cargador temprano (2.1.3; desde la 2.6.0b9, en la ruta propia)
--------------------------------------------------------------
Home Assistant decide qué scripts lleva la página al servirla, y una
integración de HACS arranca unos segundos después de que la web ya
responda. Tras un reinicio, la app recarga en ese hueco: la página sale sin
``dec-icons.js`` y los iconos ``dec:`` quedan en blanco hasta recargar.

Por eso ``dec-icons-loader.js`` se registra como **recurso de los paneles**
(una sola vez; su contenido no cambia entre versiones): reintenta cargar
``dec-icons.js`` hasta que la integración lo publica, y este repinta los
iconos que ya estaban dibujados.

El cargador se sirve desde la ruta estática de la integración
(``/dec_deepal/frontend/``), nunca desde la carpeta ``www`` del usuario: esa
carpeta es suya y todo lo que hay en ella se sirve sin autenticación (lo
pidió la revisión de HACS). Hasta la 2.6.0b8 se copiaba a
``<config>/www/dec_deepal/`` y el recurso apuntaba a ``/local/``: al
arrancar se borran esa copia y ese recurso.

Límites: los recursos solo se cargan al abrir un panel (no en Ajustes) y no
se pueden registrar si están en modo YAML. Nada de esto puede impedir que
la integración arranque.

Por qué un paquete único (2.1.2): tras reiniciar Home Assistant, la app
vuelve a cargar la página antes de que esta integración termine de
arrancar. Con una petición por icono, las que caían en ese hueco fallaban
y el script recordaba el fallo: los iconos no salían hasta recargar. Ahora
el script pide un solo paquete y lo reintenta hasta que la integración
está lista (ver ``icons/dec-icons.js``).
"""

from __future__ import annotations

import logging
from pathlib import Path

from aiohttp import web
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import (
    CARD_JS_DIR,
    CARD_JS_FILE,
    DATA,
    ICONS_BUNDLE_API,
    ICONS_JS_FILE,
    ICONS_JS_URL,
    ICONS_LIST_API,
    ICONS_LOADER_FILE,
    ICONS_LOADER_URL,
    ICONS_SVG_URL,
    INTEGRATION_DIR,
    LEGACY_LOADER_URL,
    LEGACY_LOADER_WWW_DIR,
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
    domain_data = hass.data.setdefault(DATA, {})
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
                StaticPathConfig(
                    ICONS_LOADER_URL,
                    str(INTEGRATION_DIR / "icons" / ICONS_LOADER_FILE),
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


def _remove_legacy_copy(www_dir: Path) -> bool:
    """Borra la copia antigua de ``www/dec_deepal/`` (hasta la 2.6.0b8). Bloqueante.

    Solo se borra nuestro archivo; la carpeta ``dec_deepal``, solo si queda
    vacía. Lo demás de ``www`` es del usuario y no se toca.

    Returns:
        ``True`` si había copia y se ha borrado.
    """
    folder = www_dir / LEGACY_LOADER_WWW_DIR
    target = folder / ICONS_LOADER_FILE
    if not target.is_file():
        return False
    target.unlink()
    if folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()
    return True


def _resource_collection(hass: HomeAssistant):  # noqa: ANN202 - tipo interno de HA
    """Colección de recursos de los paneles, o ``None`` si no se puede escribir."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA
    except ImportError:
        return None
    data = hass.data.get(LOVELACE_DATA)
    resources = getattr(data, "resources", None)
    # En modo YAML la colección no tiene ``async_create_item``.
    if resources is None or not hasattr(resources, "async_create_item"):
        return None
    return resources


async def _loader_resources(resources, url: str) -> list[dict]:  # noqa: ANN001
    """Recursos ya registrados que apuntan a ``url`` (sin mirar el ``?v=``)."""
    await resources.async_get_info()  # asegura que están leídos del disco
    return [
        item
        for item in resources.async_items()
        if str(item.get("url", "")).split("?")[0] == url
    ]


async def _remove_legacy(hass: HomeAssistant, resources) -> bool:  # noqa: ANN001
    """Quita el recurso ``/local/`` y la copia de ``www`` de antes de la 2.6.0b9."""
    removed = False
    if resources is not None:
        for item in await _loader_resources(resources, LEGACY_LOADER_URL):
            await resources.async_delete_item(item["id"])
            removed = True
    if await hass.async_add_executor_job(_remove_legacy_copy, Path(hass.config.path("www"))):
        removed = True
    return removed


async def async_install_early_loader(hass: HomeAssistant) -> str:
    """Registra el cargador (ruta propia) como recurso y quita el antiguo. Nunca falla.

    Returns:
        Texto corto con el resultado, para los diagnósticos.
    """
    try:
        resources = _resource_collection(hass)
        legacy = await _remove_legacy(hass, resources)
        if resources is None:
            status = "recursos en modo YAML o no disponibles: no se registra"
        elif not await _loader_resources(resources, ICONS_LOADER_URL):
            await resources.async_create_item({"res_type": "module", "url": ICONS_LOADER_URL})
            status = "recurso registrado"
        else:
            status = "recurso ya registrado"
        if legacy:
            status += "; quitado el cargador antiguo de www"
    except Exception as err:  # noqa: BLE001 - los iconos nunca deben impedir arrancar
        _LOGGER.warning("No se pudo preparar el cargador temprano de iconos: %s", err)
        return f"error: {err}"
    _LOGGER.debug("Cargador temprano de iconos: %s", status)
    return status


async def async_remove_early_loader(hass: HomeAssistant) -> None:
    """Quita el recurso (y, si queda, el antiguo de ``www``) al desinstalar. Nunca falla."""
    try:
        resources = _resource_collection(hass)
        if resources is not None:
            for item in await _loader_resources(resources, ICONS_LOADER_URL):
                await resources.async_delete_item(item["id"])
        await _remove_legacy(hass, resources)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("No se pudo quitar el cargador temprano de iconos: %s", err)
