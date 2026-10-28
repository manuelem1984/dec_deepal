"""Pestaña "Ajustes": control con PIN y lectura de datos de cada cuenta."""

from __future__ import annotations

from typing import Any, Final

import voluptuous as vol
from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant

from ..api.errors import DeepalConnectionError, DeepalError, DeepalPinError, DeepalRateLimitError
from ..const import (
    ARM_SECONDS_CHOICES,
    DEFAULT_ARM_NOTIFY,
    DEFAULT_ARM_SECONDS,
    DEFAULT_CHARGE_BALANCE,
    DEFAULT_PIN_MODE,
    MAX_SCAN_MINUTES,
    MIN_SCAN_MINUTES,
    OPT_ARM_NOTIFY,
    OPT_ARM_SECONDS,
    OPT_CHARGE_BALANCE,
    OPT_DEBUG,
    OPT_MANUAL_URLS,
    OPT_PIN,
    OPT_PIN_ENABLED,
    OPT_PIN_MODE,
    OPT_SCAN_MINUTES,
    OPT_WAKE,
    PIN_MODE_ARMED,
    PIN_MODE_DIRECT,
)
from ..manual import is_valid_url
from .comun import PanelError, command, loaded_entries
from .estado import account_settings


async def _checked_pin(entry: Any, pin: str) -> str:
    """El PIN que se va a guardar, comprobado con Deepal si es nuevo.

    Vacío = el que ya había (no se gastan intentos al guardar otra cosa).
    """
    stored = entry.options.get(OPT_PIN)
    pin = pin.strip() or str(stored or "")
    if not pin:
        raise PanelError("pin_required")
    if pin == stored:
        return pin
    try:
        await entry.runtime_data.commands.check_pin(pin)
    except DeepalRateLimitError as err:
        raise PanelError("pin_rate_limited") from err
    except DeepalConnectionError as err:
        raise PanelError("cannot_connect") from err
    except (DeepalPinError, DeepalError) as err:
        raise PanelError("pin_invalid") from err
    return pin


@command(
    {
        vol.Required("type"): "dec_deepal/panel/set_settings",
        vol.Required("entry_id"): str,
        vol.Required("pin_enabled"): bool,
        vol.Optional("pin", default=""): str,
        vol.Optional("pin_mode", default=DEFAULT_PIN_MODE): vol.In((PIN_MODE_DIRECT, PIN_MODE_ARMED)),
        vol.Optional("arm_seconds", default=DEFAULT_ARM_SECONDS): vol.In(ARM_SECONDS_CHOICES),
        vol.Optional("arm_notify", default=DEFAULT_ARM_NOTIFY): bool,
        vol.Required("scan_minutes"): vol.All(
            int, vol.Range(min=MIN_SCAN_MINUTES, max=MAX_SCAN_MINUTES)
        ),
        vol.Required("wake"): bool,
        vol.Optional("charge_balance", default=DEFAULT_CHARGE_BALANCE): bool,
        vol.Required("debug"): bool,
        vol.Optional("manual_url"): str,
    }
)
async def ws_set_settings(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Ajustes de una cuenta: control con PIN y lectura de datos."""
    entry = next((item for item in loaded_entries(hass) if item.entry_id == msg["entry_id"]), None)
    if entry is None:
        raise KeyError(msg["entry_id"])
    changes: dict[str, Any] = {
        OPT_SCAN_MINUTES: msg["scan_minutes"],
        OPT_WAKE: msg["wake"],
        OPT_CHARGE_BALANCE: msg["charge_balance"],
        OPT_DEBUG: msg["debug"],
    }
    if msg["pin_enabled"]:
        changes |= {
            OPT_PIN_ENABLED: True,
            OPT_PIN: await _checked_pin(entry, msg["pin"]),
            OPT_PIN_MODE: msg["pin_mode"],
            OPT_ARM_SECONDS: msg["arm_seconds"],
            OPT_ARM_NOTIFY: msg["arm_notify"],
        }
    else:
        # Desactivar siempre empieza de cero la próxima vez.
        changes |= {
            OPT_PIN_ENABLED: False,
            OPT_PIN: None,
            OPT_PIN_MODE: DEFAULT_PIN_MODE,
            OPT_ARM_SECONDS: DEFAULT_ARM_SECONDS,
            OPT_ARM_NOTIFY: DEFAULT_ARM_NOTIFY,
        }
    manual = account_settings(entry)["manual"]
    if manual is not None and "manual_url" in msg:
        url = msg["manual_url"].strip()
        if url and not is_valid_url(url):
            raise PanelError("invalid_url")
        model_id = next(
            vehicle.model.id for vehicle in entry.runtime_data.vehicles.values() if vehicle.configured
        )
        urls = dict(entry.options.get(OPT_MANUAL_URLS, {}))
        # El oficial, o vacío, no se guarda (se sigue el catálogo).
        if url and url != manual["official"]:
            urls[model_id] = url
        else:
            urls.pop(model_id, None)
        changes[OPT_MANUAL_URLS] = urls
    hass.config_entries.async_update_entry(entry, options={**entry.options, **changes})


COMMANDS: Final = (ws_set_settings,)
