"""Ubicación del coche (rastreador GPS en el mapa). Deshabilitada por defecto.

Hoy el Deepal S05 de España **no envía su posición** (ver
``telemetry/location.py``): la entidad se crea **deshabilitada** para que no
aparezca vacía. Si algún día el servidor empieza a enviarla, basta con
habilitarla en la ficha del dispositivo; no hará falta tocar código.

La posición es un dato personal: en los diagnósticos y capturas sale oculta.
"""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import DecDeepalEntity
from .runtime import DecDeepalConfigEntry, DecDeepalRuntime, VehicleContext
from .telemetry import signals as s


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Crea la ubicación de cada coche (deshabilitada)."""
    runtime = entry.runtime_data
    async_add_entities(DecLocation(runtime, vehicle) for vehicle in runtime.vehicles.values())


class DecLocation(DecDeepalEntity, TrackerEntity):
    """Posición GPS del coche, si el servidor la envía."""

    _attr_entity_registry_enabled_default = False

    def __init__(self, runtime: DecDeepalRuntime, vehicle: VehicleContext) -> None:
        super().__init__(runtime, vehicle, "device_tracker", "location")

    @property
    def source_type(self) -> SourceType:
        """Origen de la posición: GPS del coche."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Latitud (``None`` mientras el coche no la envíe)."""
        return self.signal(s.LATITUDE)

    @property
    def longitude(self) -> float | None:
        """Longitud (``None`` mientras el coche no la envíe)."""
        return self.signal(s.LONGITUDE)
