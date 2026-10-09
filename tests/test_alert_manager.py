"""Prueba del gestor de avisos y mantenimiento dentro de Home Assistant.

Coches y coordinadores falsos; el envío es real (un servicio ``notify`` de
prueba) y el almacén es el de Home Assistant (en memoria).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.dec_deepal.alert_rules import ALERT_TYPES
from custom_components.dec_deepal.alerts import AlertManager
from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.const import (
    OPT_ALERT_PERSISTENT,
    OPT_ALERT_TARGETS,
    OPT_ALERT_TYPES,
    OPT_ALERTS,
)
from custom_components.dec_deepal.maintenance import LEVEL_SOON, MaintenanceRecord
from custom_components.dec_deepal.registries import load_all
from custom_components.dec_deepal.telemetry import signals as s

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "dec_deepal"
OPTIONS = {
    OPT_ALERTS: {
        OPT_ALERT_TARGETS: ["mobile_app_test"],
        OPT_ALERT_TYPES: list(ALERT_TYPES),
        OPT_ALERT_PERSISTENT: False,
    }
}


class FakeCoordinator:
    """Lo mínimo de un coordinador: datos y oyentes."""

    def __init__(self, values: dict[str, Any]) -> None:
        self._listeners: list = []
        self.data = SimpleNamespace(get=values.get)

    def async_add_listener(self, listener):  # noqa: ANN001, ANN201
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def push(self, values: dict[str, Any]) -> None:
        self.data = SimpleNamespace(get=values.get)
        for listener in list(self._listeners):
            listener()


@pytest.mark.usefixtures("enable_custom_integrations", "hass_storage")
async def test_alerts_and_maintenance(hass: HomeAssistant, freezer) -> None:  # noqa: ANN001
    # 22-01-2027 a mediodía en la zona horaria de las pruebas (US/Pacific).
    freezer.move_to("2027-01-22 20:00:00+00:00")
    hass.config.language = "es"
    calls = async_mock_service(hass, "notify", "mobile_app_test")
    model = load_all(INTEGRATION).vehicles.get("s05_2024")
    coordinator = FakeCoordinator({s.CHARGING: False, s.BATTERY_LEVEL: 45, s.ODOMETER_KM: 37500})
    vehicles = {
        "car1": SimpleNamespace(
            info=VehicleInfo(vehicle_id="car1", nickname="Changote"),
            coordinator=coordinator,
            model=model,
            trim="max_awd",
        )
    }
    manager = AlertManager(hass, "entry1", OPTIONS, vehicles)
    await manager.async_load()
    manager.async_start()
    await hass.async_block_till_done()
    assert calls == []
    assert manager.status("car1") is None

    # --- Carga ---------------------------------------------------------------
    base = {s.ODOMETER_KM: 37500}
    coordinator.push({**base, s.CHARGING: True, s.BATTERY_LEVEL: 46, s.REMAINING_CHARGE_MIN: 200})
    await hass.async_block_till_done()
    assert calls[-1].data == {
        "title": "DEC Deepal Changote",
        "message": "Carga iniciada (batería al 46 %).",
    }
    coordinator.push({**base, s.CHARGING: False, s.BATTERY_LEVEL: 63})
    await hass.async_block_till_done()
    assert calls[-1].data["message"] == "Carga interrumpida (batería al 63 %)."

    # --- Testigos: una vez, hasta que se apaguen --------------------------------
    coordinator.push({**base, s.WARNING_ABS: True})
    coordinator.push({**base, s.WARNING_ABS: True})
    await hass.async_block_till_done()
    assert len(calls) == 3 and "ABS" in calls[-1].data["message"].upper()

    # --- Mantenimiento -----------------------------------------------------------
    record = MaintenanceRecord(services_done=1, last_date=date(2026, 3, 10), last_km=19500)
    await manager.async_set_record("car1", record)
    await hass.async_block_till_done()
    assert calls[-1].data["message"] == "Quedan 2.000 km o 47 días para la 2ª revisión."
    assert manager.status("car1").level == LEVEL_SOON
    coordinator.push({**base, s.WARNING_ABS: True})
    await hass.async_block_till_done()
    assert len(calls) == 4  # el mismo escalón no se repite

    # La 2.ª revisión de un AWD lleva líquido de frenos; la 3.ª, el reductor delantero.
    assert any("líquido de frenos" in name for name in manager.operations("car1"))
    await manager.async_register_service("car1", date(2027, 1, 22), 37500)
    assert manager.status("car1").number == 3
    assert any("reductor delantero" in name for name in manager.operations("car1"))

    # --- Lo guardado sobrevive a un reinicio -----------------------------------------
    await manager.async_stop()
    again = AlertManager(hass, "entry1", OPTIONS, vehicles)
    await again.async_load()
    assert again.record("car1").services_done == 2
    assert again.record("car1").history == [{"number": 2, "date": "2027-01-22", "km": 37500}]
    assert again.odometer("car1") == 37500
    again.async_start()
    await hass.async_block_till_done()
    assert len(calls) == 4  # el testigo ABS ya estaba avisado
    await again.async_stop()
