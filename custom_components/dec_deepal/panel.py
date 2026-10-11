"""Panel "DEC Deepal" de la barra lateral: registro y canal con la integración.

El panel es una página propia de Home Assistant (como la de Alarmo) donde se
ve y se configura todo lo de los coches de un vistazo: la ficha de cada uno,
quién recibe cada aviso, la copia de los datos y lo que ha pasado. **Convive**
con Configurar: los dos escriben en el mismo sitio, así que se puede usar uno
u otro.

- La página es ``frontend_panel/dec-deepal-panel.js`` (se genera uniendo los
  módulos de ``frontend_panel/src/``, igual que la tarjeta).
- Solo la ven los administradores.
- Habla con la integración por WebSocket (órdenes ``dec_deepal/panel/...``).
  Aquí no hay lógica nueva: cada orden llama a lo mismo que usa Configurar
  (``AlertManager``, el almacén de coches...).

Guía: docs/panel.md
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import date
from typing import Any, Final

import voluptuous as vol
from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.util import slugify

from . import documents as doc
from . import maintenance as mt
from . import vehicle_data as vd
from .alert_rules import (
    NOTICES,
    TARGET_PANEL,
    Route,
    ThresholdError,
    backup_text,
    clean_thresholds,
    panel_name,
)
from .const import (
    DOMAIN,
    ICONS_JS_URL,
    INTEGRATION_DIR,
    NAME,
    OPT_ALERT_VEHICLES,
    OPT_ALERTS,
    OPT_APPEARANCE,
    PANEL_JS_DIR,
    PANEL_JS_FILE,
    PANEL_URL_PATH,
    VERSION,
)
from .telemetry import signals as s
from .vehicle_store import async_export_url, async_get_store

_LOGGER = logging.getLogger(__name__)

_REGISTERED_KEY: Final = "panel_registered"
_ELEMENT: Final = "dec-deepal-panel"
#: Servicios de "notify" que no son un destino (son genéricos de HA).
_NOT_A_TARGET: Final = frozenset({"send_message", "persistent_notification", "notify"})
#: Una copia ocupa unos pocos KB: más que esto no es una copia nuestra.
_MAX_BACKUP_CARS: Final = 50


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------


async def async_register_panel(hass: HomeAssistant) -> None:
    """Añade el panel a la barra lateral (una vez; al cargar la primera cuenta)."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_REGISTERED_KEY):
        return
    domain_data[_REGISTERED_KEY] = True
    path = INTEGRATION_DIR / PANEL_JS_DIR / PANEL_JS_FILE
    url = f"{ICONS_JS_URL}/{PANEL_JS_FILE}"
    try:
        await hass.http.async_register_static_paths([StaticPathConfig(url, str(path), False)])
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
        require_admin=True,
        config={},
    )
    for command in COMMANDS:
        websocket_api.async_register_command(hass, command)


@callback
def async_unregister_panel(hass: HomeAssistant) -> None:
    """Quita el panel de la barra lateral (al borrar la última cuenta)."""
    if hass.data.get(DOMAIN, {}).pop(_REGISTERED_KEY, None):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)


# ---------------------------------------------------------------------------
# Lo que enseña el panel
# ---------------------------------------------------------------------------


def _entries(hass: HomeAssistant) -> list[Any]:
    """Cuentas cargadas."""
    return [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if getattr(getattr(entry, "runtime_data", None), "alerts", None) is not None
    ]


def _find(hass: HomeAssistant, vehicle_id: str) -> tuple[Any, Any]:
    """Cuenta y coche de un identificador: ``(entry, vehicle)``."""
    for entry in _entries(hass):
        if vehicle := entry.runtime_data.vehicles.get(vehicle_id):
            return entry, vehicle
    raise KeyError(vehicle_id)


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


def _without_notified(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != "notified"}


def _car(hass: HomeAssistant, entry: Any, vehicle_id: str, vehicle: Any) -> dict[str, Any]:
    """Todo lo de un coche que enseña el panel."""
    alerts = entry.runtime_data.alerts
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, vehicle_id)})
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
            "operations": alerts.operations(vehicle_id),
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
        "sheet": vehicle.model.sheet(vehicle.trim),
        "battery": data.get(s.BATTERY_LEVEL) if data else None,
        "range": data.get(s.RANGE_KM) if data else None,
        "odometer": alerts.odometer(vehicle_id),
        "itv_available": alerts.itv_available,
        "plan": {"interval_km": plan.interval_km, "interval_months": plan.interval_months},
        "maintenance": maintenance,
        "itv": itv,
        "insurance": insurance,
        "alerts": alerts.route(vehicle_id).to_dict(),
    }


def panel_state(hass: HomeAssistant) -> dict[str, Any]:
    """Estado completo para pintar el panel."""
    cars = [
        _car(hass, entry, vehicle_id, vehicle)
        for entry in _entries(hass)
        for vehicle_id, vehicle in entry.runtime_data.vehicles.items()
    ]
    used = {
        target for car in cars for targets in car["alerts"]["notices"].values() for target in targets
    }
    in_account = {car["key"]: car["name"] for car in cars}
    stored = [
        {
            "key": key,
            "label": in_account.get(key) or vd.label(key, car),
            "tail": key[-6:] if not key.startswith("id:") else key[3:],
            "in_account": key in in_account,
            "has": [section for section in (*vd.RECORDS, vd.APPEARANCE) if car.get(section)],
        }
        for key, car in async_get_store(hass).cars().items()
        if vd.has_data(car)
    ]
    history: dict[str, list[Any]] = {"cambios": [], "ordenes": [], "avisos": [], "errores": []}
    for entry in _entries(hass):
        for kind, events in entry.runtime_data.recorder.history().items():
            history[kind].extend(events)
    return {
        "version": VERSION,
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
        "stored": stored,
        "history": {kind: sorted(events, key=lambda e: e["time"]) for kind, events in history.items()},
    }


# ---------------------------------------------------------------------------
# Órdenes del panel
# ---------------------------------------------------------------------------


def _command(schema: dict[Any, Any]):  # noqa: ANN202
    """Orden del panel: solo administradores; un coche que no existe da error."""

    def decorator(func):  # noqa: ANN001, ANN202
        @websocket_api.websocket_command(schema)
        @websocket_api.require_admin
        @websocket_api.async_response
        async def wrapper(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
            try:
                result = await func(hass, msg)
            except KeyError:
                connection.send_error(msg["id"], "not_found", "Vehículo no encontrado")
            except ThresholdError as err:
                connection.send_error(msg["id"], err.code, err.notice)
            except vd.BackupError as err:
                connection.send_error(msg["id"], err.code, "Copia no válida")
            except ValueError as err:
                connection.send_error(msg["id"], "invalid", str(err))
            else:
                connection.send_result(msg["id"], result)

        return wrapper

    return decorator


_VEHICLE: Final = {vol.Required("vehicle_id"): str}


def _day(value: str) -> date:
    return date.fromisoformat(value)


@_command({vol.Required("type"): "dec_deepal/panel/state"})
async def ws_state(hass: HomeAssistant, msg: dict[str, Any]) -> dict[str, Any]:
    """Todo lo que pinta el panel."""
    await async_get_store(hass).async_load()
    return panel_state(hass)


@_command(
    {
        vol.Required("type"): "dec_deepal/panel/set_alerts",
        **_VEHICLE,
        vol.Required("notices"): {str: [str]},
        vol.Optional("thresholds", default=dict): {str: vol.Any(int, float)},
        vol.Optional("all_vehicles", default=False): bool,
    }
)
async def ws_set_alerts(hass: HomeAssistant, msg: dict[str, Any]) -> None:
    """Guarda a quién avisa un coche de cada cosa, y con qué plazos.

    Se escribe lo de todos los coches de la cuenta (así desaparecen los
    formatos anteriores sin cambiar nada). Cambiar las opciones recarga la
    cuenta, que es lo que aplica los destinos nuevos.
    """
    entry, _vehicle = _find(hass, msg["vehicle_id"])
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


def _reload_if(hass: HomeAssistant, entry: Any, changed: bool) -> None:
    """Activar o desactivar un apartado crea o borra entidades: eso recarga."""
    if changed:
        hass.config_entries.async_schedule_reload(entry.entry_id)


@_command(
    {
        vol.Required("type"): "dec_deepal/panel/set_maintenance",
        **_VEHICLE,
        vol.Required("enabled"): bool,
        vol.Optional("services_done", default=0): vol.All(int, vol.Range(min=0, max=50)),
        vol.Optional("last_date"): str,
        vol.Optional("last_km", default=0): vol.All(int, vol.Range(min=0, max=2000000)),
        vol.Optional("interval_km"): vol.All(int, vol.Range(min=1000, max=100000)),
        vol.Optional("interval_months"): vol.All(int, vol.Range(min=1, max=60)),
    }
)
async def ws_set_maintenance(hass: HomeAssistant, msg: dict[str, Any]) -> None:
    """Ficha de mantenimiento de un coche (o la quita)."""
    entry, vehicle = _find(hass, msg["vehicle_id"])
    alerts = entry.runtime_data.alerts
    previous = alerts.record(msg["vehicle_id"])
    record = None
    if msg["enabled"]:
        plan = vehicle.model.maintenance
        record = mt.MaintenanceRecord(
            services_done=msg["services_done"],
            last_date=_day(msg["last_date"]),
            last_km=msg["last_km"],
            interval_km=msg.get("interval_km", plan.interval_km),
            interval_months=msg.get("interval_months", plan.interval_months),
            history=list(previous.history) if previous else [],
        )
    await alerts.async_set_record(msg["vehicle_id"], record)
    _reload_if(hass, entry, (previous is None) == msg["enabled"])


@_command(
    {
        vol.Required("type"): "dec_deepal/panel/register_maintenance",
        **_VEHICLE,
        vol.Required("date"): str,
        vol.Required("km"): vol.All(int, vol.Range(min=0, max=2000000)),
    }
)
async def ws_register_maintenance(hass: HomeAssistant, msg: dict[str, Any]) -> None:
    """Anota una revisión hecha."""
    entry, _vehicle = _find(hass, msg["vehicle_id"])
    if entry.runtime_data.alerts.record(msg["vehicle_id"]) is None:
        raise KeyError(msg["vehicle_id"])
    await entry.runtime_data.alerts.async_register_service(
        msg["vehicle_id"], _day(msg["date"]), msg["km"]
    )


@_command(
    {
        vol.Required("type"): "dec_deepal/panel/set_itv",
        **_VEHICLE,
        vol.Required("enabled"): bool,
        vol.Optional("registration_date"): str,
        vol.Optional("last_date"): vol.Any(str, None),
        vol.Optional("next_date"): vol.Any(str, None),
    }
)
async def ws_set_itv(hass: HomeAssistant, msg: dict[str, Any]) -> None:
    """Ficha de ITV de un coche (o la quita)."""
    entry, _vehicle = _find(hass, msg["vehicle_id"])
    alerts = entry.runtime_data.alerts
    previous = alerts.itv_record(msg["vehicle_id"])
    record = None
    if msg["enabled"]:
        record = doc.ItvRecord(
            registration_date=_day(msg["registration_date"]),
            last_date=_day(msg["last_date"]) if msg.get("last_date") else None,
            history=list(previous.history) if previous else [],
        )
        # Una fecha a mano igual a la calculada no se guarda (se sigue el cálculo).
        chosen = msg.get("next_date")
        if chosen and _day(chosen) != doc.itv_calculated(record, alerts.rules):
            record.next_override = _day(chosen)
    await alerts.async_set_itv(msg["vehicle_id"], record)
    _reload_if(hass, entry, (previous is None) == msg["enabled"])


@_command(
    {
        vol.Required("type"): "dec_deepal/panel/register_itv",
        **_VEHICLE,
        vol.Required("date"): str,
    }
)
async def ws_register_itv(hass: HomeAssistant, msg: dict[str, Any]) -> None:
    """Anota una ITV pasada."""
    entry, _vehicle = _find(hass, msg["vehicle_id"])
    if entry.runtime_data.alerts.itv_record(msg["vehicle_id"]) is None:
        raise KeyError(msg["vehicle_id"])
    await entry.runtime_data.alerts.async_register_itv(msg["vehicle_id"], _day(msg["date"]))


@_command(
    {
        vol.Required("type"): "dec_deepal/panel/set_insurance",
        **_VEHICLE,
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
async def ws_set_insurance(hass: HomeAssistant, msg: dict[str, Any]) -> None:
    """Ficha del seguro de un coche (o la quita)."""
    entry, _vehicle = _find(hass, msg["vehicle_id"])
    alerts = entry.runtime_data.alerts
    previous = alerts.insurance_record(msg["vehicle_id"])
    record = None
    if msg["enabled"]:
        record = doc.InsuranceRecord(
            renewal_date=_day(msg["renewal_date"]),
            company=msg["company"].strip(),
            policy=msg["policy"].strip(),
            kind=msg["kind"],
            notice_days=msg["notice_days"],
            phone_assistance=msg["phone_assistance"].strip(),
            phone_company=msg["phone_company"].strip(),
        )
    await alerts.async_set_insurance(msg["vehicle_id"], record)
    _reload_if(hass, entry, (previous is None) == msg["enabled"])


# --- Datos: copia y borrado ---------------------------------------------------


def _flush(hass: HomeAssistant) -> None:
    """Lo pendiente de escribir, al almacén: la copia sale al día."""
    for entry in _entries(hass):
        entry.runtime_data.alerts.async_flush()


def _refresh(hass: HomeAssistant, already_reloading: set[str] | None = None) -> None:
    """Tras cambiar el almacén: releerlo y recargar las cuentas (cambian entidades)."""
    for entry in _entries(hass):
        entry.runtime_data.alerts.async_reload_data()
        if entry.entry_id not in (already_reloading or ()):
            hass.config_entries.async_schedule_reload(entry.entry_id)


def _apply_appearance(hass: HomeAssistant, cars: Mapping[str, Mapping[str, Any]]) -> set[str]:
    """Pone en su cuenta la apariencia que trae una copia.

    Returns:
        Cuentas cuyas opciones han cambiado (se recargan solas).
    """
    changed: set[str] = set()
    for entry in _entries(hass):
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


@_command({vol.Required("type"): "dec_deepal/panel/export_url"})
async def ws_export_url(hass: HomeAssistant, msg: dict[str, Any]) -> dict[str, str]:
    """Enlace firmado para descargar la copia (caduca a los pocos minutos)."""
    _flush(hass)
    return {"url": async_export_url(hass), "absolute": async_export_url(hass, absolute=True)}


@_command({vol.Required("type"): "dec_deepal/panel/send_backup", vol.Required("target"): str})
async def ws_send_backup(hass: HomeAssistant, msg: dict[str, Any]) -> None:
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


@_command({vol.Required("type"): "dec_deepal/panel/import_backup", vol.Required("backup"): dict})
async def ws_import_backup(hass: HomeAssistant, msg: dict[str, Any]) -> dict[str, list[str]]:
    """Carga una copia: deja los coches que trae como estaban en ella."""
    cars = vd.parse_backup(msg["backup"])
    if len(cars) > _MAX_BACKUP_CARS:
        raise vd.BackupError(vd.ERROR_INVALID)
    await async_get_store(hass).async_import(cars)
    _refresh(hass, _apply_appearance(hass, cars))
    return {"cars": [vd.label(key, car) for key, car in cars.items()]}


@_command({vol.Required("type"): "dec_deepal/panel/delete_data", vol.Required("keys"): [str]})
async def ws_delete_data(hass: HomeAssistant, msg: dict[str, Any]) -> None:
    """Borra los datos guardados de unos coches."""
    await async_get_store(hass).async_delete(msg["keys"])
    _refresh(hass)


COMMANDS: Final = (
    ws_state,
    ws_set_alerts,
    ws_set_maintenance,
    ws_register_maintenance,
    ws_set_itv,
    ws_register_itv,
    ws_set_insurance,
    ws_export_url,
    ws_send_backup,
    ws_import_backup,
    ws_delete_data,
)
