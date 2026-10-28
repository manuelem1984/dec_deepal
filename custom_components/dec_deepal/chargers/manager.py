"""Cargadores: el gestor (arranque, guardado, escuchas, configuración y temporizadores)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from ..const import DATA
from .cars import CarsMixin
from .config import ChargerError, _choice, _clean_car, clean_charger, clean_limit
from .const import (
    _MANAGER_KEY,
    CONTROL_PEOPLE,
    CONTROLS,
    EVENT_ACTION,
    LEARN_INTERVAL,
    ROLE_CHARGING,
    ROLE_ENERGY,
    ROLE_LOCK,
    ROLE_PLUGGED,
    ROLE_POWER,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .energy import EnergyMixin
from .entities import EntitiesMixin
from .limit import LimitMixin
from .models import CarLimit, ChargerConfig, HistoryRecord, LimitSettings, Session
from .notify import NotifyMixin
from .session import SessionMixin
from .status import StatusMixin


class ChargerManager(SessionMixin, LimitMixin, EnergyMixin, NotifyMixin, StatusMixin, CarsMixin, EntitiesMixin):
    """Todos los cargadores de la casa (uno por instalación de Home Assistant).

    Aquí está lo común (arranque, guardado, escuchas, configuración y
    temporizadores); el resto, en una parte por tema (ver el paquete).
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.enabled = False
        self.control = CONTROL_PEOPLE
        #: ¿Enseña la tarjeta del coche el % estimado mientras no tiene cobertura?
        self.show_estimate = True
        self.chargers: dict[str, ChargerConfig] = {}
        #: Carga en curso de cada cargador (se guarda: sobrevive a reinicios).
        self._sessions: dict[str, Session] = {}
        self._history: dict[str, list[HistoryRecord]] = {}
        self._losses: dict[str, list[float]] = {}
        #: Límite de carga y recordatorio del 100 % (Ajustes).
        self.limit: LimitSettings = clean_limit({})
        #: Por coche: límite, «la próxima al 100 %» y cargas seguidas sin llegar al 100 %.
        self._cars: dict[str, CarLimit] = {}
        self._loaded = False
        self._unsubscribe: list[CALLBACK_TYPE] = []
        #: Temporizadores por cargador: {cargador: {nombre: cancelar}}.
        self._timers: dict[str, dict[str, CALLBACK_TYPE]] = {}
        self._listeners: list[Callable[[], None]] = []
        #: La hora (las pruebas la cambian).
        self._clock: Callable[[], datetime] = dt_util.utcnow

    async def async_load(self) -> None:
        """Lee lo guardado y, si los cargadores están activados, empieza a escuchar."""
        if self._loaded:
            return
        data = await self._store.async_load() or {}
        self.enabled = bool(data.get("enabled", False))
        self.control = _choice(data.get("control"), CONTROLS, CONTROL_PEOPLE)
        self.show_estimate = bool(data.get("show_estimate", True))
        for raw in data.get("chargers") or ():
            try:
                charger = clean_charger(raw)
            except ChargerError:
                continue
            self.chargers[charger["id"]] = charger
        self._sessions = {key: dict(value) for key, value in (data.get("sessions") or {}).items() if key in self.chargers}
        self._history = {key: list(value) for key, value in (data.get("history") or {}).items()}
        self._losses = {key: [float(item) for item in value] for key, value in (data.get("losses") or {}).items()}
        self.limit = clean_limit(data.get("limit") or {})
        self._cars = {str(key): _clean_car(value) for key, value in (data.get("cars") or {}).items() if isinstance(value, Mapping)}
        self._loaded = True

        # Al apagar Home Assistant: fuera temporizadores y escuchas (lo pendiente
        # de guardar lo escribe el almacén solo, en su último guardado).
        @callback
        def _stopping(_event: Event) -> None:
            self.async_stop()

        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _stopping)
        if self.hass.is_running:
            self._resubscribe()
        else:
            # Al arrancar, los coches aún no están: se espera a que arranque todo.
            @callback
            def _started(_event: Event) -> None:
                self._resubscribe()

            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _started)

    def _data(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "control": self.control,
            "show_estimate": self.show_estimate,
            "chargers": list(self.chargers.values()),
            "sessions": self._sessions,
            "history": self._history,
            "losses": self._losses,
            "limit": self.limit,
            "cars": self._cars,
        }

    def _save(self) -> None:
        self._store.async_delay_save(self._data, 2)

    async def async_flush(self) -> None:
        await self._store.async_save(self._data())

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        """Avisa de cualquier cambio (la tarjeta se suscribe así)."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener) if listener in self._listeners else None

    def _changed(self) -> None:
        for listener in list(self._listeners):
            listener()

    @callback
    def async_stop(self) -> None:
        for unsubscribe in self._unsubscribe:
            unsubscribe()
        self._unsubscribe = []
        for charger_id in list(self._timers):
            self._cancel(charger_id)

    @callback
    def _resubscribe(self) -> None:
        self.async_stop()
        if not self.enabled or not self.chargers:
            return
        watched: dict[str, list[tuple[str, str]]] = {}
        for charger in self.chargers.values():
            for role, entity_id in charger["entities"].items():
                watched.setdefault(entity_id, []).append((charger["id"], role))
        # Tiene que ser @callback: sin eso, Home Assistant lo ejecuta en otro hilo.
        @callback
        def _changed(event: Event) -> None:
            self._on_state(event, watched)

        self._unsubscribe.append(async_track_state_change_event(self.hass, list(watched), _changed))
        self._unsubscribe.append(self.hass.bus.async_listen(EVENT_ACTION, self._on_action))
        self._unsubscribe.append(async_track_time_interval(self.hass, self._learn, LEARN_INTERVAL))
        # Lo que pasó con Home Assistant parado: se pone al día con el estado actual.
        for charger in self.chargers.values():
            self._sync(charger["id"])

    async def async_set_settings(self, enabled: bool, control: str, show_estimate: bool | None = None) -> None:
        """Activa o desactiva los cargadores, quién los controla y el % estimado en la tarjeta del coche."""
        await self.async_load()
        self.enabled = bool(enabled)
        self.control = _choice(control, CONTROLS, CONTROL_PEOPLE)
        if show_estimate is not None:
            self.show_estimate = bool(show_estimate)
        self._save()
        self._resubscribe()
        self._changed()

    async def async_save_charger(self, raw: Mapping[str, Any]) -> ChargerConfig:
        """Añade o cambia un cargador (ver :func:`clean_charger`) y empieza a escucharlo.

        Raises:
            ChargerError: el cargador no es válido.
        """
        await self.async_load()
        charger = clean_charger(raw, self._vehicle_ids())
        self.chargers[charger["id"]] = charger
        self._prune_cars()
        self._save()
        self._resubscribe()
        self._changed()
        return charger

    async def async_delete_charger(self, charger_id: str) -> None:
        """Quita un cargador con su carga en curso, su historial y sus pérdidas medidas.

        Raises:
            KeyError: no existe.
        """
        await self.async_load()
        if self.chargers.pop(charger_id, None) is None:
            raise KeyError(charger_id)
        self._cancel(charger_id)
        for store in (self._sessions, self._history, self._losses):
            store.pop(charger_id, None)
        self._prune_cars()
        self._save()
        self._resubscribe()
        self._changed()

    @callback
    def _on_state(self, event: Event, watched: Mapping[str, list[tuple[str, str]]]) -> None:
        for charger_id, role in watched.get(event.data["entity_id"], ()):
            charger = self.chargers.get(charger_id)
            if charger is None:
                continue
            if role in (ROLE_POWER, ROLE_ENERGY, ROLE_CHARGING):
                self._track_energy(charger)
                self._check_limit(charger)
            if role in (ROLE_PLUGGED, ROLE_CHARGING, ROLE_LOCK):
                self._sync(charger_id)  # avisa él a las tarjetas
            else:
                self._changed()

    def _timer(self, charger_id: str, name: str, seconds: float, action: Callable[[Any], None]) -> None:
        self._cancel(charger_id, name)
        timers = self._timers.setdefault(charger_id, {})

        @callback
        def _fire(now: Any) -> None:
            timers.pop(name, None)
            action(now)

        timers[name] = async_call_later(self.hass, seconds, _fire)

    def _cancel(self, charger_id: str, name: str | None = None) -> None:
        timers = self._timers.get(charger_id, {})
        for key in [name] if name else list(timers):
            if (cancel := timers.pop(key, None)) is not None:
                cancel()


def async_get_manager(hass: HomeAssistant) -> ChargerManager:
    """El gestor de cargadores de esta instalación (se crea la primera vez)."""
    domain_data = hass.data.setdefault(DATA, {})
    manager = domain_data.get(_MANAGER_KEY)
    if manager is None:
        manager = domain_data[_MANAGER_KEY] = ChargerManager(hass)
    return manager
