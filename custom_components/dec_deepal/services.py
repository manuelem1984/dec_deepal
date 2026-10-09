"""Servicios de la integración (acciones que se pueden llamar desde HA).

``dec_deepal.capture_snapshot`` — Captura de depuración
    Guarda una "foto" completa del estado de un coche (valores interpretados,
    MQTT en bruto, REST en bruto...) y la compara con la captura anterior del
    mismo coche. Pensado para descubrir qué significa cada dato: captura →
    cambias una cosa en el coche → captura → mira qué cambió.

    - Devuelve la captura y las diferencias como respuesta del servicio
      (se ven en Herramientas para desarrolladores → Acciones).
    - Además la escribe en ``/config/dec_deepal_capturas/`` como JSON.
    - Los datos personales salen ocultos.

``dec_deepal.register_maintenance`` — Registrar un mantenimiento hecho
    Anota que el coche ha pasado la revisión (por defecto, hoy y con el
    cuentakilómetros actual) y empieza a contar para la siguiente. Lo usa la
    tarjeta, tras pedir confirmación. Hace falta haber activado antes el
    mantenimiento del coche en Configurar → Mantenimiento.

Guía: ``docs/depuracion.md``.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util

from .const import CAPTURES_DIR, DOMAIN
from .debug.capture import build_snapshot, diff_snapshots
from .runtime import DecDeepalConfigEntry

_LOGGER = logging.getLogger(__name__)

SERVICE_CAPTURE = "capture_snapshot"
ATTR_DEVICE_ID = "device_id"
ATTR_LABEL = "label"
ATTR_REFRESH = "refresh"

#: Capturas que se guardan en memoria por coche (para comparar).
MAX_CAPTURES_PER_VEHICLE = 10

SERVICE_REGISTER_MAINTENANCE = "register_maintenance"
ATTR_DATE = "date"
ATTR_KM = "km"

REGISTER_MAINTENANCE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Optional(ATTR_DATE): cv.date,
        vol.Optional(ATTR_KM): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)

CAPTURE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Optional(ATTR_LABEL, default=""): cv.string,
        vol.Optional(ATTR_REFRESH, default=True): cv.boolean,
    }
)


def _find_vehicle(hass: HomeAssistant, device_id: str):  # noqa: ANN202
    """Localiza la cuenta y el coche de un dispositivo de HA.

    Raises:
        ServiceValidationError: el dispositivo no es un coche de DEC Deepal.
    """
    device = dr.async_get(hass).async_get(device_id)
    if device is not None:
        vehicle_ids = [ident for domain, ident in device.identifiers if domain == DOMAIN]
        for entry_id in device.config_entries:
            entry: DecDeepalConfigEntry | None = hass.config_entries.async_get_entry(entry_id)
            if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
                continue
            for vehicle_id in vehicle_ids:
                if vehicle_id in entry.runtime_data.vehicles:
                    return entry.runtime_data, entry.runtime_data.vehicles[vehicle_id]
    raise ServiceValidationError(
        translation_domain=DOMAIN, translation_key="unknown_device"
    )


def _write_capture(folder: Path, name: str, content: dict[str, Any]) -> str:
    """Escribe la captura en disco (en un hilo aparte: es bloqueante)."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


async def _async_capture(call: ServiceCall) -> ServiceResponse:
    """Implementación de ``capture_snapshot``."""
    hass = call.hass
    runtime, vehicle = _find_vehicle(hass, call.data[ATTR_DEVICE_ID])
    if call.data[ATTR_REFRESH]:
        await vehicle.coordinator.async_refresh()

    label = call.data[ATTR_LABEL] or datetime.now(UTC).strftime("%H:%M:%S")
    snapshot = build_snapshot(label, vehicle.info.display_name, vehicle.coordinator.data)

    history = runtime.captures.setdefault(vehicle.info.vehicle_id, [])
    diff = diff_snapshots(history[-1], snapshot) if history else None
    history.append(snapshot)
    del history[:-MAX_CAPTURES_PER_VEHICLE]

    file_name = f"{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}_{vehicle.info.vehicle_id[-6:]}.json"
    saved_to = await hass.async_add_executor_job(
        _write_capture,
        Path(hass.config.path(CAPTURES_DIR)),
        file_name,
        {"captura": snapshot, "diferencias_con_anterior": diff},
    )
    _LOGGER.info("Captura de depuración guardada en %s", saved_to)
    runtime.recorder.record("note", message="captura", label=label, file=file_name)
    return {"archivo": saved_to, "captura": snapshot, "diferencias_con_anterior": diff}


async def _async_register_maintenance(call: ServiceCall) -> None:
    """Implementación de ``register_maintenance``."""
    runtime, vehicle = _find_vehicle(call.hass, call.data[ATTR_DEVICE_ID])
    vehicle_id = vehicle.info.vehicle_id
    alerts = runtime.alerts
    if alerts is None or alerts.record(vehicle_id) is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="maintenance_not_configured"
        )
    km = call.data.get(ATTR_KM)
    if km is None:
        odometer = alerts.odometer(vehicle_id)
        if odometer is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="maintenance_no_odometer"
            )
        km = round(odometer)
    when = call.data.get(ATTR_DATE) or dt_util.now().date()
    await alerts.async_register_service(vehicle_id, when, km)


def async_register_services(hass: HomeAssistant) -> None:
    """Registra los servicios (una vez por arranque, desde ``async_setup``)."""
    if hass.services.has_service(DOMAIN, SERVICE_CAPTURE):
        return
    hass.services.async_register(
        DOMAIN,
        SERVICE_CAPTURE,
        _async_capture,
        schema=CAPTURE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REGISTER_MAINTENANCE,
        _async_register_maintenance,
        schema=REGISTER_MAINTENANCE_SCHEMA,
    )
