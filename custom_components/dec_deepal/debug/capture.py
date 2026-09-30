"""Capturas de estado y comparación entre capturas.

Pensado para el "plan de prueba en dos capturas" que ya usaba la comunidad
para descubrir qué significa cada dato del coche:

1. **Captura A** en reposo (coche cerrado, sin contacto, sin cargar...).
2. Se hace **un cambio concreto** (bajar una ventanilla, encender el clima...).
3. **Captura B.**
4. La comparación dice exactamente qué claves en bruto cambiaron y de qué
   valor a qué valor. Así se identifica el dato y su escala.

Una captura incluye:
- ``senales``: valores ya interpretados (lo que ven las entidades).
- ``origen``: de dónde salió cada valor (mqtt / rest / anterior / optimista).
- ``mqtt``: parámetros MQTT en bruto.
- ``mqtt_sin_mapear``: claves MQTT que ninguna señal usa todavía.
- ``rest``: JSON REST en bruto.

Todo pasa por :func:`~.redact.redact` antes de guardarse.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from ..telemetry.mqtt_map import MAPPED_MQTT_KEYS
from ..telemetry.state import VehicleState
from .redact import redact


def _jsonable(value: Any) -> Any:
    """Convierte fechas a texto ISO para que todo sea serializable a JSON."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    """Aplana un JSON anidado: ``{"a": {"b": 1}}`` → ``{"a.b": 1}``."""
    flat: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            flat.update(_flatten(item, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            flat.update(_flatten(item, f"{prefix}[{index}]"))
    else:
        flat[prefix] = value
    return flat


def build_snapshot(label: str, vehicle_name: str, state: VehicleState | None) -> dict[str, Any]:
    """Construye una captura del estado actual de un vehículo."""
    snapshot: dict[str, Any] = {
        "etiqueta": label,
        "vehiculo": vehicle_name,
        "hora": datetime.now(UTC).isoformat(),
    }
    if state is None:
        snapshot["aviso"] = "Todavía no hay datos del vehículo"
        return snapshot
    mqtt = state.mqtt_raw or {}
    snapshot.update(
        {
            "lectura": state.fetched_at.isoformat(),
            "senales": _jsonable(dict(state.values)),
            "origen": dict(state.sources),
            "mqtt": _jsonable(mqtt),
            "mqtt_sin_mapear": sorted(set(mqtt) - MAPPED_MQTT_KEYS),
            "mqtt_servicios_desconocidos": _jsonable(state.mqtt_unknown),
            "rest": _jsonable(state.rest_raw or {}),
            "avisos": list(state.warnings),
        }
    )
    return redact(snapshot)


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Qué cambió entre dos capturas, sección por sección.

    Returns:
        ``{"mqtt": {"clave": {"antes": x, "despues": y}}, "rest": {...},
        "senales": {...}}``. Solo aparecen las claves que cambiaron.
    """
    result: dict[str, Any] = {
        "desde": before.get("etiqueta"),
        "hasta": after.get("etiqueta"),
    }
    for section in ("senales", "mqtt", "rest"):
        old = _flatten(before.get(section) or {})
        new = _flatten(after.get(section) or {})
        changes = {
            key: {"antes": old.get(key), "despues": new.get(key)}
            for key in sorted(set(old) | set(new))
            if old.get(key) != new.get(key)
        }
        result[section] = changes
    return result
