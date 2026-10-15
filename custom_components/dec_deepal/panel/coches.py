"""Pestaña "Coches": apariencia, personas y fichas (mantenimiento, ITV, seguro)."""

from __future__ import annotations

from typing import Any, Final

import voluptuous as vol
from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant

from .. import appearance as ap
from .. import documents as doc
from .. import maintenance as mt
from .. import vehicle_data as vd
from ..const import OPT_COLOR, OPT_MODEL, OPT_TRIM, OPT_WHEELS
from ..registries.vehicles import GENERIC_MODEL_ID
from .comun import VEHICLE, PanelError, command, day, find_vehicle, reload_if


@command(
    {
        vol.Required("type"): "dec_deepal/panel/set_appearance",
        **VEHICLE,
        vol.Required("model"): str,
        vol.Optional("trim"): vol.Any(str, None),
        vol.Optional("color"): vol.Any(str, None),
        vol.Optional("wheels"): vol.Any(str, None),
    }
)
async def ws_set_appearance(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Modelo, versión, color y llanta de un coche.

    Cambiar las opciones recarga la cuenta: se crean las entidades de esa
    versión y se quitan las que no le tocan.
    """
    entry, _vehicle = find_vehicle(hass, msg["vehicle_id"])
    runtime = entry.runtime_data
    offered = {
        model.id: model
        for model in runtime.registries.vehicles.for_country(runtime.country.id)
        if model.id != GENERIC_MODEL_ID
    }
    # Lo que el modelo no tiene (una versión de otro, un color retirado) se descarta.
    chosen = vd.clean_appearance(
        {
            OPT_MODEL: msg["model"],
            OPT_TRIM: msg.get("trim"),
            OPT_COLOR: msg.get("color"),
            OPT_WHEELS: msg.get("wheels"),
        },
        offered,
    )
    if chosen is None:
        raise PanelError("unknown_model")
    hass.config_entries.async_update_entry(
        entry,
        options=ap.updated_options(entry.options, msg["vehicle_id"], offered[msg["model"]], chosen),
    )


@command(
    {
        vol.Required("type"): "dec_deepal/panel/set_people",
        **VEHICLE,
        vol.Required("people"): [str],
    }
)
async def ws_set_people(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """A quién pertenece un coche: personas de Home Assistant (``person.*``).

    Solo se aceptan personas que existen. No recarga nada: de momento solo se
    enseña (más adelante decidirá quién puede hacer qué con cada coche).
    """
    entry, _vehicle = find_vehicle(hass, msg["vehicle_id"])
    unknown = [item for item in msg["people"] if hass.states.get(item) is None or not item.startswith("person.")]
    if unknown:
        raise PanelError("unknown_person")
    await entry.runtime_data.alerts.async_set_people(msg["vehicle_id"], msg["people"])


@command(
    {
        vol.Required("type"): "dec_deepal/panel/set_maintenance",
        **VEHICLE,
        vol.Required("enabled"): bool,
        vol.Optional("services_done", default=0): vol.All(int, vol.Range(min=0, max=50)),
        vol.Optional("last_date"): str,
        vol.Optional("last_km", default=0): vol.All(int, vol.Range(min=0, max=2000000)),
        vol.Optional("interval_km"): vol.All(int, vol.Range(min=1000, max=100000)),
        vol.Optional("interval_months"): vol.All(int, vol.Range(min=1, max=60)),
    }
)
async def ws_set_maintenance(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Ficha de mantenimiento de un coche (o la quita)."""
    entry, vehicle = find_vehicle(hass, msg["vehicle_id"])
    alerts = entry.runtime_data.alerts
    previous = alerts.record(msg["vehicle_id"])
    record = None
    if msg["enabled"]:
        plan = vehicle.model.maintenance
        record = mt.MaintenanceRecord(
            services_done=msg["services_done"],
            last_date=day(msg["last_date"]),
            last_km=msg["last_km"],
            interval_km=msg.get("interval_km", plan.interval_km),
            interval_months=msg.get("interval_months", plan.interval_months),
            history=list(previous.history) if previous else [],
        )
    await alerts.async_set_record(msg["vehicle_id"], record)
    reload_if(hass, entry, (previous is None) == msg["enabled"])


@command(
    {
        vol.Required("type"): "dec_deepal/panel/register_maintenance",
        **VEHICLE,
        vol.Required("date"): str,
        vol.Required("km"): vol.All(int, vol.Range(min=0, max=2000000)),
    }
)
async def ws_register_maintenance(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Anota una revisión hecha."""
    entry, _vehicle = find_vehicle(hass, msg["vehicle_id"])
    if entry.runtime_data.alerts.record(msg["vehicle_id"]) is None:
        raise KeyError(msg["vehicle_id"])
    await entry.runtime_data.alerts.async_register_service(
        msg["vehicle_id"], day(msg["date"]), msg["km"]
    )


@command(
    {
        vol.Required("type"): "dec_deepal/panel/set_itv",
        **VEHICLE,
        vol.Required("enabled"): bool,
        vol.Optional("registration_date"): str,
        vol.Optional("last_date"): vol.Any(str, None),
        vol.Optional("next_date"): vol.Any(str, None),
    }
)
async def ws_set_itv(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Ficha de ITV de un coche (o la quita)."""
    entry, _vehicle = find_vehicle(hass, msg["vehicle_id"])
    alerts = entry.runtime_data.alerts
    previous = alerts.itv_record(msg["vehicle_id"])
    record = None
    if msg["enabled"]:
        record = doc.ItvRecord(
            registration_date=day(msg["registration_date"]),
            last_date=day(msg["last_date"]) if msg.get("last_date") else None,
            history=list(previous.history) if previous else [],
        )
        # Una fecha a mano igual a la calculada no se guarda (se sigue el cálculo).
        chosen = msg.get("next_date")
        if chosen and day(chosen) != doc.itv_calculated(record, alerts.rules):
            record.next_override = day(chosen)
    await alerts.async_set_itv(msg["vehicle_id"], record)
    reload_if(hass, entry, (previous is None) == msg["enabled"])


@command(
    {
        vol.Required("type"): "dec_deepal/panel/register_itv",
        **VEHICLE,
        vol.Required("date"): str,
    }
)
async def ws_register_itv(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Anota una ITV pasada."""
    entry, _vehicle = find_vehicle(hass, msg["vehicle_id"])
    if entry.runtime_data.alerts.itv_record(msg["vehicle_id"]) is None:
        raise KeyError(msg["vehicle_id"])
    await entry.runtime_data.alerts.async_register_itv(msg["vehicle_id"], day(msg["date"]))


@command(
    {
        vol.Required("type"): "dec_deepal/panel/set_insurance",
        **VEHICLE,
        vol.Required("enabled"): bool,
        vol.Optional("renewal_date"): str,
        vol.Optional("company", default=""): str,
        vol.Optional("policy", default=""): str,
        vol.Optional("kind", default=doc.KIND_THIRD_PARTY): vol.In(doc.INSURANCE_KINDS),
        vol.Optional("notice_days", default=doc.DEFAULT_NOTICE_DAYS): vol.All(
            int, vol.Range(min=1, max=180)
        ),
        vol.Optional("phone_assistance", default=""): str,
        vol.Optional("phone_company", default=""): str,
    }
)
async def ws_set_insurance(hass: HomeAssistant, msg: dict[str, Any], user: User) -> None:
    """Ficha del seguro de un coche (o la quita)."""
    entry, _vehicle = find_vehicle(hass, msg["vehicle_id"])
    alerts = entry.runtime_data.alerts
    previous = alerts.insurance_record(msg["vehicle_id"])
    record = None
    if msg["enabled"]:
        record = doc.InsuranceRecord(
            renewal_date=day(msg["renewal_date"]),
            company=msg["company"].strip(),
            policy=msg["policy"].strip(),
            kind=msg["kind"],
            notice_days=msg["notice_days"],
            phone_assistance=msg["phone_assistance"].strip(),
            phone_company=msg["phone_company"].strip(),
        )
    await alerts.async_set_insurance(msg["vehicle_id"], record)
    reload_if(hass, entry, (previous is None) == msg["enabled"])


COMMANDS: Final = (
    ws_set_appearance,
    ws_set_people,
    ws_set_maintenance,
    ws_register_maintenance,
    ws_set_itv,
    ws_register_itv,
    ws_set_insurance,
)
