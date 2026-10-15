"""Pruebas de la climatización (límites de temperatura)."""

from __future__ import annotations

from custom_components.dec_deepal.climate import (
    DEFAULT_TEMP_C,
    MAX_TEMP_C,
    MIN_TEMP_C,
    clamp_temperature,
)


def test_limits_are_the_gateway_ones() -> None:
    """La pasarela rechaza fuera de 18-32 °C (COMMON_1_1_01_005)."""
    assert (MIN_TEMP_C, MAX_TEMP_C) == (18.0, 32.0)


def test_temperature_is_clamped_before_sending() -> None:
    # El coche puede informar de una temperatura fuera de rango, y al
    # encender se reutiliza la que informa.
    assert clamp_temperature(16.0) == 18.0
    assert clamp_temperature(35.0) == 32.0
    assert clamp_temperature(22.5) == 22.5
    assert clamp_temperature(None) == DEFAULT_TEMP_C
