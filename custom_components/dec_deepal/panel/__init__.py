"""Panel "DEC Deepal" de la barra lateral: registro y órdenes.

El panel es una página propia de Home Assistant (como la de Alarmo) donde se
ve y se configura todo lo de los coches: la ficha de cada uno y su
apariencia, a quién pertenece, quién recibe cada aviso, la copia de los
datos, lo que ha pasado y los ajustes de la cuenta. El botón **Configurar**
de la integración lleva aquí.

- La página es ``frontend_panel/dec-deepal-panel.js`` (se genera uniendo los
  módulos de ``frontend_panel/src/``, igual que la tarjeta).
- Habla con la integración por WebSocket (órdenes ``dec_deepal/panel/...``).
- **Administradores:** todo. **Resto de usuarios:** solo lectura de las
  pestañas Coches y Avisos (ver ``estado.panel_state``).

Un módulo por pestaña, con el mismo nombre que su fichero del panel
(``frontend_panel/src/6x_<nombre>.js``), para encontrar rápido las dos mitades
de cada cosa:

====================  ===================================================
``comun.py``          Permisos, búsqueda de coches y errores de las órdenes
``estado.py``         Lo que pinta el panel (orden ``state``)
``coches.py``         Apariencia, personas y fichas (mantenimiento, ITV, seguro)
``avisos.py``         A quién avisa cada coche de cada cosa
``datos.py``          Copia de seguridad y borrado
``ajustes.py``        PIN y lectura de datos de cada cuenta
``cargadores.py``     Cargadores (Ajustes) y órdenes de su tarjeta
====================  ===================================================

Los errores se mandan con un código; el panel enseña el texto
``error_<código>`` de ``idiomas/<idioma>.json`` (sección ``panel``).

Añadir una orden: escribirla en el módulo de su pestaña con ``@command`` (de
``comun.py``), añadirla a la tupla ``COMMANDS`` de ese módulo y, si tiene
errores propios, sus textos ``error_<código>`` en cada idioma.

Guía: docs/panel.md
"""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from ..const import (
    DATA,
    DOMAIN,
    ICONS_JS_URL,
    INTEGRATION_DIR,
    NAME,
    PANEL_JS_DIR,
    PANEL_JS_FILE,
    PANEL_URL_PATH,
    PHOTOS_URL,
    VERSION,
)
from . import ajustes, avisos, cargadores, coches, datos, estado
from .avisos import notify_targets
from .estado import panel_state

__all__ = ["COMMANDS", "async_register_panel", "async_unregister_panel", "notify_targets", "panel_state"]

_LOGGER = logging.getLogger(__name__)

_REGISTERED_KEY: Final = "panel_registered"
_ELEMENT: Final = "dec-deepal-panel"

#: Todas las órdenes del panel.
COMMANDS: Final = (
    *estado.COMMANDS,
    *coches.COMMANDS,
    *avisos.COMMANDS,
    *datos.COMMANDS,
    *ajustes.COMMANDS,
    *cargadores.COMMANDS,
)


async def async_register_panel(hass: HomeAssistant) -> None:
    """Añade el panel a la barra lateral (una vez; al cargar la primera cuenta)."""
    domain_data = hass.data.setdefault(DATA, {})
    if domain_data.get(_REGISTERED_KEY):
        return
    domain_data[_REGISTERED_KEY] = True
    path = INTEGRATION_DIR / PANEL_JS_DIR / PANEL_JS_FILE
    url = f"{ICONS_JS_URL}/{PANEL_JS_FILE}"
    try:
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(url, str(path), False),
                StaticPathConfig(PHOTOS_URL, str(INTEGRATION_DIR / "vehicles" / "photos"), True),
            ]
        )
    except RuntimeError as err:  # ruta ya registrada (tras quitar y volver a añadir la cuenta)
        _LOGGER.debug("Ruta del panel ya registrada: %s", err)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=_ELEMENT,
        sidebar_title=NAME,
        sidebar_icon="mdi:car-electric",
        # ?v=<versión> evita que el navegador use un panel viejo tras actualizar.
        module_url=f"{url}?v={VERSION}",
        # Lo ven todos los usuarios; quien no es administrador, en solo lectura
        # (cada orden comprueba sus permisos, ver comun.command).
        require_admin=False,
        config={},
        # El botón "Configurar" de la integración abre el panel.
        config_panel_domain=DOMAIN,
    )
    for command in COMMANDS:
        websocket_api.async_register_command(hass, command)


@callback
def async_unregister_panel(hass: HomeAssistant) -> None:
    """Quita el panel de la barra lateral (al borrar la última cuenta)."""
    if hass.data.get(DATA, {}).pop(_REGISTERED_KEY, None):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
