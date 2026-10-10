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
    assert config["base"] == "en" and set(languages) == {"es", "en", "pt"}
    # El español (idioma del proyecto) y el base están siempre completos.
    gaps = tool.missing(config, languages)
    assert gaps["en"] == [] and gaps["es"] == []
    # Home Assistant: un fichero por idioma, más los prestados; el base es strings.json.
    assert json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8")) == _translations("en")
    assert _translations("en")["entity"]["sensor"]["battery_level"]["name"] == "Battery"
    assert _translations("pt")["entity"]["binary_sensor"]["trunk"]["name"] == "Mala"
    assert generated.BASE_LANGUAGE == "en"
    assert generated.BORROWED_LANGUAGES == {"ca": "es", "eu": "es", "gl": "es"}
    for language in generated.BORROWED_LANGUAGES:
        assert _translations(language) == _translations("es"), language


def test_partial_language_is_filled_with_the_base(tool) -> None:  # noqa: ANN001
    """Un idioma a medias se publica igual: lo que falta sale en el idioma base."""
    config, languages = tool.load()
    italian = {"avisos": {"charge_started": "Ricarica avviata{battery}."}, "tarjeta": {"comfort": "Comfort"}}
    config = {**config, "idiomas": {**config["idiomas"], "it": {"nombre": "Italiano"}}}
    languages = {**languages, "it": italian}
    assert len(tool.missing(config, languages)["it"]) > 400
    files = tool.outputs(config, languages)
    text = files[INTEGRATION / "textos_generados.py"]
    assert '"charge_started": "Ricarica avviata{battery}."' in text
    assert json.loads(files[INTEGRATION / "translations" / "it.json"]) == _translations("en")
    assert '"it": {' in files[INTEGRATION / "frontend_card" / "dec-deepal-card.js"]


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
    # Idioma sin traducción: el base (inglés), como el resto de Home Assistant...
    assert ar.charge_text(ar.ALERT_CHARGE_STARTED, None, "fr") == "Charging started."
    # ...salvo los prestados: catalán, gallego y euskera se muestran en español.
    for language in ("ca", "gl", "eu", "ca-ES"):
        assert ar.charge_text(ar.ALERT_CHARGE_STARTED, None, language) == "Carga iniciada."
    assert ar.charge_text(ar.ALERT_CHARGE_STARTED, 46, "pt-BR") == "Carregamento iniciado (bateria a 46 %)."


def test_catalogue_names_in_every_language() -> None:
    plan = load_all(INTEGRATION).vehicles.get("s05_2024").maintenance
    for operation in plan.operations:
        assert set(operation.names) == {"es", "en", "pt"}, operation.names
    assert plan.operations_for(2, "max", "en")[1] == "Tyres (inspection and adjustment)"
    assert "travões" in " ".join(plan.operations_for(2, "max", "pt"))
    assert plan.operations_for(1, "max", "fr") == plan.operations_for(1, "max", "en")
    assert plan.operations_for(1, "max", "eu") == plan.operations_for(1, "max", "es")


def test_card_uses_only_existing_texts() -> None:
    source = (INTEGRATION / "frontend_card" / "dec-deepal-card.js").read_text(encoding="utf-8")
    spanish = json.loads((INTEGRATION / "idiomas" / "es.json").read_text(encoding="utf-8"))["tarjeta"]
    used = set(re.findall(r'_t\("([a-z_0-9]+)"', source)) | set(re.findall(r'translate\([^,]+, "([a-z_0-9]+)"', source))
    assert used - set(spanish) == set(), used - set(spanish)
    assert len(spanish) > 100
    # Los tipos de seguro de la tarjeta son los de la integración.
    from custom_components.dec_deepal.documents import INSURANCE_KINDS

    assert {f"kind_{kind}" for kind in INSURANCE_KINDS} <= set(spanish)
