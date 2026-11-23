"""Plan de carga del coche (carga programada): leerlo y decidir qué órdenes mandar.

Sin Home Assistant: solo datos. Lo usa ``rest_map`` para las señales y
``charge_plan_control`` para cambiar el plan.

**Cómo lo guarda el coche** (REST condition, ``charge.chargePlanList``; lo
estudió Deepal Alternative 1.9 con S05 EV y PHEV reales):

- Cada plan es ``{"planId", "startTime", "endTime", "isValid", "timeZone"...}``.
  Las horas van como ``"HHMM"`` (``"0130"``). Sin ``endTime`` es un plan
  **«hasta llenar»** (empieza a una hora y carga hasta el límite).
- ``isValid`` = 1 es un plan activo. La lista es un historial: puede traer
  planes viejos inactivos.
- El S05 **no acepta** ``modify-plan``: un plan se **sustituye** (se borran
  los activos y se añade otro) y se apaga **borrándolo**.
- En el **PHEV**, el plan con id ``"1"`` es el que guarda la app oficial o el
  propio coche: no se puede apagar ni borrar desde fuera (el coche rechaza la
  orden o la ignora). Si está activo, hay que quitarlo en la app o en el coche.
- El plan tiene que durar al menos **30 minutos** (la app no deja menos).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from . import converters as c
from . import signals as s

#: Id del plan que guarda la app oficial (o el coche) en el PHEV. Ver arriba.
APP_PLAN_ID: Final = "1"
#: Duración mínima de un plan con hora de fin (minutos), como la app.
MIN_PLAN_MINUTES: Final = 30
#: Como mucho se borran tantos planes viejos de una vez (la lista es un historial).
MAX_DELETES: Final = 25


def plans(rest_raw: Mapping[str, Any] | None) -> list[dict[str, Any]] | None:
    """Lista de planes del REST; ``None`` si el informe no la trae."""
    charge = (rest_raw or {}).get("charge")
    raw = charge.get("chargePlanList") if isinstance(charge, Mapping) else None
    if not isinstance(raw, list):
        return None
    return [plan for plan in raw if isinstance(plan, dict)]


def is_active(plan: Mapping[str, Any]) -> bool:
    """¿Plan activo (``isValid`` = 1, con id)?"""
    return c.to_int(plan.get("isValid")) == 1 and plan.get("planId") is not None


def followed(plan_list: list[dict[str, Any]]) -> dict[str, Any] | None:
    """El plan que sigue el coche: el primero activo o, si no hay, el primero."""
    return next((plan for plan in plan_list if is_active(plan)), plan_list[0] if plan_list else None)


def hhmm_to_clock(value: Any) -> str | None:
    """``"0130"`` → ``"01:30"``; ``None`` si no es una hora válida."""
    text = str(value).strip().replace(":", "") if value is not None else ""
    if len(text) != 4 or not text.isdigit():
        return None
    hours, minutes = int(text[:2]), int(text[2:])
    return f"{hours:02d}:{minutes:02d}" if hours < 24 and minutes < 60 else None


def clock_to_hhmm(value: str) -> str:
    """``"01:30"`` (o ``"01:30:00"``) → ``"0130"``, el formato del coche."""
    parts = str(value).split(":")
    return f"{int(parts[0]):02d}{int(parts[1]):02d}"


def minutes_between(start: str, end: str) -> int:
    """Minutos de ``start`` a ``end`` (``"HH:MM"``), pasando la medianoche."""
    a, b = clock_to_hhmm(start), clock_to_hhmm(end)
    return (int(b[:2]) * 60 + int(b[2:]) - int(a[:2]) * 60 - int(a[2:])) % 1440


def signals_from_rest(rest_raw: Mapping[str, Any]) -> dict[str, Any]:
    """Señales del plan: activo, hora de inicio, de fin y «hasta llenar».

    Sin lista en el informe, nada (se conserva lo último). Con la lista vacía
    o sin planes activos, el plan está apagado; las horas del último plan se
    conservan (``KEEP_LAST``) para volver a encenderlo igual.
    """
    plan_list = plans(rest_raw)
    if plan_list is None:
        return {}
    values: dict[str, Any] = {s.CHARGE_PLAN_ON: any(is_active(plan) for plan in plan_list)}
    plan = followed(plan_list)
    if plan is not None and (start := hhmm_to_clock(plan.get("startTime"))) is not None:
        values[s.CHARGE_PLAN_START] = start
        end = hhmm_to_clock(plan.get("endTime"))
        values[s.CHARGE_PLAN_UNTIL_FULL] = end is None
        if end is not None:
            values[s.CHARGE_PLAN_END] = end
    return values


@dataclass(frozen=True)
class PlanChange:
    """Órdenes para dejar el plan como se pide (en este orden)."""

    #: Ids de plan que hay que borrar.
    delete: tuple[str, ...]
    #: Plan que hay que añadir: ``(inicio "HHMM", fin "HHMM" o None)``; ``None`` si ninguno.
    add: tuple[str, str | None] | None


class PlanError(ValueError):
    """El plan pedido no se puede poner. ``key`` es la clave del mensaje traducido."""

    def __init__(self, key: str, **placeholders: str) -> None:
        super().__init__(key)
        self.key = key
        self.placeholders = placeholders


def plan_change(
    plan_list: list[dict[str, Any]],
    *,
    enabled: bool,
    start: str | None,
    end: str | None,
    phev: bool,
) -> PlanChange:
    """Qué hay que mandar para dejar el plan encendido (con esas horas) o apagado.

    Args:
        plan_list: planes que tiene ahora el coche (REST, recién leído).
        enabled: dejar un plan activo o ninguno.
        start: hora de inicio ``"HH:MM"`` (obligatoria si ``enabled``).
        end: hora de fin ``"HH:MM"``; ``None`` = «hasta llenar».
        phev: el coche es un S05 PHEV (el plan ``"1"`` es de la app).

    Raises:
        PlanError: ``charge_plan_set_in_app`` (PHEV con el plan de la app
            activo), ``charge_plan_no_start`` o ``charge_plan_too_short``.
    """
    active_ids = [str(plan["planId"]) for plan in plan_list if is_active(plan)]
    if phev and APP_PLAN_ID in active_ids:
        # Ni se apaga ni se puede sustituir: dos planes activos a la vez.
        raise PlanError("charge_plan_set_in_app")
    deletable = tuple(dict.fromkeys(plan_id for plan_id in active_ids if not (phev and plan_id == APP_PLAN_ID)))
    if not enabled:
        return PlanChange(delete=deletable[:MAX_DELETES], add=None)
    if not start:
        raise PlanError("charge_plan_no_start")
    if end is not None and minutes_between(start, end) < MIN_PLAN_MINUTES:
        raise PlanError("charge_plan_too_short", start=start[:5], end=end[:5])
    return PlanChange(
        delete=deletable[:MAX_DELETES],
        add=(clock_to_hhmm(start), clock_to_hhmm(end) if end is not None else None),
    )
