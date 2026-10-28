"""Cargadores: límite de carga por coche (parar la carga bloqueando el cargador) y recordatorio de cargar al 100 %."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.core import callback

from .const import (
    ACTION_FULL,
    ACTION_NEXT_FULL,
    ACTION_NO,
    ACTION_PREFIX,
    DEFAULT_LIMIT,
    FULL_LEVEL,
    LIMIT_CHOICES,
    NOTICE_FULL,
    NOTICE_LIMIT,
    ROLE_LOCK,
)
from .config import ChargerError, _choice, _clean_car, clean_limit
from .util import _iso


class LimitMixin:
    """Límite de carga por coche (parar la carga bloqueando el cargador) y recordatorio de cargar al 100 %.

    Es una parte de :class:`~.manager.ChargerManager` (se juntan por herencia):
    usa sus atributos y los métodos de las demás partes a través de ``self``.
    """

    async def async_set_limit_settings(self, raw: Mapping[str, Any]) -> None:
        """Opciones del límite de carga y del recordatorio del 100 % (lo que no llega, se queda)."""
        await self.async_load()
        self.limit = clean_limit({**self.limit, **raw})
        self._save()
        for charger_id in list(self._sessions):
            self._check_limit(self.chargers[charger_id])
        self._changed()

    async def async_set_car_limit(
        self,
        vehicle_id: str,
        user: Any,
        *,
        limit: int | None = None,
        once_full: bool | None = None,
        check: bool = True,
    ) -> None:
        """Límite de un coche y «Solo esta: 100 %» (tarjeta del coche, panel o notificación).

        Raises:
            ChargerError: sin permiso (``unauthorized``) o un coche que no está
                (``charger_vehicle``).
        """
        await self.async_load()
        if self._vehicle(vehicle_id) is None:
            raise ChargerError("charger_vehicle")
        if check and not self.can_control_vehicle(vehicle_id, user):
            raise ChargerError("unauthorized")
        car = self._car(vehicle_id)
        if limit is not None:
            car["limit"] = _choice(int(limit), LIMIT_CHOICES, car["limit"])
        if once_full is not None:
            car["once_full"] = bool(once_full)
        self._save()
        for charger_id, session in list(self._sessions.items()):
            if session.get("vehicle_id") != vehicle_id:
                continue
            charger = self.chargers[charger_id]
            level = self._level(charger, session)
            if session.get("limit_hit") and (level is None or level < self.target(vehicle_id, session)):
                # Parada por el límite y ahora el objetivo es mayor: sigue cargando.
                session.pop("limit_hit", None)
                if session.pop("limit_locked", None):
                    await self._set_locked(charger, False)
                self._save()
            else:
                self._check_limit(charger)
        self._changed()

    def _prune_cars(self) -> None:
        """Olvida el límite de los coches que ya no están en ningún cargador."""
        linked = {vehicle_id for charger in self.chargers.values() for vehicle_id in charger["vehicles"]}
        for vehicle_id in [vehicle_id for vehicle_id in self._cars if vehicle_id not in linked]:
            del self._cars[vehicle_id]

    def _car(self, vehicle_id: str) -> dict[str, Any]:
        return self._cars.setdefault(vehicle_id, _clean_car({}))

    def target(self, vehicle_id: str | None, session: Mapping[str, Any] | None = None) -> int:
        """% al que se para la carga de este coche (100 = no se para)."""
        if not vehicle_id or not self.limit["enabled"]:
            return 100
        car = self._cars.get(vehicle_id) or {}
        if car.get("once_full") or (session or {}).get("full"):
            return 100
        return int(car.get("limit", DEFAULT_LIMIT))

    def vehicle_for_device(self, device_id: str) -> str | None:
        """El coche de un dispositivo de Home Assistant (la tarjeta habla en dispositivos)."""
        return next((vehicle_id for vehicle_id in self._vehicle_ids() if self._device_id(vehicle_id) == device_id), None)

    def _linked(self) -> list[str]:
        """Coches que tienen algún cargador (los únicos a los que se puede parar la carga)."""
        return [vehicle_id for vehicle_id in dict.fromkeys(v for c in self.chargers.values() for v in c["vehicles"]) if self._vehicle(vehicle_id)]

    def _count_charge(self, charger: Mapping[str, Any], vehicle_id: str, level: float | None) -> None:
        """Cuenta las cargas seguidas sin llegar al 100 % y, cada N, recuerda hacer una completa."""
        if level is None:
            return
        car = self._car(vehicle_id)
        if level >= FULL_LEVEL:
            car["incomplete"] = 0
            car["once_full"] = False
            return
        car["incomplete"] += 1
        if not self.limit["remind"] or car["once_full"] or car["incomplete"] % self.limit["every"]:
            return
        count = car["incomplete"]
        if self.limit["auto"]:
            car["once_full"] = True
            self._send(charger, NOTICE_FULL, [vehicle_id], self._text("charger_full_auto", count=count))
            return
        self._send(
            charger,
            NOTICE_FULL,
            [vehicle_id],
            self._text("charger_full_reminder", count=count),
            [
                (f"{ACTION_PREFIX}|{charger['id']}|{ACTION_NEXT_FULL}{vehicle_id}", self._text("action_next_full")),
                (f"{ACTION_PREFIX}|{charger['id']}|{ACTION_NO}", self._text("action_not_now")),
            ],
        )

    @callback
    def _check_limit(self, charger: Mapping[str, Any]) -> None:
        """Al llegar al límite del coche (real o estimado), se para la carga."""
        session = self._sessions.get(charger["id"])
        if session is None or not self.limit["enabled"] or session.get("limit_hit"):
            return
        vehicle_id = session.get("vehicle_id")
        target = self.target(vehicle_id, session)
        if not vehicle_id or target >= 100 or self.charging(charger) is False:
            return
        level = self._level(charger, session)
        if level is None or level < target:
            return
        session["limit_hit"] = _iso(self._clock())
        self._save()
        self.hass.async_create_task(self._stop_at_limit(charger, vehicle_id, target, level), "dec_deepal: parar en el límite")

    async def _stop_at_limit(self, charger: Mapping[str, Any], vehicle_id: str, target: int, level: float) -> None:
        """Bloquea el cargador (lo único que para la carga) y avisa. Sin bloqueo, solo avisa."""
        locked = False
        if charger["entities"].get(ROLE_LOCK) and self.locked(charger) is not True:
            locked = await self._set_locked(charger, True)
        session = self._sessions.get(charger["id"])
        if session is not None and locked:
            session["limit_locked"] = True
            self._save()
        if self.limit["notify"]:
            approx = "≈ " if session is not None and self._is_estimated(session) else ""
            self._send(
                charger,
                NOTICE_LIMIT,
                [vehicle_id],
                self._text(
                    "charger_limit_locked" if locked else "charger_limit_reached",
                    charger=charger["name"],
                    level=f"{approx}{round(level)}",
                    limit=target,
                ),
                [(f"{ACTION_PREFIX}|{charger['id']}|{ACTION_FULL}", self._text("action_full"))] if locked else None,
            )
        self._changed()
