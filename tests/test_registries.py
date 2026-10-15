"""Pruebas de registries/ con los catálogos reales del repositorio."""

from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.registries import RegistryError, load_all
from custom_components.dec_deepal.registries.countries import load_countries
from custom_components.dec_deepal.registries.vehicles import (
    FEATURE_FUEL,
    FEATURE_POWER_TAILGATE,
    FEATURE_SEAT_HEAT,
    FEATURE_SEAT_VENT,
    FEATURE_WHEEL_HEAT,
)

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "dec_deepal"


@pytest.fixture(scope="module")
def registries():  # noqa: ANN201
    return load_all(INTEGRATION)


def test_spain_profile(registries) -> None:  # noqa: ANN001
    spain = registries.countries.get("es")
    assert spain.profile().sales_country == "ES"
    # Solo se entra con correo: el país ya no lleva prefijo ni métodos de acceso.
    assert not hasattr(spain, "login_methods") and not hasattr(spain.profile(), "dial_code")


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
    # Vista lateral sin tapacubos: foto propia del Max con la llanta "open" (2.5.0b11),
    # en los cinco colores; con la de serie (o una que no es elegible), la normal.
    for color in model.colors:
        assert model.photo_for("max", color, "open").name == f"max_{color}_open.png"
    assert model.photo_for("max", "andromeda_blue", "cover").name == "max_andromeda_blue.png"
    assert model.photo_for("pro", "andromeda_blue", "open").name == "pro_andromeda_blue.png"  # sin foto propia
    assert model.photo_for("pro", "andromeda_blue", "pro").name == "pro_andromeda_blue.png"
    assert model.display_name("max") == "Deepal S05 EV RWD Max"
    assert model.display_name("max_awd") == "Deepal S05 EV 4WD Max"
    assert model.display_name(None) == "Deepal S05 EV"


def test_vehicle_sheets(registries) -> None:  # noqa: ANN001
    """La ficha de cada coche: el modelo, cambiado por su versión; un modelo puede copiar a otro."""
    vehicles = registries.vehicles
    ev, phev, generic = vehicles.get("s05_2024"), vehicles.get("s05_phev"), vehicles.generic

    # Las cinco variantes del S05.
    names = [model.display_name(trim) for model in (ev, phev) for trim in model.trims]
    assert names == [
        "Deepal S05 EV RWD Pro",
        "Deepal S05 EV RWD Max",
        "Deepal S05 EV 4WD Max",
        # El PHEV es de tracción delantera y su versión alta no se llama Max.
        "Deepal S05 PHEV Pro",
        "Deepal S05 PHEV Limited Edition",
    ]

    # Equipamiento de cada versión, según los catálogos oficiales de España.
    comfort = (FEATURE_SEAT_HEAT, FEATURE_SEAT_VENT, FEATURE_WHEEL_HEAT, FEATURE_POWER_TAILGATE)
    equipped = (
        (ev, "pro", False),
        (ev, "max", True),
        (ev, "max_awd", True),
        (phev, "pro", False),
        (phev, "limited_edition", True),
    )
    for model, trim, has_it in equipped:
        for feature in comfort:
            assert model.has(feature, trim) is has_it, (model.id, trim, feature)
    # Llantas: 18" en el EV Pro y en los dos PHEV; 20" (a elegir) en los Max.
    assert ev.wheel_for("pro", "open") == "pro" and ev.wheel_for("max", "open") == "open"
    assert phev.wheel_for("pro", None) == phev.wheel_for("limited_edition", "open") == "pro"
    assert ev.colors["ganymade_grey"].name == "Ganymede Grey"
    # Cada color lleva su muestra para el panel.
    assert all(color.swatch.startswith("#") and len(color.swatch) == 7 for color in ev.colors.values())

    # Solo está verificada la del coche que se ha probado de verdad.
    assert ev.sheet("max")["verificada"] is True and ev.sheet("max")["origen"] == "de su versión"
    assert ev.sheet("pro")["verificada"] is False
    assert ev.sheet("pro")["funciones"][FEATURE_SEAT_VENT] is False

    # Sin versión, o con una que no está en el catálogo: la ficha del modelo (la del Max).
    for trim in (None, "no_existe"):
        sheet = ev.sheet(trim)
        assert sheet["funciones"] == ev.sheet("max")["funciones"], trim
        assert sheet["origen"].startswith("del modelo") and sheet["verificada"] is False
        assert ev.has(FEATURE_SEAT_VENT, trim)

    # El PHEV copia al EV y solo cambia lo suyo.
    assert phev.based_on == "s05_2024" and phev.sheet("pro")["copia_de"] == "s05_2024"
    assert phev.has(FEATURE_FUEL) and not ev.has(FEATURE_FUEL)
    assert phev.colors == ev.colors and phev.views.keys() == ev.views.keys()
    assert phev.photo_for("limited_edition", "andromeda_blue") == ev.photo_for("max", "andromeda_blue")
    assert set(phev.trims) == {"pro", "limited_edition"}  # no hay 4WD
    assert phev.sheet("limited_edition")["verificada"] is False
    # Manual y plan de mantenimiento propios (manual oficial del PHEV, julio de 2026).
    assert phev.manual_url.endswith("S05_PHEV_Manual_de_Usuario_ES-compressed.pdf")
    assert phev.manual_url != ev.manual_url
    plan = phev.maintenance
    assert (plan.interval_km, plan.interval_months) == (20000, 12)
    first, second, third = (plan.operations_for(number, "pro", "es") for number in (1, 2, 3))
    # El motor de gasolina: aceite y filtro en todas; bujías y filtro de aire cada dos.
    assert any("aceite del motor" in name for name in first)
    assert not any("bujías" in name for name in first)
    assert any("bujías" in name for name in second) and any("filtro de aire del motor" in name for name in second)
    assert any("líquido de frenos" in name for name in second)
    # Tracción delantera: reductor delantero en todas las versiones, y no hay trasero.
    assert any("reductor delantero" in name for name in third)
    assert any("reductor delantero" in name for name in plan.operations_for(3, "limited_edition", "es"))
    assert not any("reductor trasero" in name for number in range(1, 11) for name in plan.operations_for(number, "pro", "es"))
    # El EV sigue sin nada del motor de gasolina.
    assert not any("motor" in name for number in range(1, 6) for name in ev.maintenance.operations_for(number, "max", "es"))

    # Testigos que no avisan: salen de la ficha (y son señales que existen).
    from custom_components.dec_deepal.alert_rules import PROBLEM_SIGNALS

    for model in (ev, phev, generic):
        assert model.silent_warnings == {"warning_airbag"}, model.id
        assert model.silent_warnings <= set(PROBLEM_SIGNALS)
    assert generic.sheet(None)["origen"].startswith("genérica")


def test_recognising_ev_and_phev(registries) -> None:  # noqa: ANN001
    """Si encajan varios modelos, gana el más concreto (PHEV antes que S05)."""
    ev = VehicleInfo(vehicle_id="1", series_name="S05", model_code="SC6464AAKBEV")
    phev = VehicleInfo(vehicle_id="2", series_name="S05", model_code="SC6464AAKPHEV")
    assert registries.vehicles.match(ev, "es").id == "s05_2024"
    assert registries.vehicles.match(phev, "es").id == "s05_phev"


def test_s05_has_no_front_defrost(registries) -> None:  # noqa: ANN001
    """El S05 no es compatible con el desempañado delantero (02-10-2026)."""
    from custom_components.dec_deepal.registries.vehicles import (
        FEATURE_DEFROST,
        FEATURE_WHEEL_HEAT,
    )

    model = registries.vehicles.get("s05_2024")
    for trim in ("pro", "max", "max_awd"):
        assert not model.has(FEATURE_DEFROST, trim)
        # El volante calefactado es de los Max (catálogo oficial, sep. 2026).
        assert model.has(FEATURE_WHEEL_HEAT, trim) is (trim != "pro")


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
    # Llave del S05 (2.2.0b2): normal y, con la pila baja, con exclamación.
    assert icons.resolve("key_battery_low", "off") == "dec:key_battery_low_off"
    assert icons.resolve("key_battery_low", "on") == "dec:key_battery_low_on"
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

