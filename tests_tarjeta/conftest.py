"""Pruebas de la tarjeta y del panel en un navegador de verdad.

Cada prueba abre ``pagina.html`` (la tarjeta con un Home Assistant falso,
``banco.js``) o ``pagina_panel.html`` (el panel, con ``banco_panel.js``) y lo
maneja como lo haría una persona: mira lo que pinta y pulsa. Si lanza un
error de JavaScript, la prueba falla aunque lo que se mire esté bien.

Navegador: el Chromium de Playwright. Para usar uno ya instalado (sin
descargar nada), ``DEC_NAVEGADOR=msedge`` o ``DEC_NAVEGADOR=chrome``.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

PAGE = (Path(__file__).parent / "pagina.html").as_uri()
PANEL_PAGE = (Path(__file__).parent / "pagina_panel.html").as_uri()


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.environ.get("DEC_NAVEGADOR") or None)
        yield browser
        browser.close()


def _open(browser: Browser, url: str, element: str) -> Iterator[Page]:
    context = browser.new_context(
        locale="es-ES", timezone_id="Europe/Madrid", viewport={"width": 1180, "height": 900}
    )
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.goto(url)
    page.wait_for_function(f"Boolean(window.banco && customElements.get('{element}'))")
    yield page
    context.close()
    assert errors == [], "Ha habido errores de JavaScript en el navegador"


@pytest.fixture
def page(browser: Browser) -> Iterator[Page]:
    """La página del banco de pruebas de la tarjeta, ya cargada (falta ``banco.montar``)."""
    yield from _open(browser, PAGE, "dec-deepal-card")


@pytest.fixture
def panel(browser: Browser) -> Iterator[Page]:
    """La página del banco de pruebas del panel, ya cargada (falta ``banco.montar``)."""
    yield from _open(browser, PANEL_PAGE, "dec-deepal-panel")
