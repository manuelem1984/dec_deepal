"""Horas: inicio y fin de la carga programada ⚠️, y hora de la climatización programada.

Solo en los coches con ``plan_carga`` en la ficha (el S05). Cambiar una hora
con el plan encendido sustituye el plan del coche; con el plan apagado solo
se apunta, para cuando se encienda (ver ``charge_plan_control.py``).

La hora es la local del coche (la zona del plan o, si no tiene, la de Home
Assistant).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time as dt_time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .charge_plan_control import async_set_charge_plan
from .climate_schedule_entities import ScheduleTime, schedule_vehicles
from .entity import DecDeepalEntity, remove_entities
from .registries.vehicles import FEATURE_CHARGE_PLAN
from .runtime import DecDeepalConfigEntry, DecDeepalRuntime, VehicleContext
from .telemetry import signals as s


@dataclass(frozen=True, kw_only=True)
class DecTimeDescription(TimeEntityDescription):
    """Una hora del plan de carga."""

    signal: str
    #: Argumento de ``async_set_charge_plan`` que cambia (``start`` / ``end``).
    argument: str


TIMES: tuple[DecTimeDescription, ...] = (
    DecTimeDescription(key="charge_plan_start", signal=s.CHARGE_PLAN_START, argument="start"),
    DecTimeDescription(key="charge_plan_end", signal=s.CHARGE_PLAN_END, argument="end"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea las horas del plan de carga de cada coche que lo tiene."""
    runtime = entry.runtime_data
    for vehicle in runtime.vehicles.values():
        if vehicle.configured and not vehicle.has(FEATURE_CHARGE_PLAN):
            remove_entities(hass, "time", vehicle.info.vehicle_id, tuple(d.key for d in TIMES))
    async_add_entities(
        DecChargePlanTime(runtime, vehicle, description)
        for vehicle in runtime.vehicles.values()
        if vehicle.has(FEATURE_CHARGE_PLAN)
        for description in TIMES
    )
    async_add_entities(ScheduleTime(runtime, vehicle) for vehicle in schedule_vehicles(runtime))


def parse_clock(value: str | None) -> dt_time | None:
    """``"01:30"`` → ``time(1, 30)``; ``None`` si no hay."""
    if not value:
        return None
    hours, minutes = value.split(":")[:2]
    return dt_time(int(hours), int(minutes))


class DecChargePlanTime(DecDeepalEntity, TimeEntity):
    """Hora de inicio o de fin de la carga programada."""

    entity_description: DecTimeDescription

    def __init__(
        self,
        runtime: DecDeepalRuntime,
        vehicle: VehicleContext,
        description: DecTimeDescription,
    ) -> None:
        super().__init__(runtime, vehicle, "time", description.key)
        self.entity_description = description

    @property
    def native_value(self) -> dt_time | None:
        """La hora del plan (o la apuntada si está apagado)."""
        return parse_clock(self.signal(self.entity_description.signal))

    async def async_set_value(self, value: dt_time) -> None:
        """Cambia la hora (y el plan del coche si está encendido)."""
        await async_set_charge_plan(
            self.hass,
            self.runtime,
            self.vehicle,
            **{self.entity_description.argument: f"{value.hour:02d}:{value.minute:02d}"},
        )
