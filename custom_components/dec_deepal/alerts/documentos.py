"""Avisos: las fichas de ITV y seguro de cada coche y sus avisos."""

from __future__ import annotations

from datetime import date

from homeassistant.util import dt as dt_util

from .. import documents as doc
from ..alert_rules import (
    ALERT_INSURANCE,
    ALERT_ITV,
    GROUP_INSURANCE,
    GROUP_ITV,
    format_date,
    insurance_text,
    itv_text,
)
from .const import QUIET_BEFORE_HOUR, QUIET_FROM_HOUR


class DocumentsMixin:
    """Las fichas de ITV y seguro de cada coche y sus avisos.

    Es una parte de :class:`~.manager.AlertManager` (se juntan por herencia):
    usa sus atributos y los métodos de las demás partes a través de ``self``.
    """

    def itv_record(self, vehicle_id: str) -> doc.ItvRecord | None:
        """Ficha de ITV del coche (``None`` = sin configurar)."""
        return self._itv.get(vehicle_id)

    def itv_status(self, vehicle_id: str) -> doc.DueStatus | None:
        """Cuánto falta para la próxima ITV (``None`` = sin configurar)."""
        record = self._itv.get(vehicle_id)
        if record is None:
            return None
        return self._itv_status(vehicle_id, record, dt_util.now().date())

    def _itv_status(self, vehicle_id: str, record: doc.ItvRecord, today: date) -> doc.DueStatus:
        return doc.itv_status(
            record, today, self.rules, self._routes[vehicle_id].steps(GROUP_ITV, "t")
        )

    def _insurance_status(
        self, vehicle_id: str, record: doc.InsuranceRecord, today: date
    ) -> doc.InsuranceStatus:
        route = self._routes[vehicle_id]
        return doc.insurance_status(
            record, today, route.steps(GROUP_INSURANCE, "c"), route.steps(GROUP_INSURANCE, "r")
        )

    def insurance_record(self, vehicle_id: str) -> doc.InsuranceRecord | None:
        """Ficha del seguro del coche (``None`` = sin configurar)."""
        return self._insurance.get(vehicle_id)

    def insurance_status(self, vehicle_id: str) -> doc.InsuranceStatus | None:
        """Situación del seguro (``None`` = sin configurar)."""
        record = self._insurance.get(vehicle_id)
        if record is None:
            return None
        return self._insurance_status(vehicle_id, record, dt_util.now().date())

    async def async_set_itv(self, vehicle_id: str, record: doc.ItvRecord | None) -> None:
        """Guarda (o borra, con ``None``) la ficha de ITV de un coche."""
        if record is None:
            self._itv.pop(vehicle_id, None)
        else:
            self._itv[vehicle_id] = record
        self._check_documents(vehicle_id)
        await self._async_save()
        self._notify_listeners()

    async def async_register_itv(self, vehicle_id: str, when: date) -> None:
        """Anota una ITV pasada."""
        doc.register_itv(self._itv[vehicle_id], when)
        await self._async_save()
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
        await self._async_save()
        self._notify_listeners()

    def _check_documents(self, vehicle_id: str) -> None:
        """Avisos de ITV y seguro (de día y una vez cada uno); renueva el seguro si toca."""
        now = dt_util.now()
        today = now.date()
        daytime = QUIET_BEFORE_HOUR <= now.hour < QUIET_FROM_HOUR
        language = self.hass.config.language
        route = self._routes[vehicle_id]

        def day(value: date) -> str:
            return format_date(value, language)

        itv = self._itv.get(vehicle_id)
        if itv is not None and daytime and doc.STEP_OVERDUE not in itv.notified:
            current = self._itv_status(vehicle_id, itv, today)
            fresh, targets = self._fresh(vehicle_id, GROUP_ITV, current.steps, itv.notified)
            if fresh:
                self._send(
                    vehicle_id,
                    ALERT_ITV,
                    itv_text(
                        "overdue" if doc.STEP_OVERDUE in fresh else "remaining",
                        days_left=current.days_left,
                        due_date=day(current.due_date),
                        language=language,
                    ),
                    targets,
                )
                itv.notified |= current.steps
                self._save()

        insurance = self._insurance.get(vehicle_id)
        if insurance is None:
            return
        # La renovación se aplica siempre (aunque no avise a nadie o sea de noche).
        if doc.insurance_roll(insurance, today):
            self._save()
            if renewed := route.targets_for(f"{GROUP_INSURANCE}_renewed"):
                self._send(
                    vehicle_id,
                    ALERT_INSURANCE,
                    insurance_text(
                        "renewed",
                        days_to_cancel=0,
                        deadline="",
                        renewal=day(insurance.renewal_date),
                        company=insurance.company,
                        language=language,
                    ),
                    renewed,
                )
        if not daytime:
            return
        status = self._insurance_status(vehicle_id, insurance, today)
        fresh, targets = self._fresh(vehicle_id, GROUP_INSURANCE, status.steps, insurance.notified)
        if not fresh:
            return
        # Si coinciden varios, manda el más urgente: último día, desistir, renovación.
        if doc.STEP_LAST_DAY in fresh:
            kind = "last_day"
        else:
            kind = "cancel" if any(step.startswith("c") for step in fresh) else "renewal"
        self._send(
            vehicle_id,
            ALERT_INSURANCE,
            insurance_text(
                kind,
                days_to_cancel=status.days_to_renewal if kind == "renewal" else status.days_to_cancel,
                deadline=day(status.cancel_deadline),
                renewal=day(status.renewal_date),
                company=insurance.company,
                language=language,
            ),
            targets,
        )
        insurance.notified |= status.steps
        self._save()
