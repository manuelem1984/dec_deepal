"""Diario del coche: viajes y cargas, con energía y coste estimados (2.6.0b17).

Sin Home Assistant: funciones puras sobre un ``dict`` que se guarda (ver
``car_log_manager.py``). Con cada lectura del coche, :func:`update`:

- **Viaje:** del encendido al apagado. Se apuntan los km (cuentakilómetros) y
  el % de batería gastado; con la capacidad de la batería del catálogo, los
  kWh. Un viaje de menos de :data:`MIN_TRIP_KM` no se apunta (mover el coche
  en el garaje, encenderlo para climatizar...).
- **Carga:** de "cargando" a "no cargando", **con o sin cargador vinculado**.
  La energía es la que entró en la batería (Δ% por capacidad): no cuenta las
  pérdidas de la carga, así que el coste real es algo mayor. El precio es el
  de casa (AC) o el de carga rápida (DC), elegidos en las entidades del coche.

Los totales (km de viajes, kWh y coste de las cargas) solo suben: son los
sensores con ``state_class`` total que Home Assistant usa para sus
estadísticas por día, semana y mes.

Lo que se guarda (por coche)::

    {
        "trip": {...en curso...}, "charge": {...en curso...},
        "entries": [{"kind": "trip"|"charge", ...}, ...],   # las últimas MAX_ENTRIES
        "totals": {"trip_km": 0.0, "charge_kwh": 0.0, "charge_cost": 0.0},
        "prices": {"ac": 0.15, "dc": 0.45},
    }
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final

KIND_TRIP: Final = "trip"
KIND_CHARGE: Final = "charge"
#: Entradas que se guardan por coche (las más nuevas).
MAX_ENTRIES: Final = 300
#: Un viaje más corto no se apunta.
MIN_TRIP_KM: Final = 0.5
#: Una carga sin ganar batería y más corta que esto, tampoco (el coche dudando al enchufar).
MIN_CHARGE_SECONDS: Final = 120
#: Viajes que se usan para el consumo medio.
CONSUMPTION_TRIPS: Final = 10
#: Por debajo de esto, el consumo de un viaje no es de fiar (el % va en enteros).
MIN_CONSUMPTION_KM: Final = 20.0
PRICE_KINDS: Final = ("ac", "dc")


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def empty() -> dict[str, Any]:
    """Un diario vacío."""
    return {"entries": [], "totals": {"trip_km": 0.0, "charge_kwh": 0.0, "charge_cost": 0.0}, "prices": {}}


def clean(raw: Any) -> dict[str, Any]:
    """Lo guardado, validado (lo que no se entiende se descarta)."""
    log = empty()
    if not isinstance(raw, Mapping):
        return log
    for key in ("trip", "charge"):
        if isinstance(raw.get(key), Mapping) and isinstance(raw[key].get("start"), str):
            log[key] = dict(raw[key])
    entries = raw.get("entries")
    if isinstance(entries, list):
        log["entries"] = [dict(e) for e in entries if isinstance(e, Mapping) and e.get("kind") in (KIND_TRIP, KIND_CHARGE)][
            -MAX_ENTRIES:
        ]
    totals = raw.get("totals")
    if isinstance(totals, Mapping):
        for key in log["totals"]:
            if (value := _number(totals.get(key))) is not None and value >= 0:
                log["totals"][key] = value
    prices = raw.get("prices")
    if isinstance(prices, Mapping):
        log["prices"] = {k: v for k in PRICE_KINDS if (v := _number(prices.get(k))) is not None and v >= 0}
    return log


def _energy(delta_percent: float | None, capacity_kwh: float | None) -> float | None:
    if delta_percent is None or capacity_kwh is None:
        return None
    return round(delta_percent * capacity_kwh / 100, 2)


def update(
    log: dict[str, Any],
    values: Mapping[str, Any],
    now: datetime,
    capacity_kwh: float | None,
) -> list[dict[str, Any]]:
    """Pone al día el diario con una lectura. Devuelve las entradas nuevas (terminadas).

    Args:
        log: el diario (se cambia aquí mismo).
        values: ``power_on``, ``charging``, ``battery_level``, ``odometer_km`` y
            ``dc`` (cargando en continua) de la lectura; ``None`` = no se sabe.
        now: momento de la lectura.
        capacity_kwh: capacidad útil de la batería (catálogo); sin ella no hay kWh.
    """
    stamp = now.isoformat(timespec="seconds")
    level = _number(values.get("battery_level"))
    odometer = _number(values.get("odometer_km"))
    done: list[dict[str, Any]] = []

    # --- Viajes -----------------------------------------------------------------------
    power_on = values.get("power_on")
    trip = log.get("trip")
    if power_on is True and trip is None:
        log["trip"] = {"start": stamp, "start_km": odometer, "start_level": level}
    elif power_on is True and trip is not None:
        for key, value in (("start_km", odometer), ("start_level", level)):
            if trip.get(key) is None and value is not None:
                trip[key] = value
    elif power_on is False and trip is not None:
        del log["trip"]
        km = None if odometer is None or trip.get("start_km") is None else round(odometer - trip["start_km"], 1)
        if km is not None and km >= MIN_TRIP_KM:
            used = None if level is None or trip.get("start_level") is None else trip["start_level"] - level
            entry = {
                "kind": KIND_TRIP,
                "start": trip["start"],
                "end": stamp,
                "km": km,
                "start_level": trip.get("start_level"),
                "end_level": level,
                "kwh": _energy(used, capacity_kwh) if used is not None and used >= 0 else None,
            }
            done.append(entry)
            log["totals"]["trip_km"] = round(log["totals"]["trip_km"] + km, 1)

    # --- Cargas -----------------------------------------------------------------------
    charging = values.get("charging")
    charge = log.get("charge")
    if charging is True and charge is None:
        log["charge"] = {"start": stamp, "start_level": level, "dc": bool(values.get("dc"))}
    elif charging is True and charge is not None:
        if charge.get("start_level") is None and level is not None:
            charge["start_level"] = level
        if values.get("dc"):
            charge["dc"] = True
    elif charging is False and charge is not None:
        del log["charge"]
        seconds = (now - datetime.fromisoformat(charge["start"])).total_seconds()
        gained = None if level is None or charge.get("start_level") is None else level - charge["start_level"]
        if seconds >= MIN_CHARGE_SECONDS or (gained or 0) > 0:
            kind = "dc" if charge.get("dc") else "ac"
            kwh = _energy(gained, capacity_kwh) if gained is not None and gained > 0 else None
            price = log["prices"].get(kind)
            cost = round(kwh * price, 2) if kwh is not None and price is not None else None
            done.append(
                {
                    "kind": KIND_CHARGE,
                    "start": charge["start"],
                    "end": stamp,
                    "type": kind,
                    "start_level": charge.get("start_level"),
                    "end_level": level,
                    "kwh": kwh,
                    "price": price,
                    "cost": cost,
                }
            )
            if kwh is not None:
                log["totals"]["charge_kwh"] = round(log["totals"]["charge_kwh"] + kwh, 2)
            if cost is not None:
                log["totals"]["charge_cost"] = round(log["totals"]["charge_cost"] + cost, 2)

    if done:
        log["entries"] = [*log["entries"], *done][-MAX_ENTRIES:]
    return done


def consumption(log: Mapping[str, Any]) -> float | None:
    """Consumo medio (kWh/100 km) de los últimos viajes largos con kWh conocidos."""
    trips = [
        e for e in log.get("entries", ())
        if e.get("kind") == KIND_TRIP and e.get("kwh") is not None and (e.get("km") or 0) >= MIN_CONSUMPTION_KM
    ][-CONSUMPTION_TRIPS:]  # fmt: skip
    km = sum(e["km"] for e in trips)
    if not trips or km <= 0:
        return None
    return round(sum(e["kwh"] for e in trips) / km * 100, 1)


def last(log: Mapping[str, Any], kind: str) -> dict[str, Any] | None:
    """La última entrada de un tipo."""
    return next((e for e in reversed(log.get("entries", ())) if e.get("kind") == kind), None)


def month_summary(log: Mapping[str, Any], year: int, month: int) -> dict[str, Any]:
    """Resumen de un mes: viajes, km, cargas, kWh y coste (por la fecha de fin)."""
    prefix = f"{year:04d}-{month:02d}"
    entries = [e for e in log.get("entries", ()) if str(e.get("end", "")).startswith(prefix)]
    trips = [e for e in entries if e["kind"] == KIND_TRIP]
    charges = [e for e in entries if e["kind"] == KIND_CHARGE]
    return {
        "viajes": len(trips),
        "km": round(sum(e.get("km") or 0 for e in trips), 1),
        "cargas": len(charges),
        "kwh": round(sum(e.get("kwh") or 0 for e in charges), 2),
        "coste": round(sum(e.get("cost") or 0 for e in charges), 2),
    }
