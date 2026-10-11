"""La tarjeta y el panel se generan uniendo los módulos de sus carpetas ``src/``.

Lo que hacen se prueba en un navegador (``tests_tarjeta/``); aquí solo se
comprueba que los ficheros que carga Home Assistant están al día.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


@pytest.fixture(scope="module")
def tool():  # noqa: ANN201
    """El constructor (``tools/construir_tarjeta.py``), cargado como módulo."""
    spec = importlib.util.spec_from_file_location("construir_tarjeta", ROOT / "tools" / "construir_tarjeta.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_card_is_up_to_date(tool) -> None:  # noqa: ANN001
    """Si falla: ejecutar ``python tools/construir_tarjeta.py`` y subir el resultado."""
    assert tool.CARD.read_text(encoding="utf-8") == tool.build(tool.read_sources())
    assert tool.main(["--check"]) == 0


def test_panel_is_built_the_same_way(tool) -> None:  # noqa: ANN001
    built = tool.outputs()
    assert set(built) == {tool.CARD, tool.PANEL}
    panel = built[tool.PANEL]
    assert tool.PANEL.read_text(encoding="utf-8") == panel
    assert panel.startswith(tool.PANEL_BANNER) and "frontend_panel/src/" in tool.PANEL_BANNER
    assert 'customElements.define(TAG, DecDeepalPanel)' in panel
    for content in tool.read_sources(tool.PANEL_SRC).values():
        assert content in panel


def test_modules_are_joined_in_order(tool) -> None:  # noqa: ANN001
    sources = tool.read_sources()
    card = tool.build(sources)
    assert card.startswith(tool.BANNER) and card.endswith("})();\n")
    positions = [card.index(f"// ── src/{name} ") for name in sorted(sources) if name != tool.HEADER]
    assert positions == sorted(positions) and len(positions) >= 12
    # Lo que hay en src/ es lo que se ejecuta: no se transforma.
    for content in sources.values():
        assert content in card


def test_mistakes_are_reported(tool) -> None:  # noqa: ANN001
    sources = tool.read_sources()
    with pytest.raises(tool.BuildError, match="nombre"):
        tool.build({**sources, "ventana nueva.js": "  // x\n"})
    with pytest.raises(tool.BuildError, match="salto de línea"):
        tool.build({**sources, "66_nueva.js": "  // x"})
    with pytest.raises(tool.BuildError, match="Falta"):
        tool.build({name: text for name, text in sources.items() if name != tool.HEADER})
