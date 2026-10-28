"""Cargadores: preguntar qué coche es, desbloquear (al confirmar o a mano) y mandar los avisos y sus botones."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import Event, callback

from ..alert_rules import SECTION_CHARGE, TARGET_PANEL, texts
from ..const import DOMAIN, NAME, PANEL_URL_PATH
from .config import ChargerError
from .const import (
    ACTION_AGAIN,
    ACTION_FULL,
    ACTION_NEXT_FULL,
    ACTION_NO,
    ACTION_PREFIX,
    BY_USER,
    NOT_CHARGING_AFTER,
    NOTICE_CONFIRM,
    NOTICE_FINISHED,
    NOTICE_NOT_CHARGING,
    NOTICE_UNLOCKED,
    ROLE_CHARGING,
    ROLE_LOCK,
)
from .util import _iso

_LOGGER = logging.getLogger(__package__)


class NotifyMixin:
    """Preguntar qué coche es, desbloquear (al confirmar o a mano) y mandar los avisos y sus botones.

    Es una parte de :class:`~.manager.ChargerManager` (se juntan por herencia):
    usa sus atributos y los métodos de las demás partes a través de ``self``.
    """

    def _ask(self, charger: Mapping[str, Any], *, reminder: bool = False) -> None:
        charger_id = charger["id"]
        session = self._sessions.get(charger_id)
        if session is None or (session.get("vehicle_id") and not reminder):
            return
        session["asked"] = True
        self._save()
        if charger["notify_confirm"]:
            candidates = self._candidates(charger)
            if reminder:
                text = self._text("charger_reminder", charger=charger["name"])
            elif len(candidates) == 1:
                text = self._text("charger_confirm_one", charger=charger["name"], car=self._name(candidates[0]))
            else:
                text = self._text("charger_confirm_many", charger=charger["name"])
            if len(candidates) == 1:
                actions = [(f"{ACTION_PREFIX}|{charger_id}|{candidates[0]}", self._text("action_unlock"))]
                actions.append((f"{ACTION_PREFIX}|{charger_id}|{ACTION_NO}", self._text("action_no")))
            else:
                actions = [(f"{ACTION_PREFIX}|{charger_id}|{vehicle_id}", self._name(vehicle_id)) for vehicle_id in candidates]
                if not reminder:
                    actions.append((f"{ACTION_PREFIX}|{charger_id}|{ACTION_NO}", self._text("action_no_unlock")))
            self._send(charger, NOTICE_CONFIRM, candidates, text, actions[:3] if len(candidates) <= 2 else actions)

        @callback
        def _remind(_now: Any) -> None:
            current = self.chargers.get(charger_id)
            session = self._sessions.get(charger_id)
            if current is None or session is None or session.get("vehicle_id") or not self.locked(current):
                return
            self._ask(current, reminder=True)

        if not reminder:
            self._timer(charger_id, "remind", charger["remind_minutes"] * 60, _remind)
        self._changed()

    async def async_confirm(self, charger_id: str, vehicle_id: str | None, user: Any = None, *, check: bool = True) -> None:
        """Alguien eligió el coche (o "no desbloquear"). Desbloquea si toca.

        Raises:
            ChargerError: sin permiso (``unauthorized``) o un coche que no es
                de ese cargador (``charger_vehicle``).
            KeyError: el cargador no existe.
        """
        charger = self.chargers[charger_id]
        if check and not self.can_control(charger_id, user):
            raise ChargerError("unauthorized")
        if vehicle_id in (None, ACTION_NO):
            self._cancel(charger_id, "remind")
            self._changed()
            return
        if vehicle_id == ACTION_AGAIN:
            await self._set_locked(charger, False)
            self._changed()
            return
        if vehicle_id == ACTION_FULL:
            # Parada por el límite: esta carga sigue hasta el 100 %.
            if (session := self._sessions.get(charger_id)) is not None:
                session["full"] = True
                session.pop("limit_hit", None)
                session.pop("limit_locked", None)
                self._save()
            await self._set_locked(charger, False)
            self._changed()
            return
        if vehicle_id.startswith(ACTION_NEXT_FULL):
            car_id = vehicle_id.removeprefix(ACTION_NEXT_FULL)
            if car_id not in charger["vehicles"]:
                raise ChargerError("charger_vehicle")
            await self.async_set_car_limit(car_id, user, once_full=True, check=False)
            return
        if vehicle_id not in charger["vehicles"]:
            raise ChargerError("charger_vehicle")
        if (session := self._sessions.get(charger_id)) is not None:
            self._assign(charger, vehicle_id, BY_USER)
            session["asked"] = True
        self._cancel(charger_id, "wait")
        self._cancel(charger_id, "remind")
        if self.locked(charger):
            await self._unlock_for(charger, vehicle_id)
        self._changed()

    async def async_set_lock(self, charger_id: str, locked: bool, user: Any) -> None:
        """Bloquear o desbloquear a mano (tarjeta)."""
        charger = self.chargers[charger_id]
        if not self.can_control(charger_id, user):
            raise ChargerError("unauthorized")
        if not charger["entities"].get(ROLE_LOCK):
            raise ChargerError("charger_no_lock")
        await self._set_locked(charger, locked)
        if not locked:
            self._cancel(charger_id, "remind")
        self._changed()

    async def _unlock_for(self, charger: Mapping[str, Any], vehicle_id: str, *, by_car: bool = False) -> None:
        if not await self._set_locked(charger, False):
            return
        charger_id = charger["id"]
        if (session := self._sessions.get(charger_id)) is not None:
            session["unlocked_at"] = _iso(self._clock())
            self._save()
        if by_car:
            self._send(
                charger,
                NOTICE_UNLOCKED,
                [vehicle_id],
                self._text("charger_unlocked", charger=charger["name"], car=self._name(vehicle_id)),
            )
        if charger["entities"].get(ROLE_CHARGING):

            @callback
            def _not_charging(_now: Any) -> None:
                current = self.chargers.get(charger_id)
                session = self._sessions.get(charger_id)
                if current is None or session is None or session.get("charging_since") or self.charging(current):
                    return
                minutes = int(NOT_CHARGING_AFTER.total_seconds() // 60)
                self._send(
                    current,
                    NOTICE_NOT_CHARGING,
                    [session["vehicle_id"]] if session.get("vehicle_id") else current["vehicles"],
                    self._text("charger_not_charging", charger=current["name"], minutes=minutes),
                )

            self._timer(charger_id, "not_charging", NOT_CHARGING_AFTER.total_seconds(), _not_charging)
        self._changed()

    def _notify_finished(self, charger: Mapping[str, Any], session: Mapping[str, Any]) -> None:
        self._track_energy(charger, dict(session), save=False)
        energy = float(session.get("energy") or 0.0)
        price = self.price(charger)
        parts = []
        start, end = session.get("soc_start"), self._level(charger, session)
        if start is not None and end is not None:
            approx = "≈ " if self._is_estimated(session) else ""
            parts.append(f"{round(start)} % → {approx}{round(end)} %")
        if energy > 0:
            parts.append(f"+{self._decimal(energy, 1)} kWh")
        if price is not None and energy > 0:
            parts.append(f"{self._decimal(energy * price, 2)} €")
        details = (" · " + " · ".join(parts)) if parts else ""
        vehicles = [session["vehicle_id"]] if session.get("vehicle_id") else charger["vehicles"]
        self._send(charger, NOTICE_FINISHED, vehicles, self._text("charger_finished", charger=charger["name"], details=details))

    def _decimal(self, value: float, digits: int) -> str:
        """Número con la coma decimal del idioma (en inglés, punto)."""
        text = f"{value:.{digits}f}"
        return text if self.hass.config.language.startswith("en") else text.replace(".", ",")

    def _text(self, key: str, **values: Any) -> str:
        return texts(self.hass.config.language)[key].format(**values)

    def _send(
        self,
        charger: Mapping[str, Any],
        notice: str,
        vehicle_ids: Iterable[str],
        message: str,
        actions: list[tuple[str, str]] | None = None,
    ) -> None:
        """Manda un aviso del cargador a los destinos de esos coches."""
        vehicle_ids = [vehicle_id for vehicle_id in vehicle_ids if vehicle_id]
        targets: dict[str, None] = {}
        for vehicle_id in vehicle_ids:
            found = self._vehicle(vehicle_id)
            if found is None:
                continue
            route = found[0].runtime_data.alerts.route(vehicle_id)
            for target in route.targets_for(notice) or route.targets_for(SECTION_CHARGE):
                targets[target] = None
        title = f"{NAME} {self._name(vehicle_ids[0])}" if len(vehicle_ids) == 1 else f"{NAME} · {charger['name']}"
        data: dict[str, Any] = {"tag": f"{DOMAIN}_charger_{charger['id']}"}
        if notice == NOTICE_CONFIRM:
            # Tocar la notificación abre el panel en la ventana de elegir el coche
            # (en el iPhone, los botones solo salen al mantenerla pulsada).
            data["url"] = data["clickAction"] = f"/{PANEL_URL_PATH}?elegir={charger['id']}"
        if actions:
            data["actions"] = [{"action": action, "title": label} for action, label in actions]
        for service in targets:
            if service == TARGET_PANEL:
                persistent_notification.async_create(
                    self.hass, message, title=title, notification_id=f"{DOMAIN}_charger_{charger['id']}"
                )
                continue
            if not self.hass.services.has_service("notify", service):
                continue
            payload: dict[str, Any] = {"title": title, "message": message}
            if service.startswith("mobile_app_"):
                payload["data"] = data
            self.hass.async_create_task(
                self.hass.services.async_call("notify", service, payload, blocking=False),
                "dec_deepal: aviso del cargador",
            )
        _LOGGER.debug("Aviso del cargador %s (%s): %s", charger["name"], notice, message)

    @callback
    def _on_action(self, event: Event) -> None:
        """Botón de una notificación: ``DEC_DEEPAL_CHARGER|<cargador>|<coche, -, again, full o nextfull:coche>``."""
        action = str(event.data.get("action") or "")
        if not action.startswith(f"{ACTION_PREFIX}|"):
            return
        try:
            _prefix, charger_id, choice = action.split("|", 2)
        except ValueError:
            return
        if charger_id not in self.chargers:
            return
        user_id = event.context.user_id

        async def _run() -> None:
            user = await self.hass.auth.async_get_user(user_id) if user_id else None
            try:
                # Sin usuario conocido: el botón solo lo tiene quien recibió el aviso.
                await self.async_confirm(charger_id, choice, user, check=user is not None)
            except (ChargerError, KeyError) as err:
                _LOGGER.warning("Botón del cargador no atendido (%s): %s", charger_id, err)

        self.hass.async_create_task(_run(), "dec_deepal: botón de la notificación")
