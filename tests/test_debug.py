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
