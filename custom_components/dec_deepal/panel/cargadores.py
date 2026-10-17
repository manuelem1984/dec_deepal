"""Cargadores: su configuración (panel → Ajustes) y las órdenes de la tarjeta.

Del panel (solo administradores):

- ``dec_deepal/panel/set_chargers``: activar o desactivar y quién controla.
- ``dec_deepal/panel/save_charger`` / ``delete_charger``.

De la tarjeta del cargador (cualquier usuario; las que cambian algo miran
:meth:`ChargerManager.can_control`):

- ``dec_deepal/chargers/subscribe``: estado de todos los cargadores, y otra
  vez cada vez que cambia algo.
- ``dec_deepal/chargers/state``: lo mismo, una vez (el editor de la tarjeta).
- ``dec_deepal/chargers/confirm``: elegir el coche (desbloquea si toca).
- ``dec_deepal/chargers/lock``: bloquear o desbloquear a mano.
"""

from __future__ import annotations

from typing import Any, Final

import voluptuous as vol
from homeassistant.auth.models import User
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from ..chargers import CONTROLS, ChargerError, async_get_manager
from .comun import command


@command(
    {
        vol.Required("type"): "dec_deepal/panel/set_chargers",
        vol.Required("enabled"): bool,
        vol.Required("control"): vol.In(CONTROLS),
    }
)
async def ws_set_chargers(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Activa o desactiva los cargadores y dice quién puede controlarlos."""
    await async_get_manager(hass).async_set_settings(msg["enabled"], msg["control"])


@command({vol.Required("type"): "dec_deepal/panel/save_charger", vol.Required("charger"): dict})
async def ws_save_charger(hass: HomeAssistant, msg: dict[str, Any], user: User) -> dict[str, Any]:
    """Añade o cambia un cargador."""
    return await async_get_manager(hass).async_save_charger(msg["charger"])


@command({vol.Required("type"): "dec_deepal/panel/delete_charger", vol.Required("charger_id"): str})
async def ws_delete_charger(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Quita un cargador (y lo apuntado de él)."""
    await async_get_manager(hass).async_delete_charger(msg["charger_id"])


@websocket_api.websocket_command({vol.Required("type"): "dec_deepal/chargers/subscribe"})
@websocket_api.async_response
async def ws_subscribe(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Estado de los cargadores, ahora y cada vez que cambie."""
    manager = async_get_manager(hass)
    await manager.async_load()
    user = connection.user

    @callback
    def _send() -> None:
        connection.send_message(websocket_api.event_message(msg["id"], manager.statuses(user)))

    connection.subscriptions[msg["id"]] = manager.async_add_listener(_send)
    connection.send_result(msg["id"])
    _send()


@command({vol.Required("type"): "dec_deepal/chargers/state"}, admin=False)
async def ws_charger_state(hass: HomeAssistant, msg: dict[str, Any], user: User) -> dict[str, Any]:
    """Estado de los cargadores (una vez)."""
    manager = async_get_manager(hass)
    await manager.async_load()
    return manager.statuses(user)


@command(
    {
        vol.Required("type"): "dec_deepal/chargers/confirm",
        vol.Required("charger_id"): str,
        vol.Required("vehicle_id"): vol.Any(str, None),
    },
    admin=False,
)
async def ws_confirm(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Elige el coche que carga (y desbloquea si el cargador lo pide)."""
    await async_get_manager(hass).async_confirm(msg["charger_id"], msg["vehicle_id"], user)


@command(
    {
        vol.Required("type"): "dec_deepal/chargers/lock",
        vol.Required("charger_id"): str,
        vol.Required("locked"): bool,
    },
    admin=False,
)
async def ws_lock(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Bloquea o desbloquea el cargador a mano."""
    await async_get_manager(hass).async_set_lock(msg["charger_id"], msg["locked"], user)


COMMANDS: Final = (
    ws_set_chargers,
    ws_save_charger,
    ws_delete_charger,
    ws_subscribe,
    ws_charger_state,
    ws_confirm,
    ws_lock,
)

__all__ = ["COMMANDS", "ChargerError"]
