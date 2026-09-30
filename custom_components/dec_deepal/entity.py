"""Entidad base de DEC Deepal.

Todas las entidades heredan de :class:`DecDeepalEntity`, que aporta:

- **Dispositivo:** todas las entidades de un coche cuelgan del mismo
  dispositivo (el coche), con modelo, versión, VIN y versión del software.
- **Nombre traducido:** ``translation_key`` = clave de la entidad; el texto
  está en ``translations/<idioma>.json`` → ``entity.<plataforma>.<clave>``.
- **Identificador único:** ``<vehicle_id>_<plataforma>_<clave>``.
- **Icono sin código:** se pregunta al registro de iconos (``icons/icons.yaml``
  + ``icons/svg``) usando la clave y el estado actual. Ver ``docs/iconos.md``.

Cada plataforma solo tiene que decir qué estado usar para el icono,
sobrescribiendo :meth:`icon_state` (por defecto, ninguno).
"""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COMMUNITY_URL, DOMAIN, MANUFACTURER, VERSION
from .coordinator import VehicleCoordinator
from .runtime import DecDeepalRuntime, VehicleContext


class DecDeepalEntity(CoordinatorEntity[VehicleCoordinator]):
    """Base de todas las entidades de un vehículo."""

    _attr_has_entity_name = True

    def __init__(
        self,
        runtime: DecDeepalRuntime,
        vehicle: VehicleContext,
        platform: str,
        key: str,
    ) -> None:
        """Crea la entidad.

        Args:
            runtime: objetos vivos de la cuenta.
            vehicle: el coche al que pertenece.
            platform: ``"sensor"``, ``"lock"``... (forma parte del id único).
            key: clave de la entidad; también es su ``translation_key`` y su
                nombre en ``icons.yaml``.
        """
        super().__init__(vehicle.coordinator)
        self.runtime = runtime
        self.vehicle = vehicle
        self.key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{vehicle.info.vehicle_id}_{platform}_{key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vehicle.info.vehicle_id)},
            name=vehicle.info.display_name,
            manufacturer=MANUFACTURER,
            # "Deepal S05 Max (2024-25)": modelo y versión en un solo texto
            # (ver "nombre_con_version" en vehicles.yaml).
            model=vehicle.model.display_name(vehicle.trim),
            serial_number=vehicle.info.vin,
            sw_version=VERSION,
            configuration_url=COMMUNITY_URL,
        )

    # ------------------------------------------------------------------
    # Acceso a datos
    # ------------------------------------------------------------------

    def signal(self, name: str) -> Any:
        """Valor actual de una señal (``None`` si no hay datos)."""
        data = self.coordinator.data
        return None if data is None else data.get(name)

    # ------------------------------------------------------------------
    # Iconos
    # ------------------------------------------------------------------

    def icon_state(self) -> str | None:
        """Estado que se usa para elegir el icono (``None`` = sin estados).

        Las plataformas lo sobrescriben: ``"on"``/``"off"``, ``"open"``/
        ``"closed"``, ``"locked"``/``"unlocked"``, el nivel, la opción...
        """
        return None

    @property
    def icon(self) -> str | None:
        """Icono resuelto por el registro de iconos (ver ``icons/icons.yaml``).

        ``None`` deja que Home Assistant ponga su icono estándar.
        """
        return self.runtime.registries.icons.resolve(self.key, self.icon_state())
