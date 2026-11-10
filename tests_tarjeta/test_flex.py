"""Tarjeta «DEC Deepal · A medida» (custom:dec-deepal-flex-card, 2.6.0b16), en un navegador."""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

TAG = "dec-deepal-flex-card"
ROOT = "banco.card.shadowRoot"


def mount(page: Page, config: dict[str, Any] | None = None, **options: Any) -> None:
    page.evaluate("options => banco.montar(options)", {"tarjeta": TAG, "config": config or {}, **options})
    page.wait_for_function("banco.registro.some(line => line.includes('manual_info'))")
    page.wait_for_timeout(30)


def buttons(page: Page) -> list[str]:
    return page.evaluate(f"Array.from({ROOT}.querySelectorAll('.tile')).map(t => t.dataset.action)")


def card_classes(page: Page) -> list[str]:
    return page.evaluate(f"Array.from({ROOT}.querySelector('ha-card').classList)")


def test_defaults_look_like_the_card_of_always(page: Page) -> None:
    """Sin configurar nada: estilo completo, vista isométrica y los seis botones de siempre."""
    mount(page)
    assert "st-full" in card_classes(page)
    assert buttons(page) == ["comfort", "lock", "trunk", "vent", "locate", "others"]
    assert page.evaluate(f"{ROOT}.querySelector('.tiles').className") == "tiles c3"
    assert page.evaluate(f"{ROOT}.querySelector('.carbox').hidden") is False
    assert page.evaluate(f"{ROOT}.querySelector('.extra').hidden") is True
    # Está en el selector de tarjetas.
    cards = page.evaluate("window.customCards.map(c => [c.type, c.name])")
    assert [TAG, "DEC Deepal · A medida"] in cards


def test_chosen_buttons_order_and_columns(page: Page) -> None:
    mount(page, {"buttons": ["climate", "lock", "seat", "flash"], "columns": 2})
    assert buttons(page) == ["climate", "lock", "seat", "flash"]
    assert page.evaluate(f"{ROOT}.querySelector('.tiles').className") == "tiles c2"
    # Los directos llevan su marca; los de siempre, no.
    direct = page.evaluate(f"Array.from({ROOT}.querySelectorAll('.tile.dir')).map(t => t.dataset.action)")
    assert direct == ["climate", "seat", "flash"]
    names = page.evaluate(f"Array.from({ROOT}.querySelectorAll('.tile b')).map(b => b.textContent)")
    assert names == ["Clima rápido", "Bloqueo", "Asiento", "Luces"]


def test_direct_buttons_send_the_command(page: Page) -> None:
    mount(page, {"buttons": ["climate", "seat", "wheel", "flash", "refresh"]})
    for action, expected in (
        ("climate", "climate.turn_on"),
        ("seat", 'number.set_value {"entity_id":"number.changote_seat_heat_driver_x","value":1}'),
        ("wheel", "switch.toggle"),
        ("flash", "button.press"),
    ):
        page.evaluate(f"{ROOT}.querySelector('.tile[data-action={action}]').click()")
        page.wait_for_function("expected => banco.registro.some(line => line.startsWith(expected))", arg=expected)
    page.wait_for_function("banco.avisos.length >= 4")
    assert page.evaluate("banco.avisos[0]") == "Clima rápido: orden enviada"


def test_buttons_the_car_does_not_have_are_hidden(page: Page) -> None:
    """Un Pro sin calefacción de asientos: el botón «Asiento» no sale."""
    mount(page, {"buttons": ["seat", "lock"]}, sin=["number.seat_heat_driver"])
    assert buttons(page) == ["lock"]


def test_styles(page: Page) -> None:
    # Compacta: tres botones y la imagen al lado.
    mount(page, {"style": "compact"})
    assert "st-compact" in card_classes(page) and buttons(page) == ["comfort", "lock", "locate"]
    # Mini: una fila, sin testigos ni hora, con dos botones sin texto.
    mount(page, {"style": "mini"})
    assert "st-mini" in card_classes(page) and buttons(page) == ["lock", "climate"]
    assert page.evaluate(f"{ROOT}.querySelector('.status').hidden") is True
    assert page.evaluate(f"{ROOT}.querySelector('.upd').hidden") is True
    assert page.evaluate(f"getComputedStyle({ROOT}.querySelector('.tile b')).display") == "none"
    assert page.evaluate("banco.card.getCardSize()") == 2
    # Solo datos: sin imagen y con los datos extra.
    mount(page, {"style": "data"}, estados={"sensor.tire_pressure_front_left": [2.4, {"unit_of_measurement": "bar"}],
                                            "sensor.tire_pressure_rear_right": [2.6, {"unit_of_measurement": "bar"}]})
    assert page.evaluate(f"{ROOT}.querySelector('.carbox').hidden") is True
    extra = page.evaluate(f"Array.from({ROOT}.querySelectorAll('.extra b')).map(b => b.textContent)")
    assert extra[1] == "37.500 km" and extra[2] == "2,4 bar"
    # Lo elegido manda sobre el estilo.
    mount(page, {"style": "data", "image": "isometric", "show_extra": False})
    assert page.evaluate(f"{ROOT}.querySelector('.carbox').hidden") is False
    assert page.evaluate(f"{ROOT}.querySelector('.extra').hidden") is True


def test_images_and_the_charging_view(page: Page) -> None:
    src = f"{ROOT}.querySelector('.car').getAttribute('src')"
    mount(page, {"image": "top"})
    assert "#planta" in page.evaluate(src)
    # Con la manguera puesta, la vista de carga (si está activada).
    mount(page, {"image": "isometric", "charging_view": True}, estados={"sensor.charge_status": ["connected_ac"]})
    assert "#carga" in page.evaluate(src)
    assert page.evaluate(f"{ROOT}.querySelector('.carbox').classList.contains('charging')")
    mount(page, {"image": "isometric", "charging_view": False}, estados={"sensor.charge_status": ["connected_ac"]})
    assert "#carga" not in page.evaluate(src)
    mount(page, {"image": "none"}, estados={"sensor.charge_status": ["charging_ac"]})
    assert page.evaluate(f"{ROOT}.querySelector('.carbox').hidden") is True


def test_look_name_language_and_accent(page: Page) -> None:
    mount(page, {"name": "Mi Deepal", "language": "en", "accent": "purple", "buttons": ["comfort"]})
    assert page.evaluate(f"{ROOT}.querySelector('.name').textContent") == "Mi Deepal"
    assert page.evaluate(f"{ROOT}.querySelector('.tile b').textContent") == "Comfort"
    assert "accent" in card_classes(page)
    assert "purple" in page.evaluate("banco.card.style.getPropertyValue('--dec-accent')")
    assert page.evaluate(f"{ROOT}.querySelector('.bar i').style.background") == "var(--dec-accent)"


def test_hiding_parts(page: Page) -> None:
    mount(page, {"show_status": False, "show_updated": False, "show_extra": True})
    assert page.evaluate(f"{ROOT}.querySelector('.status').hidden") is True
    assert page.evaluate(f"{ROOT}.querySelector('.upd').hidden") is True
    assert page.evaluate(f"{ROOT}.querySelector('.extra').hidden") is False


def test_editor_form(page: Page) -> None:
    """El editor visual: apartados plegables, botones que se ordenan y textos traducidos."""
    page.evaluate("banco.montar({})")
    form = f"customElements.get('{TAG}').getConfigForm()"
    names = page.evaluate(f"{form}.schema.map(f => f.name || f.title)")
    assert names == ["device_id", "style", "Imagen", "Datos", "Botones", "Aspecto"]
    assert page.evaluate(f"{form}.schema.filter(f => f.type === 'expandable').every(f => f.flatten)")
    buttons_field = page.evaluate(f"{form}.schema[4].schema[0]")
    assert buttons_field["name"] == "buttons"
    assert buttons_field["selector"]["select"]["multiple"] and buttons_field["selector"]["select"]["reorder"]
    assert len(buttons_field["selector"]["select"]["options"]) == 12
    assert page.evaluate(f"{form}.computeLabel({{name: 'charging_view'}})") == "Vista de carga al enchufar"
    assert page.evaluate(f"{form}.computeHelper({{name: 'buttons'}})").startswith("Elígelos y arrástralos")
    stub = page.evaluate(f"customElements.get('{TAG}').getStubConfig(banco.hass)")
    assert stub["style"] == "full" and stub["charging_view"] is True and stub["show_status"] is True
