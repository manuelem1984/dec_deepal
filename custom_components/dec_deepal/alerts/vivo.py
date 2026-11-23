"""Avisos: «Carga en vivo» y «Coche abierto o sin bloquear» (2.6.0b17).

**Carga en vivo** (``charge_live``): mientras carga, una notificación en el
móvil que se **actualiza** (misma ``tag``) con el % y la hora a la que
termina. En Android sale como *Live Update* (barra de progreso y cuenta
atrás); en iPhone, como una notificación que se reemplaza. Al acabar la carga
se quita (``clear_notification``). Solo a los móviles (``notify.mobile_app_*``):
en el panel de notificaciones no tiene sentido. Nunca es crítica.

**Coche abierto o sin bloquear** (``left_open``): con el coche apagado,
si lleva N minutos (10 de fábrica, se cambia en el panel) sin bloquear o
con una puerta, ventanilla, el maletero o el capó abiertos, avisa **una
vez** (hasta que se cierre todo). Si el control con PIN está activo, el aviso
trae un botón **Bloquear** (solo bloquear, nunca abrir).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import CALLBACK_TYPE, Event, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from ..alert_rules import (
    ALERT_CHARGE_LIVE,
    ALERT_LEFT_OPEN,
    left_open_text,
    live_charge_text,
    texts,
)
from ..const import DOMAIN
from ..registries.vehicles import FEATURE_PIN_COMMANDS
from ..telemetry import signals as s

_LOGGER = logging.getLogger(__package__)

#: Evento de la app móvil al tocar un botón de una notificación.
EVENT_ACTION = "mobile_app_notification_action"
#: Botón «Bloquear»: ``DEC_DEEPAL_LOCK|<coche>``.
ACTION_LOCK = "DEC_DEEPAL_LOCK"
#: Señales de «abierto» y la clave de su texto.
OPEN_PARTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("left_open_doors", (s.DOOR_FRONT_LEFT, s.DOOR_FRONT_RIGHT, s.DOOR_REAR_LEFT, s.DOOR_REAR_RIGHT)),
    ("left_open_windows", (s.WINDOW_FRONT_LEFT, s.WINDOW_FRONT_RIGHT, s.WINDOW_REAR_LEFT, s.WINDOW_REAR_RIGHT)),
    ("left_open_trunk", (s.TRUNK_OPEN,)),
    ("left_open_hood", (s.HOOD_OPEN,)),
)


def open_parts(values: Any) -> list[str]:
    """Qué está sin cerrar (claves de texto), solo con el coche **apagado**.

    Encendido o sin saberlo, nada: es normal ir con la ventanilla bajada.
    """
    if values.get(s.POWER_ON) is not False:
        return []
    parts = ["left_open_unlocked"] if values.get(s.CENTRAL_LOCKED) is False else []
    parts += [key for key, signals in OPEN_PARTS if any(values.get(signal) is True for signal in signals)]
    return parts


class LiveMixin:
    """Carga en vivo y coche abierto. Parte de :class:`~.manager.AlertManager`."""

    # --- Carga en vivo ---------------------------------------------------------

    def _phone_targets(self, vehicle_id: str, alert: str) -> tuple[str, ...]:
        return tuple(t for t in self._routes[vehicle_id].targets_for(alert) if t.startswith("mobile_app_"))

    def _check_live_charge(self, vehicle_id: str, values: Any) -> None:
        """Pone al día (o quita) la notificación de la carga en curso."""
        targets = self._phone_targets(vehicle_id, ALERT_CHARGE_LIVE)
        live: dict[str, tuple[Any, Any]] = self.__dict__.setdefault("_live", {})
        if not targets:
            live.pop(vehicle_id, None)
            return
        tag = f"{DOMAIN}_charge_live_{vehicle_id}"
        if values.get(s.CHARGING) is not True:
            if live.pop(vehicle_id, None) is not None:
                self._send(vehicle_id, ALERT_CHARGE_LIVE, "clear_notification", targets, data={"tag": tag})
            return
        level = values.get(s.BATTERY_LEVEL)
        remaining = values.get(s.REMAINING_CHARGE_MIN)
        if live.get(vehicle_id) == (level, remaining):
            return  # nada nuevo: no se repite
        live[vehicle_id] = (level, remaining)
        ends = dt_util.now() + timedelta(minutes=remaining) if remaining else None
        data: dict[str, Any] = {
            "tag": tag,
            # Android: Live Update (barra y cuenta atrás); sin sonido al actualizar.
            "live_update": True,
            "alert_once": True,
            "sticky": True,
            "notification_icon": "mdi:ev-station",
        }
        if level is not None:
            data |= {"progress": round(level), "progress_max": 100}
        if ends is not None:
            data |= {"chronometer": True, "when": int(ends.timestamp()), "when_relative": False}
        message = live_charge_text(level, ends, self.hass.config.language)
        self._send(vehicle_id, ALERT_CHARGE_LIVE, message, targets, data=data)

    # --- Coche abierto o sin bloquear ----------------------------------------------

    def _check_left_open(self, vehicle_id: str, values: Any, now: datetime | None = None) -> None:
        """Avisa si el coche lleva un rato apagado y sin cerrar (una vez)."""
        since: dict[str, datetime] = self.__dict__.setdefault("_open_since", {})
        notified: set[str] = self.__dict__.setdefault("_open_notified", set())
        timers: dict[str, CALLBACK_TYPE] = self.__dict__.setdefault("_open_timers", {})
        parts = open_parts(values) if self._wants(vehicle_id, ALERT_LEFT_OPEN) else []
        if not parts:
            since.pop(vehicle_id, None)
            notified.discard(vehicle_id)
            if (cancel := timers.pop(vehicle_id, None)) is not None:
                cancel()
            return
        now = now or dt_util.now()
        start = since.setdefault(vehicle_id, now)
        if vehicle_id in notified:
            return
        wait = timedelta(minutes=self._routes[vehicle_id].threshold(ALERT_LEFT_OPEN))
        if now - start < wait:
            if vehicle_id not in timers:
                # Las lecturas van cada 5 min: se vuelve a mirar justo al cumplirse.
                @callback
                def _again(_now: Any, vehicle_id: str = vehicle_id) -> None:
                    timers.pop(vehicle_id, None)
                    data = self._vehicles[vehicle_id].coordinator.data
                    if data is not None:
                        self._check_left_open(vehicle_id, data)

                timers[vehicle_id] = async_call_later(self.hass, (start + wait - now).total_seconds() + 1, _again)
            return
        notified.add(vehicle_id)
        minutes = max(1, round((now - start).total_seconds() / 60))
        language = self.hass.config.language
        actions = None
        if "left_open_unlocked" in parts and self._can_lock(vehicle_id):
            actions = [{"action": f"{ACTION_LOCK}|{vehicle_id}", "title": texts(language)["action_lock"]}]
        data: dict[str, Any] = {"tag": f"{DOMAIN}_left_open_{vehicle_id}"}
        if actions:
            data["actions"] = actions
        self._send(vehicle_id, ALERT_LEFT_OPEN, left_open_text(parts, minutes, language), data=data)

    def _can_lock(self, vehicle_id: str) -> bool:
        """¿Se puede bloquear desde aquí? (control con PIN activo y PIN guardado)."""
        vehicle = self._vehicles[vehicle_id]
        return vehicle.has(FEATURE_PIN_COMMANDS) and bool(vehicle.runner.commands.control_pin)

    @callback
    def _on_notification_action(self, event: Event) -> None:
        """Botón «Bloquear» de la notificación."""
        action = str(event.data.get("action") or "")
        prefix, _, vehicle_id = action.partition("|")
        if prefix != ACTION_LOCK or vehicle_id not in self._vehicles or not self._can_lock(vehicle_id):
            return
        vehicle = self._vehicles[vehicle_id]
        language = self.hass.config.language

        async def _lock() -> None:
            runner = vehicle.runner
            try:
                await runner.run(
                    "doors",
                    lambda: runner.commands.doors(vehicle_id, unlock=False),
                    optimistic={s.LOCKED_DRIVER: True, s.LOCKED_PASSENGER: True},
                    needs_arming=True,
                )
            except HomeAssistantError as err:
                _LOGGER.warning("%s: no se pudo bloquear desde la notificación: %s", vehicle.info.display_name, err)
                message = texts(language)["lock_failed"].format(error=str(err) or err.translation_key or "")
            else:
                message = texts(language)["lock_done"]
            self._send(vehicle_id, ALERT_LEFT_OPEN, message, data={"tag": f"{DOMAIN}_left_open_{vehicle_id}"})

        self.hass.async_create_task(_lock(), "dec_deepal: bloquear desde la notificación")

    def _stop_live(self) -> None:
        """Cancela las esperas pendientes (al descargar la cuenta)."""
        for cancel in self.__dict__.get("_open_timers", {}).values():
            cancel()
        self.__dict__.get("_open_timers", {}).clear()
