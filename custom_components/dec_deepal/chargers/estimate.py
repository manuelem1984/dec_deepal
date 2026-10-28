"""Cuentas sin estado: % estimado, minutos que faltan y pérdida medida de una carga."""

from __future__ import annotations

from .const import (
    MAX_LOSS,
)


def estimate_level(start: float | None, energy_kwh: float | None, loss: float, capacity: float | None) -> float | None:
    """% de batería estimado: el de partida más los kWh que llegan a la batería."""
    if start is None or energy_kwh is None or not capacity:
        return None
    return min(100.0, start + energy_kwh * (1 - loss / 100) / capacity * 100)


def estimate_minutes(
    level: float | None, power_w: float | None, loss: float, capacity: float | None, target: float = 100
) -> float | None:
    """Minutos que faltan para ``target`` % con la potencia actual (sin el equilibrado)."""
    if level is None or not power_w or power_w <= 0 or not capacity:
        return None
    missing_kwh = max(0.0, target - level) / 100 * capacity / max(0.01, 1 - loss / 100)
    return missing_kwh / (power_w / 1000) * 60


def measured_loss(start: float, end: float, energy_kwh: float, capacity: float) -> float | None:
    """Pérdida real de una carga, o ``None`` si los datos no son creíbles."""
    if energy_kwh < 1 or end <= start:
        return None
    stored = (end - start) / 100 * capacity
    loss = (1 - stored / energy_kwh) * 100
    return round(loss, 1) if 0 <= loss <= MAX_LOSS else None
