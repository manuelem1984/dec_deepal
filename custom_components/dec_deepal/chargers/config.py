"""Validar lo que manda el panel: un cargador, las opciones del límite y el límite de un coche."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from typing import Any

from .models import CarLimit, ChargerConfig, LimitSettings
from .const import (
    COVERAGES,
    COVERAGE_UNKNOWN,
    DEFAULT_LIMIT,
    DEFAULT_LOSS,
    FULL_EVERY_CHOICES,
    LIMIT_CHOICES,
    LOCK_FULL_CHOICES,
    MAX_LOSS,
    READ_CHOICES,
    RELOCK_CHOICES,
    REMIND_CHOICES,
    ROLES,
    ROLE_DOMAINS,
    ROLE_PLUGGED,
    UNLOCK_MODES,
    UNLOCK_NONE,
)


class ChargerError(ValueError):
    """Un cargador mal configurado o una orden que no se puede cumplir."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _choice(value: Any, choices: Iterable[Any], default: Any) -> Any:
    return value if value in tuple(choices) else default


def clean_charger(raw: Mapping[str, Any], known: Iterable[str] = ()) -> ChargerConfig:
    """Un cargador válido a partir de lo que manda el panel.

    Raises:
        ChargerError: sin nombre (``charger_name``), sin entidad de manguera
            (``charger_plugged``) o con un papel en un dominio que no vale
            (``charger_entity``).
    """
    name = str(raw.get("name") or "").strip()[:40]
    if not name:
        raise ChargerError("charger_name")
    entities: dict[str, str] = {}
    for role in ROLES:
        entity_id = str((raw.get("entities") or {}).get(role) or "").strip()
        if not entity_id:
            continue
        if entity_id.split(".", 1)[0] not in ROLE_DOMAINS[role]:
            raise ChargerError("charger_entity")
        entities[role] = entity_id
    if ROLE_PLUGGED not in entities:
        raise ChargerError("charger_plugged")
    known = set(known)
    vehicles = [str(item) for item in dict.fromkeys(raw.get("vehicles") or ()) if not known or str(item) in known]
    try:
        loss = float(raw.get("loss", DEFAULT_LOSS))
    except (TypeError, ValueError):
        loss = DEFAULT_LOSS
    price = raw.get("price")
    try:
        price = None if price in (None, "") else max(0.0, round(float(price), 4))
    except (TypeError, ValueError):
        price = None
    price_entity = str(raw.get("price_entity") or "").strip()
    if price_entity and price_entity.split(".", 1)[0] not in ("sensor", "input_number", "number"):
        raise ChargerError("charger_entity")
    return {
        "id": str(raw.get("id") or uuid.uuid4().hex[:10]),
        "name": name,
        "entities": entities,
        # En un interruptor: ¿encendido = bloqueado? (en una cerradura no hace falta).
        "lock_on_locked": bool(raw.get("lock_on_locked", True)),
        "vehicles": vehicles,
        "coverage": _choice(raw.get("coverage"), COVERAGES, COVERAGE_UNKNOWN),
        "unlock": _choice(raw.get("unlock"), UNLOCK_MODES, UNLOCK_NONE),
        "notify_confirm": bool(raw.get("notify_confirm", True)),
        "remind_minutes": _choice(raw.get("remind_minutes"), REMIND_CHOICES, 15),
        "relock": bool(raw.get("relock", True)),
        "relock_minutes": _choice(raw.get("relock_minutes"), RELOCK_CHOICES, 5),
        "relock_notify": bool(raw.get("relock_notify", True)),
        # Bloquear al terminar: enchufado, al 100 % y sin cargar ``lock_full_minutes``.
        "lock_full": bool(raw.get("lock_full", True)),
        "lock_full_minutes": _choice(raw.get("lock_full_minutes"), LOCK_FULL_CHOICES, 30),
        # Con cobertura (o "no lo sé"): despertar el coche cada N min mientras carga.
        "read_interval": _choice(raw.get("read_interval"), READ_CHOICES, 15),
        "loss": min(MAX_LOSS, max(0.0, round(loss, 1))),
        "learn": bool(raw.get("learn", True)),
        "price": price,
        "price_entity": price_entity,
    }


def clean_limit(raw: Mapping[str, Any]) -> LimitSettings:
    """Opciones del límite de carga y del recordatorio del 100 % (Ajustes)."""
    return {
        "enabled": bool(raw.get("enabled", False)),
        "notify": bool(raw.get("notify", True)),
        "remind": bool(raw.get("remind", False)),
        "every": _choice(raw.get("every"), FULL_EVERY_CHOICES, 4),
        "auto": bool(raw.get("auto", False)),
    }


def _clean_car(raw: Mapping[str, Any]) -> CarLimit:
    try:
        incomplete = max(0, int(raw.get("incomplete") or 0))
    except (TypeError, ValueError):
        incomplete = 0
    return {
        "limit": _choice(raw.get("limit"), LIMIT_CHOICES, DEFAULT_LIMIT),
        "once_full": bool(raw.get("once_full", False)),
        "incomplete": incomplete,
    }
