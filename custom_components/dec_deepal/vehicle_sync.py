"""Coches de la cuenta: nuevos, retirados y datos al día.

Al arrancar y cada ``SYNC_INTERVAL`` se pide al servidor la lista de coches de
la cuenta y se compara con los que tiene la integración:

- **Datos al día:** de los coches que ya están (matrícula, imagen, apodo...),
  sin recargar nada.
- **Coche nuevo** (por ejemplo, otro compartido con la cuenta): aviso en
  Reparaciones para añadirlo. Al añadirlo, sale el de siempre, "Configura tu
  vehículo" (está pendiente de elegir modelo). Si no se quiere, se ignora.
- **Coche que ya no está** en la cuenta: aviso para quitarlo de la
  integración. Sus fichas (mantenimiento, ITV, seguro) se conservan: son del
  coche, por bastidor, y vuelven si se añade otra vez.

Los asistentes de los avisos están en ``repairs.py``. Nunca falla: sin red, se
sigue con lo guardado.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Final

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir

from .api.client import DeepalClient
from .appearance import issue_id as setup_issue_id
from .api.errors import DeepalError
from .api.models import VehicleInfo
from .const import CONF_VEHICLES, DOMAIN

_LOGGER = logging.getLogger(__name__)

#: Cada cuánto se mira la lista de coches de la cuenta.
SYNC_INTERVAL: Final = timedelta(minutes=30)

#: Tipos de aviso (van en los datos del aviso para elegir su asistente).
KIND_ADDED: Final = "vehicle_added"
KIND_REMOVED: Final = "vehicle_removed"


def added_issue_id(vehicle_id: str) -> str:
    """Id del aviso "Coche nuevo en tu cuenta"."""
    return f"{KIND_ADDED}_{vehicle_id}"


def removed_issue_id(vehicle_id: str) -> str:
    """Id del aviso "Este coche ya no está en tu cuenta"."""
    return f"{KIND_REMOVED}_{vehicle_id}"


def _in_other_entries(hass: HomeAssistant, entry_id: str) -> set[str]:
    """Coches que ya tiene otra cuenta de la integración (no se ofrecen dos veces)."""
    return {
        str(item.get("vehicle_id"))
        for other in hass.config_entries.async_entries(DOMAIN)
        if other.entry_id != entry_id
        for item in other.data.get(CONF_VEHICLES, [])
    }


async def async_sync_vehicles(hass: HomeAssistant, entry: Any, client: DeepalClient) -> None:
    """Compara los coches de la cuenta con los de la integración (ver arriba)."""
    try:
        account = await client.get_vehicles()
    except DeepalError as err:
        _LOGGER.debug("No se pudo leer la lista de vehículos: %s", err)
        return
    fresh: dict[str, VehicleInfo] = {vehicle.vehicle_id: vehicle for vehicle in account}

    stored: list[dict[str, Any]] = entry.data[CONF_VEHICLES]
    updated = [
        {**item, **fresh[item["vehicle_id"]].to_dict()} if item.get("vehicle_id") in fresh else item
        for item in stored
    ]
    if updated != stored:
        hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_VEHICLES: updated})
    update_issues(hass, entry, fresh)


def update_issues(hass: HomeAssistant, entry: Any, fresh: dict[str, VehicleInfo]) -> None:
    """Crea o borra los avisos de coches nuevos y retirados de una cuenta."""
    stored = {str(item.get("vehicle_id")): item for item in entry.data.get(CONF_VEHICLES, [])}
    elsewhere = _in_other_entries(hass, entry.entry_id)

    for vehicle_id, vehicle in fresh.items():
        issue = added_issue_id(vehicle_id)
        if vehicle_id in stored or vehicle_id in elsewhere:
            ir.async_delete_issue(hass, DOMAIN, issue)
            continue
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue,
            is_fixable=True,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=KIND_ADDED,
            translation_placeholders={"vehicle": vehicle.display_name},
            data={
                "kind": KIND_ADDED,
                "entry_id": entry.entry_id,
                "vehicle_id": vehicle_id,
                "vehicle": vehicle.to_dict(),
            },
        )

    # Avisos que ya no tocan: un coche nuevo que dejó de estar en la cuenta, o
    # uno retirado que ya no está en la integración.
    for (domain, issue_id), issue in list(ir.async_get(hass).issues.items()):
        data = issue.data or {}
        if domain != DOMAIN or data.get("entry_id") != entry.entry_id:
            continue
        vehicle_id = str(data.get("vehicle_id"))
        if (data.get("kind") == KIND_ADDED and vehicle_id not in fresh) or (
            data.get("kind") == KIND_REMOVED and vehicle_id not in stored
        ):
            ir.async_delete_issue(hass, DOMAIN, issue_id)

    for vehicle_id, item in stored.items():
        issue = removed_issue_id(vehicle_id)
        if vehicle_id in fresh:
            ir.async_delete_issue(hass, DOMAIN, issue)
            continue
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue,
            is_fixable=True,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=KIND_REMOVED,
            translation_placeholders={"vehicle": VehicleInfo.from_dict(item).display_name},
            data={"kind": KIND_REMOVED, "entry_id": entry.entry_id, "vehicle_id": vehicle_id},
        )


def delete_issues(hass: HomeAssistant, entry: Any) -> None:
    """Borra los avisos de coches nuevos y retirados de una cuenta (al quitarla)."""
    prefixes = (f"{KIND_ADDED}_", f"{KIND_REMOVED}_")
    for (domain, issue_id), issue in list(ir.async_get(hass).issues.items()):
        if domain == DOMAIN and issue_id.startswith(prefixes) and (issue.data or {}).get("entry_id") == entry.entry_id:
            ir.async_delete_issue(hass, DOMAIN, issue_id)


def add_vehicle(hass: HomeAssistant, entry: Any, vehicle: dict[str, Any]) -> None:
    """Añade un coche de la cuenta a la integración (y la recarga)."""
    stored = list(entry.data.get(CONF_VEHICLES, []))
    if all(item.get("vehicle_id") != vehicle.get("vehicle_id") for item in stored):
        stored.append(dict(vehicle))
        hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_VEHICLES: stored})
    hass.config_entries.async_schedule_reload(entry.entry_id)


def remove_vehicle(hass: HomeAssistant, entry: Any, vehicle_id: str) -> None:
    """Quita un coche de la integración: su dispositivo y entidades (y la recarga).

    Sus fichas se quedan en el almacén (por bastidor), como al quitar la cuenta.
    """
    stored = [item for item in entry.data.get(CONF_VEHICLES, []) if item.get("vehicle_id") != vehicle_id]
    hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_VEHICLES: stored})
    ir.async_delete_issue(hass, DOMAIN, setup_issue_id(vehicle_id))
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        if (DOMAIN, vehicle_id) in device.identifiers:
            registry.async_remove_device(device.id)
    hass.config_entries.async_schedule_reload(entry.entry_id)
