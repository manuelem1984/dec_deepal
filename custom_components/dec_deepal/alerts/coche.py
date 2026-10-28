"""Avisos: los avisos por cambios del coche (carga, testigos, neumáticos, pila del mando) y las cargas apuntadas."""

from __future__ import annotations

from typing import Any

from homeassistant.core import callback
from homeassistant.util import dt as dt_util

from .. import charging
from ..alert_rules import (
    ALERT_CHARGE_FINISHED,
    ALERT_CHARGE_INTERRUPTED,
    ALERT_CHARGE_STARTED,
    PROBLEM_SIGNALS,
    WATCHED_SIGNALS,
    charge_event,
    charge_text,
    new_problems,
    problem_text,
)
from ..runtime import VehicleContext
from ..telemetry import signals as s


class CarMixin:
    """Los avisos por cambios del coche (carga, testigos, neumáticos, pila del mando) y las cargas apuntadas.

    Es una parte de :class:`~.manager.AlertManager` (se juntan por herencia):
    usa sus atributos y los métodos de las demás partes a través de ``self``.
    """

    def _track_charge(self, vehicle_id: str) -> None:
        """Apunta el principio y el final de cada carga (ver ``charging.py``)."""
        vehicle = self._vehicles.get(vehicle_id)
        data = vehicle.coordinator.data if vehicle is not None else None
        if data is None:
            return
        state, changed = charging.update(
            self._charge.get(vehicle_id),
            data.get(s.CHARGING),
            data.get(s.BATTERY_LEVEL),
            data.get(s.RANGE_KM),
            dt_util.now(),
        )
        if changed:
            self._charge[vehicle_id] = state
            self._save()

    def charge_info(self, vehicle_id: str) -> dict[str, Any]:
        """Carga en curso y última carga, para el sensor "Cargando".

        Se pone al día aquí mismo: así el sensor enseña la carga recién
        empezada aunque se actualice antes de que este gestor vea la lectura.
        """
        self._track_charge(vehicle_id)
        return charging.attributes(self._charge.get(vehicle_id))

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
        self._track_charge(vehicle_id)
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
        if event in (ALERT_CHARGE_STARTED, ALERT_CHARGE_INTERRUPTED, ALERT_CHARGE_FINISHED) and self._wants(vehicle_id, event):
            self._send(vehicle_id, event, charge_text(event, current.get(s.BATTERY_LEVEL), language))

        active = self._active.setdefault(vehicle_id, set())
        before = set(active)
        fresh = new_problems(current, active, vehicle.model.silent_warnings)
        if active != before:
            self._save()
        for alert in dict.fromkeys(PROBLEM_SIGNALS[signal] for signal in fresh):
            if not self._wants(vehicle_id, alert):
                continue
            names = [
                self._names.get(signal, signal)
                for signal in fresh
                if PROBLEM_SIGNALS[signal] == alert
            ]
            self._send(vehicle_id, alert, problem_text(alert, names, language))

        self._check_maintenance(vehicle_id)
        self._check_documents(vehicle_id)
