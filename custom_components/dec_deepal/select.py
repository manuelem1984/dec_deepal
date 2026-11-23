"""Listas de opciones: días de la climatización programada (ver ``climate_schedule.py``)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .climate_schedule_entities import ScheduleDays, schedule_vehicles
from .runtime import DecDeepalConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea los días de la climatización programada de cada coche."""
    runtime = entry.runtime_data
    async_add_entities(ScheduleDays(runtime, vehicle) for vehicle in schedule_vehicles(runtime))
