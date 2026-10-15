"""Pestaña "Datos": copia de seguridad de lo de cada coche y borrado."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

import voluptuous as vol
from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant

from .. import vehicle_data as vd
from ..alert_rules import backup_text
from ..const import NAME, OPT_APPEARANCE
from ..vehicle_store import async_export_url, async_get_store
from .comun import command, loaded_entries

#: Más coches que esto no es una copia nuestra.
_MAX_BACKUP_CARS: Final = 50


def _flush(hass: HomeAssistant) -> None:
    """Lo pendiente de escribir, al almacén: la copia sale al día."""
    for entry in loaded_entries(hass):
        entry.runtime_data.alerts.async_flush()


def _refresh(hass: HomeAssistant, already_reloading: set[str] | None = None) -> None:
    """Tras cambiar el almacén: releerlo y recargar las cuentas (cambian entidades)."""
    for entry in loaded_entries(hass):
        entry.runtime_data.alerts.async_reload_data()
        if entry.entry_id not in (already_reloading or ()):
            hass.config_entries.async_schedule_reload(entry.entry_id)


def _apply_appearance(hass: HomeAssistant, cars: Mapping[str, Mapping[str, Any]]) -> set[str]:
    """Pone en su cuenta la apariencia que trae una copia.

    Returns:
        Cuentas cuyas opciones han cambiado (se recargan solas).
    """
    changed: set[str] = set()
    for entry in loaded_entries(hass):
        models = entry.runtime_data.registries.vehicles.models
        appearance = dict(entry.options.get(OPT_APPEARANCE, {}))
        before = dict(appearance)
        for vehicle_id, vehicle in entry.runtime_data.vehicles.items():
            saved = cars.get(vd.car_key(vehicle.info.vin, vehicle_id), {}).get(vd.APPEARANCE)
            if (clean := vd.clean_appearance(saved, models)) is not None:
                appearance[vehicle_id] = clean
        if appearance != before:
            hass.config_entries.async_update_entry(
                entry, options={**entry.options, OPT_APPEARANCE: appearance}
            )
            changed.add(entry.entry_id)
    return changed


@command({vol.Required("type"): "dec_deepal/panel/export_url"})
async def ws_export_url(hass: HomeAssistant, msg: dict[str, Any], user: User) -> dict[str, str]:
    """Enlace firmado para descargar la copia (caduca a los pocos minutos)."""
    _flush(hass)
    return {"url": async_export_url(hass), "absolute": async_export_url(hass, absolute=True)}


@command({vol.Required("type"): "dec_deepal/panel/send_backup", vol.Required("target"): str})
async def ws_send_backup(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Manda a un móvil una notificación con el enlace de la copia."""
    if not hass.services.has_service("notify", msg["target"]):
        raise KeyError(msg["target"])
    _flush(hass)
    url = async_export_url(hass, absolute=True)
    await hass.services.async_call(
        "notify",
        msg["target"],
        {
            "title": NAME,
            "message": backup_text("notification", hass.config.language),
            # "url" lo abre el iPhone; "clickAction", Android.
            "data": {"url": url, "clickAction": url},
        },
        blocking=False,
    )


@command({vol.Required("type"): "dec_deepal/panel/import_backup", vol.Required("backup"): dict})
async def ws_import_backup(
    hass: HomeAssistant, msg: dict[str, Any], user: User
) -> dict[str, list[str]]:
    """Carga una copia: deja los coches que trae como estaban en ella."""
    cars = vd.parse_backup(msg["backup"])
    if len(cars) > _MAX_BACKUP_CARS:
        raise vd.BackupError(vd.ERROR_INVALID)
    await async_get_store(hass).async_import(cars)
    _refresh(hass, _apply_appearance(hass, cars))
    return {"cars": [vd.label(key, car) for key, car in cars.items()]}


@command({vol.Required("type"): "dec_deepal/panel/delete_data", vol.Required("keys"): [str]})
async def ws_delete_data(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Borra los datos guardados de unos coches."""
    await async_get_store(hass).async_delete(msg["keys"])
    _refresh(hass)


COMMANDS: Final = (ws_export_url, ws_send_backup, ws_import_backup, ws_delete_data)
