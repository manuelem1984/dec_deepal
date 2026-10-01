"""Ubicación del coche, por si algún día la envía.

Hoy el Deepal S05 de España **no envía su posición** ni por MQTT ni por REST
(revisado en todas las capturas hasta el 01-10-2026). Aun así, Deepal
Alternative empezó a ocultar ``Lat``/``Lng`` en sus registros (v1.4.0-beta.3),
señal de que algún modelo o respuesta la incluye.

Por eso se busca de forma genérica: cualquier clave que se llame (sin
distinguir mayúsculas) ``lat``/``latitude`` y ``lng``/``lon``/``longitude``,
primero en el MQTT plano y después en el REST anidado. Si aparece, la entidad
"Ubicación" (deshabilitada por defecto) empezará a mostrarla sin tocar código.

Se descartan valores imposibles (fuera de rango) y el par 0,0 (típico de
"sin posición").
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from .converters import to_float

LATITUDE_KEYS: Final = frozenset({"lat", "latitude"})
LONGITUDE_KEYS: Final = frozenset({"lng", "lon", "longitude"})


def _search(data: Any, keys: frozenset[str], depth: int = 0) -> Any:
    """Primer valor cuya clave (en minúsculas) esté en ``keys``, buscando en profundidad."""
    if depth > 6:
        return None
    if isinstance(data, Mapping):
        for key, value in data.items():
            if str(key).lower() in keys and value not in (None, ""):
                return value
        for value in data.values():
            found = _search(value, keys, depth + 1)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _search(item, keys, depth + 1)
            if found is not None:
                return found
    return None


def find_location(*sources: Mapping[str, Any] | None) -> tuple[float, float] | None:
    """``(latitud, longitud)`` de la primera fuente que la tenga, o ``None``."""
    for source in sources:
        if not source:
            continue
        lat = to_float(_search(source, LATITUDE_KEYS))
        lon = to_float(_search(source, LONGITUDE_KEYS))
        if lat is None or lon is None:
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
            continue
        return lat, lon
    return None
