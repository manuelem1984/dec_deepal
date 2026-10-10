"""Avisos al móvil y ficha de mantenimiento de cada coche.

Un :class:`AlertManager` por cuenta. Hace dos cosas:

1. **Avisos.** Escucha cada lectura de cada coche y, según lo que el usuario
   haya activado en Configurar → Avisos, envía una notificación a las apps de
   Home Assistant elegidas (y, si quiere, también al panel de notificaciones).
   Qué se avisa y con qué texto: ``alert_rules.py``. El título es siempre
   ``DEC Deepal <nombre del coche>``. Ningún aviso es crítico.
2. **Mantenimiento.** Guarda la ficha de cada coche (última revisión,
   intervalo, historial) y calcula cuánto falta (``maintenance.py``).
3. **ITV y seguro.** Lo mismo con sus fichas (``documents.py``).

Dónde se guarda
---------------
En un almacén propio (``.storage/dec_deepal.<id de la cuenta>``), no en las
opciones: registrar una revisión o apuntar un aviso ya enviado no debe
recargar la integración. Entra en las copias de seguridad de Home Assistant.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime
from typing import Any, Final

from homeassistant.components import persistent_notification
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util

from . import documents as doc
from . import maintenance as mt
from .alert_rules import (
    ALERT_CHARGE_FINISHED,
    ALERT_CHARGE_INTERRUPTED,
    ALERT_CHARGE_STARTED,
    ALERT_INSURANCE,
    ALERT_ITV,
    ALERT_MAINTENANCE,
    PROBLEM_SIGNALS,
    WATCHED_SIGNALS,
    charge_event,
    charge_text,
    enabled_types,
    insurance_text,
    itv_text,
    maintenance_text,
    new_problems,
    problem_text,
)
from .const import (
    DEFAULT_ALERT_PERSISTENT,
    DOMAIN,
    NAME,
    OPT_ALERT_KNOWN,
    OPT_ALERT_PERSISTENT,
    OPT_ALERT_TARGETS,
    OPT_ALERT_TYPES,
    OPT_ALERTS,
)
from .runtime import VehicleContext
from .telemetry import signals as s

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION: Final = 1
#: Los avisos de mantenimiento solo salen a estas horas (hora local).
QUIET_BEFORE_HOUR: Final = 8
QUIET_FROM_HOUR: Final = 22
#: Revisión diaria del mantenimiento (y, a medianoche, de los días que quedan).
DAILY_CHECK_HOURS: Final = (0, 10)


def storage_key(entry_id: str) -> str:
    """Nombre del almacén de una cuenta."""
    return f"{DOMAIN}.{entry_id}"


class AlertManager:
    """Avisos y mantenimiento de los coches de una cuenta."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        options: dict[str, Any],
        vehicles: dict[str, VehicleContext],
        rules: doc.CountryRules = doc.DEFAULT_RULES,
    ) -> None:
        self.hass = hass
        self._vehicles = vehicles
        #: Normas del país de la cuenta (ITV, preaviso del seguro).
        self.rules = rules
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, storage_key(entry_id))
        config = options.get(OPT_ALERTS, {})
        self._targets: list[str] = list(config.get(OPT_ALERT_TARGETS, []))
        self._types: set[str] = (
            enabled_types(config.get(OPT_ALERT_TYPES), config.get(OPT_ALERT_KNOWN))
            if config
            else set()
        )
        self._persistent = bool(config.get(OPT_ALERT_PERSISTENT, DEFAULT_ALERT_PERSISTENT))
        self._records: dict[str, mt.MaintenanceRecord] = {}
        self._itv: dict[str, doc.ItvRecord] = {}
        self._insurance: dict[str, doc.InsuranceRecord] = {}
        #: Testigos encendidos y ya avisados, por coche.
        self._active: dict[str, set[str]] = {}
        #: Última lectura de cada coche (solo las señales que se vigilan).
        self._previous: dict[str, dict[str, Any]] = {}
        self._odometer: dict[str, float] = {}
        self._names: dict[str, str] = {}
        self._listeners: list[Callable[[], None]] = []
        self._unsubscribe: list[CALLBACK_TYPE] = []

    # ------------------------------------------------------------------
    # Arranque y parada
    # ------------------------------------------------------------------

    async def async_load(self) -> None:
        """Lee lo guardado. Una ficha ilegible se descarta (se avisa en el registro)."""
        data = await self._store.async_load() or {}
        for vehicle_id, raw in data.get("maintenance", {}).items():
            try:
                self._records[vehicle_id] = mt.MaintenanceRecord.from_dict(raw)
            except (KeyError, TypeError, ValueError) as err:
                _LOGGER.warning("Ficha de mantenimiento ilegible (%s): %s", vehicle_id, err)
        for key, target, loader in (
            ("itv", self._itv, doc.ItvRecord.from_dict),
            ("insurance", self._insurance, doc.InsuranceRecord.from_dict),
        ):
            for vehicle_id, raw in data.get(key, {}).items():
                try:
                    target[vehicle_id] = loader(raw)
                except (KeyError, TypeError, ValueError) as err:
                    _LOGGER.warning("Ficha de %s ilegible (%s): %s", key, vehicle_id, err)
        self._active = {
            vehicle_id: set(signals) for vehicle_id, signals in data.get("active", {}).items()
        }
        self._odometer = {
            vehicle_id: float(km) for vehicle_id, km in data.get("odometer", {}).items()
        }
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "entity", [DOMAIN]
        )
        prefix = f"component.{DOMAIN}.entity.binary_sensor."
        self._names = {
            key[len(prefix) : -len(".name")]: text
            for key, text in translations.items()
            if key.startswith(prefix) and key.endswith(".name")
        }

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
        await self._store.async_save(self._data_to_save())

    async def async_remove_storage(self) -> None:
        """Borra el almacén (al quitar la cuenta)."""
        await self._store.async_remove()

    def _save(self) -> None:
        self._store.async_delay_save(self._data_to_save, 2)

    def _data_to_save(self) -> dict[str, Any]:
        return {
            "maintenance": {
                vehicle_id: record.to_dict() for vehicle_id, record in self._records.items()
            },
            "itv": {vehicle_id: record.to_dict() for vehicle_id, record in self._itv.items()},
            "insurance": {
                vehicle_id: record.to_dict() for vehicle_id, record in self._insurance.items()
            },
            "active": {vehicle_id: sorted(signals) for vehicle_id, signals in self._active.items()},
            "odometer": dict(self._odometer),
        }

    # ------------------------------------------------------------------
    # Mantenimiento
    # ------------------------------------------------------------------

    def record(self, vehicle_id: str) -> mt.MaintenanceRecord | None:
        """Ficha de mantenimiento del coche (``None`` = sin configurar)."""
        return self._records.get(vehicle_id)

    def odometer(self, vehicle_id: str) -> float | None:
        """Último cuentakilómetros conocido (aunque el coche esté dormido)."""
        return self._odometer.get(vehicle_id)

    def status(self, vehicle_id: str) -> mt.MaintenanceStatus | None:
        """Cuánto falta para la próxima revisión (``None`` = sin configurar)."""
        record = self._records.get(vehicle_id)
        if record is None:
            return None
        return mt.status(record, dt_util.now().date(), self.odometer(vehicle_id))

    def operations(self, vehicle_id: str) -> list[str]:
        """Operaciones de la próxima revisión, según el plan del modelo."""
        record = self._records.get(vehicle_id)
        vehicle = self._vehicles.get(vehicle_id)
        if record is None or vehicle is None:
            return []
        return vehicle.model.maintenance.operations_for(
            record.services_done + 1, vehicle.trim, self.hass.config.language
        )

    async def async_set_record(
        self, vehicle_id: str, record: mt.MaintenanceRecord | None
    ) -> None:
        """Guarda (o borra, con ``None``) la ficha de un coche.

        Se escribe en disco al momento: activar o desactivar el mantenimiento
        recarga la integración justo después.
        """
        if record is None:
            self._records.pop(vehicle_id, None)
        else:
            self._records[vehicle_id] = record
        self._check_maintenance(vehicle_id)
        await self._store.async_save(self._data_to_save())
        self._notify_listeners()

    async def async_register_service(self, vehicle_id: str, when: date, km: int) -> None:
        """Anota una revisión hecha y pasa a la siguiente."""
        mt.register_service(self._records[vehicle_id], when, km)
        await self._store.async_save(self._data_to_save())
        self._notify_listeners()

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

    # ------------------------------------------------------------------
    # ITV y seguro
    # ------------------------------------------------------------------

    def itv_record(self, vehicle_id: str) -> doc.ItvRecord | None:
        """Ficha de ITV del coche (``None`` = sin configurar)."""
        return self._itv.get(vehicle_id)

    def itv_status(self, vehicle_id: str) -> doc.DueStatus | None:
        """Cuánto falta para la próxima ITV (``None`` = sin configurar)."""
        record = self._itv.get(vehicle_id)
        if record is None:
            return None
        return doc.itv_status(record, dt_util.now().date(), self.rules)

    def insurance_record(self, vehicle_id: str) -> doc.InsuranceRecord | None:
        """Ficha del seguro del coche (``None`` = sin configurar)."""
        return self._insurance.get(vehicle_id)

    def insurance_status(self, vehicle_id: str) -> doc.InsuranceStatus | None:
        """Situación del seguro (``None`` = sin configurar)."""
        record = self._insurance.get(vehicle_id)
        return None if record is None else doc.insurance_status(record, dt_util.now().date())

    async def async_set_itv(self, vehicle_id: str, record: doc.ItvRecord | None) -> None:
        """Guarda (o borra, con ``None``) la ficha de ITV de un coche."""
        if record is None:
            self._itv.pop(vehicle_id, None)
        else:
            self._itv[vehicle_id] = record
        self._check_documents(vehicle_id)
        await self._store.async_save(self._data_to_save())
        self._notify_listeners()

    async def async_register_itv(self, vehicle_id: str, when: date) -> None:
        """Anota una ITV pasada."""
        doc.register_itv(self._itv[vehicle_id], when)
        await self._store.async_save(self._data_to_save())
        self._notify_listeners()

    async def async_set_insurance(
        self, vehicle_id: str, record: doc.InsuranceRecord | None
    ) -> None:
        """Guarda (o borra, con ``None``) la ficha del seguro de un coche."""
        if record is None:
            self._insurance.pop(vehicle_id, None)
        else:
            self._insurance[vehicle_id] = record
        self._check_documents(vehicle_id)
        await self._store.async_save(self._data_to_save())
        self._notify_listeners()

    def _check_documents(self, vehicle_id: str) -> None:
        """Avisos de ITV y seguro (de día y una vez cada uno); renueva el seguro si toca."""
        now = dt_util.now()
        today = now.date()
        daytime = QUIET_BEFORE_HOUR <= now.hour < QUIET_FROM_HOUR
        language = self.hass.config.language

        def day(value: date) -> str:
            return value.strftime("%d/%m/%Y")

        itv = self._itv.get(vehicle_id)
        if itv is not None and daytime and ALERT_ITV in self._types:
            current = doc.itv_status(itv, today, self.rules)
            kind = doc.itv_pending_notice(itv, current)
            if kind is not None:
                self._send(
                    vehicle_id,
                    itv_text(
                        kind,
                        days_left=current.days_left,
                        due_date=day(current.due_date),
                        language=language,
                    ),
                )
                itv.notified |= current.steps
                self._save()

        insurance = self._insurance.get(vehicle_id)
        if insurance is None:
            return
        # La renovación se aplica siempre (aunque el aviso esté desactivado o sea de noche).
        if doc.insurance_roll(insurance, today):
            self._save()
            if ALERT_INSURANCE in self._types:
                self._send(
                    vehicle_id,
                    insurance_text(
                        "renewed",
                        days_to_cancel=0,
                        deadline="",
                        renewal=day(insurance.renewal_date),
                        company=insurance.company,
                        language=language,
                    ),
                )
        if not daytime or ALERT_INSURANCE not in self._types:
            return
        status = doc.insurance_status(insurance, today)
        kind = doc.insurance_pending_notice(insurance, status)
        if kind is not None:
            self._send(
                vehicle_id,
                insurance_text(
                    kind,
                    days_to_cancel=status.days_to_cancel,
                    deadline=day(status.cancel_deadline),
                    renewal=day(status.renewal_date),
                    company=insurance.company,
                    language=language,
                ),
            )
            insurance.notified |= status.steps
            self._save()

    def _check_maintenance(self, vehicle_id: str) -> None:
        """Envía el aviso de mantenimiento que toque (de día y una sola vez)."""
        record = self._records.get(vehicle_id)
        if record is None or ALERT_MAINTENANCE not in self._types:
            return
        now = dt_util.now()
        if not QUIET_BEFORE_HOUR <= now.hour < QUIET_FROM_HOUR:
            return
        current = mt.status(record, now.date(), self.odometer(vehicle_id))
        kind = mt.pending_notice(record, current)
        if kind is None:
            return
        language = self.hass.config.language
        self._send(
            vehicle_id,
            maintenance_text(
                kind,
                number=current.number,
                days_left=current.days_left,
                km_left=current.km_left,
                due_date=current.due_date.strftime("%d/%m/%Y"),
                due_km=current.due_km,
                language=language,
            ),
        )
        mt.mark_notified(record, current)
        self._save()

    # ------------------------------------------------------------------
    # Avisos por cambios del coche
    # ------------------------------------------------------------------

    @staticmethod
    def _snapshot(vehicle: VehicleContext) -> dict[str, Any]:
        data = vehicle.coordinator.data
        return {} if data is None else {signal: data.get(signal) for signal in WATCHED_SIGNALS}

    @callback
    def _on_update(self, vehicle_id: str) -> None:
        """Nueva lectura del coche: compara con la anterior y avisa."""
        vehicle = self._vehicles[vehicle_id]
        data = vehicle.coordinator.data
        if data is None:
            return
        odometer = data.get(s.ODOMETER_KM)
        if odometer is not None and odometer != self._odometer.get(vehicle_id):
            self._odometer[vehicle_id] = float(odometer)
            if vehicle_id in self._records:
                self._save()

        current = self._snapshot(vehicle)
        previous = self._previous.get(vehicle_id)
        self._previous[vehicle_id] = current
        language = self.hass.config.language

        event = charge_event(previous, current)
        if event in (ALERT_CHARGE_STARTED, ALERT_CHARGE_INTERRUPTED, ALERT_CHARGE_FINISHED):
            if event in self._types:
                self._send(vehicle_id, charge_text(event, current.get(s.BATTERY_LEVEL), language))

        active = self._active.setdefault(vehicle_id, set())
        before = set(active)
        fresh = new_problems(current, active)
        if active != before:
            self._save()
        for alert in dict.fromkeys(PROBLEM_SIGNALS[signal] for signal in fresh):
            if alert not in self._types:
                continue
            names = [
                self._names.get(signal, signal)
                for signal in fresh
                if PROBLEM_SIGNALS[signal] == alert
            ]
            self._send(vehicle_id, problem_text(alert, names, language))

        self._check_maintenance(vehicle_id)
        self._check_documents(vehicle_id)

    # ------------------------------------------------------------------
    # Envío
    # ------------------------------------------------------------------

    def _vehicle_name(self, vehicle_id: str) -> str:
        """Nombre del coche: el que le haya puesto el usuario en Home Assistant."""
        device = dr.async_get(self.hass).async_get_device(identifiers={(DOMAIN, vehicle_id)})
        if device is not None and (device.name_by_user or device.name):
            return device.name_by_user or device.name
        return self._vehicles[vehicle_id].info.display_name

    def _send(self, vehicle_id: str, message: str) -> None:
        """Envía un aviso a los destinos elegidos (sin esperar a que lleguen)."""
        title = f"{NAME} {self._vehicle_name(vehicle_id)}"
        _LOGGER.debug("Aviso: %s — %s", title, message)
        for service in self._targets:
            if not self.hass.services.has_service("notify", service):
                _LOGGER.warning("Aviso no enviado: ya no existe notify.%s", service)
                continue
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "notify", service, {"title": title, "message": message}, blocking=False
                )
            )
        if self._persistent:
            persistent_notification.async_create(self.hass, message, title=title)

    # ------------------------------------------------------------------
    # Diagnóstico
    # ------------------------------------------------------------------

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
        """Configuración de avisos, sin los nombres de los móviles."""
        return {
            "tipos": sorted(self._types),
            "destinos": len(self._targets),
            "panel": self._persistent,
        }
