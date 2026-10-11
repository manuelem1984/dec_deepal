"""Pruebas de debug/ y de la clasificación de errores."""

from __future__ import annotations

from custom_components.dec_deepal.api.errors import (
    DeepalAuthError,
    DeepalPinError,
    DeepalRateLimitError,
    DeepalSigningError,
    error_from_response,
    is_auth_error,
)
from custom_components.dec_deepal.debug.capture import build_snapshot, diff_snapshots
from custom_components.dec_deepal.debug.history import changes
from custom_components.dec_deepal.debug.recorder import DebugRecorder
from custom_components.dec_deepal.debug.redact import REDACTED, redact
from custom_components.dec_deepal.telemetry.state import build_state


def test_redact_nested_and_jwt() -> None:
    data = {
        "vin": "LS123",
        "session": {"access_token": "x", "user_id": "9"},
        "soc": 80,
        "note": "eyJhbGciOi.eyJzdWIi.c2lnbmF0dXJl",
    }
    result = redact(data)
    assert result["vin"] == REDACTED
    assert result["session"] == {"access_token": REDACTED, "user_id": REDACTED}
    assert result["soc"] == 80
    assert result["note"] == REDACTED
    # "driving" contiene "vin": no debe ocultarse por eso.
    assert redact({"unlockKeyDrivingStatus": "0"}) == {"unlockKeyDrivingStatus": "0"}


def test_history_of_changes() -> None:
    """El historial dice qué cambió entre dos lecturas, sin el ruido de fondo."""
    before = {"charging": False, "battery_level": 55, "range_km": 270, "warning_airbag": False}
    after = {"charging": True, "battery_level": 55, "range_km": 271, "warning_airbag": True}
    assert changes(None, after) == []  # la primera lectura no es un cambio
    assert changes(before, after) == ["charging: False → True", "warning_airbag: False → True"]
    # Un dato que deja de llegar también cuenta; la autonomía (cambia siempre), no.
    assert changes(after, {"charging": True, "battery_level": 56}) == [
        "battery_level: 55 → 56",
        "warning_airbag: True → —",
    ]


def test_recorder_keeps_what_matters() -> None:
    """La rutina no borra lo importante: órdenes, cambios, avisos y errores duran más."""
    recorder = DebugRecorder(5)
    car = recorder.for_vehicle("Changote")
    car.record("command", name="lock", stage="rechazado", code=1032, error="Power is not off")
    car.record("change", changes=["pin_arm: locked → unlocked"])
    recorder.record("alert", vehicle="Changote", type="charge_started", targets=2, sent=2)
    car.record("wake", ok=False, error="sin red")
    for _ in range(20):  # lecturas rutinarias de sobra para llenar el registro general
        car.record("update", ok=True)
    assert [event["kind"] for event in recorder.events()] == ["update"] * 5
    history = recorder.history()
    assert [event["kind"] for event in history["ordenes"]] == ["command", "wake"]
    assert history["ordenes"][0]["vehicle"] == "Changote" and history["ordenes"][0]["code"] == 1032
    # Los cambios van como texto: el filtro de datos sensibles no los oculta.
    assert history["cambios"][0]["changes"] == ["pin_arm: locked → unlocked"]
    assert history["avisos"][0]["type"] == "charge_started"
    assert [event["kind"] for event in history["errores"]] == ["command", "wake"]
    recorder.clear()
    assert recorder.history() == {"cambios": [], "ordenes": [], "avisos": [], "errores": []}


def test_error_classification() -> None:
    assert isinstance(error_from_response("/x", "APP_1_1_02_004", "", 200), DeepalAuthError)
    assert isinstance(error_from_response("/x", "HW_1_1_01_047", "", 200), DeepalRateLimitError)
    assert isinstance(error_from_response("/x", "HW_1_1_01_074", "", 200), DeepalPinError)
    assert isinstance(
        error_from_response("/api/serial-no/get", "COMMON_1_1_01_001", "", 200),
        DeepalSigningError,
    )
    # "invalided" (sic) contiene "invalid": el servidor lo usa para token caducado.
    assert is_auth_error("APIGW_-1_7_01_004", "invalided token") is True
    assert is_auth_error("X", "token expired") is True
    assert is_auth_error("COMMON_1_1_01_005", "bad level") is False


def test_capture_diff() -> None:
    before = build_snapshot("A", "coche", build_state(mqtt_params={"diverWindow": 0, "soc": 80}, rest_raw=None, previous=None))
    after = build_snapshot("B", "coche", build_state(mqtt_params={"diverWindow": 1, "soc": 80}, rest_raw=None, previous=None))
    diff = diff_snapshots(before, after)
    assert diff["mqtt"] == {"diverWindow": {"antes": 0, "despues": 1}}
    assert "window_front_left" in diff["senales"]
