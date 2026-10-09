"""Pruebas de registries/ con los catálogos reales del repositorio."""

from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.registries import RegistryError, load_all
from custom_components.dec_deepal.registries.countries import load_countries
from custom_components.dec_deepal.registries.vehicles import FEATURE_SEAT_VENT

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "dec_deepal"


@pytest.fixture(scope="module")
def registries():  # noqa: ANN201
    return load_all(INTEGRATION)


def test_spain_profile(registries) -> None:  # noqa: ANN001
    spain = registries.countries.get("es")
    assert spain.profile().sales_country == "ES"
    assert spain.normalize_mobile("+34 600-000-000") == "600000000"
    assert spain.is_valid_mobile("600000000")
    assert not spain.is_valid_mobile("6000")


def test_match_s05_and_generic(registries) -> None:  # noqa: ANN001
    s05 = VehicleInfo(vehicle_id="1", model_name="Deepal S05 Max")
    other = VehicleInfo(vehicle_id="2", model_name="Otro coche")
    assert registries.vehicles.match(s05, "es").id == "s05_2024"
    assert registries.vehicles.match(other, "es").id == "generico"


def test_trim_features_and_photos(registries) -> None:  # noqa: ANN001
    model = registries.vehicles.get("s05_2024")
    assert not model.has(FEATURE_SEAT_VENT, "pro")
    assert model.has(FEATURE_SEAT_VENT, "max")
    assert model.photo_for("max_awd", "andromeda_blue").name == "max_andromeda_blue.png"
    assert model.photo_for(None, None).name == "default.png"
    assert model.display_name("max") == "Deepal S05 Max (2024-25)"
    assert model.display_name(None) == "Deepal S05 (2024-25)"


def test_s05_has_no_front_defrost(registries) -> None:  # noqa: ANN001
    """El S05 no es compatible con el desempañado delantero (02-10-2026)."""
    from custom_components.dec_deepal.registries.vehicles import (
        FEATURE_DEFROST,
        FEATURE_WHEEL_HEAT,
    )

    model = registries.vehicles.get("s05_2024")
    for trim in ("pro", "max", "max_awd"):
        assert not model.has(FEATURE_DEFROST, trim)
        assert model.has(FEATURE_WHEEL_HEAT, trim)


def test_capabilities_spanish_max_codes() -> None:
    """Códigos reales de un S05 Max de España (diagnóstico 30-09-2026)."""
    from custom_components.dec_deepal.api.models import Capabilities

    max_codes = ["#battery", "#heat3", "#vent3", "FronSeatVentilationSW", "DriverSeatHeaterSW"]
    assert Capabilities(raw_codes=max_codes).trim_hint == "max"
    assert Capabilities(raw_codes=["#battery", "#heat3"]).trim_hint == "pro"
    assert Capabilities(raw_codes=[]).trim_hint is None


def test_tire_alarm_icons(registries) -> None:  # noqa: ANN001
    icons = registries.icons
    assert icons.resolve("tire_alarm_front_left", "off") == "mdi:tire"
    assert icons.resolve("tire_alarm_front_left", "on") == "mdi:car-tire-alert"
    assert icons.resolve("tire_alarm_front_left", None) == "mdi:tire"


def test_icon_resolution(registries) -> None:  # noqa: ANN001
    icons = registries.icons
    assert icons.resolve("high_beam", "on") == "dec:high_beam"
    assert icons.resolve("high_beam", "off") == "dec:high_beam"
    assert icons.resolve("indicator_left", "on") == "dec:indicator_left_on"
    assert icons.resolve("steering_wheel_heat", "off") == "dec:steering_wheel_heat"
    # Ventanillas: estado de HA invertido ("open" = cerradas de verdad).
    assert icons.resolve("windows", "open") == "mdi:window-closed-variant"
    assert icons.resolve("windows", "closed") == "mdi:window-open-variant"
    # Iconos propios de la 2.1.0b2 (derivados de Material Design Icons).
    assert icons.resolve("door_front_left", "on") == "dec:door_front_left_open"
    assert icons.resolve("door_rear_right", "off") == "dec:door_rear_right_closed"
    assert icons.resolve("hood", "on") == "dec:hood_open"
    assert icons.resolve("trunk", "off") == "dec:trunk_closed"
    # Retiradas en la 2.1.0: sin icono propio ni entrada en el registro.
    assert icons.resolve("charge_cover", "on") is None
    assert icons.resolve("front_fog_lamp", "on") is None
    assert icons.resolve("battery_level") is None
    assert icons.warnings == []


def test_icon_bundle(registries) -> None:  # noqa: ANN001
    """El paquete que pide el navegador trae todos los SVG, con su dibujo."""
    bundle = registries.icons.bundle()
    assert set(bundle) == set(registries.icons.available)
    assert "door_front_left_open" in bundle and "hood_open" in bundle
    assert all("<path" in text and "viewBox" in text for text in bundle.values())
    assert "charge_cover_open" not in bundle  # está en icons/reserva/


def test_countries_validation(tmp_path: Path) -> None:
    bad = tmp_path / "countries.yaml"
    bad.write_text("entornos: {}\npaises:\n  es: {nombre: X, entorno: nada}\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="entorno"):
        load_countries(bad)


def test_card_file_is_shipped() -> None:
    """La tarjeta existe, se define con su nombre y usa las claves reales de las entidades."""
    import json
    import re

    from custom_components.dec_deepal.const import CARD_JS_DIR, CARD_JS_FILE

    source = (INTEGRATION / CARD_JS_DIR / CARD_JS_FILE).read_text(encoding="utf-8")
    assert 'const TAG = "dec-deepal-card"' in source and "customElements.define(TAG" in source
    assert CARD_JS_FILE in (INTEGRATION / "icons" / "dec-icons.js").read_text(encoding="utf-8")
    # Cada "dominio.clave" que usa la tarjeta debe existir en las traducciones.
    names = json.loads((INTEGRATION / "translations" / "es.json").read_text(encoding="utf-8"))["entity"]
    used = set(re.findall(r'"((?:sensor|binary_sensor|image|climate|lock|cover|button|switch|number)\.[a-z_]+)"', source))
    assert len(used) > 20
    missing = sorted(key for key in used if key.split(".")[1] not in names.get(key.split(".")[0], {}))
    assert missing == [], missing

