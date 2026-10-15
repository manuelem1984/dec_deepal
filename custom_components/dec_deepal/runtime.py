"""Objetos vivos de una entrada de configuración (una cuenta).

Home Assistant guarda en ``entry.runtime_data`` un :class:`DecDeepalRuntime`
por cada cuenta configurada. Ahí vive todo lo que se crea al arrancar y se
destruye al descargar la integración:

::

    DecDeepalRuntime  (una cuenta)
    ├── country       país de la cuenta (de countries.yaml)
    ├── account       sesión compartida + renovación (api/account.py)
    ├── client        lecturas (api/client.py)
    ├── commands      comandos firmados (api/commands.py)
    ├── recorder      registro de depuración (debug/recorder.py)
    ├── registries    catálogos: países, vehículos, iconos
    ├── alerts        avisos al móvil y fichas de mantenimiento (alerts.py)
    └── vehicles      {vehicle_id: VehicleContext}
        └── VehicleContext  (un coche)
            ├── info         datos del servidor (VIN, modelo...)
            ├── model        modelo del catálogo reconocido
            ├── trim/color   elegidos en Configurar (o pista automática)
            ├── coordinator  lecturas periódicas (coordinator.py)
            └── runner       ejecución de comandos (command_runner.py)

También contiene la carga (única por arranque) de los catálogos, que se
comparten entre todas las cuentas.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .api.account import DeepalAccount
from .api.client import DeepalClient
from .api.commands import DeepalCommands
from .api.models import Capabilities, VehicleInfo
from .const import DOMAIN, INTEGRATION_DIR
from .debug.recorder import DebugRecorder
from .registries import Registries, load_all
from .registries.countries import Country
from .registries.vehicles import VehicleModel

if TYPE_CHECKING:
    from .alerts import AlertManager
    from .command_runner import CommandRunner
    from .coordinator import VehicleCoordinator

_LOGGER = logging.getLogger(__name__)

_REGISTRIES_KEY = "registries"


@dataclass(slots=True)
class VehicleContext:
    """Todo lo relativo a un coche concreto de la cuenta."""

    info: VehicleInfo
    model: VehicleModel
    trim: str | None
    color: str | None
    coordinator: VehicleCoordinator
    runner: CommandRunner
    #: Modelo reconocido por el nombre que da el servidor (solo sugerencia).
    suggested_model: VehicleModel | None = None
    #: ``True`` si el usuario ya eligió el modelo (si no, funciona como genérico).
    configured: bool = False
    #: Llanta elegida en Configurar (la efectiva la da :attr:`wheel`).
    wheels: str | None = None
    #: Capacidades del servidor, solo para diagnóstico.
    capabilities: Capabilities | None = None
    #: Resultado de la última descarga de la imagen oficial (diagnóstico).
    official_image_status: dict[str, Any] = field(default_factory=dict)
    #: Imagen oficial ya descargada ``(bytes, content_type)``; la comparten
    #: "Imagen oficial" e "Vista lateral" (cuando no hay foto del catálogo).
    official_image_cache: tuple[bytes, str] | None = None

    @property
    def wheel(self) -> str | None:
        """Llanta que lleva el coche (la fija de la versión, la elegida o la de por defecto)."""
        return self.model.wheel_for(self.trim, self.wheels)

    def has(self, feature: str) -> bool:
        """¿El coche tiene esta función? (según modelo y versión)."""
        return self.model.has(feature, self.trim)


@dataclass(slots=True)
class DecDeepalRuntime:
    """Objetos vivos de una cuenta configurada."""

    country: Country
    account: DeepalAccount
    client: DeepalClient
    commands: DeepalCommands
    recorder: DebugRecorder
    registries: Registries
    vehicles: dict[str, VehicleContext] = field(default_factory=dict)
    #: Avisos y mantenimiento (se crea al arrancar la cuenta).
    alerts: AlertManager | None = None
    #: Últimas capturas por vehículo (servicio capture_snapshot).
    captures: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


type DecDeepalConfigEntry = ConfigEntry[DecDeepalRuntime]


async def async_get_registries(hass: HomeAssistant) -> Registries:
    """Carga los catálogos una sola vez por arranque y los comparte.

    La lectura de ficheros es bloqueante, así que se hace en un hilo aparte.
    Los avisos sobre iconos (nombres raros, SVG incompatibles) se escriben
    en el registro de Home Assistant para que el colaborador los vea.

    Raises:
        RegistryError: algún catálogo tiene errores (el mensaje dice cuál).
    """
    domain_data = hass.data.setdefault(DOMAIN, {})
    if _REGISTRIES_KEY not in domain_data:
        registries = await hass.async_add_executor_job(load_all, INTEGRATION_DIR)
        for warning in registries.icons.warnings:
            _LOGGER.warning("Iconos: %s", warning)
        _LOGGER.debug(
            "Catálogos cargados: %d países, %d modelos, %d iconos SVG",
            len(registries.countries.countries),
            len(registries.vehicles.models),
            len(registries.icons.available),
        )
        domain_data[_REGISTRIES_KEY] = registries
    return domain_data[_REGISTRIES_KEY]


def vehicle_device(hass: HomeAssistant, entry_id: str, vehicle_id: str) -> dr.DeviceEntry | None:
    """Dispositivo de Home Assistant de un coche (o ``None`` si aún no existe).

    Desde Home Assistant 2026.10 un identificador solo es único dentro de su
    cuenta, y ``async_get_device(identifiers=...)`` está obsoleto (deja de
    funcionar en la 2027.8). Las versiones anteriores no tienen la búsqueda
    nueva, así que se usa la que haya.
    """
    registry = dr.async_get(hass)
    identifier = (DOMAIN, vehicle_id)
    if hasattr(registry, "async_get_device_by_identifier"):
        return registry.async_get_device_by_identifier(identifier, entry_id)
    return registry.async_get_device(identifiers={identifier})


def device_entry_ids(device: dr.DeviceEntry) -> list[str]:
    """Cuentas a las que pertenece un dispositivo.

    Desde Home Assistant 2026.10 un dispositivo es de una sola cuenta
    (``config_entry_id``) y ``config_entries`` está obsoleto; antes solo
    existía ``config_entries``.
    """
    entry_id = getattr(device, "config_entry_id", None)
    if entry_id is not None:
        return [entry_id]
    return list(getattr(device, "config_entries", ()))

