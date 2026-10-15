"""Matrícula con el formato de su país (placa del panel)."""

from __future__ import annotations

from custom_components.dec_deepal.plates import plate


def test_each_country_format() -> None:
    assert plate("6545NPD", "ES") == {"code": "E", "parts": ["6545 NPD"]}
    assert plate(" 6545 npd ", "es") == {"code": "E", "parts": ["6545 NPD"]}
    assert plate("AA00AA", "PT") == {"code": "P", "parts": ["AA-00-AA"]}
    assert plate("12-AB-34", "PT") == {"code": "P", "parts": ["12-AB-34"]}
    assert plate("AB123CD", "IT") == {"code": "I", "parts": ["AB 123 CD"]}
    assert plate("ab-123-cd", "FR") == {"code": "F", "parts": ["AB-123-CD"]}
    # Alemania: ciudad y resto, para poner los sellos entre medias.
    assert plate("M-AB 1234", "DE") == {"code": "D", "parts": ["M", "AB 1234"]}
    assert plate("HH XY 12E", "DE") == {"code": "D", "parts": ["HH", "XY 12E"]}


def test_never_invents() -> None:
    """Lo que no encaja con el patrón se enseña tal cual."""
    assert plate("M-1234-AB", "ES") == {"code": "E", "parts": ["M-1234-AB"]}  # formato antiguo
    assert plate("MAB1234", "DE") == {"code": "D", "parts": ["MAB1234"]}  # sin saber dónde acaba la ciudad
    assert plate("6545NPD", "SE") == {"code": "SE", "parts": ["6545NPD"]}  # país sin formato
    assert plate(None, "ES") is None and plate("  ", "ES") is None
