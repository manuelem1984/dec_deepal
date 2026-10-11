"""Pruebas de la tarjeta en un navegador de verdad.

Cada prueba abre ``pagina.html`` (la tarjeta con un Home Assistant falso,
``banco.js``) y la maneja como lo haría una persona: mira lo que pinta y
pulsa. Si la tarjeta lanza un error de JavaScript, la prueba falla aunque lo
que se mire esté bien.

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


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.environ.get("DEC_NAVEGADOR") or None)
        yield browser
        browser.close()


@pytest.fixture
def page(browser: Browser) -> Iterator[Page]:
    """La página del banco de pruebas, ya cargada (falta ``banco.montar``)."""
    context = browser.new_context(locale="es-ES", timezone_id="Europe/Madrid")
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.goto(PAGE)
    page.wait_for_function("Boolean(window.banco && customElements.get('dec-deepal-card'))")
    yield page
    context.close()
    assert errors == [], "La tarjeta ha dado errores en el navegador"
