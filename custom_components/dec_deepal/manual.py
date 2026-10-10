"""Manual de usuario del coche: el enlace que abre la tarjeta ("Otros → Manual").

El manual es un PDF en la web del fabricante. La tarjeta lo abre en el
navegador del dispositivo (pestaña nueva), que es donde mejor se lee un PDF
largo. La integración solo le dice **qué enlace** abrir.

(En la 2.3.0b3 se enseñaba incrustado en una ventana, con Home Assistant de
intermediario; se descartó porque en el móvil no se podía pasar de página.)

Qué enlace se usa (:func:`manual_url`):

1. El que el usuario haya puesto en Configurar → Avanzado para ese modelo.
2. Si no, el del catálogo (``manual:`` del modelo en ``vehicles.yaml``).
3. Si el modelo no tiene, no hay manual (la tarjeta no enseña la opción).

Vista, solo para usuarios con sesión en Home Assistant:

- ``GET /api/dec_deepal/manual_info/<device_id>`` →
  ``{"available": bool, "url": str | null}``.

En este módulo está también la otra vista que usa la tarjeta para datos que
no deben ir a ninguna entidad (quedarían en el historial y a la vista de
cualquiera con acceso al panel):

- ``GET /api/dec_deepal/insurance_info/<device_id>`` →
  ``{"policy": str, "phone_assistance": str, "phone_company": str}``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aiohttp import web
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, INSURANCE_INFO_API, MANUAL_INFO_API, OPT_MANUAL_URLS
from .runtime import VehicleContext


def is_valid_url(url: str) -> bool:
    """¿Es una dirección web (http o https)?"""
    return url.startswith(("http://", "https://")) and len(url) > 10 and " " not in url


def manual_url(options: Mapping[str, Any], vehicle: VehicleContext) -> str | None:
    """Enlace del manual de un coche (``None`` = no tiene)."""
    custom = str(options.get(OPT_MANUAL_URLS, {}).get(vehicle.model.id) or "").strip()
    if custom and is_valid_url(custom):
        return custom
    return vehicle.model.manual_url or None


def _find(hass: HomeAssistant, device_id: str):  # noqa: ANN202
    """Cuenta y coche de un dispositivo: ``(entry, vehicle)``.

    Raises:
        web.HTTPNotFound: el dispositivo no es un coche de DEC Deepal.
    """
    device = dr.async_get(hass).async_get(device_id)
    if device is not None:
        vehicle_ids = [ident for domain, ident in device.identifiers if domain == DOMAIN]
        for entry_id in device.config_entries:
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
                continue
            for vehicle_id in vehicle_ids:
                if vehicle := entry.runtime_data.vehicles.get(vehicle_id):
                    return entry, vehicle
    raise web.HTTPNotFound


def _device_manual_url(hass: HomeAssistant, device_id: str) -> str | None:
    """Enlace del manual del coche de un dispositivo."""
    entry, vehicle = _find(hass, device_id)
    return manual_url(entry.options, vehicle)


class ManualInfoView(HomeAssistantView):
    """``GET /api/dec_deepal/manual_info/<device_id>`` → enlace del manual."""

    url = MANUAL_INFO_API
    name = "api:dec_deepal:manual_info"

    async def get(self, request: web.Request, device_id: str) -> web.Response:
        """Dice a la tarjeta si hay manual y qué enlace abrir."""
        url = _device_manual_url(request.app[KEY_HASS], device_id)
        return self.json({"available": url is not None, "url": url})


class InsuranceInfoView(HomeAssistantView):
    """``GET /api/dec_deepal/insurance_info/<device_id>`` → póliza y teléfonos."""

    url = INSURANCE_INFO_API
    name = "api:dec_deepal:insurance_info"

    async def get(self, request: web.Request, device_id: str) -> web.Response:
        """Datos del seguro que solo se enseñan en la tarjeta."""
        entry, vehicle = _find(request.app[KEY_HASS], device_id)
        alerts = getattr(entry.runtime_data, "alerts", None)
        record = alerts.insurance_record(vehicle.info.vehicle_id) if alerts else None
        if record is None:
            raise web.HTTPNotFound
        return self.json(
            {
                "policy": record.policy,
                "phone_assistance": record.phone_assistance,
                "phone_company": record.phone_company,
            }
        )


def async_register_manual(hass: HomeAssistant) -> None:
    """Registra las vistas (una vez por arranque)."""
    hass.http.register_view(ManualInfoView())
    hass.http.register_view(InsuranceInfoView())
