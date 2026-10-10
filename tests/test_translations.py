"""Los idiomas (español, inglés, portugués) tienen siempre los mismos textos.

Vigila los tres sitios donde hay texto: los ficheros de idioma de Home
Assistant, los avisos al móvil y la tarjeta.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from custom_components.dec_deepal import alert_rules as ar
from custom_components.dec_deepal.registries import load_all

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "dec_deepal"
LANGUAGES = ("es", "en", "pt")
PLACEHOLDER = re.compile(r"\{[a-z_]+\}")


def _flat(obj, prefix: str = ""):  # noqa: ANN001, ANN202
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _flat(value, f"{prefix}.{key}" if prefix else key)
    else:
        yield prefix, obj


def _language_file(language: str) -> dict[str, str]:
    path = INTEGRATION / "translations" / f"{language}.json"
    return dict(_flat(json.loads(path.read_text(encoding="utf-8"))))


def test_language_files_match() -> None:
    spanish = _language_file("es")
    for language in ("en", "pt"):
        other = _language_file(language)
        assert set(other) == set(spanish), (language, set(other) ^ set(spanish))
        for key, text in spanish.items():
            # Mismos marcadores ({vehicle}, {error}...) y nada que parezca HTML.
            assert sorted(PLACEHOLDER.findall(text)) == sorted(PLACEHOLDER.findall(other[key])), (language, key)
            assert "<" not in other[key], (language, key)
    # strings.json es el idioma base de Home Assistant: inglés.
    base = dict(_flat(json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))))
    assert base == _language_file("en")
    # De verdad traducido (antes los tres ficheros eran el mismo texto en español).
    assert _language_file("en")["entity.sensor.battery_level.name"] == "Battery"
    assert _language_file("pt")["entity.binary_sensor.trunk.name"] == "Mala"
    assert spanish["entity.binary_sensor.trunk.name"] == "Maletero"
    # Catalán, gallego y euskera: el mismo texto que en español (si no, Home
    # Assistant les pondría el inglés).
    for language in ("ca", "gl", "eu"):
        assert _language_file(language) == spanish, language


def test_notification_texts_match() -> None:
    assert set(ar.TEXTS) == set(LANGUAGES)
    for language in ("en", "pt"):
        assert set(ar.TEXTS[language]) == set(ar.TEXTS["es"]), language
        for key, text in ar.TEXTS["es"].items():
            assert sorted(PLACEHOLDER.findall(text)) == sorted(PLACEHOLDER.findall(ar.TEXTS[language][key])), (language, key)
    kwargs = {"number": 2, "days_left": 47, "km_left": 2000, "due_date": "10/03/2027", "due_km": 39500}
    assert ar.maintenance_text("remaining", language="pt", **kwargs) == "Faltam 2.000 km ou 47 dias para a 2.ª revisão."
    assert ar.maintenance_text("remaining", language="en-GB", **kwargs) == "2,000 km or 47 days left until the 2nd service."
    # Idioma sin traducción: inglés, como el resto de Home Assistant...
    assert ar.charge_text(ar.ALERT_CHARGE_STARTED, None, "fr") == "Charging started."
    # ...salvo catalán, gallego y euskera, que se muestran en español.
    for language in ("ca", "gl", "eu", "ca-ES"):
        assert ar.charge_text(ar.ALERT_CHARGE_STARTED, None, language) == "Carga iniciada."
    assert ar.charge_text(ar.ALERT_CHARGE_STARTED, 46, "pt-BR") == "Carregamento iniciado (bateria a 46 %)."


def test_catalogue_names_in_every_language() -> None:
    plan = load_all(INTEGRATION).vehicles.get("s05_2024").maintenance
    for operation in plan.operations:
        assert set(operation.names) == set(LANGUAGES), operation.names
    assert plan.operations_for(2, "max", "en")[1] == "Tyres (inspection and adjustment)"
    assert "travões" in " ".join(plan.operations_for(2, "max", "pt"))
    assert plan.operations_for(1, "max", "fr") == plan.operations_for(1, "max", "en")
    assert plan.operations_for(1, "max", "eu") == plan.operations_for(1, "max", "es")


def test_card_texts_match() -> None:
    source = (INTEGRATION / "frontend_card" / "dec-deepal-card.js").read_text(encoding="utf-8")
    tables = {
        language: set(re.findall(r"^      ([a-z_0-9]+):", block, re.M))
        for language, block in re.findall(r"^    (es|en|pt): \{\n(.*?)^    \},", source, re.M | re.S)
    }
    assert set(tables) == set(LANGUAGES)
    assert tables["es"] == tables["en"] == tables["pt"]
    assert len(tables["es"]) > 100
    # Todo texto que pide el código existe en la tabla.
    used = set(re.findall(r'_t\("([a-z_0-9]+)"', source))
    assert used - tables["es"] == set(), used - tables["es"]
    # Los tipos de seguro de la tarjeta son los de la integración.
    from custom_components.dec_deepal.documents import INSURANCE_KINDS

    assert {f"kind_{kind}" for kind in INSURANCE_KINDS} <= tables["es"]
    assert 'const SPANISH_FALLBACK = ["ca", "gl", "eu"];' in source
