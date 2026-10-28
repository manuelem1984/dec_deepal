"""Cargadores: lo que ven la tarjeta del cargador, la del coche y el panel (solo lee: no cambia nada)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util

from ..telemetry import signals as s
from .const import (
    DEFAULT_LOSS,
    FULL_EVERY_CHOICES,
    LIMIT_CHOICES,
    LOCK_FULL_CHOICES,
    READ_CHOICES,
    RELOCK_CHOICES,
    REMIND_CHOICES,
    ROLE_DOMAINS,
    ROLE_LOCK,
    UNLOCK_CONFIRM,
)
from .config import _clean_car
from .estimate import estimate_minutes
from .util import _iso, _when


class StatusMixin:
    """Lo que ven la tarjeta del cargador, la del coche y el panel (solo lee: no cambia nada).

    Es una parte de :class:`~.manager.ChargerManager` (se juntan por herencia):
    usa sus atributos y los métodos de las demás partes a través de ``self``.
    """

    def status(self, charger_id: str, user: Any = None) -> dict[str, Any]:
        """Estado de un cargador para la tarjeta (y la ventana de carga del coche)."""
        charger = self.chargers[charger_id]
        session = self._sessions.get(charger_id)
        if session is not None:
            # Los kWh hasta este momento, sobre una copia: leer el estado no
            # cambia la carga apuntada ni la guarda (lo hacen los cambios del
            # cargador, en _on_state).
            session = dict(session)
            self._track_energy(charger, session, save=False)
        price = self.price(charger)
        power = self.power_w(charger)
        locked = self.locked(charger)
        current = None
        if session is not None:
            vehicle_id = session.get("vehicle_id")
            energy = round(float(session.get("energy") or 0.0), 2)
            level = self._level(charger, session)
            estimated = self._is_estimated(session)
            minutes = (
                estimate_minutes(level, power, charger["loss"], self._capacity(vehicle_id))
                if estimated and self.charging(charger)
                else None
            )
            target = self.target(vehicle_id, session)
            to_target = (
                estimate_minutes(level, power, charger["loss"], self._capacity(vehicle_id), target)
                if target < 100 and self.charging(charger) and level is not None and level < target
                else None
            )
            current = {
                "since": session.get("plugged_at"),
                "charging_since": session.get("charging_since"),
                "finished_at": session.get("finished_at"),
                "vehicle_id": vehicle_id,
                "vehicle": self._name(vehicle_id) or None,
                "device_id": self._device_id(vehicle_id),
                "assigned": session.get("assigned"),
                "waiting": vehicle_id is None and locked is True and charger["unlock"] == UNLOCK_CONFIRM,
                "energy": energy,
                "battery_energy": round(energy * (1 - charger["loss"] / 100), 2),
                "cost": None if price is None else round(energy * price, 2),
                "soc_start": session.get("soc_start"),
                "level": None if level is None else round(level, 1),
                "estimated": estimated,
                "minutes_left": None if minutes is None else round(minutes),
                # Cuánto ha durado (hasta que terminó, o hasta ahora) y cuándo se bloquea solo.
                "energy_source": session.get("energy_source"),
                "no_coverage": bool(session.get("no_coverage")),
                "last_report": _iso(report) if isinstance(report := self._car_data(vehicle_id).get(s.REPORT_TIME), datetime) else None,
                "duration": self._minutes_between(session.get("charging_since") or session.get("plugged_at"), session.get("finished_at")),
                "lock_at": session.get("lock_at"),
                # Minutos de equilibrado que se suman al final (Ajustes de la cuenta del coche).
                "balance": self._balance(vehicle_id),
                # Límite de carga: a qué % se para (None = no se para), cuánto falta y si ya paró.
                "target": target if target < 100 else None,
                "minutes_to_target": None if to_target is None else round(to_target),
                "limit_hit": bool(session.get("limit_hit")),
                "limit_locked": bool(session.get("limit_locked")),
            }
        history = self._history.get(charger_id) or []
        month = dt_util.now().strftime("%Y-%m")
        this_month = [
            item
            for item in history
            if (start := _when(item.get("start"))) is not None and dt_util.as_local(start).strftime("%Y-%m") == month
        ]
        by_vehicle: dict[str, int] = {}
        for item in this_month:
            name = self._name(item.get("vehicle_id")) or "?"
            by_vehicle[name] = by_vehicle.get(name, 0) + 1
        last = history[-1] if history else None
        return {
            "id": charger_id,
            "name": charger["name"],
            "plugged": self.plugged(charger),
            "charging": self.charging(charger),
            "locked": locked,
            "has_lock": bool(charger["entities"].get(ROLE_LOCK)),
            "power": power,
            "unlock": charger["unlock"],
            "coverage": charger["coverage"],
            "loss": charger["loss"],
            "price": price,
            "vehicles": [
                {"id": vehicle_id, "name": self._name(vehicle_id), "device_id": self._device_id(vehicle_id)}
                for vehicle_id in self._candidates(charger)
            ],
            "session": current,
            "last": None
            if last is None
            else {
                **{key: last.get(key) for key in ("start", "end", "energy", "cost", "soc_start", "soc_end", "estimated")},
                "vehicle": self._name(last.get("vehicle_id")) or None,
            },
            "month": {
                "count": len(this_month),
                "energy": round(sum(float(item.get("energy") or 0) for item in this_month), 1),
                "cost": round(sum(float(item.get("cost") or 0) for item in this_month), 2) if price is not None else None,
                "by_vehicle": by_vehicle,
            },
            "history": [
                {
                    **{key: item.get(key) for key in ("start", "end", "energy", "cost", "soc_start", "soc_end", "estimated")},
                    "vehicle": self._name(item.get("vehicle_id")) or None,
                }
                for item in reversed(history[-20:])
            ],
            "can_control": self.can_control(charger_id, user),
        }

    def _minutes_between(self, start: Any, end: Any) -> int | None:
        begin = _when(start)
        if begin is None:
            return None
        return max(0, round(((_when(end) or self._clock()) - begin).total_seconds() / 60))

    def estimates(self) -> dict[str, dict[str, Any]]:
        """% estimado de cada coche sin cobertura, por dispositivo (tarjeta del coche).

        Mientras carga (o sigue enchufado) y, después, el de la última carga
        hasta que el coche vuelva a informar.
        """
        result: dict[str, dict[str, Any]] = {}
        for charger_id, charger in self.chargers.items():
            session = self._sessions.get(charger_id)
            if session is not None and session.get("vehicle_id") and self._is_estimated(session):
                level = self._level(charger, session)
                state = "charging" if self.charging(charger) else "finished" if session.get("finished_at") else "plugged"
                entry = {
                    "level": level,
                    "energy": round(float(session.get("energy") or 0), 1),
                    "state": state,
                    "no_coverage": bool(session.get("no_coverage")),
                }
                vehicle_id = session["vehicle_id"]
            else:
                last = (self._history.get(charger_id) or [None])[-1]
                if not last or not last.get("estimated") or not last.get("vehicle_id") or last.get("soc_end") is None:
                    continue
                vehicle_id = last["vehicle_id"]
                if self._reported_since(vehicle_id, _when(last.get("end"))):
                    continue
                entry = {"level": last["soc_end"], "energy": last.get("energy"), "state": "unplugged"}
            device_id = self._device_id(vehicle_id)
            if device_id and entry["level"] is not None:
                result[device_id] = {**entry, "level": round(float(entry["level"]), 1), "charger": charger["name"]}
        return result

    def cars(self, user: Any = None) -> dict[str, dict[str, Any]]:
        """Límite de carga de cada coche con cargador, por dispositivo (tarjeta del coche)."""
        result: dict[str, dict[str, Any]] = {}
        for vehicle_id in self._linked():
            device_id = self._device_id(vehicle_id)
            if not device_id:
                continue
            car = self._cars.get(vehicle_id) or _clean_car({})
            result[device_id] = {
                "vehicle_id": vehicle_id,
                "limit": car["limit"],
                "once_full": car["once_full"],
                "incomplete": car["incomplete"],
                "target": self.target(vehicle_id),
                "can_control": self.can_control_vehicle(vehicle_id, user),
            }
        return result

    def statuses(self, user: Any = None) -> dict[str, Any]:
        """Todos los cargadores (lo que recibe la suscripción de la tarjeta)."""
        return {
            "enabled": self.enabled,
            "show_estimate": self.show_estimate,
            "chargers": [self.status(charger_id, user) for charger_id in self.chargers] if self.enabled else [],
            "estimates": self.estimates() if self.enabled and self.show_estimate else {},
            "limit": {**self.limit, "choices": list(LIMIT_CHOICES)} if self.enabled else {"enabled": False},
            "cars": self.cars(user) if self.enabled and self.limit["enabled"] else {},
        }

    def panel_config(self) -> dict[str, Any]:
        """Configuración para el panel (Ajustes → Cargadores)."""
        return {
            "enabled": self.enabled,
            "control": self.control,
            "show_estimate": self.show_estimate,
            "chargers": [
                {
                    **charger,
                    "measured": self.measured(charger["id"]),
                    "plugged": self.plugged(charger),
                    "locked": self.locked(charger),
                    # kWh de la carga en curso sacados de la potencia: el contador no avanza.
                    "energy_source": (self._sessions.get(charger["id"]) or {}).get("energy_source"),
                }
                for charger in self.chargers.values()
            ],
            "roles": {role: list(domains) for role, domains in ROLE_DOMAINS.items()},
            "remind_choices": list(REMIND_CHOICES),
            "read_choices": list(READ_CHOICES),
            "relock_choices": list(RELOCK_CHOICES),
            "lock_full_choices": list(LOCK_FULL_CHOICES),
            "default_loss": DEFAULT_LOSS,
            "limit": {
                **self.limit,
                "choices": list(LIMIT_CHOICES),
                "every_choices": list(FULL_EVERY_CHOICES),
                "cars": [
                    {"id": vehicle_id, "limit": (self._cars.get(vehicle_id) or _clean_car({}))["limit"]}
                    for vehicle_id in self._linked()
                ],
            },
        }
