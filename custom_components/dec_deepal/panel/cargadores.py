"""Cargadores: su configuración (panel → Ajustes) y las órdenes de la tarjeta.

Del panel (solo administradores):

- ``dec_deepal/panel/set_chargers``: activar o desactivar y quién controla.
- ``dec_deepal/panel/save_charger`` / ``delete_charger``.
- ``dec_deepal/panel/set_limit``: límite de carga y recordatorio del 100 %.

De la tarjeta del cargador (cualquier usuario; las que cambian algo miran
:meth:`ChargerManager.can_control`):

- ``dec_deepal/chargers/subscribe``: estado de todos los cargadores, y otra
  vez cada vez que cambia algo.
- ``dec_deepal/chargers/state``: lo mismo, una vez (el editor de la tarjeta).
- ``dec_deepal/chargers/confirm``: elegir el coche (desbloquea si toca).
- ``dec_deepal/chargers/lock``: bloquear o desbloquear a mano.
- ``dec_deepal/chargers/car_limit``: límite de un coche y «Solo esta: 100 %»
  (tarjeta del coche y panel; mira :meth:`ChargerManager.can_control_vehicle`).
"""

from __future__ import annotations

from typing import Any, Final

import voluptuous as vol
from homeassistant.auth.models import User
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from ..chargers import CONTROLS, FULL_EVERY_CHOICES, LIMIT_CHOICES, ChargerError, async_get_manager
from .comun import command


@command(
    {
        vol.Required("type"): "dec_deepal/panel/set_chargers",
        vol.Required("enabled"): bool,
        vol.Required("control"): vol.In(CONTROLS),
        vol.Optional("show_estimate"): bool,
    }
)
async def ws_set_chargers(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Activa o desactiva los cargadores, quién los controla y el % estimado en la tarjeta del coche."""
    await async_get_manager(hass).async_set_settings(msg["enabled"], msg["control"], msg.get("show_estimate"))


@command({vol.Required("type"): "dec_deepal/panel/save_charger", vol.Required("charger"): dict})
async def ws_save_charger(hass: HomeAssistant, msg: dict[str, Any], user: User) -> dict[str, Any]:
    """Añade o cambia un cargador."""
    return await async_get_manager(hass).async_save_charger(msg["charger"])


@command({vol.Required("type"): "dec_deepal/panel/delete_charger", vol.Required("charger_id"): str})
async def ws_delete_charger(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Quita un cargador (y lo apuntado de él)."""
    await async_get_manager(hass).async_delete_charger(msg["charger_id"])


@command(
    {
        vol.Required("type"): "dec_deepal/panel/set_limit",
        vol.Optional("enabled"): bool,
        vol.Optional("notify"): bool,
        vol.Optional("remind"): bool,
        vol.Optional("every"): vol.In(FULL_EVERY_CHOICES),
        vol.Optional("auto"): bool,
    }
)
async def ws_set_limit(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Opciones del límite de carga y del recordatorio de cargar al 100 %."""
    await async_get_manager(hass).async_set_limit_settings({key: value for key, value in msg.items() if key not in ("type", "id")})


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


@command(
    {
        vol.Required("type"): "dec_deepal/chargers/car_limit",
        vol.Exclusive("vehicle_id", "car"): str,
        vol.Exclusive("device_id", "car"): str,
        vol.Optional("limit"): vol.In(LIMIT_CHOICES),
        vol.Optional("once_full"): bool,
    },
    admin=False,
)
async def ws_car_limit(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Límite de carga de un coche (70-100 %) y «Solo esta: 100 %»."""
    manager = async_get_manager(hass)
    await manager.async_load()
    vehicle_id = msg.get("vehicle_id") or manager.vehicle_for_device(msg.get("device_id") or "")
    if not vehicle_id:
        raise ChargerError("charger_vehicle")
    await manager.async_set_car_limit(vehicle_id, user, limit=msg.get("limit"), once_full=msg.get("once_full"))


COMMANDS: Final = (
    ws_set_chargers,
    ws_save_charger,
    ws_delete_charger,
    ws_set_limit,
    ws_subscribe,
    ws_charger_state,
    ws_confirm,
    ws_lock,
    ws_car_limit,
)

__all__ = ["COMMANDS", "ChargerError"]
