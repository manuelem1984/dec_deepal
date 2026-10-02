"""Catálogos editables: países, vehículos e iconos.

Cada catálogo es un fichero YAML en su propia carpeta, pensado para que un
colaborador pueda editarlo sin saber Python:

====================================  =======================================
Fichero de datos                      Cargador
====================================  =======================================
``countries/countries.yaml``          :mod:`.countries`
``vehicles/vehicles.yaml`` + fotos    :mod:`.vehicles`
``vehicles/vista_planta/`` + capas    :mod:`.top_view` (lo carga vehicles)
``icons/icons.yaml`` + ``icons/svg``  :mod:`.icons`
====================================  =======================================

Los cargadores son Python puro (sin Home Assistant) y **validan** el fichero:
si falta un campo o un valor no tiene sentido, lanzan :class:`RegistryError`
con un mensaje que dice exactamente qué y dónde, en vez de fallar más tarde
con un error críptico.

Leer ficheros es una operación bloqueante; Home Assistant llama a
:func:`load_all` en un hilo aparte (ver ``runtime.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .countries import CountryRegistry, load_countries
from .errors import RegistryError
from .icons import IconRegistry, load_icons
from .vehicles import VehicleRegistry, load_vehicles

__all__ = [
    "CountryRegistry",
    "IconRegistry",
    "Registries",
    "RegistryError",
    "VehicleRegistry",
    "load_all",
]


@dataclass(frozen=True, slots=True)
class Registries:
    """Los tres catálogos cargados."""

    countries: CountryRegistry
    vehicles: VehicleRegistry
    icons: IconRegistry


def load_all(integration_dir: Path) -> Registries:
    """Carga los tres catálogos desde la carpeta de la integración.

    Raises:
        RegistryError: algún fichero no existe o tiene errores.
    """
    return Registries(
        countries=load_countries(integration_dir / "countries" / "countries.yaml"),
        vehicles=load_vehicles(integration_dir / "vehicles"),
        icons=load_icons(integration_dir / "icons"),
    )
