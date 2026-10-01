"""Ocultar datos sensibles antes de mostrarlos o guardarlos.

Se aplica a todo lo que sale de la integración hacia el usuario: diagnósticos,
registro de depuración y capturas. Dos mecanismos combinados:

1. **Nombre exacto** (:data:`EXACT_KEYS`): claves conocidas.
2. **Contiene** (:data:`SENSITIVE_PARTS`): cualquier clave cuyo nombre
   contenga una de estas partes, sin distinguir mayúsculas. Así, un campo
   sensible nuevo que nadie haya añadido a la lista también se oculta.

Además, los valores de texto que parecen un JWT se ocultan aunque su clave
parezca inocente.
"""

from __future__ import annotations

import re
from typing import Any, Final

REDACTED: Final = "**OCULTO**"

#: Claves concretas que siempre se ocultan.
EXACT_KEYS: Final = frozenset(
    {
        "vin",
        "VIN",
        "vinCode",
        "vehicle_vin",
        "vehicle_id",
        "vehicleId",
        "carId",
        "car_id",
        "cid",
        "uid",
        "ruid",
        "did",
        "image_url",
        "lat",
        "lon",
        "lng",
        "licensePlate",
        "license_plate",
        "plateNumber",
        "seriralNo",
        "sign",
        "safeCode",
        "pubKey",
        "authCode",
        "auth_code",
    }
)

#: Partes de nombre que delatan un dato sensible.
SENSITIVE_PARTS: Final = (
    "token",
    "password",
    "secret",
    "private",
    "pin",
    "serial",
    # "vin" NO va aquí: "driving" lo contiene y ocultaba claves inocentes como
    # "unlockKeyDrivingStatus". El VIN se oculta por nombre exacto (EXACT_KEYS).
    "device_id",
    "deviceid",
    "user_id",
    "userid",
    "email",
    "mobile",
    "phone",
    "latitude",
    "longitude",
    "plate",  # licensePlate, plateNumber, license_plate...
    "authorization",
)

_JWT: Final = re.compile(r"^eyJ[\w-]+\.[\w-]+\.[\w-]+$")


#: Las mismas claves exactas, en minúsculas: la comparación no distingue
#: mayúsculas (Deepal manda a veces ``Lat``/``Lng``, visto por Deepal
#: Alternative en v1.4.0-beta.3).
_EXACT_KEYS_LOWER: Final = frozenset(key.lower() for key in EXACT_KEYS)


def is_sensitive_key(key: Any) -> bool:
    """¿Hay que ocultar el valor de esta clave? (sin distinguir mayúsculas)."""
    lowered = str(key).lower()
    if lowered in _EXACT_KEYS_LOWER:
        return True
    return any(part in lowered for part in SENSITIVE_PARTS)


def redact(value: Any) -> Any:
    """Copia de ``value`` con los datos sensibles ocultos (recursivo)."""
    if isinstance(value, dict):
        return {
            key: REDACTED if is_sensitive_key(key) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str) and _JWT.match(value):
        return REDACTED
    return value


def redact_topic(topic: str) -> str:
    """Oculta los identificadores de un topic MQTT ``$vdp/<did>/...``."""
    parts = topic.split("/")
    if len(parts) > 2 and parts[0] == "$vdp":
        parts[1] = REDACTED
    return "/".join(parts)
