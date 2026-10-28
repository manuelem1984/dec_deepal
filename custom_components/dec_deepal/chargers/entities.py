"""Cargadores: las entidades del cargador: leerlas (manguera, carga, potencia, energía, bloqueo, precio) y bloquear o desbloquear."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.const import (
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import State

from .const import (
    ROLE_CHARGING,
    ROLE_ENERGY,
    ROLE_LOCK,
    ROLE_PLUGGED,
    ROLE_POWER,
)
from .util import _flag, _number


class EntitiesMixin:
    """Las entidades del cargador: leerlas (manguera, carga, potencia, energía, bloqueo, precio) y bloquear o desbloquear.

    Es una parte de :class:`~.manager.ChargerManager` (se juntan por herencia):
    usa sus atributos y los métodos de las demás partes a través de ``self``.
    """

    def _state(self, charger: Mapping[str, Any], role: str) -> State | None:
        entity_id = charger["entities"].get(role)
        return self.hass.states.get(entity_id) if entity_id else None

    def plugged(self, charger: Mapping[str, Any]) -> bool | None:
        return _flag(self._state(charger, ROLE_PLUGGED))

    def charging(self, charger: Mapping[str, Any]) -> bool | None:
        return _flag(self._state(charger, ROLE_CHARGING))

    def power_w(self, charger: Mapping[str, Any]) -> float | None:
        """Potencia de carga en W (la entidad puede estar en W o en kW)."""
        state = self._state(charger, ROLE_POWER)
        value = _number(state)
        if value is None:
            return None
        unit = str(state.attributes.get("unit_of_measurement") or "W")
        return value * 1000 if unit.lower() == "kw" else value

    def _energy_raw(self, charger: Mapping[str, Any]) -> float | None:
        state = self._state(charger, ROLE_ENERGY)
        value = _number(state)
        if value is None:
            return None
        unit = str(state.attributes.get("unit_of_measurement") or "kWh")
        return value / 1000 if unit.lower() == "wh" else value

    def locked(self, charger: Mapping[str, Any]) -> bool | None:
        """¿Bloqueado? Una cerradura dice ``locked``; un interruptor, según ``lock_on_locked``."""
        state = self._state(charger, ROLE_LOCK)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        if state.domain == "lock":
            return state.state == "locked"
        on = state.state == STATE_ON
        return on if charger["lock_on_locked"] else not on

    def price(self, charger: Mapping[str, Any]) -> float | None:
        if charger.get("price_entity"):
            return _number(self.hass.states.get(charger["price_entity"]))
        return charger.get("price")

    async def _set_locked(self, charger: Mapping[str, Any], locked: bool) -> bool:
        """Bloquea o desbloquea. ``False`` si el cargador no tiene bloqueo."""
        entity_id = charger["entities"].get(ROLE_LOCK)
        if not entity_id:
            return False
        domain = entity_id.split(".", 1)[0]
        if domain == "lock":
            service = "lock" if locked else "unlock"
        else:
            turn_on = locked if charger["lock_on_locked"] else not locked
            service = "turn_on" if turn_on else "turn_off"
        await self.hass.services.async_call(domain, service, {"entity_id": entity_id}, blocking=True)
        return True
