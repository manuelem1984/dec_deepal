"""Piezas comunes de las órdenes del panel: permisos, coches y errores."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any, Final

import voluptuous as vol
from homeassistant.auth.models import User
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .. import vehicle_data as vd
from ..alert_rules import ThresholdError
from ..const import DOMAIN

#: Esquema de las órdenes que actúan sobre un coche.
VEHICLE: Final = {vol.Required("vehicle_id"): str}

#: Una orden: recibe Home Assistant, el mensaje y el usuario que la manda.
Handler = Callable[[HomeAssistant, dict[str, Any], User], Awaitable[Any]]


class PanelError(ValueError):
    """Una orden del panel que no se puede cumplir. ``code`` es la clave del texto."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def command(schema: dict[Any, Any], *, admin: bool = True):  # noqa: ANN201
    """Convierte una función en orden del panel.

    Args:
        schema: esquema del mensaje (con su ``type``).
        admin: ``True`` (lo normal) = solo administradores; ``False`` = la
            puede usar cualquier usuario (solo para órdenes de lectura).

    Los errores conocidos se devuelven con su código (``not_found``, el de
    un :class:`PanelError`...) y el panel enseña su texto traducido.
    """

    def decorator(func: Handler):  # noqa: ANN202
        @websocket_api.websocket_command(schema)
        @websocket_api.async_response
        async def wrapper(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
            if admin and not connection.user.is_admin:
                connection.send_error(msg["id"], "unauthorized", "unauthorized")
                return
            try:
                result = await func(hass, msg, connection.user)
            except KeyError:
                connection.send_error(msg["id"], "not_found", "not_found")
            except ThresholdError as err:
                connection.send_error(msg["id"], err.code, err.notice)
            except (PanelError, vd.BackupError) as err:
                connection.send_error(msg["id"], err.code, err.code)
            except ValueError as err:
                connection.send_error(msg["id"], "invalid", str(err))
            else:
                connection.send_result(msg["id"], result)

        return wrapper

    return decorator


def loaded_entries(hass: HomeAssistant) -> list[Any]:
    """Cuentas cargadas."""
    return [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if getattr(getattr(entry, "runtime_data", None), "alerts", None) is not None
    ]


def find_vehicle(hass: HomeAssistant, vehicle_id: str) -> tuple[Any, Any]:
    """Cuenta y coche de un identificador: ``(entry, vehicle)``."""
    for entry in loaded_entries(hass):
        if vehicle := entry.runtime_data.vehicles.get(vehicle_id):
            return entry, vehicle
    raise KeyError(vehicle_id)


def day(value: str) -> date:
    """Fecha ``AAAA-MM-DD`` del panel."""
    return date.fromisoformat(value)


def reload_if(hass: HomeAssistant, entry: Any, changed: bool) -> None:
    """Activar o desactivar un apartado crea o borra entidades: eso recarga."""
    if changed:
        hass.config_entries.async_schedule_reload(entry.entry_id)
