"""Registro de Home Assistant: los viajes y las cargas del diario del coche (``car_log_manager.py``)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.core import Event, HomeAssistant, callback

from .alert_rules import texts
from .car_log import KIND_CHARGE
from .car_log_manager import EVENT_CAR_LOG
from .const import DOMAIN, NAME


def _decimal(value: float, language: str) -> str:
    text = f"{value:g}"
    return text if language.startswith("en") else text.replace(".", ",")


def describe(data: dict[str, Any], language: str, currency: str = "EUR") -> str:
    """Texto de una entrada del diario (en el idioma y la moneda de Home Assistant)."""
    t = texts(language)
    energy = "" if data.get("kwh") is None else t["log_energy"].format(kwh=_decimal(data["kwh"], language))
    if data.get("kind") == KIND_CHARGE:
        cost = "" if data.get("cost") is None else t["log_cost"].format(cost=_decimal(data["cost"], language), currency=currency)
        return t["log_charge_" + ("dc" if data.get("type") == "dc" else "ac")].format(
            start=_level(data.get("start_level")), end=_level(data.get("end_level")), energy=energy, cost=cost
        )
    return t["log_trip"].format(
        km=_decimal(data.get("km") or 0, language),
        start=_level(data.get("start_level")),
        end=_level(data.get("end_level")),
        energy=energy,
    )


def _level(value: Any) -> str:
    return "?" if value is None else str(round(value))


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, str]]], None],
) -> None:
    """Describe los eventos del diario para el Registro."""

    @callback
    def _describe(event: Event) -> dict[str, str]:
        return {
            LOGBOOK_ENTRY_NAME: NAME,
            LOGBOOK_ENTRY_MESSAGE: describe(dict(event.data), hass.config.language, hass.config.currency),
        }

    async_describe_event(DOMAIN, EVENT_CAR_LOG, _describe)
