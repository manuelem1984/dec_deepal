"""Diario del coche en Home Assistant: escucha las lecturas, guarda y avisa (ver ``car_log.py``).

- Guarda en ``.storage/dec_deepal.car_log`` (por coche: viajes y cargas,
  totales y precios).
- Cada viaje o carga terminados se lanza como evento ``dec_deepal_car_log``:
  sale en el **Registro** de Home Assistant (``logbook.py``) y se puede usar
  en automatizaciones.
- Lo enseñan los sensores «Energía cargada», «Coste de las cargas»,
  «Consumo medio» y «Último viaje», y se descarga con la acción
  ``dec_deepal.export_car_log``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any, Final

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import car_log
from .const import DOMAIN
from .runtime import VehicleContext, vehicle_device
from .telemetry import signals as s
from .telemetry.derived import CHARGE_CHARGING_DC

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY: Final = f"{DOMAIN}.car_log"
STORAGE_VERSION: Final = 1
#: Evento de cada viaje o carga terminados (lo describe ``logbook.py``).
EVENT_CAR_LOG: Final = f"{DOMAIN}_car_log"


class CarLogManager:
    """Los diarios de los coches de una cuenta."""

    def __init__(self, hass: HomeAssistant, entry_id: str, vehicles: dict[str, VehicleContext]) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._vehicles = vehicles
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._logs: dict[str, dict[str, Any]] = {}
        self._listeners: list[Callable[[], None]] = []
        self._unsubscribe: list[CALLBACK_TYPE] = []

    async def async_load(self) -> None:
        """Lee lo guardado."""
        raw = await self._store.async_load() or {}
        self._logs = {vehicle_id: car_log.clean(raw.get(vehicle_id)) for vehicle_id in self._vehicles}

    @callback
    def async_start(self) -> None:
        """Empieza a escuchar las lecturas de los coches."""
        for vehicle_id, vehicle in self._vehicles.items():
            self._unsubscribe.append(
                vehicle.coordinator.async_add_listener(lambda vehicle_id=vehicle_id: self._on_update(vehicle_id))
            )
            self._on_update(vehicle_id)

    @callback
    def async_stop(self) -> None:
        """Deja de escuchar (al descargar la cuenta)."""
        for unsubscribe in self._unsubscribe:
            unsubscribe()
        self._unsubscribe.clear()

    def log(self, vehicle_id: str) -> dict[str, Any]:
        """El diario de un coche."""
        return self._logs.setdefault(vehicle_id, car_log.empty())

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        """Avisa a los sensores cuando cambia algo."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def _changed(self) -> None:
        self._store.async_delay_save(lambda: self._logs, 10)
        for listener in list(self._listeners):
            listener()

    def capacity(self, vehicle_id: str) -> float | None:
        """Capacidad útil de la batería del coche (catálogo), en kWh."""
        vehicle = self._vehicles[vehicle_id]
        trim = vehicle.model.trims.get(vehicle.trim or "")
        return getattr(trim, "battery_kwh", None)

    async def async_set_price(self, vehicle_id: str, kind: str, price: float | None) -> None:
        """Precio de la electricidad (€/kWh) en casa (``ac``) o en carga rápida (``dc``)."""
        prices = self.log(vehicle_id)["prices"]
        if price is None or price <= 0:
            prices.pop(kind, None)
        else:
            prices[kind] = round(float(price), 4)
        self._changed()

    @callback
    def _on_update(self, vehicle_id: str, now: datetime | None = None) -> None:
        data = self._vehicles[vehicle_id].coordinator.data
        if data is None:
            return
        values = {
            "power_on": data.get(s.POWER_ON),
            "charging": data.get(s.CHARGING),
            "battery_level": data.get(s.BATTERY_LEVEL),
            "odometer_km": data.get(s.ODOMETER_KM),
            "dc": data.get(s.CHARGE_STATUS) == CHARGE_CHARGING_DC,
        }
        log = self.log(vehicle_id)
        before = (log.get("trip"), log.get("charge"))
        done = car_log.update(log, values, now or dt_util.now(), self.capacity(vehicle_id))
        if not done and before == (log.get("trip"), log.get("charge")):
            return
        device = vehicle_device(self.hass, self._entry_id, vehicle_id)
        for entry in done:
            self.hass.bus.async_fire(
                EVENT_CAR_LOG,
                {"vehicle_id": vehicle_id, "device_id": device.id if device else None, **entry},
            )
        self._changed()

    def diagnostics(self, vehicle_id: str) -> dict[str, Any]:
        """Resumen para el diagnóstico (sin fechas exactas de los viajes)."""
        log = self.log(vehicle_id)
        return {
            "entradas": len(log["entries"]),
            "viaje_en_curso": "trip" in log,
            "carga_en_curso": "charge" in log,
            "totales": dict(log["totals"]),
            "con_precios": sorted(log["prices"]),
            "capacidad_kwh": self.capacity(vehicle_id),
        }
