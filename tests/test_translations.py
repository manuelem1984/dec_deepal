"""Idiomas: una sola fuente (``idiomas/``) y todo lo demás generado.

Comprueba que los ficheros generados están al día, que el idioma base está
completo, que los idiomas "prestados" funcionan y que un idioma a medias se
rellena con el idioma base.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

from custom_components.dec_deepal import alert_rules as ar
from custom_components.dec_deepal import textos_generados as generated
from custom_components.dec_deepal.registries import load_all

#: Idiomas con fichero propio.
LANGUAGES = ("es", "en", "pt", "it", "pl", "de", "fr", "nl", "nb", "da", "el", "sl")

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "dec_deepal"


@pytest.fixture(scope="module")
def tool():  # noqa: ANN201
    """El generador (``tools/generar_idiomas.py``), cargado como módulo."""
    spec = importlib.util.spec_from_file_location("generar_idiomas", ROOT / "tools" / "generar_idiomas.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _translations(language: str) -> dict:
    return json.loads((INTEGRATION / "translations" / f"{language}.json").read_text(encoding="utf-8"))


def test_generated_files_are_up_to_date(tool) -> None:  # noqa: ANN001
    """Si falla: ejecutar ``python tools/generar_idiomas.py`` y subir el resultado."""
    config, languages = tool.load()
    stale = [
        str(path.relative_to(ROOT))
        for path, content in tool.outputs(config, languages).items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]
    assert stale == []
    assert tool.main(["--check"]) == 0


def test_languages_and_fallbacks(tool) -> None:  # noqa: ANN001
    config, languages = tool.load()
    assert config["base"] == "en" and set(languages) == set(LANGUAGES)
    # El español (idioma del proyecto) y el base están siempre completos.
    gaps = tool.missing(config, languages)
    assert gaps["en"] == [] and gaps["es"] == []
    # A los demás solo les puede faltar lo de las pantallas antiguas de Configurar
    # (ya no se abren desde que el panel las sustituye): todo lo que se ve está traducido.
    for language, keys in gaps.items():
        assert all(key.startswith("integracion.options.step.") for key in keys), (language, keys[:3])
    # Home Assistant: un fichero por idioma, más los prestados; el base es strings.json.
    assert json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8")) == _translations("en")
    assert _translations("en")["entity"]["sensor"]["battery_level"]["name"] == "Battery"
    assert _translations("pt")["entity"]["binary_sensor"]["trunk"]["name"] == "Mala"
    assert _translations("it")["entity"]["binary_sensor"]["trunk"]["name"] == "Bagagliaio"
    assert _translations("pl")["entity"]["binary_sensor"]["trunk"]["name"] == "Bagażnik"
    assert {code: _translations(code)["entity"]["binary_sensor"]["trunk"]["name"] for code in LANGUAGES[5:]} == {
        "de": "Kofferraum", "fr": "Coffre", "nl": "Kofferbak", "nb": "Bagasjerom",
        "da": "Bagagerum", "el": "Πορτμπαγκάζ", "sl": "Prtljažnik",
    }
    assert generated.BASE_LANGUAGE == "en"
    assert generated.BORROWED_LANGUAGES == {"ca": "es", "eu": "es", "gl": "es", "nn": "nb", "lb": "fr"}
    for language in generated.BORROWED_LANGUAGES:
        assert _translations(language) == _translations(generated.BORROWED_LANGUAGES[language]), language


def test_partial_language_is_filled_with_the_base(tool) -> None:  # noqa: ANN001
    """Un idioma a medias se publica igual: lo que falta sale en el idioma base."""
    config, languages = tool.load()
    swedish = {"avisos": {"charge_started": "Laddning startad{battery}."}, "tarjeta": {"comfort": "Komfort"}}
    config = {**config, "idiomas": {**config["idiomas"], "sv": {"nombre": "Svenska"}}}
    languages = {**languages, "sv": swedish}
    assert len(tool.missing(config, languages)["sv"]) > 400
    files = tool.outputs(config, languages)
    text = files[INTEGRATION / "textos_generados.py"]
    assert '"charge_started": "Laddning startad{battery}."' in text
    assert json.loads(files[INTEGRATION / "translations" / "sv.json"]) == _translations("en")
    assert '"sv": {' in files[INTEGRATION / "frontend_card" / "dec-deepal-card.js"]


def test_mistakes_are_reported(tool, monkeypatch, tmp_path) -> None:  # noqa: ANN001
    """Clave que no existe o marcador distinto: error claro, no un texto roto."""
    sources = tmp_path / "idiomas"
    sources.mkdir()
    for path in (INTEGRATION / "idiomas").glob("*.json"):
        (sources / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(tool, "SOURCES", sources)
    monkeypatch.setattr(tool, "CONFIG", sources / "idiomas.json")
    portuguese = json.loads((sources / "pt.json").read_text(encoding="utf-8"))

    portuguese["avisos"]["charge_started"] = "Carregamento iniciado."  # falta {battery}
    (sources / "pt.json").write_text(json.dumps(portuguese), encoding="utf-8")
    with pytest.raises(tool.LanguageError, match="marcadores"):
        tool.load()

    portuguese["avisos"]["charge_started"] = "Carregamento iniciado{battery}."
    portuguese["tarjeta"]["no_existe"] = "x"
    (sources / "pt.json").write_text(json.dumps(portuguese), encoding="utf-8")
    with pytest.raises(tool.LanguageError, match="no existen"):
        tool.load()


def test_notifications_in_each_language() -> None:
    kwargs = {"number": 2, "days_left": 47, "km_left": 2000, "due_date": "10/03/2027", "due_km": 39500}
    assert ar.maintenance_text("remaining", language="pt", **kwargs) == "Faltam 2.000 km ou 47 dias para a 2.ª revisão."
    assert ar.maintenance_text("remaining", language="en-GB", **kwargs) == "2,000 km or 47 days left until the 2nd service."
    # Italiano y polaco: cada uno con su formato de ordinal, de miles y de fecha.
    assert ar.maintenance_text("remaining", language="it", **kwargs) == "Mancano 2.000 km o 47 giorni al 2º tagliando."
    assert ar.maintenance_text("remaining", language="pl", **kwargs) == "Do 2. przeglądu: 2 000 km lub 47 dni."
    from datetime import date

    assert ar.format_date(date(2027, 3, 10), "pl") == "10.03.2027"
    assert ar.format_date(date(2027, 3, 10), "es") == "10/03/2027"
    # Los de la 2.5.0b4, cada uno con su separador de miles y su fecha.
    assert ar.maintenance_text("remaining", language="de", **kwargs) == "Noch 2.000 km oder 47 Tage bis zur 2. Wartung."
    assert ar.maintenance_text("remaining", language="fr", **kwargs) == "Il reste 2 000 km ou 47 jours avant le 2e entretien."
    assert ar.format_date(date(2027, 3, 10), "nl") == "10-03-2027"
    assert ar.format_date(date(2027, 3, 10), "sl") == "10. 03. 2027"
    assert ar.charge_text(ar.ALERT_CHARGE_STARTED, 46, "el") == "Η φόρτιση ξεκίνησε (μπαταρία στο 46%)."
    assert ar.charge_text(ar.ALERT_CHARGE_STARTED, None, "nn") == "Lading startet."  # nynorsk: como bokmål
    assert ar.ordinal(3, "sv") == "3rd"  # sin traducir: como en inglés
    # Idioma sin traducción: el base (inglés), como el resto de Home Assistant...
    assert ar.charge_text(ar.ALERT_CHARGE_STARTED, None, "sv") == "Charging started."
    # ...salvo los prestados: catalán, gallego y euskera se muestran en español.
    for language in ("ca", "gl", "eu", "ca-ES"):
        assert ar.charge_text(ar.ALERT_CHARGE_STARTED, None, language) == "Carga iniciada."
    assert ar.charge_text(ar.ALERT_CHARGE_STARTED, 46, "pt-BR") == "Carregamento iniciado (bateria a 46 %)."


def test_catalogue_names_in_every_language() -> None:
    plan = load_all(INTEGRATION).vehicles.get("s05_2024").maintenance
    for operation in plan.operations:
        assert set(operation.names) == set(LANGUAGES), operation.names
    assert plan.operations_for(2, "max", "en")[1] == "Tyres (inspection and adjustment)"
    assert "travões" in " ".join(plan.operations_for(2, "max", "pt"))
    assert plan.operations_for(1, "max", "sv") == plan.operations_for(1, "max", "en")
    assert plan.operations_for(1, "max", "eu") == plan.operations_for(1, "max", "es")


def test_panel_texts() -> None:
    """El panel solo usa textos que existen, y hay nombre para cada aviso y apartado."""
    from custom_components.dec_deepal.alert_rules import NOTICES, SECTIONS
    from custom_components.dec_deepal.documents import INSURANCE_KINDS

    spanish = json.loads((INTEGRATION / "idiomas" / "es.json").read_text(encoding="utf-8"))["panel"]
    english = json.loads((INTEGRATION / "idiomas" / "en.json").read_text(encoding="utf-8"))["panel"]
    assert set(spanish) == set(english) and len(spanish) > 150
    sources = (INTEGRATION / "frontend_panel" / "src").glob("*.js")
    code = "".join(path.read_text(encoding="utf-8") for path in sources if path.name != "20_textos.js")
    used = set(re.findall(r'_(?:t|maybe)\("([a-z_0-9]+)"', code))
    assert used - set(spanish) == set(), used - set(spanish)
    # Claves que se montan en el código: avisos, apartados, plazos sin número, tipos de seguro.
    for notice in NOTICES:
        assert f"notice_{notice.id}" in spanish, notice.id
        if notice.threshold is None and notice.section not in ("charge", "warnings"):
            assert f"when_{notice.id}" in spanish, notice.id
    for section in SECTIONS:
        assert f"section_{section}" in spanish, section
    assert {f"kind_{kind}" for kind in INSURANCE_KINDS} <= set(spanish)
    assert {"tab_cars", "tab_alerts", "tab_data", "tab_diagnostics"} <= set(spanish)
    assert {"error_threshold_order", "error_threshold_range", "error_invalid_file", "error_not_found"} <= set(spanish)


def test_card_uses_only_existing_texts() -> None:
    source = (INTEGRATION / "frontend_card" / "dec-deepal-card.js").read_text(encoding="utf-8")
    spanish = json.loads((INTEGRATION / "idiomas" / "es.json").read_text(encoding="utf-8"))["tarjeta"]
    used = set(re.findall(r'_t\("([a-z_0-9]+)"', source)) | set(re.findall(r'translate\([^,]+, "([a-z_0-9]+)"', source))
    assert used - set(spanish) == set(), used - set(spanish)
    assert len(spanish) > 100
    # Los tipos de seguro de la tarjeta son los de la integración.
    from custom_components.dec_deepal.documents import INSURANCE_KINDS

    assert {f"kind_{kind}" for kind in INSURANCE_KINDS} <= set(spanish)
