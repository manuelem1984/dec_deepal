"""Cambiar el plan de carga del coche (carga programada). ⚠️ Sin probar con nuestros coches.

Lo usan el interruptor «Carga programada», las horas de inicio y fin, el
interruptor «Hasta llenar» y la acción ``dec_deepal.set_charge_plan``.

Pasos (las reglas del coche están en ``telemetry/charge_plan.py``):

1. Se relee la lista de planes del servidor (la del coordinador puede ir
   por detrás justo después de otro cambio).
2. ``plan_change`` decide qué borrar y qué añadir, o explica por qué no se
   puede (plan de la app activo en el PHEV, menos de 30 minutos...).
3. Se mandan las órdenes de una en una, esperando a que el coche acepte
   cada una. En el EV primero se borran los planes activos y luego se añade
   el nuevo; en el PHEV, primero se añade (así no se queda sin plan si el
   borrado falla) y después se borran los anteriores, como Deepal Alternative.
4. Al acabar se muestran ya los valores nuevos y se relee el coche.

Con el plan apagado, cambiar una hora solo la apunta (para encenderlo luego):
no se manda nada al coche.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .api.errors import DeepalError
from .command_runner import to_ha_error
from .const import DOMAIN
from .registries.vehicles import FEATURE_FUEL
from .runtime import DecDeepalRuntime, VehicleContext
from .telemetry import charge_plan as cp
from .telemetry import signals as s

_LOGGER = logging.getLogger(__name__)


def gmt_offset(hass: HomeAssistant, when: datetime | None = None) -> str:
    """Zona horaria de Home Assistant como la escribe la app: ``"GMT+01:00"``."""
    try:
        offset = (when or datetime.now(ZoneInfo(hass.config.time_zone))).astimezone(
            ZoneInfo(hass.config.time_zone)
        ).utcoffset()
    except (ValueError, KeyError):  # zona mal configurada: no se rompe la orden
        offset = None
    minutes = int(offset.total_seconds() // 60) if offset is not None else 0
    sign = "+" if minutes >= 0 else "-"
    hours, rest = divmod(abs(minutes), 60)
    return f"GMT{sign}{hours:02d}:{rest:02d}"


def _plan_error(err: cp.PlanError) -> HomeAssistantError:
    return HomeAssistantError(
        translation_domain=DOMAIN, translation_key=err.key, translation_placeholders=err.placeholders or None
    )


async def async_set_charge_plan(
    hass: HomeAssistant,
    runtime: DecDeepalRuntime,
    vehicle: VehicleContext,
    *,
    enabled: bool | None = None,
    start: str | None = None,
    end: str | None = None,
    until_full: bool | None = None,
) -> None:
    """Deja el plan de carga del coche como se pide.

    Lo que no se indica se queda como está (o como se apuntó la última vez).

    Args:
        enabled: plan activo o ninguno. ``None``: como esté ahora.
        start: hora de inicio ``"HH:MM"``.
        end: hora de fin ``"HH:MM"``.
        until_full: ``True`` = sin hora de fin (carga hasta el límite).

    Raises:
        HomeAssistantError: con un mensaje traducido si no se puede.
    """
    coordinator = vehicle.coordinator
    current = coordinator.data
    get = current.get if current is not None else (lambda _signal: None)
    is_on = bool(get(s.CHARGE_PLAN_ON)) if enabled is None else enabled
    start = start or get(s.CHARGE_PLAN_START)
    if until_full is None:
        until_full = bool(get(s.CHARGE_PLAN_UNTIL_FULL)) if end is None else False
    end = None if until_full else (end or get(s.CHARGE_PLAN_END))
    wanted = {
        s.CHARGE_PLAN_START: start[:5] if start else None,
        s.CHARGE_PLAN_END: end[:5] if end else None,
        s.CHARGE_PLAN_UNTIL_FULL: until_full,
    }

    if not is_on and not get(s.CHARGE_PLAN_ON):
        # Apagado y sigue apagado: solo se apuntan las horas para luego.
        coordinator.set_local_values({key: value for key, value in wanted.items() if value is not None})
        return
    if is_on and not until_full and end is None:
        raise _plan_error(cp.PlanError("charge_plan_no_end"))

    vehicle_id = vehicle.info.vehicle_id
    try:
        rest = await coordinator.client.get_condition(vehicle_id)
    except DeepalError as err:
        raise to_ha_error(err) from err
    plan_list = cp.plans(rest) or []
    phev = vehicle.has(FEATURE_FUEL)
    try:
        change = cp.plan_change(plan_list, enabled=is_on, start=start, end=end, phev=phev)
    except cp.PlanError as err:
        raise _plan_error(err) from err

    # La zona del plan que ya tiene el coche manda; si no, la de Home Assistant.
    followed = cp.followed(plan_list) or {}
    time_zone = str(followed.get("timeZone") or gmt_offset(hass))
    commands = runtime.commands
    runner = vehicle.runner
    _LOGGER.debug("%s: plan de carga %s (borrar %s)", vehicle.info.display_name, change.add, change.delete)

    async def _delete_all() -> None:
        for plan_id in change.delete:
            await runner.run(
                "charge_plan_delete",
                lambda plan_id=plan_id: commands.charge_plan_delete(vehicle_id, plan_id),
                serialize=True,
                refresh_after=False,
            )

    async def _add() -> None:
        if change.add is None:
            return
        plan_start, plan_end = change.add
        await runner.run(
            "charge_plan_add",
            lambda: commands.charge_plan_add(vehicle_id, start=plan_start, end=plan_end, time_zone=time_zone),
            serialize=True,
            refresh_after=False,
        )

    if phev:
        await _add()
        await _delete_all()
    else:
        await _delete_all()
        await _add()

    coordinator.apply_optimistic(
        {s.CHARGE_PLAN_ON: is_on, **{key: value for key, value in wanted.items() if value is not None}}
    )
    await runner.refresh_soon()


def vehicle_plan_values(vehicle: VehicleContext) -> dict[str, Any]:
    """Valores actuales del plan (para la tarjeta y el diagnóstico)."""
    data = vehicle.coordinator.data
    if data is None:
        return {}
    return {
        signal: data.get(signal)
        for signal in (s.CHARGE_PLAN_ON, s.CHARGE_PLAN_START, s.CHARGE_PLAN_END, s.CHARGE_PLAN_UNTIL_FULL)
    }
