"""Cargadores: los coches: dónde están, cómo se llaman, sus datos y quién puede tocar qué."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta
from typing import Any

from ..const import DOMAIN
from ..runtime import vehicle_device
from ..telemetry import signals as s
from .const import (
    CONTROL_PEOPLE,
)


class CarsMixin:
    """Los coches: dónde están, cómo se llaman, sus datos y quién puede tocar qué.

    Es una parte de :class:`~.manager.ChargerManager` (se juntan por herencia):
    usa sus atributos y los métodos de las demás partes a través de ``self``.
    """

    def _entries(self) -> list[Any]:
        return [
            entry
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if getattr(getattr(entry, "runtime_data", None), "alerts", None) is not None
        ]

    def _vehicle(self, vehicle_id: str) -> tuple[Any, Any] | None:
        for entry in self._entries():
            if vehicle := entry.runtime_data.vehicles.get(vehicle_id):
                return entry, vehicle
        return None

    def _vehicle_ids(self) -> list[str]:
        return [vehicle_id for entry in self._entries() for vehicle_id in entry.runtime_data.vehicles]

    def _candidates(self, charger: Mapping[str, Any]) -> list[str]:
        """Coches del cargador que están cargados en Home Assistant."""
        return [vehicle_id for vehicle_id in charger["vehicles"] if self._vehicle(vehicle_id)]

    def _name(self, vehicle_id: str | None) -> str:
        found = self._vehicle(vehicle_id) if vehicle_id else None
        if found is None:
            return ""
        entry, vehicle = found
        device = vehicle_device(self.hass, entry.entry_id, vehicle_id)
        if device is not None and (device.name_by_user or device.name):
            return device.name_by_user or device.name
        return vehicle.info.display_name

    def _device_id(self, vehicle_id: str | None) -> str | None:
        found = self._vehicle(vehicle_id) if vehicle_id else None
        if found is None:
            return None
        device = vehicle_device(self.hass, found[0].entry_id, vehicle_id)
        return device.id if device else None

    def _car_data(self, vehicle_id: str | None) -> Mapping[str, Any]:
        found = self._vehicle(vehicle_id) if vehicle_id else None
        return (found[1].coordinator.data or {}) if found else {}

    def _capacity(self, vehicle_id: str | None) -> float | None:
        found = self._vehicle(vehicle_id) if vehicle_id else None
        if found is None:
            return None
        vehicle = found[1]
        trim = vehicle.model.trims.get(vehicle.trim or "")
        return getattr(trim, "battery_kwh", None)

    def _balance(self, vehicle_id: str | None) -> int:
        found = self._vehicle(vehicle_id) if vehicle_id else None
        return int(getattr(found[0].runtime_data, "charge_balance_minutes", 0) or 0) if found else 0

    def _reported_since(self, vehicle_id: str, since: datetime | None) -> bool:
        """¿Ha informado el coche después de ``since``?"""
        report = self._car_data(vehicle_id).get(s.REPORT_TIME)
        return isinstance(report, datetime) and since is not None and report >= since - timedelta(minutes=2)

    def _people_users(self, vehicle_ids: Iterable[str]) -> set[str]:
        """Usuarios de Home Assistant de las personas de esos coches."""
        users: set[str] = set()
        for vehicle_id in vehicle_ids:
            found = self._vehicle(vehicle_id)
            if found is None:
                continue
            for person_id in found[0].runtime_data.alerts.people(vehicle_id):
                state = self.hass.states.get(person_id)
                if state is not None and state.attributes.get("user_id"):
                    users.add(state.attributes["user_id"])
        return users

    def can_control_vehicle(self, vehicle_id: str, user: Any) -> bool:
        """¿Puede este usuario cambiar el límite de carga de este coche?"""
        if user is None or getattr(user, "is_admin", False):
            return user is not None
        return self.control == CONTROL_PEOPLE and user.id in self._people_users([vehicle_id])

    def can_control(self, charger_id: str, user: Any) -> bool:
        """¿Puede este usuario desbloquear el cargador o elegir el coche?"""
        if user is None or getattr(user, "is_admin", False):
            return user is not None
        if self.control != CONTROL_PEOPLE:
            return False
        charger = self.chargers.get(charger_id)
        return charger is not None and user.id in self._people_users(charger["vehicles"])
