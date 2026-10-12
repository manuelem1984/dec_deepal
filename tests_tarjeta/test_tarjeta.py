"""La tarjeta, probada en un navegador: lo que pinta y lo que hace al pulsar."""

from __future__ import annotations

from playwright.sync_api import Page

CHARGE = "component.dec_deepal.entity.sensor.charge_status.state."
CLIMATE_ON = {"climate.cabin_climate": ["heat_cool", {"temperature": 22.5, "min_temp": 16, "max_temp": 32}]}


def mount(page: Page, **options) -> None:  # noqa: ANN003
    page.evaluate("options => banco.montar(options)", options)
    # La tarjeta pregunta a la integración por el manual nada más pintarse.
    page.wait_for_function("banco.registro.some(line => line.includes('manual_info'))")


def tiles(page: Page) -> dict[str, list[str]]:
    return page.evaluate("banco.botones()")


def window_text(page: Page) -> str:
    """Texto de la ventana de encima (espacios compactados)."""
    return " ".join(page.evaluate("banco.ventana().querySelector('.dlg').textContent").split())


def click_window(page: Page, selector: str) -> None:
    page.evaluate("selector => banco.ventana().querySelector(selector).click()", selector)


def click_tile(page: Page, action: str) -> None:
    page.evaluate(
        "action => banco.card.shadowRoot.querySelector(`.tile[data-action=\"${action}\"]`).click()", action
    )


def services(page: Page) -> list[str]:
    """Órdenes al coche (sin las preguntas a la integración)."""
    return [line for line in page.evaluate("banco.registro") if not line.startswith("api ")]


# --- Lo que pinta ---------------------------------------------------------------


def test_a_parked_car(page: Page) -> None:
    mount(page)
    root = "banco.card.shadowRoot"
    assert page.evaluate(f"{root}.querySelector('.name').textContent") == "Changote"
    assert page.evaluate(f"{root}.querySelector('.km').textContent") == "378 km"
    assert page.evaluate("banco.estado()") == ["mdi:check-circle"]
    assert tiles(page) == {
        "comfort": ["Confort", "Apagado · 26 °C", ""],
        "lock": ["Bloqueo", "Bloqueado", ""],
        "trunk": ["Maletero", "Cerrado", ""],
        "vent": ["Ventilar", "Cerradas", ""],
        "locate": ["Localizar vehículo", "Luces y claxon", ""],
        "others": ["Otros", "Manual y documentos", ""],
    }


def test_top_view_card(page: Page) -> None:
    """La otra tarjeta: lo mismo, con el coche visto desde arriba."""
    box = "banco.card.shadowRoot.querySelector('.carbox')"
    car = "banco.card.shadowRoot.querySelector('.car')"
    # La de siempre sigue con la isométrica.
    mount(page)
    assert page.evaluate(f"{box}.className") == "carbox" and "#planta" not in page.evaluate(f"{car}.src")

    mount(page, tarjeta="dec-deepal-top-card")
    assert page.evaluate("banco.card.localName") == "dec-deepal-top-card"
    assert "#planta" in page.evaluate(f"{car}.src")
    assert page.evaluate(f"Array.from({box}.classList)") == ["carbox", "top"]
    # Tumbada: más ancha que alta, con la imagen girada (morro a la izquierda).
    wide = page.evaluate(f"(() => {{ const r = {box}.getBoundingClientRect(); return r.width / r.height; }})()")
    assert abs(wide - 720 / 510) < 0.02
    assert page.evaluate(f"getComputedStyle({car}).transform") != "none"
    # El resto es la misma tarjeta: mismos botones y mismas ventanas.
    assert tiles(page)["lock"] == ["Bloqueo", "Bloqueado", ""] and len(tiles(page)) == 6
    click_tile(page, "others")
    assert "Manual" in window_text(page)
    click_window(page, '[data-action="close"]')

    # De pie: más alta que ancha y sin girar.
    mount(page, tarjeta="dec-deepal-top-card", config={"orientation": "vertical"})
    assert page.evaluate(f"Array.from({box}.classList)") == ["carbox", "top", "vertical"]
    tall = page.evaluate(f"(() => {{ const r = {box}.getBoundingClientRect(); return r.width / r.height; }})()")
    assert abs(tall - 510 / 720) < 0.02
    assert page.evaluate(f"getComputedStyle({car}).transform") == "none"
    assert page.evaluate("banco.card.getCardSize()") == 11

    # Un coche sin vista de planta: la imagen DEC, sin recortar.
    mount(page, tarjeta="dec-deepal-top-card", sin=["image.top_view"], estados={"image.dec_photo": ["x", {"entity_picture": "coche.svg"}]})
    assert page.evaluate(f"Array.from({box}.classList)") == ["carbox", "plain"]

    # Las dos salen en el selector de tarjetas, y la de planta deja elegir la orientación.
    cards = page.evaluate("window.customCards.filter(c => c.type.startsWith('dec-deepal')).map(c => [c.type, c.name])")
    assert cards == [["dec-deepal-card", "DEC Deepal"], ["dec-deepal-top-card", "DEC Deepal · Vista de planta"]]
    form = "customElements.get('dec-deepal-top-card').getConfigForm()"
    assert page.evaluate(f"{form}.schema.map(f => f.name)") == ["device_id", "orientation"]
    assert page.evaluate(f"{form}.schema[1].selector.select.options.map(o => o.label)") == ["Horizontal (tumbado)", "Vertical (de pie)"]
    assert page.evaluate(f"[{form}.computeLabel({{name: 'device_id'}}), {form}.computeLabel({{name: 'orientation'}})]") == ["Coche", "Orientación del coche"]
    assert page.evaluate("customElements.get('dec-deepal-card').getConfigForm().schema.map(f => f.name)") == ["device_id"]


def charge_stats(page: Page) -> list[list[str]]:
    """Recuadros de la ventana de carga: `[título, valor, detalle]`."""
    return page.evaluate(
        "Array.from(banco.ventana().querySelectorAll('.st')).map(st => "
        "['.k', '.n', '.d'].map(part => st.querySelector(part).textContent.trim()))"
    )


def test_charge_window(page: Page) -> None:
    """Pulsar la franja de la batería abre la ventana de carga."""
    energy = "banco.card.shadowRoot.querySelector('.energy')"
    window = "banco.ventana()"

    # --- Sin enchufar, con una carga anterior apuntada -----------------------
    last = {"inicio": "2026-10-11T22:10:00", "fin": "2026-10-12T03:40:00", "nivel_inicio": 22, "nivel_fin": 80,
            "autonomia_inicio": 108, "autonomia_fin": 394}
    mount(page, estados={"binary_sensor.charging": ["off", {"ultima_carga": last}]})
    assert page.evaluate(f"{energy}.getAttribute('aria-label')") == "Ver la carga"
    page.evaluate(f"{energy}.click()")
    assert "Carga" in window_text(page) and "Sin enchufar" in window_text(page)
    assert page.evaluate(f"[{window}.querySelector('.pct b').textContent, {window}.querySelector('.pct span').textContent]") == ["78 %", "378 km de autonomía"]
    assert "#carga" in page.evaluate(f"{window}.querySelector('.view img').src")
    # Tema claro: el coche (translúcido y claro) se oscurece para que se vea.
    assert page.evaluate(f"getComputedStyle({window}.querySelector('.view img')).filter") != "none"
    assert charge_stats(page) == [["Última carga", "Del 22 % al 80 %", "11 oct, 22:10 – 3:40 · 5 h 30 min"]]
    # No se abre dos veces, y "Actualizar" pide una lectura al coche.
    page.evaluate(f"{energy}.click()")
    assert page.evaluate("banco.ventanas().length") == 1
    click_window(page, '[data-action="refresh"]')
    assert services(page)[-1].startswith("button.press")

    # --- Se enchufa y empieza a cargar: la ventana abierta se repinta sola ------
    page.evaluate(
        """() => banco.cambiar({
            "sensor.battery_level": [56],
            "sensor.range": [276, { unit_of_measurement: "km" }],
            "sensor.charge_status": ["charging_ac"],
            "sensor.remaining_charge_time_hhmm": ["3:25"],
            "sensor.charge_current": [16, { unit_of_measurement: "A" }],
            "binary_sensor.charging": ["on", {
                carga_actual: { inicio: new Date(Date.now() - 65 * 60000).toISOString(), nivel_inicio: 44, autonomia_inicio: 217 },
                ultima_carga: { inicio: "2026-10-11T22:10:00", fin: "2026-10-12T03:40:00", nivel_inicio: 22, nivel_fin: 80 },
            }],
        })"""
    )
    text = window_text(page)
    assert "Cargando · AC · lleno a las " in text and "56 %" in text and "276 km de autonomía" in text
    assert page.evaluate(f"{window}.querySelector('.now').classList.contains('on')")
    stats = charge_stats(page)
    assert [stat[0] for stat in stats] == ["Tiempo restante", "Corriente", "Conector", "Esta carga"]
    assert stats[0][1] == "3 h 25 min" and stats[0][2].startswith("Termina hacia las ")
    assert stats[1][1:] == ["16 A", "Corriente alterna"]
    assert stats[2][1:] == ["AC · Tipo 2", "Enchufado"]
    assert stats[3][1] == "+12 % · +59 km" and stats[3][2].startswith("Desde las ") and stats[3][2].endswith("· 1 h 5 min")
    click_window(page, '[data-action="close"]')

    # --- Enchufado sin cargar (DC), en tema oscuro y sin vista de carga ----------
    mount(
        page,
        oscuro=True,
        sin=["image.charging_view"],
        estados={"sensor.battery_level": [100], "sensor.charge_status": ["connected_dc"]},
    )
    page.evaluate(f"{energy}.click()")
    assert "Enchufado · no carga" in window_text(page)
    assert page.evaluate(f"{window}.querySelector('.view').hidden") is True
    assert page.evaluate(f"{window}.querySelector('.chg').classList.contains('dark')")
    assert charge_stats(page) == [["Corriente", "0 A", "Sin carga en curso"], ["Conector", "DC · CCS2", "Enchufado"]]
    click_window(page, '[data-action="close"]')

    # --- Igual en la tarjeta de planta, y también con el teclado ------------------
    mount(page, tarjeta="dec-deepal-top-card")
    page.evaluate(f"{energy}.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', bubbles: true, composed: true }}))")
    assert "Sin enchufar" in window_text(page)
    assert charge_stats(page) == []  # ninguna carga apuntada todavía


def test_comfort_is_highlighted_only_when_something_is_on(page: Page) -> None:
    """Fallo de la 2.3.0b11: Confort salía en azul con todo apagado."""
    mount(page)
    assert tiles(page)["comfort"][2] == ""
    page.evaluate("states => banco.cambiar(states)", CLIMATE_ON)
    assert tiles(page)["comfort"] == ["Confort", "Encendido · 22,5 °C", "pri"]
    page.evaluate("banco.cambiar({'climate.cabin_climate': ['off'], 'number.seat_heat_driver': [2]})")
    assert tiles(page)["comfort"] == ["Confort", "Asientos · 26 °C", "pri"]
    page.evaluate("banco.cambiar({'number.seat_heat_driver': [0]})")
    assert tiles(page)["comfort"][2] == ""


def test_open_car_and_charging(page: Page) -> None:
    mount(
        page,
        estados={
            "sensor.battery_level": [34],
            "sensor.charge_status": ["charging_ac"],
            "binary_sensor.charging": ["on"],
            "sensor.remaining_charge_time_hhmm": ["1:35"],
            "binary_sensor.trunk": ["on"],
            "lock.doors": ["unlocked"],
            "cover.windows": ["closed"],
        },
        textos={f"{CHARGE}charging_ac": "Cargando AC"},
    )
    assert page.evaluate("banco.card.shadowRoot.querySelector('.charge span').textContent") == "Cargando AC · 1:35 h"
    shown = tiles(page)
    assert shown["lock"] == ["Bloqueo", "Desbloqueado", "on"]
    assert shown["trunk"] == ["Maletero", "Abierto", "on"]
    assert shown["vent"] == ["Ventilar", "Ventilando", "on"]


def test_warning_lights(page: Page) -> None:
    mount(page, estados={"binary_sensor.warning_abs": ["on"], "binary_sensor.warning_12v_battery": ["on"]})
    assert page.evaluate("banco.estado()") == ["mdi:car-battery", "mdi:car-brake-abs"]
    # El del airbag se enciende solo al despertar el S05: su ficha lo silencia.
    page.evaluate(
        "banco.cambiar({'binary_sensor.warning_abs': ['off'], 'binary_sensor.warning_12v_battery': ['off'],"
        " 'binary_sensor.warning_airbag': ['on']})"
    )
    assert page.evaluate("banco.estado()") == ["mdi:check-circle"]


def test_silent_warnings_come_from_the_vehicle_sheet(page: Page) -> None:
    """Qué testigos no se enseñan lo dice la ficha del coche, no la tarjeta."""
    airbag = {"binary_sensor.warning_airbag": ["on"]}
    # Un coche cuya ficha no silencia nada: el airbag se enseña.
    mount(page, estados=airbag, manual={"available": False, "url": None, "itv": True, "silent_warnings": []})
    page.wait_for_function("banco.estado().includes('mdi:airbag')")
    # Otro que silencia el ABS: ese es el que no sale.
    mount(
        page,
        estados={**airbag, "binary_sensor.warning_abs": ["on"]},
        manual={"available": False, "url": None, "itv": True, "silent_warnings": ["warning_abs"]},
    )
    page.wait_for_function("JSON.stringify(banco.estado()) === '[\"mdi:airbag\"]'")


def test_due_indicators_open_their_window(page: Page) -> None:
    mount(
        page,
        estados={
            "binary_sensor.maintenance_due": ["on", {
                "nivel": "soon", "revision": 2, "fecha_prevista": "2027-03-10", "km_previstos": 39500,
                "dias_restantes": 47, "km_restantes": 2000, "operaciones": ["Inspección general"], "historial": [],
            }],
        },
    )
    assert page.evaluate("banco.estado()") == ["mdi:wrench"]
    page.evaluate("banco.card.shadowRoot.querySelector('.status button').click()")
    text = window_text(page)
    assert "2ª revisión" in text and "47" in text and "2.000" in text and "Inspección general" in text
    # Registrar pide confirmación y, al aceptar, se lo dice a la integración.
    click_window(page, '[data-action="register"]')
    assert services(page) == []
    click_window(page, '[data-action="ok"]')
    page.wait_for_function("banco.ventanas().length === 0")
    assert services(page) == ['dec_deepal.register_maintenance {"device_id":"dev1"}']


# --- Idiomas --------------------------------------------------------------------


def test_languages(page: Page) -> None:
    mount(page, idioma="en")
    assert tiles(page)["trunk"] == ["Boot", "Closed", ""]
    # Catalán, gallego y euskera se ven en español; uno sin traducir, en inglés.
    for language, expected in (
        ("ca", "Maletero"), ("eu", "Maletero"), ("pl", "Bagażnik"), ("fr", "Coffre"), ("de", "Kofferraum"),
        ("el", "Πορτμπαγκάζ"), ("lb", "Coffre"), ("sv", "Boot"),
    ):
        mount(page, idioma=language)
        assert tiles(page)["trunk"][0] == expected, language


def test_state_text_follows_a_language_change(page: Page) -> None:
    """Fallo de la 2.3.0b11: "Desconectado" se quedaba en el idioma anterior.

    Home Assistant cambia primero el idioma y un poco después sus textos: la
    tarjeta tiene que repintar también cuando llegan los textos.
    """
    mount(page, textos={f"{CHARGE}disconnected": "Desconectado"})
    charge = "banco.card.shadowRoot.querySelector('.charge span').textContent"
    assert page.evaluate(charge) == "Desconectado"
    page.evaluate("textos => banco.idioma('it', textos)", {f"{CHARGE}disconnected": "Scollegato"})
    assert page.evaluate(charge) == "Scollegato"
    assert tiles(page)["trunk"][0] == "Bagagliaio"


# --- Menús y ventanas -----------------------------------------------------------


def test_others_menu(page: Page) -> None:
    mount(page)
    click_tile(page, "others")
    options = page.evaluate(
        "Array.from(banco.ventana().querySelectorAll('.tile')).map(t => t.querySelector('b').textContent)"
    )
    assert options == ["Manual", "Mantenimiento", "ITV", "Seguro"]
    # El manual es un enlace que se abre en otra pestaña (no dentro de la app).
    link = "banco.ventana().querySelector('a[data-action=\"manual\"]')"
    assert page.evaluate(f"[{link}.href, {link}.target]") == ["https://example.com/manual.pdf", "_blank"]


def test_itv_is_hidden_where_the_country_has_none(page: Page) -> None:
    mount(page, manual={"available": True, "url": "https://example.com/manual.pdf", "itv": False})
    click_tile(page, "others")
    options = page.evaluate(
        "Array.from(banco.ventana().querySelectorAll('.tile')).map(t => t.querySelector('b').textContent)"
    )
    assert options == ["Manual", "Mantenimiento", "Seguro"]


def test_itv_window_registers_with_confirmation(page: Page) -> None:
    mount(
        page,
        estados={
            "binary_sensor.itv_due": ["on", {
                "nivel": "soon", "fecha_limite": "2026-11-26", "dias_restantes": 47,
                "matriculacion": "2022-11-26", "ultima_itv": None, "historial": [],
            }],
        },
    )
    assert page.evaluate("banco.estado()") == ["mdi:clipboard-check-outline"]
    assert tiles(page)["others"][1] == "ITV en 47 días"
    page.evaluate("banco.card.shadowRoot.querySelector('.status button').click()")
    assert "26 nov 2026" in window_text(page)
    click_window(page, '[data-action="register"]')
    click_window(page, '[data-action="ok"]')
    page.wait_for_function("banco.ventanas().length === 0")
    assert services(page) == ['dec_deepal.register_itv {"device_id":"dev1"}']


def test_insurance_window_and_call_buttons(page: Page) -> None:
    """Fallo de la 2.3.0b10: en la app del móvil los botones de llamar no hacían nada."""
    mount(page)
    click_tile(page, "others")
    click_window(page, '[data-action="insurance"]')
    page.wait_for_function("banco.ventana() && banco.ventana().querySelector('.call')")
    text = window_text(page)
    assert "Mutua Ejemplo" in text and "0123 4567 89" in text and "Todo riesgo con franquicia" in text
    calls = page.evaluate(
        "Array.from(banco.ventana().querySelectorAll('.call')).map(a =>"
        " [a.getAttribute('href'), a.target, a.textContent.replace(/\\s+/g, ' ').trim()])"
    )
    # Enlace "tel:" que sale de la app (target=_blank) y con el número a la vista.
    assert calls == [
        ["tel:900000000", "_blank", "Asistencia900 000 000"],
        ["tel:910000000", "_blank", "Compañía910 000 000"],
    ]
    # Al pulsar, además, copia el número y lo dice.
    page.evaluate(
        """() => {
          window.copiado = null;
          Object.defineProperty(navigator, "clipboard", {
            value: { writeText: async (text) => { window.copiado = text; } }, configurable: true });
          const call = banco.ventana().querySelector(".call");
          call.addEventListener("click", (event) => event.preventDefault());
          call.click();
        }"""
    )
    page.wait_for_function("banco.avisos.length === 1")
    assert page.evaluate("[window.copiado, banco.avisos[0]]") == ["900 000 000", "Número copiado: 900 000 000"]


def test_insurance_not_configured(page: Page) -> None:
    mount(page, sin=["binary_sensor.insurance_due"])
    click_tile(page, "others")
    click_window(page, '[data-action="insurance"]')
    assert "Seguro" in window_text(page)
    assert page.evaluate("banco.ventana().querySelector('.call')") is None


# --- Órdenes al coche -------------------------------------------------------------


def test_unlock_asks_first_and_arms_the_pin(page: Page) -> None:
    mount(page)
    click_tile(page, "lock")
    assert "Changote" in window_text(page)
    assert services(page) == []  # hasta que no se confirma, no se envía nada
    click_window(page, '[data-action="ok"]')
    page.wait_for_function("banco.registro.filter(line => line.startsWith('lock.')).length === 2")
    # Modo "desbloqueo previo": primero arma el PIN y después desbloquea.
    assert services(page) == [
        'lock.unlock {"entity_id":"lock.changote_pin_arm_x"}',
        'lock.unlock {"entity_id":"lock.changote_doors_x"}',
    ]
    assert tiles(page)["lock"] == ["Bloqueo", "Desbloqueado", "on"]


def test_cancelling_sends_nothing(page: Page) -> None:
    mount(page)
    click_tile(page, "trunk")
    click_window(page, '[data-action="close"]')
    assert page.evaluate("banco.ventanas().length") == 0 and services(page) == []


def test_a_version_without_power_tailgate(page: Page) -> None:
    """Un Pro no tiene portón eléctrico: la tarjeta lo dice en vez de pedir el PIN."""
    mount(
        page,
        sin=["cover.trunk_control"],
        manual={
            "available": True, "url": "https://example.com/manual.pdf", "itv": True,
            "silent_warnings": [], "features": {"porton_electrico": False},
        },
    )
    page.wait_for_function("banco.card._features && banco.card._features.porton_electrico === false")
    assert tiles(page)["trunk"] == ["Maletero", "Cerrado", ""]  # el estado sí se enseña
    click_tile(page, "trunk")
    assert page.evaluate("banco.ventanas().length") == 0 and services(page) == []
    assert page.evaluate("banco.avisos") == [
        "Este coche no tiene portón eléctrico: el maletero se abre y se cierra a mano."
    ]


def test_locate_menu(page: Page) -> None:
    mount(page)
    click_tile(page, "locate")
    options = page.evaluate(
        "Array.from(banco.ventana().querySelectorAll('.tile b')).map(b => b.textContent)"
    )
    assert options == ["Luces", "Claxon", "Luces y claxon"]
    click_window(page, '[data-key="button.honk_horn"]')
    page.wait_for_function("banco.ventanas().length === 0")
    assert services(page) == ['button.press {"entity_id":"button.changote_honk_horn_x"}']


def test_comfort_window(page: Page) -> None:
    mount(page)
    click_tile(page, "comfort")
    click_window(page, '[data-key="number.seat_heat_driver"]')
    click_window(page, '[data-key="switch.steering_wheel_heat"]')
    click_window(page, '[data-action="power"]')
    page.wait_for_function("banco.registro.filter(line => !line.startsWith('api ')).length === 3")
    assert services(page) == [
        'number.set_value {"entity_id":"number.changote_seat_heat_driver_x","value":1}',
        'switch.toggle {"entity_id":"switch.changote_steering_wheel_heat_x"}',
        'climate.turn_on {"entity_id":"climate.changote_cabin_climate_x"}',
    ]
    # La ventana y el botón de la tarjeta reflejan lo que ha cambiado.
    assert page.evaluate("banco.ventana().querySelector('.power').classList.contains('on')")
    assert tiles(page)["comfort"][2] == "pri"


def test_a_failed_command_is_reported(page: Page) -> None:
    mount(page, fallo="El coche no responde")
    click_tile(page, "locate")
    click_window(page, '[data-key="button.flash_lights"]')
    page.wait_for_function("banco.avisos.length === 1")
    assert page.evaluate("banco.avisos[0]") == "El coche no responde"


def test_a_car_without_optional_entities(page: Page) -> None:
    """Un Pro (sin asientos calefactados) o un coche sin configurar: nada se rompe."""
    mount(
        page,
        sin=[
            "number.seat_heat_driver", "number.seat_heat_passenger", "number.seat_vent_driver",
            "number.seat_vent_passenger", "switch.steering_wheel_heat", "binary_sensor.maintenance_due",
            "binary_sensor.itv_due", "binary_sensor.insurance_due", "lock.pin_arm",
        ],
    )
    assert tiles(page)["comfort"][0] == "Confort"
    click_tile(page, "comfort")
    assert page.evaluate("banco.ventana().querySelectorAll('.hot').length") == 0
    click_window(page, '[data-action="close"]')
    click_tile(page, "others")
    assert "Sin activar" in window_text(page)
