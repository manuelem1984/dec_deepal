"""Lo que pinta el panel (orden ``state``), según quién lo mira.

- **Administradores:** todo (coches, avisos, copia, diagnóstico y ajustes).
- **Resto de usuarios:** solo lo de las pestañas Coches y Avisos, para
  verlo (sin ajustes de la cuenta, sin datos guardados ni historial).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

import voluptuous as vol
from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant

from .. import documents as doc
from .. import vehicle_data as vd
from ..alert_rules import NOTICES
from ..const import (
    ARM_SECONDS_CHOICES,
    DEFAULT_ARM_NOTIFY,
    DEFAULT_ARM_SECONDS,
    DEFAULT_PIN_MODE,
    DEFAULT_SCAN_MINUTES,
    DEFAULT_WAKE,
    INTEGRATION_DIR,
    MAX_SCAN_MINUTES,
    MIN_SCAN_MINUTES,
    OPT_ARM_NOTIFY,
    OPT_ARM_SECONDS,
    OPT_DEBUG,
    OPT_MANUAL_URLS,
    OPT_PIN,
    OPT_PIN_ENABLED,
    OPT_PIN_MODE,
    OPT_SCAN_MINUTES,
    OPT_WAKE,
    PHOTOS_URL,
    VERSION,
)
from ..manual import manual_url
from ..plates import plate
from ..registries.vehicles import FEATURE_FUEL, GENERIC_MODEL_ID
from ..runtime import vehicle_device
from ..telemetry import signals as s
from ..vehicle_store import async_get_store
from .avisos import notify_targets
from .comun import command, loaded_entries

#: Equipamiento de confort que se cuenta en cada versión (para elegir apariencia).
_COMFORT: Final = ("asientos_calefaccion", "asientos_ventilacion", "volante_calefactado", "porton_electrico")


def _photo_url(model: Any, trim: str | None, color: str | None) -> str | None:
    """Dirección de la foto del catálogo para esa versión y ese color."""
    photo = model.photo_for(trim, color)
    if photo is None:
        return None
    relative = photo.relative_to(INTEGRATION_DIR / "vehicles" / "photos").as_posix()
    return f"{PHOTOS_URL}/{relative}?v={VERSION}"


def _model(model: Any) -> dict[str, Any]:
    """Un modelo del catálogo, con lo que hace falta para elegir la apariencia."""
    return {
        "id": model.id,
        "name": model.name,
        "fuel": model.has(FEATURE_FUEL),
        "trims": [
            {
                "id": trim.id,
                "name": trim.name,
                # Llanta fija de la versión ("" = se puede elegir).
                "wheel": trim.wheel,
                "equipped": sum(1 for feature in _COMFORT if model.has(feature, trim.id)),
            }
            for trim in model.trims.values()
        ],
        "colors": [
            {"id": color.id, "name": color.name, "swatch": color.swatch}
            for color in model.colors.values()
        ],
        "wheels": list(model.wheel_options),
        # Foto de cada combinación: "<versión>|<color>" (vacíos = sin elegir).
        "photos": {
            f"{trim or ''}|{color or ''}": _photo_url(model, trim, color)
            for trim in (None, *model.trims)
            for color in (None, *model.colors)
        },
    }


def account_settings(entry: Any) -> dict[str, Any]:
    """Ajustes de una cuenta (sin el PIN: solo si lo tiene)."""
    options = entry.options
    models = {
        vehicle.model.id: vehicle.model
        for vehicle in entry.runtime_data.vehicles.values()
        if vehicle.configured
    }
    # El enlace del manual es por modelo; solo se ofrece si todos los coches
    # de la cuenta son del mismo (lo normal).
    model = next(iter(models.values())) if len(models) == 1 else None
    custom = str(options.get(OPT_MANUAL_URLS, {}).get(model.id) or "") if model else ""
    return {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "pin_enabled": bool(options.get(OPT_PIN_ENABLED, False)),
        "pin_set": bool(options.get(OPT_PIN)),
        "pin_mode": options.get(OPT_PIN_MODE, DEFAULT_PIN_MODE),
        "arm_seconds": int(options.get(OPT_ARM_SECONDS, DEFAULT_ARM_SECONDS)),
        "arm_notify": bool(options.get(OPT_ARM_NOTIFY, DEFAULT_ARM_NOTIFY)),
        "arm_choices": list(ARM_SECONDS_CHOICES),
        "scan_minutes": int(options.get(OPT_SCAN_MINUTES, DEFAULT_SCAN_MINUTES)),
        "scan_limits": [MIN_SCAN_MINUTES, MAX_SCAN_MINUTES],
        "wake": bool(options.get(OPT_WAKE, DEFAULT_WAKE)),
        "debug": bool(options.get(OPT_DEBUG, False)),
        "manual": (
            None
            if model is None
            else {
                "kind": "phev" if model.has(FEATURE_FUEL) else "bev",
                "url": custom or model.manual_url,
                "official": model.manual_url,
            }
        ),
    }


def _sales_country(entry: Any) -> str:
    """País de la cuenta como lo espera el servidor (``ES``)."""
    country = entry.runtime_data.country
    return str(getattr(country, "sales_country", None) or country.id).upper()


def _without_notified(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != "notified"}


def _people(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Personas de Home Assistant: ``[{"id": "person.ana", "name": "Ana", "user_id": ...}]``."""
    return sorted(
        (
            {
                "id": state.entity_id,
                "name": state.attributes.get("friendly_name") or state.entity_id,
                "user_id": state.attributes.get("user_id"),
            }
            for state in hass.states.async_all("person")
        ),
        key=lambda person: str(person["name"]).casefold(),
    )


def _car(
    hass: HomeAssistant,
    entry: Any,
    vehicle_id: str,
    vehicle: Any,
    people: Mapping[str, Mapping[str, Any]],
    user: User,
) -> dict[str, Any]:
    """Todo lo de un coche que enseña el panel."""
    alerts = entry.runtime_data.alerts
    device = vehicle_device(hass, entry.entry_id, vehicle_id)
    data = vehicle.coordinator.data
    color = vehicle.model.colors.get(vehicle.color or "")
    plan = vehicle.model.maintenance

    maintenance = None
    if (record := alerts.record(vehicle_id)) is not None:
        current = alerts.status(vehicle_id)
        maintenance = {
            "record": _without_notified(record.to_dict()),
            "number": current.number,
            "due_date": current.due_date.isoformat(),
            "due_km": current.due_km,
            "days_left": current.days_left,
            "km_left": current.km_left,
            "level": current.level,
            "operations": (now_ops := alerts.operations(vehicle_id)),
            # Lo que se añade en la siguiente revisión (para prever una más larga).
            "next_extra": [
                name
                for name in plan.operations_for(
                    current.number + 1, vehicle.trim, hass.config.language
                )
                if name not in now_ops
            ],
        }
    itv = None
    if alerts.itv_available and (itv_record := alerts.itv_record(vehicle_id)) is not None:
        itv_now = alerts.itv_status(vehicle_id)
        itv = {
            "record": _without_notified(itv_record.to_dict()),
            "due_date": itv_now.due_date.isoformat(),
            "calculated": doc.itv_calculated(itv_record, alerts.rules).isoformat(),
            "days_left": itv_now.days_left,
            "level": itv_now.level,
        }
    insurance = None
    if (policy := alerts.insurance_record(vehicle_id)) is not None:
        insured = alerts.insurance_status(vehicle_id)
        insurance = {
            "record": _without_notified(policy.to_dict()),
            "cancel_deadline": insured.cancel_deadline.isoformat(),
            "days_to_renewal": insured.days_to_renewal,
            "days_to_cancel": insured.days_to_cancel,
            "level": insured.level,
        }
    owners = alerts.people(vehicle_id)
    return {
        "id": vehicle_id,
        "entry_id": entry.entry_id,
        "device_id": device.id if device else None,
        "key": vd.car_key(vehicle.info.vin, vehicle_id),
        "name": (device.name_by_user or device.name) if device else vehicle.info.display_name,
        "model": vehicle.model.display_name(vehicle.trim),
        "color": color.name if color else None,
        "wheel": vehicle.wheel,
        "configured": vehicle.configured,
        # Lo elegido en Apariencia (sin modelo: nada elegido todavía).
        "appearance": {
            "model": vehicle.model.id if vehicle.configured else None,
            "trim": vehicle.trim,
            "color": vehicle.color,
            "wheels": getattr(vehicle, "wheels", None),
        },
        # A quién pertenece (una persona borrada sale con su identificador).
        "people": [
            {"id": person_id, "name": people.get(person_id, {}).get("name", person_id)}
            for person_id in owners
        ],
        # ¿Es de quien está mirando el panel?
        "mine": any(people.get(person_id, {}).get("user_id") == user.id for person_id in owners),
        "country": entry.runtime_data.country.id,
        # Matrícula con el formato del país de la cuenta (placa del panel).
        "plate": plate(vehicle.info.license_plate, _sales_country(entry)),
        "sheet": vehicle.model.sheet(vehicle.trim),
        "battery": data.get(s.BATTERY_LEVEL) if data else None,
        "range": data.get(s.RANGE_KM) if data else None,
        "odometer": alerts.odometer(vehicle_id),
        "itv_available": alerts.itv_available,
        "plan": {"interval_km": plan.interval_km, "interval_months": plan.interval_months},
        # Normas del país para calcular la ITV (el formulario enseña la fecha antes de guardar).
        "itv_rules": {
            "first_months": alerts.rules.itv_first_months,
            "interval_months": alerts.rules.itv_interval_months,
            "reduced_from_months": alerts.rules.itv_reduced_from_months,
            "reduced_interval_months": alerts.rules.itv_reduced_interval_months,
        },
        "manual_url": manual_url(entry.options, vehicle),
        "maintenance": maintenance,
        "itv": itv,
        "insurance": insurance,
        "alerts": alerts.route(vehicle_id).to_dict(),
    }


def _stored(hass: HomeAssistant, cars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Coches con datos guardados (pestaña Datos), estén o no en una cuenta."""
    in_account = {car["key"]: car["name"] for car in cars}
    return [
        {
            "key": key,
            "label": in_account.get(key) or vd.label(key, car),
            "tail": key[-6:] if not key.startswith("id:") else key[3:],
            "in_account": key in in_account,
            "has": [
                section for section in (*vd.RECORDS, vd.APPEARANCE, vd.PEOPLE) if car.get(section)
            ],
        }
        for key, car in async_get_store(hass).cars().items()
        if vd.has_data(car)
    ]


def panel_state(hass: HomeAssistant, user: User) -> dict[str, Any]:
    """Estado para pintar el panel; sin lo de administración si no lo es."""
    people = {person["id"]: person for person in _people(hass)}
    entries = loaded_entries(hass)
    cars = [
        _car(hass, entry, vehicle_id, vehicle, people, user)
        for entry in entries
        for vehicle_id, vehicle in entry.runtime_data.vehicles.items()
    ]
    used = {
        target for car in cars for targets in car["alerts"]["notices"].values() for target in targets
    }
    state: dict[str, Any] = {
        "version": VERSION,
        "admin": user.is_admin,
        "cars": cars,
        "targets": notify_targets(hass, used),
        "notices": [
            {
                "id": notice.id,
                "section": notice.section,
                "unit": notice.unit,
                "threshold": notice.threshold,
                "limits": notice.limits,
            }
            for notice in NOTICES
        ],
        "insurance_kinds": list(doc.INSURANCE_KINDS),
    }
    if not user.is_admin:
        return state

    history: dict[str, list[Any]] = {"cambios": [], "ordenes": [], "avisos": [], "errores": []}
    models: dict[str, Any] = {}
    for entry in entries:
        for kind, events in entry.runtime_data.recorder.history().items():
            history[kind].extend(events)
        runtime = entry.runtime_data
        for model in runtime.registries.vehicles.for_country(runtime.country.id):
            if model.id != GENERIC_MODEL_ID:
                models.setdefault(model.id, _model(model))
    return state | {
        "models": list(models.values()),
        "accounts": [account_settings(entry) for entry in entries],
        "people": [{"id": person["id"], "name": person["name"]} for person in people.values()],
        "stored": _stored(hass, cars),
        "history": {kind: sorted(events, key=lambda e: e["time"]) for kind, events in history.items()},
    }


@command({vol.Required("type"): "dec_deepal/panel/state"}, admin=False)
async def ws_state(hass: HomeAssistant, msg: dict[str, Any], user: User) -> dict[str, Any]:
    """Todo lo que pinta el panel (lo puede pedir cualquier usuario)."""
    await async_get_store(hass).async_load()
    return panel_state(hass, user)


COMMANDS: Final = (ws_state,)
