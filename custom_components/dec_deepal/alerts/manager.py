"""Avisos: el gestor (arranque, guardado, escuchas, destinos y envío)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.translation import async_get_translations

from .. import charging
from .. import documents as doc
from .. import maintenance as mt
from .. import vehicle_data as vd
from ..alert_rules import (
    TARGET_PANEL,
    Route,
    route_for,
)
from ..const import (
    DOMAIN,
    NAME,
    OPT_ALERTS,
    OPT_COLOR,
    OPT_MODEL,
    OPT_TRIM,
    OPT_WHEELS,
)
from ..runtime import VehicleContext, vehicle_device
from ..vehicle_store import VehicleStore, async_get_store
from .coche import CarMixin
from .const import DAILY_CHECK_HOURS
from .documentos import DocumentsMixin
from .mantenimiento import MaintenanceMixin

_LOGGER = logging.getLogger(__package__)


class AlertManager(CarMixin, MaintenanceMixin, DocumentsMixin):
    """Avisos y mantenimiento de los coches de una cuenta.

    Aquí está lo común (arranque, guardado, escuchas, destinos y envío); los
    avisos de cada tema, en su parte (ver el paquete).
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        options: dict[str, Any],
        vehicles: dict[str, VehicleContext],
        rules: doc.CountryRules = doc.DEFAULT_RULES,
        itv_available: bool = True,
        store: VehicleStore | None = None,
        recorder: Any = None,
    ) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._vehicles = vehicles
        #: Normas del país de la cuenta (ITV, preaviso del seguro).
        self.rules = rules
        #: La ITV es una norma de cada país: solo existe donde está dada de
        #: alta (hoy, España). En los demás no hay entidades, avisos ni menú.
        self.itv_available = itv_available
        self._store = store or async_get_store(hass)
        #: A quién avisa cada coche de cada cosa (ver ``alert_rules.route_for``).
        self._routes: dict[str, Route] = {
            vehicle_id: route_for(options.get(OPT_ALERTS), vehicle_id) for vehicle_id in vehicles
        }
        #: Registro de depuración (``debug/recorder.py``): apunta cada aviso enviado.
        self._recorder = recorder
        self._records: dict[str, mt.MaintenanceRecord] = {}
        self._itv: dict[str, doc.ItvRecord] = {}
        self._insurance: dict[str, doc.InsuranceRecord] = {}
        #: Personas a las que pertenece cada coche (``person.*``).
        self._people: dict[str, list[str]] = {}
        #: Testigos encendidos y ya avisados, por coche.
        self._active: dict[str, set[str]] = {}
        #: Última lectura de cada coche (solo las señales que se vigilan).
        self._previous: dict[str, dict[str, Any]] = {}
        self._odometer: dict[str, float] = {}
        #: Carga en curso y última carga de cada coche (ver ``charging.py``).
        self._charge: dict[str, dict[str, Any]] = {}
        self._names: dict[str, str] = {}
        self._listeners: list[Callable[[], None]] = []
        self._unsubscribe: list[CALLBACK_TYPE] = []

    def _key(self, vehicle_id: str) -> str:
        """Clave del coche en el almacén: su bastidor."""
        return vd.car_key(self._vehicles[vehicle_id].info.vin, vehicle_id)

    async def async_load(self) -> None:
        """Lee lo guardado. Una ficha ilegible se descarta (se avisa en el registro)."""
        await self._store.async_load()
        # Hasta la 2.3.0 había un almacén por cuenta: se pasa al de coches.
        await self._store.async_adopt_legacy(
            self._entry_id, {vehicle_id: self._key(vehicle_id) for vehicle_id in self._vehicles}
        )
        self._read()
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "entity", [DOMAIN]
        )
        prefix = f"component.{DOMAIN}.entity.binary_sensor."
        self._names = {
            key[len(prefix) : -len(".name")]: text
            for key, text in translations.items()
            if key.startswith(prefix) and key.endswith(".name")
        }

    def _read(self) -> None:
        """Pasa a memoria lo guardado de los coches de esta cuenta."""
        targets: dict[str, dict[str, Any]] = {
            vd.MAINTENANCE: self._records,
            vd.ITV: self._itv,
            vd.INSURANCE: self._insurance,
        }
        for target in (*targets.values(), self._active, self._odometer, self._charge, self._people):
            target.clear()
        for vehicle_id in self._vehicles:
            car = self._store.car(self._key(vehicle_id))
            for section, target in targets.items():
                # País sin ITV: la ficha se conserva en el almacén, pero no se usa.
                if not car.get(section) or (section == vd.ITV and not self.itv_available):
                    continue
                try:
                    target[vehicle_id] = vd.RECORDS[section](car[section])
                except (AttributeError, KeyError, TypeError, ValueError) as err:
                    _LOGGER.warning("Ficha de %s ilegible (%s): %s", section, vehicle_id, err)
            if car.get(vd.ACTIVE):
                self._active[vehicle_id] = set(car[vd.ACTIVE])
            if car.get(vd.ODOMETER) is not None:
                self._odometer[vehicle_id] = float(car[vd.ODOMETER])
            if stored := charging.clean(car.get(vd.CHARGE)):
                self._charge[vehicle_id] = stored
            if people := vd.clean_people(car.get(vd.PEOPLE)):
                self._people[vehicle_id] = people

    @callback
    def async_reload_data(self) -> None:
        """Vuelve a leer el almacén (tras cargar una copia o borrar datos)."""
        self._read()
        self._notify_listeners()

    @callback
    def async_start(self) -> None:
        """Empieza a vigilar (tras la primera lectura de cada coche)."""
        for vehicle_id, vehicle in self._vehicles.items():
            self._previous[vehicle_id] = self._snapshot(vehicle)
            self._unsubscribe.append(
                vehicle.coordinator.async_add_listener(
                    lambda vehicle_id=vehicle_id: self._on_update(vehicle_id)
                )
            )
            self._on_update(vehicle_id)
        self._unsubscribe.append(
            async_track_time_change(
                self.hass, self._on_daily_check, hour=DAILY_CHECK_HOURS, minute=0, second=30
            )
        )

    async def async_stop(self) -> None:
        """Deja de vigilar y guarda lo pendiente (al descargar la cuenta)."""
        for unsubscribe in self._unsubscribe:
            unsubscribe()
        self._unsubscribe.clear()
        await self._async_save()

    def _save(self) -> None:
        """Guarda dentro de un momento."""
        self._write()
        self._store.async_delay_save()

    @callback
    def async_flush(self) -> None:
        """Pasa al almacén lo que haya en memoria (antes de hacer una copia)."""
        self._write()

    async def _async_save(self) -> None:
        """Guarda ya."""
        self._write()
        await self._store.async_save()

    def _write(self) -> None:
        """Pasa al almacén lo que hay en memoria de los coches de esta cuenta."""
        for vehicle_id in self._vehicles:
            key = self._key(vehicle_id)
            car: dict[str, Any] = {
                vd.VEHICLE_ID: vehicle_id,
                vd.NAME: self._vehicle_name(vehicle_id),
            }
            if vehicle_id in self._records:
                car[vd.MAINTENANCE] = self._records[vehicle_id].to_dict()
            if vehicle_id in self._itv:
                car[vd.ITV] = self._itv[vehicle_id].to_dict()
            elif not self.itv_available and (parked := self._store.car(key).get(vd.ITV)):
                car[vd.ITV] = parked  # país sin ITV: se conserva lo que hubiera
            if vehicle_id in self._insurance:
                car[vd.INSURANCE] = self._insurance[vehicle_id].to_dict()
            if self._active.get(vehicle_id):
                car[vd.ACTIVE] = sorted(self._active[vehicle_id])
            if vehicle_id in self._odometer:
                car[vd.ODOMETER] = self._odometer[vehicle_id]
            if self._charge.get(vehicle_id):
                car[vd.CHARGE] = self._charge[vehicle_id]
            if appearance := self._appearance(vehicle_id, key):
                car[vd.APPEARANCE] = appearance
            if self._people.get(vehicle_id):
                car[vd.PEOPLE] = list(self._people[vehicle_id])
            self._store.set_car(key, car)

    def _appearance(self, vehicle_id: str, key: str) -> dict[str, Any] | None:
        """Apariencia que se guarda con el coche: la elegida en Configurar.

        Mientras el coche no tenga modelo elegido, se conserva la que hubiera
        guardada (es la que se le devolverá).
        """
        vehicle = self._vehicles[vehicle_id]
        if not getattr(vehicle, "configured", False):
            return self._store.car(key).get(vd.APPEARANCE)
        return vd.clean_appearance(
            {
                OPT_MODEL: vehicle.model.id,
                OPT_TRIM: vehicle.trim,
                OPT_COLOR: getattr(vehicle, "color", None),
                OPT_WHEELS: getattr(vehicle, "wheels", None),
            }
        )

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        """Las entidades de mantenimiento se apuntan para repintarse."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            listener()

    @callback
    def _on_daily_check(self, _now: datetime) -> None:
        for vehicle_id in self._vehicles:
            self._check_maintenance(vehicle_id)
            self._check_documents(vehicle_id)
        self._notify_listeners()

    def people(self, vehicle_id: str) -> list[str]:
        """Personas a las que pertenece un coche (``person.*``)."""
        return list(self._people.get(vehicle_id, []))

    async def async_set_people(self, vehicle_id: str, people: list[str]) -> None:
        """Guarda a quién pertenece un coche (lista vacía = a nadie en concreto)."""
        if clean := vd.clean_people(people):
            self._people[vehicle_id] = clean
        else:
            self._people.pop(vehicle_id, None)
        await self._async_save()
        self._notify_listeners()

    def route(self, vehicle_id: str) -> Route:
        """A quién avisa un coche de cada cosa."""
        return self._routes[vehicle_id]

    def _wants(self, vehicle_id: str, alert: str) -> bool:
        """¿Tiene ese coche algún destino para ese tipo de aviso?"""
        return bool(self._routes[vehicle_id].targets_for(alert))

    def _fresh(
        self, vehicle_id: str, section: str, steps: frozenset[str], notified: set[str]
    ) -> tuple[set[str], tuple[str, ...]]:
        """Escalones recién alcanzados que tienen a quién avisar, y esos destinos.

        Cada escalón es un aviso con sus propios destinos
        (``<apartado>_<escalón>``). Uno sin destinos no cuenta: si más
        adelante se le ponen, avisará entonces.
        """
        route = self._routes[vehicle_id]
        fresh = {step for step in steps - notified if route.targets_for(f"{section}_{step}")}
        targets = dict.fromkeys(
            target for step in sorted(fresh) for target in route.targets_for(f"{section}_{step}")
        )
        return fresh, tuple(targets)

    def _vehicle_name(self, vehicle_id: str) -> str:
        """Nombre del coche: el que le haya puesto el usuario en Home Assistant."""
        device = vehicle_device(self.hass, self._entry_id, vehicle_id)
        if device is not None and (device.name_by_user or device.name):
            return device.name_by_user or device.name
        return self._vehicles[vehicle_id].info.display_name

    def _send(
        self, vehicle_id: str, alert: str, message: str, targets: tuple[str, ...] | None = None
    ) -> None:
        """Envía un aviso (sin esperar a que llegue).

        Args:
            alert: tipo de aviso (para el historial).
            targets: a quién; si no se dice, los destinos de ese aviso.
        """
        title = f"{NAME} {self._vehicle_name(vehicle_id)}"
        _LOGGER.debug("Aviso: %s — %s", title, message)
        if targets is None:
            targets = self._routes[vehicle_id].targets_for(alert)
        sent = 0
        for service in targets:
            if service == TARGET_PANEL:
                persistent_notification.async_create(self.hass, message, title=title)
                sent += 1
                continue
            if not self.hass.services.has_service("notify", service):
                _LOGGER.warning("Aviso no enviado: ya no existe notify.%s", service)
                continue
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "notify", service, {"title": title, "message": message}, blocking=False
                ),
                "dec_deepal: aviso",
            )
            sent += 1
        if self._recorder is not None:
            # Sin el texto (el del seguro lleva la compañía) ni los destinos.
            self._recorder.record(
                "alert",
                vehicle=self._vehicles[vehicle_id].info.display_name,
                type=alert,
                targets=len(targets),
                sent=sent,
            )

    def diagnostics(self, vehicle_id: str) -> dict[str, Any]:
        """Resumen para el informe de diagnóstico (sin datos personales)."""
        record = self._records.get(vehicle_id)
        current = self.status(vehicle_id)
        return {
            "mantenimiento": None if record is None else record.to_dict(),
            "mantenimiento_estado": (
                None
                if current is None
                else {
                    "revision": current.number,
                    "dias": current.days_left,
                    "km": current.km_left,
                    "nivel": current.level,
                }
            ),
            "testigos_avisados": sorted(self._active.get(vehicle_id, ())),
            "itv": self._itv[vehicle_id].to_dict() if vehicle_id in self._itv else None,
            # Del seguro, sin compañía, póliza ni teléfonos.
            "seguro": (
                {
                    "tipo": self._insurance[vehicle_id].kind,
                    "renovacion": self._insurance[vehicle_id].renewal_date.isoformat(),
                    "dias_desistimiento": self._insurance[vehicle_id].notice_days,
                }
                if vehicle_id in self._insurance
                else None
            ),
        }

    def config_summary(self) -> dict[str, Any]:
        """Configuración de avisos de cada coche, sin los nombres de los móviles."""
        return {
            self._vehicles[vehicle_id].info.display_name: {
                # Nº de destinos de cada aviso (sin nombres) y plazos cambiados.
                "destinos": {
                    notice: len(targets) for notice, targets in route.targets.items() if targets
                },
                "plazos": dict(route.thresholds),
            }
            for vehicle_id, route in self._routes.items()
        }
