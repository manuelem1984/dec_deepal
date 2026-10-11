"""Datos de cada coche (mantenimiento, ITV, seguro, apariencia): formato, migración y copia.

Lógica pura (sin Home Assistant) para que se pueda probar sola. Quién la usa:
``vehicle_store.py`` (el almacén) y Configurar → Datos de los coches.

Los datos van **por coche, no por cuenta**: la clave es el bastidor. Así, si
se quita la cuenta y se vuelve a añadir, el coche recupera su historial.

Formato del almacén (``.storage/dec_deepal.vehicles``)::

    {"cars": {"<bastidor>": {
        "vehicle_id": "...", "name": "Changote",
        "maintenance": {...}, "itv": {...}, "insurance": {...},
        "appearance": {"model": "s05_2024", "trim": "max", "color": "...", "wheels": "cover"},
        "active": ["warning_abs"], "odometer": 37500.0}}}

La **apariencia** (modelo, versión, color y llanta) manda en las opciones de
la cuenta; aquí se guarda una copia para devolvérsela al coche si la cuenta
se quita y se vuelve a añadir, y para que viaje en las copias de seguridad.

Cambiar el formato: subir ``DATA_VERSION`` y añadir el paso en :func:`migrate`.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final

from . import documents as doc
from . import maintenance as mt
from .const import OPT_COLOR, OPT_MODEL, OPT_TRIM, OPT_WHEELS

#: Versión del formato del almacén y de las copias.
DATA_VERSION: Final = 1
#: Marca de las copias: evita cargar por error un fichero que no es nuestro.
EXPORT_FORMAT: Final = "dec_deepal.datos"

MAINTENANCE: Final = "maintenance"
ITV: Final = "itv"
INSURANCE: Final = "insurance"
APPEARANCE: Final = "appearance"
ACTIVE: Final = "active"
ODOMETER: Final = "odometer"
NAME: Final = "name"
VEHICLE_ID: Final = "vehicle_id"

#: Fichas que rellena el usuario, con quien sabe leerlas (para validarlas).
RECORDS: Final = {
    MAINTENANCE: mt.MaintenanceRecord.from_dict,
    ITV: doc.ItvRecord.from_dict,
    INSURANCE: doc.InsuranceRecord.from_dict,
}

#: Motivos por los que se rechaza una copia (claves de los textos de error).
ERROR_INVALID: Final = "invalid_file"
ERROR_NEWER: Final = "newer_file"
ERROR_EMPTY: Final = "empty_file"


class BackupError(ValueError):
    """La copia no se puede cargar. ``code`` es la clave del texto de error."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def car_key(vin: str | None, vehicle_id: str) -> str:
    """Clave de un coche: su bastidor; sin bastidor, el identificador del servidor."""
    vin = (vin or "").strip().upper()
    return vin or f"id:{vehicle_id}"


def migrate(data: Mapping[str, Any] | None, version: int) -> dict[str, Any]:
    """Lleva unos datos guardados con un formato anterior al actual.

    Hoy solo existe la versión 1. Cuando haya una 2, aquí irá
    ``if version < 2: ...`` (un paso por versión, en orden).
    """
    if version > DATA_VERSION:
        raise BackupError(ERROR_NEWER)
    cars = (data or {}).get("cars")
    return {"cars": dict(cars) if isinstance(cars, Mapping) else {}}


def from_legacy(legacy: Mapping[str, Any], keys: Mapping[str, str]) -> dict[str, dict[str, Any]]:
    """Convierte el almacén antiguo (uno por cuenta) al formato por coche.

    Args:
        legacy: ``{"maintenance": {<id del coche>: ...}, "itv": {...}, ...}``.
        keys: clave nueva (bastidor) de cada identificador de coche.
    """
    cars: dict[str, dict[str, Any]] = {}
    for section in (MAINTENANCE, ITV, INSURANCE, ACTIVE, ODOMETER):
        values = legacy.get(section)
        if not isinstance(values, Mapping):
            continue
        for vehicle_id, value in values.items():
            key = keys.get(str(vehicle_id)) or car_key(None, str(vehicle_id))
            cars.setdefault(key, {VEHICLE_ID: str(vehicle_id)})[section] = value
    return cars


def has_records(car: Mapping[str, Any]) -> bool:
    """¿Tiene el coche alguna ficha (mantenimiento, ITV o seguro)?"""
    return any(car.get(section) for section in RECORDS)


def has_data(car: Mapping[str, Any]) -> bool:
    """¿Tiene el coche algo que merezca una copia? (fichas o apariencia)."""
    return has_records(car) or bool(car.get(APPEARANCE))


def clean_appearance(raw: Any, models: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """Apariencia válida a partir de lo guardado, o ``None`` si no sirve.

    Args:
        raw: ``{"model": ..., "trim": ..., "color": ..., "wheels": ...}``.
        models: catálogo (``{id: modelo}``). Con él, se descarta un modelo que
            ya no existe y la versión, el color o la llanta que ese modelo no
            tiene. Sin él solo se comprueba la forma.
    """
    if not isinstance(raw, Mapping):
        return None
    model_id = raw.get(OPT_MODEL)
    if not isinstance(model_id, str) or not model_id.strip():
        return None
    values = {
        field: raw.get(field) if isinstance(raw.get(field), str) and raw[field].strip() else None
        for field in (OPT_TRIM, OPT_COLOR, OPT_WHEELS)
    }
    if models is not None:
        model = models.get(model_id)
        if model is None:
            return None
        allowed = {OPT_TRIM: model.trims, OPT_COLOR: model.colors, OPT_WHEELS: model.wheel_options}
        values = {
            field: value if value in allowed[field] else None for field, value in values.items()
        }
    appearance: dict[str, Any] = {
        OPT_MODEL: model_id,
        OPT_TRIM: values[OPT_TRIM],
        OPT_COLOR: values[OPT_COLOR],
    }
    if values[OPT_WHEELS]:
        appearance[OPT_WHEELS] = values[OPT_WHEELS]
    return appearance


def label(key: str, car: Mapping[str, Any]) -> str:
    """Nombre para enseñar un coche guardado: ``Changote (…123456)``."""
    tail = key[-6:] if not key.startswith("id:") else key[3:]
    name = str(car.get(NAME) or "").strip()
    return f"{name} (…{tail})" if name else f"Deepal …{tail}"


def export_payload(cars: Mapping[str, Mapping[str, Any]], now: datetime) -> dict[str, Any]:
    """Contenido de una copia: lo que rellenó el usuario, no el estado interno."""
    exported: dict[str, dict[str, Any]] = {}
    for key, car in cars.items():
        if not has_data(car):
            continue
        exported[key] = {
            field: car[field]
            for field in (VEHICLE_ID, NAME, MAINTENANCE, ITV, INSURANCE, APPEARANCE, ODOMETER)
            if car.get(field) not in (None, "", {})
        }
    return {
        "formato": EXPORT_FORMAT,
        "version": DATA_VERSION,
        "exportado": now.isoformat(timespec="seconds"),
        "coches": exported,
    }


def parse_backup(payload: Any) -> dict[str, dict[str, Any]]:
    """Comprueba una copia y devuelve sus coches, listos para guardar.

    Raises:
        BackupError: no es una copia nuestra, es de una versión posterior o
            no trae ningún coche con datos.
    """
    if not isinstance(payload, Mapping) or payload.get("formato") != EXPORT_FORMAT:
        raise BackupError(ERROR_INVALID)
    version = payload.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise BackupError(ERROR_INVALID)
    raw_cars = payload.get("coches")
    if not isinstance(raw_cars, Mapping):
        raise BackupError(ERROR_INVALID)
    cars = migrate({"cars": raw_cars}, version)["cars"]

    result: dict[str, dict[str, Any]] = {}
    for key, raw in cars.items():
        if not isinstance(key, str) or not key.strip() or not isinstance(raw, Mapping):
            raise BackupError(ERROR_INVALID)
        car: dict[str, Any] = {}
        for section, loader in RECORDS.items():
            if not raw.get(section):
                continue
            try:
                # Leer y volver a escribir: valida y descarta campos extraños.
                car[section] = loader(raw[section]).to_dict()
            except (AttributeError, KeyError, TypeError, ValueError) as err:
                raise BackupError(ERROR_INVALID) from err
        if raw.get(APPEARANCE):
            appearance = clean_appearance(raw[APPEARANCE])
            if appearance is None:
                raise BackupError(ERROR_INVALID)
            car[APPEARANCE] = appearance
        if not car:
            continue
        for field in (VEHICLE_ID, NAME):
            if isinstance(raw.get(field), str) and raw[field].strip():
                car[field] = raw[field].strip()[:80]
        odometer = raw.get(ODOMETER)
        if isinstance(odometer, (int, float)) and not isinstance(odometer, bool) and odometer >= 0:
            car[ODOMETER] = float(odometer)
        result[key.strip()] = car
    if not result:
        raise BackupError(ERROR_EMPTY)
    return result
