"""Pestaña "Avisos": a quién avisa cada coche de cada cosa, y con qué plazos."""

from __future__ import annotations

from typing import Any, Final

import voluptuous as vol
from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from ..alert_rules import NOTICES, TARGET_PANEL, Route, clean_thresholds, panel_name
from ..const import OPT_ALERT_VEHICLES, OPT_ALERTS
from .comun import VEHICLE, command, find_vehicle

#: Servicios de "notify" que no son un destino (son genéricos de HA).
_NOT_A_TARGET: Final = frozenset({"send_message", "persistent_notification", "notify"})


def notify_targets(hass: HomeAssistant, used: set[str]) -> list[dict[str, str]]:
    """Destinos posibles de un aviso: móviles, otros servicios y la campana.

    Los móviles salen con el nombre que tienen en Ajustes → Aplicación móvil
    (su servicio es ``mobile_app_`` + ese nombre en minúsculas). Los destinos
    ya elegidos se mantienen aunque hoy no existan.
    """
    mobiles: dict[str, str] = {}
    for entry in hass.config_entries.async_entries("mobile_app"):
        registered = entry.data.get("device_name") or entry.title
        if registered:
            mobiles[slugify(f"mobile_app_{registered}")] = entry.title or registered
    available = set(hass.services.async_services().get("notify", {})) - _NOT_A_TARGET
    names = sorted(
        (available | used) - {TARGET_PANEL},
        key=lambda name: (not name.startswith("mobile_app_"), name),
    )
    targets = [
        {
            "id": name,
            "name": mobiles.get(name, f"notify.{name}"),
            "kind": "mobile" if name.startswith("mobile_app_") else "service",
        }
        for name in names
    ]
    targets.append(
        {"id": TARGET_PANEL, "name": panel_name(hass.config.language), "kind": "panel"}
    )
    return targets


@command(
    {
        vol.Required("type"): "dec_deepal/panel/set_alerts",
        **VEHICLE,
        vol.Required("notices"): {str: [str]},
        vol.Optional("thresholds", default=dict): {str: vol.Any(int, float)},
        vol.Optional("all_vehicles", default=False): bool,
    }
)
async def ws_set_alerts(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Guarda a quién avisa un coche de cada cosa, y con qué plazos.

    Se escribe lo de todos los coches de la cuenta (así desaparecen los
    formatos anteriores sin cambiar nada). Cambiar las opciones recarga la
    cuenta, que es lo que aplica los destinos nuevos.
    """
    entry, _vehicle = find_vehicle(hass, msg["vehicle_id"])
    alerts = entry.runtime_data.alerts
    chosen = Route(
        targets={
            notice.id: tuple(dict.fromkeys(msg["notices"].get(notice.id) or ()))
            for notice in NOTICES
        },
        thresholds=clean_thresholds(msg["thresholds"]),
    ).to_dict()
    vehicles = {
        vehicle_id: (
            chosen
            if msg["all_vehicles"] or vehicle_id == msg["vehicle_id"]
            else alerts.route(vehicle_id).to_dict()
        )
        for vehicle_id in entry.runtime_data.vehicles
    }
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, OPT_ALERTS: {OPT_ALERT_VEHICLES: vehicles}}
    )


COMMANDS: Final = (ws_set_alerts,)
