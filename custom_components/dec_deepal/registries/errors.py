"""Errores y utilidades comunes de los cargadores de catálogos."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class RegistryError(Exception):
    """Un fichero de catálogo no existe o tiene un error de contenido.

    El mensaje indica el fichero y la ruta del campo problemático, por ejemplo:
    ``vehicles.yaml → modelos.s05_2024.versiones.max: falta 'nombre'``.
    """


def read_yaml(path: Path) -> dict[str, Any]:
    """Lee un YAML y comprueba que su raíz es un diccionario.

    Raises:
        RegistryError: no existe, no es YAML válido o la raíz no es un dict.
    """
    if not path.is_file():
        raise RegistryError(f"No existe el fichero de catálogo: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as err:
        raise RegistryError(f"{path.name}: YAML no válido: {err}") from err
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise RegistryError(f"{path.name}: la raíz debe ser un diccionario")
    return data


def require(mapping: Any, key: str, where: str) -> Any:
    """Devuelve ``mapping[key]`` o lanza un error claro si falta."""
    if not isinstance(mapping, dict):
        raise RegistryError(f"{where}: se esperaba un diccionario")
    if key not in mapping or mapping[key] is None:
        raise RegistryError(f"{where}: falta '{key}'")
    return mapping[key]


def as_dict(value: Any, where: str) -> dict[str, Any]:
    """Comprueba que ``value`` es un diccionario (o vacío)."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise RegistryError(f"{where}: se esperaba un diccionario")
    return value


def as_str_list(value: Any, where: str) -> tuple[str, ...]:
    """Comprueba que ``value`` es una lista de textos (o vacía)."""
    if value is None:
        return ()
    if not isinstance(value, list):
        raise RegistryError(f"{where}: se esperaba una lista")
    return tuple(str(item) for item in value)


def state_key(value: Any) -> str:
    """Normaliza la clave de un estado.

    YAML convierte ``on``/``off`` sin comillas en ``True``/``False``; aquí se
    devuelven a ``"on"``/``"off"`` para que no importe si se pusieron comillas.
    """
    if value is True:
        return "on"
    if value is False:
        return "off"
    return str(value)
