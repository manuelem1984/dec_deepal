"""Climatización programada, con protección de la batería (2.6.0b17).

Cada coche puede tener **una** programación: a una hora, unos días
(todos, laborables o fin de semana), enciende el clima a una temperatura.
Se configura con entidades (sin YAML ni automatizaciones):

- ``switch.<coche>_climatizacion_programada`` — activa o no.
- ``time.<coche>_hora_de_la_climatizacion`` — a qué hora.
- ``select.<coche>_dias_de_la_climatizacion`` — qué días.
- ``number.<coche>_temperatura_programada`` — a cuántos grados (18-32).
- ``number.<coche>_bateria_minima_para_climatizar`` — por debajo de ese %
  no se enciende, salvo que el coche esté enchufado (así no se queda sin
  batería por calentar el coche).

Tampoco se enciende con el coche **encendido** (el servidor lo rechaza:
1032 «Power is not off»). Lo que pasa se avisa con «Climatización
programada» (apartado Testigos del panel; nace sin destinos).

La hora es la de Home Assistant. Se mira cada minuto; una programación solo
salta una vez al día. Se guarda en ``.storage/dec_deepal.climate_schedule``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from typing import Any, Final

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .alert_rules import ALERT_CLIMATE_SCHEDULE, texts
from .climate import clamp_temperature
from .const import DOMAIN
from .runtime import VehicleContext
from .telemetry import signals as s

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY: Final = f"{DOMAIN}.climate_schedule"
STORAGE_VERSION: Final = 1

DAYS_DAILY: Final = "daily"
DAYS_WEEKDAYS: Final = "weekdays"
DAYS_WEEKENDS: Final = "weekends"
DAYS_OPTIONS: Final = (DAYS_DAILY, DAYS_WEEKDAYS, DAYS_WEEKENDS)
MIN_BATTERY_LIMITS: Final = (0, 80)

#: Resultados (claves de texto del aviso, sección ``avisos``).
RESULT_STARTED: Final = "climate_schedule_started"
RESULT_LOW_BATTERY: Final = "climate_schedule_low_battery"
RESULT_POWER_ON: Final = "climate_schedule_power_on"
RESULT_FAILED: Final = "climate_schedule_failed"


@dataclass(frozen=True, slots=True)
class ClimateSchedule:
    """La programación de un coche."""

    enabled: bool = False
    time: str = "07:30"
    days: str = DAYS_WEEKDAYS
    temperature: float = 22.0
    min_battery: int = 30
    #: Último día que saltó (para no repetir), ISO.
    last_run: str | None = None

    @classmethod
    def from_dict(cls, raw: Any) -> ClimateSchedule:
        """Desde lo guardado; lo que falte o no valga, de fábrica."""
        base = cls()
        if not isinstance(raw, dict):
            return base
        days = raw.get("days")
        try:
            return cls(
                enabled=bool(raw.get("enabled", base.enabled)),
                time=_clock(raw.get("time")) or base.time,
                days=days if days in DAYS_OPTIONS else base.days,
                temperature=clamp_temperature(float(raw.get("temperature", base.temperature))),
                min_battery=max(MIN_BATTERY_LIMITS[0], min(MIN_BATTERY_LIMITS[1], int(raw.get("min_battery", base.min_battery)))),
                last_run=str(raw["last_run"]) if raw.get("last_run") else None,
            )
        except (TypeError, ValueError):
            return base

    def is_day(self, day: date) -> bool:
        """¿Toca ese día?"""
        weekend = day.weekday() >= 5
        return self.days == DAYS_DAILY or (self.days == DAYS_WEEKENDS) == weekend


def _clock(value: Any) -> str | None:
    """``"7:05"`` / ``"07:05:00"`` → ``"07:05"``; ``None`` si no es una hora."""
    try:
        hours, minutes = str(value).split(":")[:2]
        hours_i, minutes_i = int(hours), int(minutes)
    except (TypeError, ValueError):
        return None
    return f"{hours_i:02d}:{minutes_i:02d}" if 0 <= hours_i < 24 and 0 <= minutes_i < 60 else None


def decide(schedule: ClimateSchedule, values: Any) -> str | None:
    """Qué hacer al llegar la hora: ``None`` = encender; si no, por qué no (clave de texto)."""
    if values.get(s.POWER_ON) is True:
        return RESULT_POWER_ON
    battery = values.get(s.BATTERY_LEVEL)
    plugged = values.get(s.CHARGER_PLUGGED) is True
    if schedule.min_battery and not plugged and (battery is None or battery < schedule.min_battery):
        return RESULT_LOW_BATTERY
    return None


class ClimateScheduleManager:
    """Las programaciones de los coches de una cuenta."""

    def __init__(self, hass: HomeAssistant, vehicles: dict[str, VehicleContext], alerts: Any = None) -> None:
        self.hass = hass
        self._vehicles = vehicles
        self._alerts = alerts
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._schedules: dict[str, ClimateSchedule] = {}
        self._listeners: list[Callable[[], None]] = []
        self._unsubscribe: CALLBACK_TYPE | None = None

    async def async_load(self) -> None:
        """Lee lo guardado."""
        raw = await self._store.async_load() or {}
        self._schedules = {vehicle_id: ClimateSchedule.from_dict(raw.get(vehicle_id)) for vehicle_id in self._vehicles}

    @callback
    def async_start(self) -> None:
        """Mira cada minuto si toca alguna."""
        self._unsubscribe = async_track_time_change(self.hass, self._on_minute, second=5)

    @callback
    def async_stop(self) -> None:
        """Deja de mirar (al descargar la cuenta)."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def get(self, vehicle_id: str) -> ClimateSchedule:
        """La programación de un coche."""
        return self._schedules.get(vehicle_id, ClimateSchedule())

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        """Avisa a las entidades cuando cambia algo."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    async def async_update(self, vehicle_id: str, **changes: Any) -> None:
        """Cambia campos de una programación y la guarda."""
        current = self.get(vehicle_id)
        if "time" in changes:
            changes["time"] = _clock(changes["time"]) or current.time
        self._schedules[vehicle_id] = ClimateSchedule.from_dict({**asdict(current), **changes})
        self._save()
        for listener in list(self._listeners):
            listener()

    def _save(self) -> None:
        self._store.async_delay_save(lambda: {k: asdict(v) for k, v in self._schedules.items()}, 5)

    @callback
    def _on_minute(self, now: datetime) -> None:
        local = dt_util.as_local(now)
        clock = f"{local.hour:02d}:{local.minute:02d}"
        today = local.date()
        for vehicle_id, schedule in self._schedules.items():
            if not schedule.enabled or schedule.time != clock or not schedule.is_day(today):
                continue
            if schedule.last_run == today.isoformat():
                continue
            self._schedules[vehicle_id] = replace(schedule, last_run=today.isoformat())
            self._save()
            self.hass.async_create_task(self.async_run(vehicle_id), "dec_deepal: climatización programada")

    async def async_run(self, vehicle_id: str) -> str:
        """Enciende el clima de un coche según su programación (o explica por qué no)."""
        vehicle = self._vehicles[vehicle_id]
        schedule = self.get(vehicle_id)
        data = vehicle.coordinator.data
        values: Any = data if data is not None else {}
        result = decide(schedule, values)
        if result is None:
            runner = vehicle.runner
            target = clamp_temperature(schedule.temperature)
            try:
                await runner.run(
                    "climate",
                    lambda: runner.commands.air_conditioner(vehicle_id, enabled=True, target_c=target),
                    optimistic={s.CLIMATE_ON: True, s.CLIMATE_TARGET_C: target},
                )
            except HomeAssistantError as err:
                _LOGGER.warning("%s: climatización programada fallida: %s", vehicle.info.display_name, err)
                result = RESULT_FAILED
            else:
                result = RESULT_STARTED
        self._notify(vehicle_id, result, schedule, values)
        return result

    def _notify(self, vehicle_id: str, result: str, schedule: ClimateSchedule, values: Any) -> None:
        if self._alerts is None:
            return
        battery = values.get(s.BATTERY_LEVEL)
        message = texts(self.hass.config.language)[result].format(
            temperature=f"{schedule.temperature:g}",
            battery="?" if battery is None else round(battery),
            minimum=schedule.min_battery,
        )
        self._alerts.notify(vehicle_id, ALERT_CLIMATE_SCHEDULE, message)
