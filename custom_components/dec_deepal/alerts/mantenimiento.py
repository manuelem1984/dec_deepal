"""Avisos: la ficha de mantenimiento de cada coche y sus avisos."""

from __future__ import annotations

from datetime import date

from homeassistant.util import dt as dt_util

from .. import maintenance as mt
from ..alert_rules import (
    ALERT_MAINTENANCE,
    GROUP_MAINTENANCE,
    format_date,
    maintenance_text,
)
from .const import QUIET_BEFORE_HOUR, QUIET_FROM_HOUR


class MaintenanceMixin:
    """La ficha de mantenimiento de cada coche y sus avisos.

    Es una parte de :class:`~.manager.AlertManager` (se juntan por herencia):
    usa sus atributos y los métodos de las demás partes a través de ``self``.
    """

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
        return self._maintenance_status(vehicle_id, record, dt_util.now().date())

    def _maintenance_status(
        self, vehicle_id: str, record: mt.MaintenanceRecord, today: date
    ) -> mt.MaintenanceStatus:
        """Situación de la revisión, con los plazos de aviso de ese coche."""
        route = self._routes[vehicle_id]
        return mt.status(
            record,
            today,
            self.odometer(vehicle_id),
            route.steps(GROUP_MAINTENANCE, "t"),
            route.steps(GROUP_MAINTENANCE, "k"),
        )

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
        await self._async_save()
        self._notify_listeners()

    async def async_register_service(self, vehicle_id: str, when: date, km: int) -> None:
        """Anota una revisión hecha y pasa a la siguiente."""
        mt.register_service(self._records[vehicle_id], when, km)
        await self._async_save()
        self._notify_listeners()

    def _check_maintenance(self, vehicle_id: str) -> None:
        """Envía el aviso de mantenimiento que toque (de día y una sola vez)."""
        record = self._records.get(vehicle_id)
        # Tras el aviso de "vencido" ya no hay más hasta registrar la revisión.
        if record is None or mt.STEP_OVERDUE in record.notified:
            return
        now = dt_util.now()
        if not QUIET_BEFORE_HOUR <= now.hour < QUIET_FROM_HOUR:
            return
        current = self._maintenance_status(vehicle_id, record, now.date())
        fresh, targets = self._fresh(vehicle_id, GROUP_MAINTENANCE, current.steps, record.notified)
        if not fresh:
            return
        language = self.hass.config.language
        self._send(
            vehicle_id,
            ALERT_MAINTENANCE,
            maintenance_text(
                "overdue" if mt.STEP_OVERDUE in fresh else "remaining",
                number=current.number,
                days_left=current.days_left,
                km_left=current.km_left,
                due_date=format_date(current.due_date, language),
                due_km=current.due_km,
                language=language,
            ),
            targets,
        )
        mt.mark_notified(record, current)
        self._save()
