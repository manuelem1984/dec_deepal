"""Cargadores: cada carga: empieza al enchufar, se asigna a un coche, termina al desenchufar; bloquear al terminar o al desenchufar y leer el coche mientras carga."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import callback

from ..telemetry import signals as s
from .const import (
    ACTION_AGAIN,
    ACTION_PREFIX,
    BY_CAR,
    BY_SINGLE,
    CHARGE_WAIT,
    CHARGE_WAIT_STEP,
    COVERAGE_NO,
    FULL_LEVEL,
    HISTORY_SIZE,
    LIMIT_NEAR,
    LIMIT_READ_MINUTES,
    NOTICE_LOCKED,
    READ_FAILURES,
    ROLE_LOCK,
    UNLOCK_CONFIRM,
    UNLOCK_NONE,
)
from .util import _iso, _when


class SessionMixin:
    """Cada carga: empieza al enchufar, se asigna a un coche, termina al desenchufar; bloquear al terminar o al desenchufar y leer el coche mientras carga.

    Es una parte de :class:`~.manager.ChargerManager` (se juntan por herencia):
    usa sus atributos y los métodos de las demás partes a través de ``self``.
    """

    @callback
    def _sync(self, charger_id: str) -> None:
        """Compara el cargador con la carga apuntada y hace lo que toque."""
        charger = self.chargers[charger_id]
        plugged = self.plugged(charger)
        session = self._sessions.get(charger_id)
        if plugged is None:
            return
        if plugged and session is None:
            self._start(charger)
        elif not plugged and session is not None:
            self._end(charger)
        elif not plugged and session is None:
            self._maybe_relock(charger)
        if plugged and (session := self._sessions.get(charger_id)) is not None:
            charging = self.charging(charger)
            if charging and not session.get("charging_since"):
                session["charging_since"] = _iso(self._clock())
                self._cancel(charger_id, "not_charging")
                self._save()
                self._schedule_read(charger)
                self._check_limit(charger)
            elif charging is False and session.get("charging_since") and not session.get("finished_at"):
                session["finished_at"] = _iso(self._clock())
                self._save()
                # Parada por el límite: ese aviso ya lo ha contado.
                if not (session.get("limit_hit") and self.limit["notify"]):
                    self._notify_finished(charger, session)
                self._schedule_lock_full(charger)
            elif charging and session.get("finished_at"):
                session.pop("finished_at", None)  # vuelve a cargar (p. ej. la compañía reanuda)
                session.pop("lock_at", None)
                self._cancel(charger_id, "lock_full")
                self._save()
                self._schedule_read(charger)
            if self.locked(charger) is False and session.get("unlocked_at") is None:
                session["unlocked_at"] = _iso(self._clock())
                self._cancel(charger_id, "remind")
                self._save()
        self._changed()

    def _start(self, charger: dict[str, Any]) -> None:
        charger_id = charger["id"]
        self._cancel(charger_id, "relock")
        now = self._clock()
        candidates = self._candidates(charger)
        session: dict[str, Any] = {
            "plugged_at": _iso(now),
            "vehicle_id": None,
            "assigned": None,
            "energy_start": self._energy_raw(charger),
            "energy": 0.0,
            "unlocked_at": _iso(now) if self.locked(charger) is False else None,
            "asked": False,
        }
        self._sessions[charger_id] = session
        if len(candidates) == 1 and (charger["unlock"] == UNLOCK_NONE or self.locked(charger) is not True):
            self._assign(charger, candidates[0], BY_SINGLE)
        self._save()
        if charger["unlock"] == UNLOCK_CONFIRM and self.locked(charger):
            if charger["coverage"] == COVERAGE_NO:
                self._ask(charger)
            else:
                self._wait_for_car(charger, now + CHARGE_WAIT)
        elif charger["unlock"] == UNLOCK_NONE and session["vehicle_id"] is None:
            self._wait_for_car(charger, now + CHARGE_WAIT, ask=False)

    def _assign(self, charger: Mapping[str, Any], vehicle_id: str, how: str) -> None:
        session = self._sessions.get(charger["id"])
        if session is None:
            return
        data = self._car_data(vehicle_id)
        session.update(
            vehicle_id=vehicle_id,
            assigned=how,
            soc_start=data.get(s.BATTERY_LEVEL),
            range_start=data.get(s.RANGE_KM),
            odometer=data.get(s.ODOMETER_KM),
        )
        self._save()
        if self.charging(charger):
            self._schedule_read(charger)
            self._check_limit(charger)

    def _car_confirming(self, charger: Mapping[str, Any]) -> str | None:
        """El coche que dice tener la manguera puesta desde que se enchufó."""
        session = self._sessions.get(charger["id"]) or {}
        since = _when(session.get("plugged_at"))
        confirming = [
            vehicle_id
            for vehicle_id in self._candidates(charger)
            if self._reported_since(vehicle_id, since)
            and (self._car_data(vehicle_id).get(s.CHARGER_PLUGGED) or self._car_data(vehicle_id).get(s.CHARGING))
        ]
        return confirming[0] if len(confirming) == 1 else None

    def _wait_for_car(self, charger: Mapping[str, Any], until: datetime, *, ask: bool = True) -> None:
        charger_id = charger["id"]

        @callback
        def _check(_now: Any) -> None:
            session = self._sessions.get(charger_id)
            current = self.chargers.get(charger_id)
            if session is None or current is None or session.get("vehicle_id"):
                return
            if (vehicle_id := self._car_confirming(current)) is not None:
                self._assign(current, vehicle_id, BY_CAR)
                if current["unlock"] == UNLOCK_CONFIRM and self.locked(current):
                    self.hass.async_create_task(self._unlock_for(current, vehicle_id, by_car=True), "dec_deepal: desbloquear el cargador")
                self._changed()
                return
            if self._clock() >= until:
                if ask and current["unlock"] == UNLOCK_CONFIRM and self.locked(current):
                    self._ask(current)
                return
            self._timer(charger_id, "wait", CHARGE_WAIT_STEP, _check)

        self._timer(charger_id, "wait", CHARGE_WAIT_STEP, _check)

    def _end(self, charger: dict[str, Any]) -> None:
        charger_id = charger["id"]
        session = self._sessions.pop(charger_id)
        for name in ("wait", "remind", "not_charging", "lock_full", "read"):
            self._cancel(charger_id, name)
        self._track_energy(charger, session)
        now = self._clock()
        price = self.price(charger)
        energy = round(float(session.get("energy") or 0.0), 2)
        vehicle_id = session.get("vehicle_id")
        record = {
            "start": session.get("plugged_at"),
            "end": _iso(now),
            "charging_since": session.get("charging_since"),
            "finished_at": session.get("finished_at"),
            "vehicle_id": vehicle_id,
            "energy": energy,
            "cost": None if price is None else round(energy * price, 2),
            "soc_start": session.get("soc_start"),
            "soc_end": self._level(charger, session) if vehicle_id else None,
            "estimated": bool(vehicle_id) and not self._reported_since(vehicle_id, _when(session.get("charging_since") or session.get("plugged_at"))),
            "odometer": session.get("odometer"),
            "learned": False,
        }
        if session.get("charging_since") or energy > 0:
            history = self._history.setdefault(charger_id, [])
            history.append(record)
            del history[:-HISTORY_SIZE]
            if vehicle_id:
                self._count_charge(charger, vehicle_id, record["soc_end"])
        self._save()
        if session.get("limit_locked") and charger["unlock"] == UNLOCK_NONE and not charger["relock"]:
            # Bloqueado solo por el límite: se deja como estaba (desbloqueado).
            self.hass.async_create_task(self._set_locked(charger, False), "dec_deepal: desbloquear tras el límite")
        else:
            self._maybe_relock(charger)

    def _schedule_lock_full(self, charger: Mapping[str, Any]) -> None:
        """Carga terminada: bloquear pasados ``lock_full_minutes`` si sigue al 100 % y sin cargar.

        Solo con el coche al 100 % (real o estimado): si la compañía hace una
        pausa programada antes, no se bloquea (cortaría la carga).
        """
        charger_id = charger["id"]
        session = self._sessions.get(charger_id)
        if not charger["lock_full"] or not charger["entities"].get(ROLE_LOCK) or session is None:
            return
        level = self._level(charger, session)
        if level is None or level < FULL_LEVEL or self.locked(charger) is not False:
            return
        minutes = charger["lock_full_minutes"]
        session["lock_at"] = _iso(self._clock() + timedelta(minutes=minutes))
        self._save()

        @callback
        def _lock(_now: Any) -> None:
            current = self.chargers.get(charger_id)
            session = self._sessions.get(charger_id)
            if current is None or session is None or self.charging(current) or self.locked(current) is not False:
                return
            session.pop("lock_at", None)
            self.hass.async_create_task(self._lock_full(current, session.get("vehicle_id"), minutes), "dec_deepal: bloquear al terminar")

        self._timer(charger_id, "lock_full", minutes * 60, _lock)

    async def _lock_full(self, charger: Mapping[str, Any], vehicle_id: str | None, minutes: int) -> None:
        if not await self._set_locked(charger, True):
            return
        if charger["relock_notify"]:
            self._send(
                charger,
                NOTICE_LOCKED,
                [vehicle_id] if vehicle_id else charger["vehicles"],
                self._text("charger_locked_full", charger=charger["name"], minutes=minutes),
                [(f"{ACTION_PREFIX}|{charger['id']}|{ACTION_AGAIN}", self._text("action_unlock_again"))],
            )
        self._changed()

    def _maybe_relock(self, charger: Mapping[str, Any]) -> None:
        """Desbloqueado y sin manguera: se bloquea pasados ``relock_minutes``."""
        charger_id = charger["id"]
        if not charger["relock"] or self.locked(charger) is not False or "relock" in self._timers.get(charger_id, {}):
            return

        @callback
        def _relock(_now: Any) -> None:
            current = self.chargers.get(charger_id)
            if current is None or self.plugged(current) or self.locked(current) is not False:
                return
            self.hass.async_create_task(self._relock(current), "dec_deepal: bloquear al desenchufar")

        self._timer(charger_id, "relock", charger["relock_minutes"] * 60, _relock)

    async def _relock(self, charger: Mapping[str, Any]) -> None:
        if not await self._set_locked(charger, True):
            return
        if charger["relock_notify"]:
            last = (self._history.get(charger["id"]) or [{}])[-1]
            vehicles = [last["vehicle_id"]] if last.get("vehicle_id") else charger["vehicles"]
            self._send(
                charger,
                NOTICE_LOCKED,
                vehicles,
                self._text("charger_locked", charger=charger["name"], minutes=charger["relock_minutes"]),
                [(f"{ACTION_PREFIX}|{charger['id']}|{ACTION_AGAIN}", self._text("action_unlock_again"))],
            )
        self._changed()

    def _schedule_read(self, charger: Mapping[str, Any]) -> None:
        """Mientras carga, despertar y leer el coche cada ``read_interval`` minutos.

        Solo con cobertura (o "no lo sé") y con "Despertar el coche" activado
        en la cuenta. Es lo mismo que el botón Actualizar: con la carga, el
        coche está despierto y su batería de 12 V se recarga. Si falla
        ``READ_FAILURES`` veces seguidas, se da por comprobado que no hay
        cobertura y se deja de intentar en esta carga.
        """
        charger_id = charger["id"]
        session = self._sessions.get(charger_id)
        minutes = charger.get("read_interval") or 0
        if minutes and session is not None and (target := self.target(session.get("vehicle_id"), session)) < 100:
            level = self._level(charger, session)
            if level is not None and target - level <= LIMIT_NEAR:
                minutes = min(minutes, LIMIT_READ_MINUTES)
        if (
            not minutes
            or charger["coverage"] == COVERAGE_NO
            or session is None
            or not session.get("vehicle_id")
            or session.get("no_coverage")
            or "read" in self._timers.get(charger_id, {})
        ):
            return

        @callback
        def _read(_now: Any) -> None:
            current = self.chargers.get(charger_id)
            session = self._sessions.get(charger_id)
            if current is None or session is None or not self.charging(current) or not session.get("vehicle_id"):
                return
            found = self._vehicle(session["vehicle_id"])
            coordinator = getattr(found[1], "coordinator", None) if found else None
            if coordinator is None or not getattr(coordinator, "wake_enabled", False):
                return
            self.hass.async_create_task(self._read_car(current, coordinator), "dec_deepal: leer el coche mientras carga")

        self._timer(charger_id, "read", minutes * 60, _read)

    async def _read_car(self, charger: Mapping[str, Any], coordinator: Any) -> None:
        charger_id = charger["id"]
        result = str(await coordinator.async_wake_and_wait())
        session = self._sessions.get(charger_id)
        if session is None:
            return
        if result in ("informe_nuevo", "no_hace_falta"):
            session["read_failures"] = 0
            session["read_ok"] = _iso(self._clock())
        elif result in ("sin_informe", "fallo"):
            session["read_failures"] = int(session.get("read_failures") or 0) + 1
            if session["read_failures"] >= READ_FAILURES:
                session["no_coverage"] = True
        self._save()
        self._check_limit(charger)
        self._changed()
        self._schedule_read(charger)
