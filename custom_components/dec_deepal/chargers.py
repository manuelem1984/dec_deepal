"""Cargadores: une la carga de los coches con los cargadores de casa o del trabajo.

Sirve para **cualquier cargador** que tenga sus entidades en Home Assistant
(V2C, Wallbox, Easee, Zaptec, OCPP...): en el panel DEC Deepal → Ajustes →
Cargadores se elige qué entidad hace cada papel:

==============  ==========================================  =============
Papel           Entidad                                      ¿Obligatoria?
==============  ==========================================  =============
``plugged``     Manguera enchufada (``binary_sensor``)       Sí
``charging``    Cargando (``binary_sensor``)                 No
``power``       Potencia de carga (W o kW)                   No
``energy``      Energía de la carga (kWh)                    No
``lock``        Bloqueo (``switch`` o ``lock``)              No
==============  ==========================================  =============

Qué hace
--------
- **Solo bloquea y desbloquea.** Nunca inicia, pausa ni cambia la intensidad
  de la carga: con OCPP, la compañía empieza a cargar en cuanto el cargador
  queda desbloqueado.
- **Desbloquear al confirmar el coche** (``unlock = "confirm"``): al
  enchufar, el cargador sigue bloqueado hasta saber qué coche es:

  * Con cobertura (o "no lo sé"), se espera a que un coche diga que tiene la
    manguera puesta (``CHARGE_WAIT``): ese es, y se desbloquea solo.
  * Si no lo dice ninguno (o no hay cobertura), se pregunta por
    notificación, con un botón por coche (``mobile_app``). Al elegirlo, se
    desbloquea. Si nadie contesta, se recuerda pasados ``remind_minutes``.
- **Bloquear al desenchufar** (``relock``): desbloqueado y con la manguera
  quitada, se bloquea pasados ``relock_minutes`` (si no se vuelve a enchufar).
- **Cada carga** se apunta (coche, kWh, €, de qué % a cuál) y, sin cobertura,
  se **estima** el % y el tiempo con los kWh del cargador menos las
  **pérdidas** (10 % de fábrica). Cuando el coche vuelve a informar, se mide
  la pérdida real de esa carga (``learn``) y el panel la ofrece.
- **Límite de carga** (70, 80, 90 o 100 %, por coche; se elige en la tarjeta
  del coche): al llegarle (real o estimado), se **bloquea el cargador**. Es lo
  único que puede parar la carga del EV, que no aplica el límite del servidor;
  en el PHEV, además, se le manda su límite propio. Sin bloqueo, solo se
  avisa. «Solo esta: 100 %» hace la siguiente carga completa.
- **Recordar cargar al 100 %** cada 3-6 cargas seguidas sin llegar (para que
  la batería se equilibre y el % sea exacto), o hacerla al 100 % sin preguntar.

Avisos
------
Los del apartado "Cargador" de la pestaña Avisos, de cada coche. Si un coche
no tiene destinos ahí, se usan los de sus avisos de carga. Ninguno es
crítico. El título es ``DEC Deepal <coche>``; mientras no se sabe el coche,
``DEC Deepal · <cargador>``.

Todo se guarda en su almacén (``dec_deepal.chargers``): es de la casa, no de
una cuenta, y un cargador puede servir a coches de cuentas distintas.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timedelta
from typing import Any, Final

from homeassistant.components import persistent_notification
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .alert_rules import SECTION_CHARGE, TARGET_PANEL, texts
from .const import DOMAIN, NAME, PANEL_URL_PATH
from .registries.vehicles import FEATURE_CHARGE_LIMIT
from .runtime import vehicle_device
from .telemetry import signals as s

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY: Final = f"{DOMAIN}.chargers"
STORAGE_VERSION: Final = 1
_MANAGER_KEY: Final = "chargers"

# --- Papeles de las entidades -------------------------------------------------------
ROLE_PLUGGED: Final = "plugged"
ROLE_CHARGING: Final = "charging"
ROLE_POWER: Final = "power"
ROLE_ENERGY: Final = "energy"
ROLE_LOCK: Final = "lock"
ROLES: Final = (ROLE_PLUGGED, ROLE_CHARGING, ROLE_POWER, ROLE_ENERGY, ROLE_LOCK)
#: Dominios que admite cada papel.
ROLE_DOMAINS: Final = {
    ROLE_PLUGGED: ("binary_sensor", "sensor", "switch", "input_boolean"),
    ROLE_CHARGING: ("binary_sensor", "sensor", "switch", "input_boolean"),
    ROLE_POWER: ("sensor",),
    ROLE_ENERGY: ("sensor",),
    ROLE_LOCK: ("switch", "lock", "input_boolean"),
}

# --- Opciones de cada cargador ------------------------------------------------------
COVERAGE_YES: Final = "yes"
COVERAGE_NO: Final = "no"
COVERAGE_UNKNOWN: Final = "unknown"
COVERAGES: Final = (COVERAGE_YES, COVERAGE_NO, COVERAGE_UNKNOWN)
UNLOCK_NONE: Final = "none"
UNLOCK_CONFIRM: Final = "confirm"
UNLOCK_MODES: Final = (UNLOCK_NONE, UNLOCK_CONFIRM)
REMIND_CHOICES: Final = (5, 15, 60)
RELOCK_CHOICES: Final = (3, 5, 10)
#: Bloquear al terminar la carga: minutos sin cargar (con el coche al 100 %).
LOCK_FULL_CHOICES: Final = (15, 30, 45)
#: Desde qué % se da la carga por completa (real o estimado).
FULL_LEVEL: Final = 99.0
#: Leer el coche mientras carga: cada cuántos minutos (0 = no).
READ_CHOICES: Final = (0, 10, 15, 30)
#: Despertares fallidos seguidos que confirman que no hay cobertura.
READ_FAILURES: Final = 2
DEFAULT_LOSS: Final = 10.0
MAX_LOSS: Final = 40.0
#: Quién puede desbloquear desde la tarjeta o las notificaciones.
CONTROL_PEOPLE: Final = "people"  # las personas de los coches y los administradores
CONTROL_ADMINS: Final = "admins"
CONTROLS: Final = (CONTROL_PEOPLE, CONTROL_ADMINS)

# --- Tiempos ------------------------------------------------------------------------
#: Cuánto se espera a que el coche confirme la manguera antes de preguntar.
CHARGE_WAIT: Final = timedelta(minutes=5)
#: Cada cuánto se mira si algún coche lo ha confirmado.
CHARGE_WAIT_STEP: Final = 30
#: Desbloqueado y sin cargar pasado este tiempo: aviso "no carga".
NOT_CHARGING_AFTER: Final = timedelta(minutes=10)
#: Cada cuánto se intenta medir la pérdida de las cargas ya terminadas.
LEARN_INTERVAL: Final = timedelta(minutes=10)
#: Cargas que se guardan por cargador, y pérdidas medidas que se promedian.
HISTORY_SIZE: Final = 60
LOSS_SAMPLES: Final = 10

# --- Límite de carga ----------------------------------------------------------------
#: % a los que se puede limitar la carga de un coche (100 = sin límite).
LIMIT_CHOICES: Final = (70, 80, 90, 100)
DEFAULT_LIMIT: Final = 100
#: Recordar cargar al 100 % cada N cargas seguidas sin llegar.
FULL_EVERY_CHOICES: Final = (3, 4, 5, 6)
#: A menos de estos puntos del límite, el coche se lee más a menudo...
LIMIT_NEAR: Final = 5.0
#: ...cada estos minutos (si "Leer el coche mientras carga" está activado).
LIMIT_READ_MINUTES: Final = 5

# --- Notificaciones -----------------------------------------------------------------
EVENT_ACTION: Final = "mobile_app_notification_action"
ACTION_PREFIX: Final = "DEC_DEEPAL_CHARGER"
ACTION_NO: Final = "-"
ACTION_AGAIN: Final = "again"
NOTICE_CONFIRM: Final = "charger_confirm"
NOTICE_UNLOCKED: Final = "charger_unlocked"
NOTICE_NOT_CHARGING: Final = "charger_not_charging"
NOTICE_FINISHED: Final = "charger_finished"
NOTICE_LOCKED: Final = "charger_locked"
NOTICE_LIMIT: Final = "charger_limit"
NOTICE_FULL: Final = "charger_full"
#: Botones del límite: seguir hasta el 100 % (esta carga) y la próxima al 100 %.
ACTION_FULL: Final = "full"
ACTION_NEXT_FULL: Final = "nextfull:"

#: Cómo asignó la carga a un coche.
BY_CAR: Final = "car"  # el coche dijo que tenía la manguera
BY_USER: Final = "user"  # alguien lo eligió (notificación, tarjeta)
BY_SINGLE: Final = "single"  # el cargador solo tiene un coche


class ChargerError(ValueError):
    """Un cargador mal configurado o una orden que no se puede cumplir."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _choice(value: Any, choices: Iterable[Any], default: Any) -> Any:
    return value if value in tuple(choices) else default


def clean_charger(raw: Mapping[str, Any], known: Iterable[str] = ()) -> dict[str, Any]:
    """Un cargador válido a partir de lo que manda el panel.

    Raises:
        ChargerError: sin nombre (``charger_name``), sin entidad de manguera
            (``charger_plugged``) o con un papel en un dominio que no vale
            (``charger_entity``).
    """
    name = str(raw.get("name") or "").strip()[:40]
    if not name:
        raise ChargerError("charger_name")
    entities: dict[str, str] = {}
    for role in ROLES:
        entity_id = str((raw.get("entities") or {}).get(role) or "").strip()
        if not entity_id:
            continue
        if entity_id.split(".", 1)[0] not in ROLE_DOMAINS[role]:
            raise ChargerError("charger_entity")
        entities[role] = entity_id
    if ROLE_PLUGGED not in entities:
        raise ChargerError("charger_plugged")
    known = set(known)
    vehicles = [str(item) for item in dict.fromkeys(raw.get("vehicles") or ()) if not known or str(item) in known]
    try:
        loss = float(raw.get("loss", DEFAULT_LOSS))
    except (TypeError, ValueError):
        loss = DEFAULT_LOSS
    price = raw.get("price")
    try:
        price = None if price in (None, "") else max(0.0, round(float(price), 4))
    except (TypeError, ValueError):
        price = None
    price_entity = str(raw.get("price_entity") or "").strip()
    if price_entity and price_entity.split(".", 1)[0] not in ("sensor", "input_number", "number"):
        raise ChargerError("charger_entity")
    return {
        "id": str(raw.get("id") or uuid.uuid4().hex[:10]),
        "name": name,
        "entities": entities,
        # En un interruptor: ¿encendido = bloqueado? (en una cerradura no hace falta).
        "lock_on_locked": bool(raw.get("lock_on_locked", True)),
        "vehicles": vehicles,
        "coverage": _choice(raw.get("coverage"), COVERAGES, COVERAGE_UNKNOWN),
        "unlock": _choice(raw.get("unlock"), UNLOCK_MODES, UNLOCK_NONE),
        "notify_confirm": bool(raw.get("notify_confirm", True)),
        "remind_minutes": _choice(raw.get("remind_minutes"), REMIND_CHOICES, 15),
        "relock": bool(raw.get("relock", True)),
        "relock_minutes": _choice(raw.get("relock_minutes"), RELOCK_CHOICES, 5),
        "relock_notify": bool(raw.get("relock_notify", True)),
        # Bloquear al terminar: enchufado, al 100 % y sin cargar ``lock_full_minutes``.
        "lock_full": bool(raw.get("lock_full", True)),
        "lock_full_minutes": _choice(raw.get("lock_full_minutes"), LOCK_FULL_CHOICES, 30),
        # Con cobertura (o "no lo sé"): despertar el coche cada N min mientras carga.
        "read_interval": _choice(raw.get("read_interval"), READ_CHOICES, 15),
        "loss": min(MAX_LOSS, max(0.0, round(loss, 1))),
        "learn": bool(raw.get("learn", True)),
        "price": price,
        "price_entity": price_entity,
    }


def clean_limit(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Opciones del límite de carga y del recordatorio del 100 % (Ajustes)."""
    return {
        "enabled": bool(raw.get("enabled", False)),
        "notify": bool(raw.get("notify", True)),
        "remind": bool(raw.get("remind", False)),
        "every": _choice(raw.get("every"), FULL_EVERY_CHOICES, 4),
        "auto": bool(raw.get("auto", False)),
    }


def _clean_car(raw: Mapping[str, Any]) -> dict[str, Any]:
    try:
        incomplete = max(0, int(raw.get("incomplete") or 0))
    except (TypeError, ValueError):
        incomplete = 0
    return {
        "limit": _choice(raw.get("limit"), LIMIT_CHOICES, DEFAULT_LIMIT),
        "once_full": bool(raw.get("once_full", False)),
        "incomplete": incomplete,
    }


def estimate_level(start: float | None, energy_kwh: float | None, loss: float, capacity: float | None) -> float | None:
    """% de batería estimado: el de partida más los kWh que llegan a la batería."""
    if start is None or energy_kwh is None or not capacity:
        return None
    return min(100.0, start + energy_kwh * (1 - loss / 100) / capacity * 100)


def estimate_minutes(
    level: float | None, power_w: float | None, loss: float, capacity: float | None, target: float = 100
) -> float | None:
    """Minutos que faltan para ``target`` % con la potencia actual (sin el equilibrado)."""
    if level is None or not power_w or power_w <= 0 or not capacity:
        return None
    missing_kwh = max(0.0, target - level) / 100 * capacity / max(0.01, 1 - loss / 100)
    return missing_kwh / (power_w / 1000) * 60


def measured_loss(start: float, end: float, energy_kwh: float, capacity: float) -> float | None:
    """Pérdida real de una carga, o ``None`` si los datos no son creíbles."""
    if energy_kwh < 1 or end <= start:
        return None
    stored = (end - start) / 100 * capacity
    loss = (1 - stored / energy_kwh) * 100
    return round(loss, 1) if 0 <= loss <= MAX_LOSS else None


def _number(state: State | None) -> float | None:
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, ""):
        return None
    try:
        return float(state.state)
    except ValueError:
        return None


def _flag(state: State | None) -> bool | None:
    """Estado sí/no de una entidad (``None`` = no se sabe)."""
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        return None
    if state.state in (STATE_ON, "true", "plugged", "connected", "charging", "locked"):
        return True
    number = _number(state)
    if number is not None:
        return number > 0
    return False


def _iso(when: datetime | None) -> str | None:
    return None if when is None else when.isoformat()


def _when(value: Any) -> datetime | None:
    return dt_util.parse_datetime(value) if isinstance(value, str) else None


class ChargerManager:
    """Todos los cargadores de la casa (uno por instalación de Home Assistant)."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.enabled = False
        self.control = CONTROL_PEOPLE
        #: ¿Enseña la tarjeta del coche el % estimado mientras no tiene cobertura?
        self.show_estimate = True
        self.chargers: dict[str, dict[str, Any]] = {}
        #: Carga en curso de cada cargador (se guarda: sobrevive a reinicios).
        self._sessions: dict[str, dict[str, Any]] = {}
        self._history: dict[str, list[dict[str, Any]]] = {}
        self._losses: dict[str, list[float]] = {}
        #: Límite de carga y recordatorio del 100 % (Ajustes).
        self.limit: dict[str, Any] = clean_limit({})
        #: Por coche: límite, «la próxima al 100 %» y cargas seguidas sin llegar al 100 %.
        self._cars: dict[str, dict[str, Any]] = {}
        self._loaded = False
        self._unsubscribe: list[CALLBACK_TYPE] = []
        #: Temporizadores por cargador: {cargador: {nombre: cancelar}}.
        self._timers: dict[str, dict[str, CALLBACK_TYPE]] = {}
        self._listeners: list[Callable[[], None]] = []
        #: La hora (las pruebas la cambian).
        self._clock: Callable[[], datetime] = dt_util.utcnow

    # ------------------------------------------------------------------
    # Arranque, guardado y escuchas
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Configuración (panel)
    # ------------------------------------------------------------------

    async def async_set_settings(self, enabled: bool, control: str, show_estimate: bool | None = None) -> None:
        await self.async_load()
        self.enabled = bool(enabled)
        self.control = _choice(control, CONTROLS, CONTROL_PEOPLE)
        if show_estimate is not None:
            self.show_estimate = bool(show_estimate)
        self._save()
        self._resubscribe()
        self._changed()

    async def async_save_charger(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        await self.async_load()
        charger = clean_charger(raw, self._vehicle_ids())
        self.chargers[charger["id"]] = charger
        self._save()
        self._resubscribe()
        self._changed()
        return charger

    async def async_delete_charger(self, charger_id: str) -> None:
        await self.async_load()
        if self.chargers.pop(charger_id, None) is None:
            raise KeyError(charger_id)
        self._cancel(charger_id)
        for store in (self._sessions, self._history, self._losses):
            store.pop(charger_id, None)
        self._save()
        self._resubscribe()
        self._changed()

    async def async_set_limit_settings(self, raw: Mapping[str, Any]) -> None:
        """Opciones del límite de carga y del recordatorio del 100 % (lo que no llega, se queda)."""
        await self.async_load()
        self.limit = clean_limit({**self.limit, **raw})
        self._save()
        for vehicle_id, car in self._cars.items():
            if car["limit"] < 100:
                self._native_limit(vehicle_id)
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
        self._native_limit(vehicle_id)
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

    @callback
    def _native_limit(self, vehicle_id: str) -> None:
        """S05 PHEV: también se le manda su límite propio (el EV lo acepta pero no lo aplica)."""
        found = self._vehicle(vehicle_id)
        if found is None:
            return
        entry, vehicle = found
        if not vehicle.has(FEATURE_CHARGE_LIMIT):
            return
        target = self.target(vehicle_id)
        current = (vehicle.coordinator.data or {}).get(s.CHARGE_LIMIT)
        if current is not None and round(float(current)) == target:
            return
        commands = entry.runtime_data.commands

        async def _send() -> None:
            try:
                await vehicle.runner.run(
                    "charge_limit",
                    lambda: commands.charge_limit(vehicle_id, target),
                    optimistic={s.CHARGE_LIMIT: target},
                )
            except HomeAssistantError as err:
                _LOGGER.warning("No se pudo mandar el límite de carga al coche: %s", err)

        self.hass.async_create_task(_send())

    def measured(self, charger_id: str) -> dict[str, Any] | None:
        """Pérdida medida con las últimas cargas: ``{"value": 11.8, "count": 4}``."""
        samples = self._losses.get(charger_id) or []
        if not samples:
            return None
        return {"value": round(sum(samples) / len(samples), 1), "count": len(samples)}

    # ------------------------------------------------------------------
    # Coches
    # ------------------------------------------------------------------

    def _entries(self) -> list[Any]:
        return [
            entry
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if getattr(getattr(entry, "runtime_data", None), "alerts", None) is not None
        ]

    def _vehicle(self, vehicle_id: str) -> tuple[Any, Any] | None:
        for entry in self._entries():
            if vehicle := entry.runtime_data.vehicles.get(vehicle_id):
                return entry, vehicle
        return None

    def _vehicle_ids(self) -> list[str]:
        return [vehicle_id for entry in self._entries() for vehicle_id in entry.runtime_data.vehicles]

    def _candidates(self, charger: Mapping[str, Any]) -> list[str]:
        """Coches del cargador que están cargados en Home Assistant."""
        return [vehicle_id for vehicle_id in charger["vehicles"] if self._vehicle(vehicle_id)]

    def _name(self, vehicle_id: str | None) -> str:
        found = self._vehicle(vehicle_id) if vehicle_id else None
        if found is None:
            return ""
        entry, vehicle = found
        device = vehicle_device(self.hass, entry.entry_id, vehicle_id)
        if device is not None and (device.name_by_user or device.name):
            return device.name_by_user or device.name
        return vehicle.info.display_name

    def _device_id(self, vehicle_id: str | None) -> str | None:
        found = self._vehicle(vehicle_id) if vehicle_id else None
        if found is None:
            return None
        device = vehicle_device(self.hass, found[0].entry_id, vehicle_id)
        return device.id if device else None

    def _car_data(self, vehicle_id: str | None) -> Mapping[str, Any]:
        found = self._vehicle(vehicle_id) if vehicle_id else None
        return (found[1].coordinator.data or {}) if found else {}

    def _capacity(self, vehicle_id: str | None) -> float | None:
        found = self._vehicle(vehicle_id) if vehicle_id else None
        if found is None:
            return None
        vehicle = found[1]
        trim = vehicle.model.trims.get(vehicle.trim or "")
        return getattr(trim, "battery_kwh", None)

    def _balance(self, vehicle_id: str | None) -> int:
        found = self._vehicle(vehicle_id) if vehicle_id else None
        return int(getattr(found[0].runtime_data, "charge_balance_minutes", 0) or 0) if found else 0

    def _reported_since(self, vehicle_id: str, since: datetime | None) -> bool:
        """¿Ha informado el coche después de ``since``?"""
        report = self._car_data(vehicle_id).get(s.REPORT_TIME)
        return isinstance(report, datetime) and since is not None and report >= since - timedelta(minutes=2)

    def _people_users(self, vehicle_ids: Iterable[str]) -> set[str]:
        """Usuarios de Home Assistant de las personas de esos coches."""
        users: set[str] = set()
        for vehicle_id in vehicle_ids:
            found = self._vehicle(vehicle_id)
            if found is None:
                continue
            for person_id in found[0].runtime_data.alerts.people(vehicle_id):
                state = self.hass.states.get(person_id)
                if state is not None and state.attributes.get("user_id"):
                    users.add(state.attributes["user_id"])
        return users

    def can_control_vehicle(self, vehicle_id: str, user: Any) -> bool:
        """¿Puede este usuario cambiar el límite de carga de este coche?"""
        if user is None or getattr(user, "is_admin", False):
            return user is not None
        return self.control == CONTROL_PEOPLE and user.id in self._people_users([vehicle_id])

    def can_control(self, charger_id: str, user: Any) -> bool:
        """¿Puede este usuario desbloquear el cargador o elegir el coche?"""
        if user is None or getattr(user, "is_admin", False):
            return user is not None
        if self.control != CONTROL_PEOPLE:
            return False
        charger = self.chargers.get(charger_id)
        return charger is not None and user.id in self._people_users(charger["vehicles"])

    # ------------------------------------------------------------------
    # Entidades del cargador
    # ------------------------------------------------------------------

    def _state(self, charger: Mapping[str, Any], role: str) -> State | None:
        entity_id = charger["entities"].get(role)
        return self.hass.states.get(entity_id) if entity_id else None

    def plugged(self, charger: Mapping[str, Any]) -> bool | None:
        return _flag(self._state(charger, ROLE_PLUGGED))

    def charging(self, charger: Mapping[str, Any]) -> bool | None:
        return _flag(self._state(charger, ROLE_CHARGING))

    def power_w(self, charger: Mapping[str, Any]) -> float | None:
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

    # ------------------------------------------------------------------
    # Cambios del cargador
    # ------------------------------------------------------------------

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
                self._sync(charger_id)
            self._changed()

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
                    self.hass.async_create_task(self._unlock_for(current, vehicle_id, by_car=True))
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
            self.hass.async_create_task(self._set_locked(charger, False))
        else:
            self._maybe_relock(charger)

    def _count_charge(self, charger: Mapping[str, Any], vehicle_id: str, level: float | None) -> None:
        """Cuenta las cargas seguidas sin llegar al 100 % y, cada N, recuerda hacer una completa."""
        if level is None:
            return
        car = self._car(vehicle_id)
        if level >= FULL_LEVEL:
            car["incomplete"] = 0
            if car["once_full"]:
                car["once_full"] = False
                self._native_limit(vehicle_id)
            return
        car["incomplete"] += 1
        if not self.limit["remind"] or car["once_full"] or car["incomplete"] % self.limit["every"]:
            return
        count = car["incomplete"]
        if self.limit["auto"]:
            car["once_full"] = True
            self._native_limit(vehicle_id)
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
        self.hass.async_create_task(self._stop_at_limit(charger, vehicle_id, target, level))

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
            self.hass.async_create_task(self._lock_full(current, session.get("vehicle_id"), minutes))

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
            self.hass.async_create_task(self._relock(current))

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
            self.hass.async_create_task(self._read_car(current, coordinator))

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

    def _track_power(self, charger: Mapping[str, Any], session: dict[str, Any]) -> None:
        """kWh por la potencia: la última potencia leída por el tiempo que ha durado."""
        now = self._clock()
        last = _when(session.get("pw_at"))
        watts = float(session.get("pw_w") or 0.0)
        if last is not None and watts > 0:
            session["energy_power"] = float(session.get("energy_power") or 0.0) + watts * (now - last).total_seconds() / 3_600_000
        power = self.power_w(charger) if self.charging(charger) is not False else 0.0
        session["pw_at"] = _iso(now)
        session["pw_w"] = power or 0.0

    def _track_energy(self, charger: Mapping[str, Any], session: dict[str, Any] | None = None) -> None:
        """kWh de esta carga: los del contador del cargador o, si no avanza, por la potencia."""
        session = session if session is not None else self._sessions.get(charger["id"])
        if session is None:
            return
        if charger["entities"].get(ROLE_POWER):
            self._track_power(charger, session)
        self._track_meter(charger, session)
        meter = session.get("energy_meter")
        power = float(session.get("energy_power") or 0.0)
        # El contador manda; si no hay, o no se mueve mientras la potencia sí, la potencia.
        if power > 0.3 and (meter is None or meter < 0.05 or (power > 1.0 and meter < power * 0.5)):
            energy, source = power, "power"
        else:
            energy, source = float(meter or 0.0), "meter" if meter is not None else None
        session["energy"] = max(float(session.get("energy") or 0.0), energy)
        if source:
            session["energy_source"] = source
        self._save()

    def _track_meter(self, charger: Mapping[str, Any], session: dict[str, Any]) -> None:
        """kWh de esta carga: lo que ha subido el contador desde que se enchufó."""
        value = self._energy_raw(charger)
        if value is None:
            return
        start = session.get("energy_start")
        if start is None or value < start:
            # Contador por sesión (se pone a 0 al enchufar) o reiniciado.
            session["energy_start"] = start = 0.0 if start is None or value < start else start
        session["energy_meter"] = max(float(session.get("energy_meter") or 0.0), value - start)

    # ------------------------------------------------------------------
    # Preguntar, desbloquear y avisar
    # ------------------------------------------------------------------

    def _ask(self, charger: Mapping[str, Any], *, reminder: bool = False) -> None:
        charger_id = charger["id"]
        session = self._sessions.get(charger_id)
        if session is None or session.get("vehicle_id") and not reminder:
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
        self._track_energy(charger, dict(session))
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
                self.hass.services.async_call("notify", service, payload, blocking=False)
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

        self.hass.async_create_task(_run())

    # ------------------------------------------------------------------
    # Estimación y medida de pérdidas
    # ------------------------------------------------------------------

    def _is_estimated(self, session: Mapping[str, Any]) -> bool:
        vehicle_id = session.get("vehicle_id")
        return bool(vehicle_id) and not self._reported_since(vehicle_id, _when(session.get("charging_since") or session.get("plugged_at")))

    def _level(self, charger: Mapping[str, Any], session: Mapping[str, Any]) -> float | None:
        """% del coche: el real si ha informado durante la carga; si no, estimado."""
        vehicle_id = session.get("vehicle_id")
        if not vehicle_id:
            return None
        if not self._is_estimated(session):
            return self._car_data(vehicle_id).get(s.BATTERY_LEVEL)
        return estimate_level(session.get("soc_start"), session.get("energy"), charger["loss"], self._capacity(vehicle_id))

    @callback
    def _learn(self, _now: Any = None) -> None:
        """Cargas terminadas sin cobertura: cuando el coche vuelve a informar, se mide la pérdida.

        De paso, mira el límite de las cargas en curso (el coche puede haber
        informado por su cuenta).
        """
        for charger_id in list(self._sessions):
            if (charger := self.chargers.get(charger_id)) is not None:
                self._check_limit(charger)
        changed = False
        for charger_id, history in self._history.items():
            charger = self.chargers.get(charger_id)
            if charger is None:
                continue
            for record in history[-5:]:
                vehicle_id = record.get("vehicle_id")
                if record.get("learned") or not vehicle_id or record.get("soc_start") is None:
                    continue
                end = _when(record.get("end"))
                data = self._car_data(vehicle_id)
                if not self._reported_since(vehicle_id, end):
                    continue
                record["learned"] = True
                changed = True
                level = data.get(s.BATTERY_LEVEL)
                odometer = data.get(s.ODOMETER_KM)
                if level is None or (record.get("odometer") is not None and odometer is not None and odometer - record["odometer"] > 1):
                    continue  # ya ha circulado: el % no sirve
                record["soc_end"] = level
                record["estimated"] = False
                capacity = self._capacity(vehicle_id)
                if charger["learn"] and capacity and (loss := measured_loss(record["soc_start"], level, record["energy"], capacity)) is not None:
                    samples = self._losses.setdefault(charger_id, [])
                    samples.append(loss)
                    del samples[:-LOSS_SAMPLES]
        if changed:
            self._save()
            self._changed()

    # ------------------------------------------------------------------
    # Temporizadores
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Lo que ven la tarjeta y el panel
    # ------------------------------------------------------------------

    def status(self, charger_id: str, user: Any = None) -> dict[str, Any]:
        """Estado de un cargador para la tarjeta (y la ventana de carga del coche)."""
        charger = self.chargers[charger_id]
        session = self._sessions.get(charger_id)
        if session is not None:
            self._track_energy(charger, session)
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


def async_get_manager(hass: HomeAssistant) -> ChargerManager:
    """El gestor de cargadores de esta instalación (se crea la primera vez)."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    manager = domain_data.get(_MANAGER_KEY)
    if manager is None:
        manager = domain_data[_MANAGER_KEY] = ChargerManager(hass)
    return manager
