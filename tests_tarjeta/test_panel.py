"""El panel DEC Deepal, probado en un navegador: lo que pinta y lo que manda a la integración."""

from __future__ import annotations

import json
from typing import Any

from playwright.sync_api import Page

ME = "mobile_app_iphone_de_manuel"
HER = "mobile_app_iphone_de_ella"
BELL = "persistent_notification"


def mount(page: Page, **options: Any) -> None:
    page.evaluate("options => banco.montar(options)", options)
    page.wait_for_function("banco.registro.some(m => m.type === 'dec_deepal/panel/state')")
    page.wait_for_function("!banco.texto().includes('Cargando') && !banco.texto().includes('Loading')")


def tab(page: Page, name: str) -> None:
    page.evaluate("name => banco.pulsar(`[data-tab=${name}]`)", name)


def click(page: Page, selector: str, index: int = 0) -> None:
    page.evaluate("([selector, index]) => banco.pulsar(selector, index)", [selector, index])


def orders(page: Page) -> list[dict[str, Any]]:
    return page.evaluate("banco.ordenes()")


def window_text(page: Page) -> str:
    return " ".join(page.evaluate("banco.ventana().querySelector('.dlg').textContent").split())


def fill(page: Page, name: str, value: str) -> None:
    page.evaluate(
        "([name, value]) => { banco.ventana().querySelector(`[name=${name}]`).value = value; }", [name, value]
    )


def click_window(page: Page, action: str) -> None:
    page.evaluate("action => banco.ventana().querySelector(`[data-action=${action}]`).click()", action)


# --- Coches -----------------------------------------------------------------------


def test_cars_tab(panel: Page) -> None:
    mount(panel)
    text = panel.evaluate("banco.texto()")
    # Cada coche con su versión, sus datos y el equipamiento de SU ficha.
    assert "Changote" in text and "Deepal S05 EV RWD Max · Ganymede Grey" in text
    assert "56 %" in text and "276 km" in text and "3.499 km" in text  # con separador de miles
    assert "Ficha verificada" in text and "Asientos ventilados" in text and "Llanta 20\" sin tapacubos" in text
    cards = panel.evaluate("Array.from(banco.raiz().querySelectorAll('.card')).map(c => c.textContent.replace(/\\s+/g, ' '))")
    assert "Asientos" not in cards[1] and "Llanta 18\"" in cards[1] and "Ficha de catálogo" in cards[1]
    # Mantenimiento, ITV y seguro, con su engranaje; sin configurar, se ofrece añadirlos.
    assert "1ª revisión" in cards[0] and "Quedan 291 días o 16.501 km" in cards[0]
    assert "29 jul 2030" in cards[0] and "Límite para desistir: 29 jun 2027" in cards[0]
    assert cards[1].count("Sin configurar") == 3 and "Añadir el seguro" in cards[1]
    assert panel.evaluate("banco.raiz().querySelectorAll('.gear').length") == 6


def test_people_of_each_car(panel: Page) -> None:
    """A quién pertenece cada coche: se ve en la tarjeta y se elige en una ventana."""
    mount(panel)
    people = panel.evaluate(
        "Array.from(banco.raiz().querySelectorAll('.people')).map(r => Array.from(r.querySelectorAll('.chip, .none')).map(n => n.textContent.trim()))"
    )
    assert people == [["Manuel"], ["Sin asignar"]]
    cards = panel.evaluate("Array.from(banco.raiz().querySelectorAll('.card')).map(c => c.textContent)")
    assert "Tuyo" in cards[0] and "Tuyo" not in cards[1]
    click(panel, "[data-action=people]", 1)
    assert "Personas de Changuito" in window_text(panel)
    panel.evaluate("banco.ventana().querySelector('[name=\"person.ella\"]').checked = true")
    click_window(panel, "ok")
    panel.wait_for_function("banco.registro.some(m => m.type === 'dec_deepal/panel/set_people')")
    assert orders(panel)[-1] == {"type": "dec_deepal/panel/set_people", "vehicle_id": "car2", "people": ["person.ella"]}


def test_number_plates(panel: Page) -> None:
    """Placa genérica europea con la matrícula, en Coches y en Avisos."""
    mount(panel)
    plates = panel.evaluate(
        "Array.from(banco.raiz().querySelectorAll('.hero .plate')).map(p => [p.querySelector('.eu').textContent.trim(), p.querySelector('.num').textContent, p.querySelectorAll('.seals').length, p.getAttribute('aria-label')])"
    )
    assert plates == [["E", "6545 NPD", 0, "Matrícula 6545 NPD"], ["D", "MAB 1234", 1, "Matrícula M AB 1234"]]
    # Va en la línea del modelo y el color.
    assert panel.evaluate("banco.raiz().querySelector('.hero .m .plate') !== null")
    # La etiqueta "Personas" ya no lleva la raya ni el relleno de los títulos de sección.
    style = panel.evaluate("(() => { const s = getComputedStyle(banco.raiz().querySelector('.people .lbl')); return [s.borderTopWidth, s.paddingTop]; })()")
    assert style == ["0px", "0px"]
    tab(panel, "alerts")
    assert panel.evaluate("banco.raiz().querySelectorAll('.chead .plate').length") == 2


def test_studio_background_only_in_dark_theme(panel: Page) -> None:
    """Tema oscuro: fondo de estudio detrás de las fotos (el techo y la zaga no se pierden)."""
    background = "getComputedStyle(banco.raiz().querySelector('.hero img')).backgroundImage"
    mount(panel, oscuro=True)
    assert panel.evaluate("banco.panel.hasAttribute('dark')")
    assert "radial-gradient" in panel.evaluate(background)
    tab(panel, "alerts")
    assert "radial-gradient" in panel.evaluate("getComputedStyle(banco.raiz().querySelector('.chead img')).backgroundImage")
    mount(panel)
    assert panel.evaluate(background) == "none"


def test_read_only_for_other_users(panel: Page) -> None:
    """Quien no es administrador ve Coches y Avisos, sin poder cambiar nada."""
    mount(panel, lectura=True)
    tabs = panel.evaluate("Array.from(banco.raiz().querySelectorAll('[data-tab]')).map(b => b.dataset.tab)")
    assert tabs == ["cars", "alerts"]
    text = panel.evaluate("banco.texto()")
    assert "Solo lectura" in text and "Changote" in text and "Tuyo" in text
    # Ni engranajes, ni Apariencia, ni elegir personas.
    for selector in (".gear", "[data-action=appearance]", "[data-action=people]"):
        assert panel.evaluate(f"banco.raiz().querySelectorAll('{selector}').length") == 0, selector
    # La ficha se puede abrir, pero sin "Registrar" ni engranaje.
    click(panel, "[data-action=info][data-kind=maintenance]")
    assert "1ª revisión" in window_text(panel)
    assert panel.evaluate("banco.ventana().querySelectorAll('[data-action=register], [data-action=configure]').length") == 0
    click_window(panel, "close")
    # Avisos: se ve lo marcado, sin casillas que tocar ni botones de guardar.
    tab(panel, "alerts")
    assert panel.evaluate("banco.raiz().querySelectorAll('.box.ro').length") > 0
    assert panel.evaluate("banco.raiz().querySelectorAll('button.box, [data-action=copy-alerts], .foot').length") == 0
    assert not [order for order in orders(panel) if order["type"] != "dec_deepal/panel/state"]


def window_click(page: Page, selector: str) -> None:
    page.evaluate("selector => banco.ventana().querySelector(selector).click()", selector)


def write(page: Page, name: str, value: str) -> None:
    """Escribe en un campo de los formularios de Coches (los que se recalculan al teclear)."""
    page.evaluate(
        """([name, value]) => {
            const field = banco.ventana().querySelector(`[data-f=${name}]`);
            field.value = value;
            field.dispatchEvent(new Event("input", { bubbles: true }));
        }""",
        [name, value],
    )


def test_tile_opens_the_maintenance_sheet(panel: Page) -> None:
    mount(panel)
    click(panel, ".tile[data-kind=maintenance][data-car=car1]")
    text = window_text(panel)
    assert "Mantenimiento" in text and "Changote · Deepal S05 EV RWD Max" in text
    assert "1ª revisión" in text and "Lo que llegue antes: el 29 jul 2027 o a los 20.000 km." in text
    assert "16.501 km" in text and "Ahora 3.499 km · toca a los 20.000" in text
    # Las operaciones, con lo del paréntesis debajo; y lo que añade la siguiente.
    assert "Qué toca en esta revisión· 2 operaciones" in text.replace(" ·", "·")
    assert panel.evaluate("Array.from(banco.ventana().querySelectorAll('.ops li')).map(li => li.textContent.trim())") == [
        "Inspección generalPropulsión, frenos y suspensión", "Filtro del habitáculo",
    ]
    assert "En la siguiente (2ª) se añade" in text
    assert panel.evaluate("Array.from(banco.ventana().querySelectorAll('.chip')).map(c => c.textContent)") == ["Líquido de frenos"]
    assert "Todavía no hay revisiones registradas." in text
    assert panel.evaluate("banco.ventana().querySelector('a.tb').href") == "https://example.com/manual.pdf"
    # Registrar una revisión hecha: hoy y los kilómetros del coche, por defecto.
    click_window(panel, "register")
    assert "1ª revisión de Changote" in window_text(panel)
    assert panel.evaluate("banco.ventana().querySelector('[name=km]').value") == "3499"
    fill(panel, "date", "2026-10-11")
    click_window(panel, "ok")
    panel.wait_for_function("banco.ordenes().length === 1")
    assert orders(panel)[0] == {
        "type": "dec_deepal/panel/register_maintenance", "vehicle_id": "car1", "date": "2026-10-11", "km": 3499,
    }
    # Ya sale en el historial de la ficha.
    panel.wait_for_function("banco.raiz().querySelector('.tile[data-kind=maintenance]').textContent.includes('2ª revisión')")
    click(panel, ".tile[data-kind=maintenance][data-car=car1]")
    assert "1ª revisión · 11 oct 2026 · 3.499 km" in window_text(panel)


def test_tiles_of_itv_and_insurance(panel: Page) -> None:
    mount(panel)
    click(panel, ".tile[data-kind=itv][data-car=car1]")
    text = window_text(panel)
    assert "29 jul 2030" in text and "Ninguna todavía" in text and "La primera, a los 4 años" in text
    assert "La primera a los 4 años; después cada 2 y, desde los 10 años, cada año." in text
    click_window(panel, "register")
    fill(panel, "date", "2030-07-01")
    click_window(panel, "ok")
    panel.wait_for_function("banco.ordenes().length === 1")
    assert orders(panel)[0] == {"type": "dec_deepal/panel/register_itv", "vehicle_id": "car1", "date": "2030-07-01"}

    click(panel, ".tile[data-kind=insurance][data-car=car1]")
    text = window_text(panel)
    assert "Mutua Ejemplo" in text and "Todo riesgo con franquicia" in text and "0123 4567 89" in text
    assert "Último día: 29 jun 2027" in text and "Se renueva solo el 29 jul 2027" in text
    # Los teléfonos llaman con un toque.
    assert panel.evaluate("Array.from(banco.ventana().querySelectorAll('a.callb')).map(a => a.getAttribute('href'))") == [
        "tel:900000000", "tel:910000000",
    ]
    # El engranaje de la ficha lleva al formulario, ya relleno.
    click_window(panel, "configure")
    assert "Configurar el seguro" in window_text(panel)
    assert panel.evaluate("banco.ventana().querySelector('[data-f=company]').value") == "Mutua Ejemplo"
    assert panel.evaluate("banco.ventanas().length") == 1
    click_window(panel, "close")
    # Sin configurar, el recuadro abre el formulario directamente.
    click(panel, ".tile[data-kind=maintenance][data-car=car2]")
    assert "Configurar el mantenimiento" in window_text(panel) and "Changuito" in window_text(panel)


def test_gear_configures_the_insurance(panel: Page) -> None:
    mount(panel)
    click(panel, "[data-action=gear][data-kind=insurance][data-car=car2]")
    assert "Configurar el seguro" in window_text(panel) and "Changuito · Deepal S05 EV RWD Pro" in window_text(panel)
    # Sin la fecha de renovación no se guarda (ni hay nada que adelantar).
    assert panel.evaluate("banco.ventana().querySelector('.preview')") is None
    click_window(panel, "ok")
    assert "Faltan datos" in window_text(panel) and orders(panel) == []
    write(panel, "company", " Mutua ")
    write(panel, "renewal_date", "2027-03-14")
    # El recuadro verde adelanta el resultado según se escribe...
    assert "Último día para desistir: 12 feb 2027" in window_text(panel)
    # ...y al cambiar una opción se conserva lo escrito.
    window_click(panel, "[data-f=kind][data-v=comprehensive]")
    window_click(panel, '[data-f=notice][data-v="60"]')
    assert "Último día para desistir: 13 ene 2027" in window_text(panel)
    window_click(panel, "[data-f=notice][data-v=other]")
    write(panel, "notice_days", "45")
    assert "Último día para desistir: 28 ene 2027" in window_text(panel)
    click_window(panel, "ok")
    panel.wait_for_function("banco.ordenes().length === 1")
    assert orders(panel)[0] == {
        "type": "dec_deepal/panel/set_insurance", "vehicle_id": "car2", "enabled": True,
        "renewal_date": "2027-03-14", "company": " Mutua ", "policy": "", "kind": "comprehensive",
        "notice_days": 45, "phone_assistance": "", "phone_company": "",
    }
    # El panel se repinta con lo que dice la integración.
    panel.wait_for_function("!banco.raiz().querySelectorAll('.card')[1].textContent.includes('Añadir el seguro')")
    assert panel.evaluate("banco.avisos") == ["Guardado"]


def test_gear_configures_maintenance_and_itv(panel: Page) -> None:
    mount(panel)
    click(panel, "[data-action=gear][data-kind=maintenance][data-car=car1]")
    text = window_text(panel)
    assert "Configurar el mantenimiento" in text and "La próxima será la 1ª revisión." in text
    assert "El del manual20.000 km o 12 meses" in text and "Uso exigente" not in text
    assert "Próxima revisión: 29 jul 2027 o a los 20.000 km" in text
    window_click(panel, "[data-action=step][data-d='1']")
    assert "La próxima será la 2ª revisión." in window_text(panel)
    window_click(panel, "[data-action=use]")
    assert panel.evaluate("banco.ventana().querySelector('[data-f=last_km]').value") == "3499"
    # "Otro" enseña los dos campos del intervalo.
    assert panel.evaluate("banco.ventana().querySelector('[data-f=interval_km]')") is None
    window_click(panel, "[data-f=interval][data-v=other]")
    write(panel, "interval_km", "10000")
    write(panel, "interval_months", "6")
    assert "Próxima revisión: 29 ene 2027 o a los 13.499 km" in window_text(panel)
    click_window(panel, "ok")
    panel.wait_for_function("banco.ordenes().length === 1")
    assert orders(panel)[0] == {
        "type": "dec_deepal/panel/set_maintenance", "vehicle_id": "car1", "enabled": True, "services_done": 1,
        "last_date": "2026-07-29", "last_km": 3499, "interval_km": 10000, "interval_months": 6,
    }

    # ITV: la fecha se calcula sola con las normas del país, o se pone a mano.
    click(panel, "[data-action=gear][data-kind=itv][data-car=car2]")
    write(panel, "registration_date", "2020-05-10")
    assert "Próxima ITV: 10 may 2024" in window_text(panel)
    window_click(panel, "[data-f=passed]")
    click_window(panel, "ok")
    assert "Faltan datos" in window_text(panel)  # falta la fecha de la última
    write(panel, "last_date", "2024-05-08")
    assert "Próxima ITV: 8 may 2026" in window_text(panel)
    window_click(panel, "[data-f=next][data-v=manual]")
    write(panel, "next_date", "2026-06-01")
    assert "Próxima ITV: 1 jun 2026" in window_text(panel)
    window_click(panel, "[data-f=next][data-v=auto]")
    click_window(panel, "ok")
    panel.wait_for_function("banco.ordenes().length === 2")
    assert orders(panel)[1] == {
        "type": "dec_deepal/panel/set_itv", "vehicle_id": "car2", "enabled": True,
        "registration_date": "2020-05-10", "last_date": "2024-05-08", "next_date": None,
    }

    # Desactivar un apartado: basta apagar "Activado".
    click(panel, "[data-action=gear][data-kind=itv][data-car=car1]")
    window_click(panel, "[data-f=enabled]")
    assert "Desactivada" in window_text(panel)
    assert panel.evaluate("banco.ventana().querySelector('.fsec')") is None
    click_window(panel, "ok")
    panel.wait_for_function("banco.ordenes().length === 3")
    assert orders(panel)[2] == {"type": "dec_deepal/panel/set_itv", "vehicle_id": "car1", "enabled": False}


def test_appearance_window(panel: Page) -> None:
    mount(panel)
    click(panel, "[data-action=appearance][data-car=car1]")
    window = "banco.ventana()"
    chosen = f"Array.from({window}.querySelectorAll('.on')).map(n => n.firstChild.textContent.trim() || n.textContent.trim())"
    photo = f"{window}.querySelector('.prev img').getAttribute('src')"
    assert "Apariencia de Changote" in window_text(panel)
    # Abre con lo que tiene el coche, y la foto es la de esa versión y ese color.
    assert panel.evaluate(chosen) == ["Deepal S05 EV", "RWD Max", "Ganymede Grey", "Llanta 20\" sin tapacubos"]
    assert panel.evaluate(photo) == "coche.svg?max_ganymade_grey"
    # Cada versión dice qué trae.
    assert "RWD ProSin asientos ni volante calefactados · Llanta 18\"" in window_text(panel)

    def pick(field: str, value: str) -> None:
        panel.evaluate(
            "([field, value]) => banco.ventana().querySelector(`[data-field=${field}][data-value=${value}]`).click()",
            [field, value],
        )

    # Al elegir, la foto cambia; nada se guarda todavía.
    pick("color", "andromeda_blue")
    assert panel.evaluate(photo) == "coche.svg?max_andromeda_blue" and orders(panel) == []
    # El Pro trae su llanta: desaparece la elección.
    pick("trim", "pro")
    assert "Llanta 20" not in window_text(panel)
    # Otro modelo: la versión que no existe en él se quita; el color (que sí tiene) se queda.
    pick("model", "s05_phev")
    assert panel.evaluate(chosen) == ["Deepal S05 PHEV", "Pro", "Andromeda Blue"]
    pick("trim", "limited_edition")
    click_window(panel, "ok")
    panel.wait_for_function("banco.ordenes().length === 1")
    assert orders(panel)[0] == {
        "type": "dec_deepal/panel/set_appearance", "vehicle_id": "car1", "model": "s05_phev",
        "trim": "limited_edition", "color": "andromeda_blue", "wheels": None,
    }
    panel.wait_for_function("banco.texto().includes('Deepal S05 PHEV Limited Edition')")


# --- Ajustes ----------------------------------------------------------------------


def test_settings_tab(panel: Page) -> None:
    mount(panel)
    tab(panel, "settings")
    text = panel.evaluate("banco.texto()")
    assert "Control remoto con PIN" in text and "Comprobado" in text and "Manual BEV" in text
    # El PIN guardado nunca llega al panel: el campo sale vacío.
    assert panel.evaluate("banco.raiz().querySelector('[data-input=pin]').value") == ""
    assert "Hay cambios sin guardar" not in text

    def setting(field: str, value: str) -> None:
        click(panel, f"[data-action=setting][data-field={field}][data-value='{value}']")

    def typed(field: str, value: str) -> None:
        panel.evaluate(
            "([field, value]) => { const input = banco.raiz().querySelector(`[data-input=${field}]`);"
            " input.value = value; input.dispatchEvent(new Event('input', { bubbles: true, composed: true })); }",
            [field, value],
        )

    # Modo directo: desaparecen la duración y el aviso del desbloqueo.
    assert "Cuánto dura el desbloqueo" in text
    setting("pin_mode", "direct")
    assert "Cuánto dura el desbloqueo" not in panel.evaluate("banco.texto()")
    assert "Hay cambios sin guardar" in panel.evaluate("banco.texto()")
    setting("pin_mode", "armed")
    setting("arm_seconds", "60")
    setting("scan_minutes", "10")
    setting("debug", "true")
    assert "Sumar el equilibrado" in panel.evaluate("banco.texto()")
    setting("charge_balance", "false")
    # Un PIN que Deepal no acepta: se explica y no se pierde lo cambiado.
    typed("pin", "0000")
    click(panel, "[data-action=save-settings]")
    panel.wait_for_function("banco.avisos.length === 1")
    assert "El PIN no es correcto" in panel.evaluate("banco.avisos[0]")
    assert panel.evaluate("banco.raiz().querySelector('.seg .on').textContent") == "60 s"
    typed("pin", "2468")
    typed("manual_url", "https://example.com/otro.pdf")
    click(panel, "[data-action=save-settings]")
    panel.wait_for_function("banco.avisos.includes('Guardado')")
    assert orders(panel)[-1] == {
        "type": "dec_deepal/panel/set_settings", "entry_id": "entry1", "pin_enabled": True, "pin": "2468",
        "pin_mode": "armed", "arm_seconds": 60, "arm_notify": False, "scan_minutes": 10, "wake": True,
        "charge_balance": False, "debug": True, "manual_url": "https://example.com/otro.pdf",
    }
    panel.wait_for_function("!banco.texto().includes('Hay cambios sin guardar')")
    # Guardar otra cosa sin escribir el PIN: se manda vacío (= no cambiarlo).
    setting("wake", "false")
    click(panel, "[data-action=save-settings]")
    panel.wait_for_function("banco.ordenes().length === 3")
    assert orders(panel)[-1]["pin"] == "" and orders(panel)[-1]["wake"] is False
    # Desactivar las órdenes con PIN esconde todo lo suyo.
    setting("pin_enabled", "false")
    assert "Cómo se usan las órdenes" not in panel.evaluate("banco.texto()")
    click(panel, "[data-action=discard-settings]")
    assert "Cómo se usan las órdenes" in panel.evaluate("banco.texto()")


# --- Avisos -----------------------------------------------------------------------


def test_alerts_table_per_car(panel: Page) -> None:
    mount(panel)
    tab(panel, "alerts")
    # Plegado: una fila por apartado. La raya dice "solo algunos".
    assert panel.evaluate("banco.tabla('car1')") == {
        "Carga": "x..", "Testigos": "x..", "Mantenimiento": "x..", "ITV": "x..", "Seguro": "-..",
    }
    assert panel.evaluate("banco.tabla('car2')")["Carga"] == ".-."
    # Desplegado: una fila por aviso, con su plazo.
    click(panel, "[data-action=fold][data-car=car1][data-section=insurance]")
    table = panel.evaluate("banco.tabla('car1')")
    assert table["Aviso desistimiento 1"] == "x.." and table["Aviso renovación 1"] == "..."
    assert "quedan 30 días para el límite" in panel.evaluate("banco.texto('[data-car-card=car1]')")
    assert "Hay cambios sin guardar" not in panel.evaluate("banco.texto()")


def test_ticking_and_saving_alerts(panel: Page) -> None:
    mount(panel)
    tab(panel, "alerts")
    click(panel, "[data-action=fold][data-car=car2][data-section=charge]")
    # Una casilla suelta: "Carga iniciada" del coche de ella, también a Manuel.
    click(panel, f"[data-action=cell][data-car=car2][data-notice=charge_started][data-target={ME}]")
    # La casilla del apartado marca todos sus avisos para ese destino.
    click(panel, f"[data-action=section-cell][data-car=car2][data-section=warnings][data-target={BELL}]")
    table = panel.evaluate("banco.tabla('car2')")
    assert table["Carga iniciada"] == "x.." and table["Carga terminada"] == ".x." and table["Testigos"] == ".xx"
    # Nada se manda hasta guardar; el otro coche no tiene cambios.
    assert orders(panel) == []
    assert "Hay cambios sin guardar" in panel.evaluate("banco.texto('[data-car-card=car2]')")
    assert "Hay cambios sin guardar" not in panel.evaluate("banco.texto('[data-car-card=car1]')")
    click(panel, "[data-action=save-alerts][data-car=car2]")
    panel.wait_for_function("banco.ordenes().length === 1")
    sent = orders(panel)[0]
    assert sent["type"] == "dec_deepal/panel/set_alerts" and sent["vehicle_id"] == "car2"
    assert sent["notices"]["charge_started"] == [ME] and sent["notices"]["charge_finished"] == [HER]
    assert sent["notices"]["warnings"] == [HER, BELL] and sent["notices"]["key_battery"] == [HER, BELL]
    assert sent["thresholds"] == {}
    panel.wait_for_function("!banco.texto('[data-car-card=car2]').includes('Hay cambios sin guardar')")
    # Descartar deja las cosas como estaban.
    click(panel, f"[data-action=cell][data-car=car2][data-notice=charge_started][data-target={ME}]")
    click(panel, "[data-action=discard-alerts][data-car=car2]")
    assert panel.evaluate("banco.tabla('car2')")["Carga iniciada"] == "x.." and len(orders(panel)) == 1


def test_editing_a_lead_time_with_the_pencil(panel: Page) -> None:
    mount(panel)
    tab(panel, "alerts")
    click(panel, "[data-action=fold][data-car=car1][data-section=maintenance]")
    card = "banco.texto('[data-car-card=car1]')"
    assert "quedan 5.000 km" in panel.evaluate(card)
    # Solo llevan lápiz los avisos con plazo (6 de los 7 de mantenimiento).
    assert panel.evaluate("banco.raiz().querySelectorAll('[data-car-card=car1] .pen').length") == 6

    def edit(notice: str, value: str) -> None:
        click(panel, f"[data-action=edit][data-car=car1][data-notice={notice}]")
        panel.evaluate("value => { banco.raiz().querySelector('.inp input').value = value; }", value)
        click(panel, "[data-action=edit-ok]")

    # Fuera de los límites: se dice y no se cambia nada.
    edit("maintenance_k1", "50")
    assert panel.evaluate("banco.avisos") == ["El plazo tiene que estar entre 100 y 20.000."]
    click(panel, "[data-action=edit-cancel]")
    edit("maintenance_k1", "4000")
    assert "quedan 4.000 km" in panel.evaluate(card) and "Plazos de fábrica" in panel.evaluate(card)
    # Desordenados (el aviso 2 antes que el 1): lo rechaza la integración y se explica.
    edit("maintenance_k2", "4500")
    click(panel, "[data-action=save-alerts][data-car=car1]")
    panel.wait_for_function("banco.avisos.length === 2")
    assert "de mayor a menor" in panel.evaluate("banco.avisos[1]")
    assert "Hay cambios sin guardar" in panel.evaluate(card)  # el borrador no se pierde
    edit("maintenance_k2", "2000")
    click(panel, "[data-action=save-alerts][data-car=car1]")
    panel.wait_for_function("banco.avisos.includes('Guardado')")
    assert orders(panel)[-1]["thresholds"] == {"maintenance_k1": 4000, "maintenance_k2": 2000}
    # Volver a los de fábrica.
    click(panel, "[data-action=reset-thresholds][data-car=car1]")
    assert "quedan 5.000 km" in panel.evaluate(card)


def test_copying_from_another_car(panel: Page) -> None:
    mount(panel)
    tab(panel, "alerts")
    click(panel, "[data-action=copy-alerts][data-car=car2]")
    # Con dos coches se copia del otro sin preguntar; queda como borrador.
    assert panel.evaluate("banco.tabla('car2')") == panel.evaluate("banco.tabla('car1')")
    assert "Hay cambios sin guardar" in panel.evaluate("banco.texto('[data-car-card=car2]')") and orders(panel) == []


# --- Datos y diagnóstico --------------------------------------------------------------


def test_data_tab(panel: Page) -> None:
    mount(panel)
    tab(panel, "data")
    panel.wait_for_function("banco.raiz().querySelector('a.btn[href]')")
    link = "banco.raiz().querySelector('a.btn')"
    # Un enlace de verdad, que se abre fuera de la app del móvil.
    assert panel.evaluate(f"[{link}.getAttribute('href'), {link}.target]") == [
        "/api/dec_deepal/export?authSig=abc", "_blank",
    ]
    # Enviar la copia a un móvil.
    click(panel, "[data-action=send-backup]")
    panel.wait_for_function("banco.ordenes().length === 1")
    assert orders(panel)[0] == {"type": "dec_deepal/panel/send_backup", "target": ME}
    assert panel.evaluate("banco.avisos") == ["Notificación enviada a iPhone de Manuel."]
    # Borrar los datos de un coche que ya no está: pide confirmación.
    text = panel.evaluate("banco.texto()")
    assert "Deepal …774512" in text and "Sin cuenta" in text
    click(panel, "[data-action=delete-data]", 1)
    assert "No se puede deshacer" in window_text(panel) and len(orders(panel)) == 1
    click_window(panel, "ok")
    panel.wait_for_function("banco.ordenes().length === 2")
    assert orders(panel)[1] == {"type": "dec_deepal/panel/delete_data", "keys": ["LS5A3ABE0RA774512"]}
    panel.wait_for_function("!banco.texto().includes('774512')")


def test_loading_a_backup(panel: Page, tmp_path) -> None:  # noqa: ANN001
    mount(panel)
    tab(panel, "data")
    chooser = panel.locator("input[type=file]")
    # Un fichero que no es una copia: se dice y no se manda nada.
    broken = tmp_path / "roto.json"
    broken.write_text("esto no es json", encoding="utf-8")
    chooser.set_input_files(str(broken))
    panel.wait_for_function("banco.avisos.length === 1")
    assert "no es una copia" in panel.evaluate("banco.avisos[0]") and orders(panel) == []
    # Una copia de otro programa: la rechaza la integración.
    other = tmp_path / "otro.json"
    other.write_text(json.dumps({"formato": "otra-cosa"}), encoding="utf-8")
    chooser.set_input_files(str(other))
    panel.wait_for_function("banco.avisos.length === 2")
    assert "no es una copia" in panel.evaluate("banco.avisos[1]")
    good = tmp_path / "copia.json"
    backup = {"formato": "dec_deepal.datos", "version": 1, "coches": {"LS5A3ABE0RA000001": {"name": "Changote"}}}
    good.write_text(json.dumps(backup), encoding="utf-8")
    chooser.set_input_files(str(good))
    panel.wait_for_function("banco.avisos.length === 3")
    assert panel.evaluate("banco.avisos[2]") == "Copia cargada: LS5A3ABE0RA000001."
    assert orders(panel)[-1] == {"type": "dec_deepal/panel/import_backup", "backup": backup}


def test_diagnostics_tab(panel: Page) -> None:
    mount(panel)
    tab(panel, "diagnostics")
    text = panel.evaluate("banco.texto()")
    assert "Aviso enviado: Carga iniciada" in text and "charging: False → True" in text
    assert "Orden: climate_on" in text and "código 1032" in text and "Power is not off" in text
    assert "Changote · Deepal S05 EV RWD Max" in text
    # Lo más reciente, arriba.
    titles = panel.evaluate("Array.from(banco.raiz().querySelectorAll('.log .what')).map(n => n.firstChild.textContent)")
    assert titles[0].startswith("Aviso enviado") and titles[-1] == "Orden: lock"
    click(panel, "[data-filter=errors]")
    assert panel.evaluate("banco.raiz().querySelectorAll('.log').length") == 1
    click(panel, "[data-filter='car:Changote']")
    assert panel.evaluate("banco.raiz().querySelectorAll('.log').length") == 3
    # El fichero de diagnóstico de la cuenta, con un enlace firmado.
    panel.wait_for_function("banco.raiz().querySelector('a.btn[href]')")
    assert panel.evaluate("banco.raiz().querySelector('a.btn').getAttribute('href')") == (
        "/api/diagnostics/config_entry/entry1?authSig=abc"
    )


# --- Idiomas y casos raros --------------------------------------------------------------


def test_languages(panel: Page) -> None:
    mount(panel, idioma="en")
    assert "Verified sheet" in panel.evaluate("banco.texto()")
    assert panel.evaluate("banco.texto('.tabs')") == "VehiclesNotificationsDataDiagnosticsSettings"
    # Catalán, gallego y euskera, en español; un idioma aún sin traducir, en inglés.
    for language, expected in (
        ("ca", "Coches"), ("pt", "VeículosAvisosDadosDiagnósticoDefinições"), ("de", "Fahrzeuge"), ("fr", "Véhicules"),
        ("nl", "Voertuigen"), ("nb", "Kjøretøy"), ("nn", "Kjøretøy"), ("da", "Køretøjer"), ("el", "Οχήματα"),
        ("sl", "Vozila"), ("it", "Veicoli"), ("pl", "Pojazdy"), ("sv", "Vehicles"),
    ):
        mount(panel, idioma=language)
        assert panel.evaluate("banco.texto('.tabs')").startswith(expected), language


def test_errors_and_no_cars(panel: Page) -> None:
    mount(panel, sin_coches=True)
    assert "No hay ningún coche" in panel.evaluate("banco.texto()")
    panel.evaluate("banco.montar({ fallo: 'Sin conexión' })")
    panel.wait_for_function("banco.texto().includes('Sin conexión')")
    assert "Reintentar" in panel.evaluate("banco.texto()")


# --- Ajustes → Cargadores ---------------------------------------------------------------


def test_chargers(panel: Page) -> None:
    """Activar los cargadores, añadir uno con sus entidades y el apartado de Avisos."""
    mount(panel)
    tab(panel, "settings")
    assert "Cargadores" in panel.evaluate("banco.texto()")
    assert "Añadir cargador" not in panel.evaluate("banco.texto()")  # desactivados
    click(panel, "[data-action=chargers-enabled]")
    panel.wait_for_function("banco.texto().includes('Añadir cargador')")
    assert orders(panel)[-1] == {"type": "dec_deepal/panel/set_chargers", "enabled": True, "control": "people"}

    # Nuevo cargador: sin «Enchufado» no se guarda.
    click(panel, "[data-action=charger-edit]")
    assert "Entidades del cargador" in window_text(panel)
    click_window(panel, "ok")
    assert "Elige la entidad «Enchufado»" in window_text(panel)
    # Cada lista solo enseña lo que vale: la potencia, solo sensores en W o kW.
    power = panel.evaluate("Array.from(banco.ventana().querySelectorAll('[data-role=power] option')).map(o => o.value)")
    assert power == ["", "sensor.evse_energia_de_la_casa", "sensor.evse_potencia_de_carga"]
    for role, entity in (("plugged", "binary_sensor.evse_conectado"), ("lock", "switch.evse_bloquear_evse")):
        panel.evaluate(
            "([role, entity]) => { const s = banco.ventana().querySelector(`[data-role=${role}]`); s.value = entity;"
            " s.dispatchEvent(new Event('change', { bubbles: true })); }",
            [role, entity],
        )
    text = window_text(panel)
    assert "El bloqueo, encendido es…" in text and "Bloquear al desenchufar" in text and "Pérdidas de carga" in text
    assert "Bloquear al terminar la carga" in text
    click_window(panel, "ok")
    panel.wait_for_function("banco.ordenes().some(m => m.type === 'dec_deepal/panel/save_charger')")
    saved = orders(panel)[-1]["charger"]
    assert saved["entities"] == {"plugged": "binary_sensor.evse_conectado", "lock": "switch.evse_bloquear_evse"}
    assert (saved["name"], saved["vehicles"], saved["unlock"], saved["coverage"]) == ("Garaje", ["car1", "car2"], "confirm", "unknown")
    assert (saved["relock"], saved["relock_minutes"], saved["loss"], saved["price"]) == (True, 5, 10, None)
    assert (saved["lock_full"], saved["lock_full_minutes"], saved["read_interval"]) == (True, 30, 15)
    panel.wait_for_function("banco.texto().includes('Changote, Changuito')")
    # El % estimado en la tarjeta del coche se quita y se pone al momento.
    click(panel, "[data-action=chargers-estimate]")
    panel.wait_for_function("banco.ordenes().some(m => m.show_estimate === false)")

    # Con los cargadores activados, Avisos tiene el apartado «Cargador».
    tab(panel, "alerts")
    assert "Cargador" in panel.evaluate("banco.texto()")


def test_charge_limit_settings(panel: Page) -> None:
    """Ajustes → Límite de carga: solo con cargadores; límite por coche y recordatorio del 100 %."""
    mount(panel)
    tab(panel, "settings")
    assert "Límite de carga" not in panel.evaluate("banco.texto()")  # cargadores desactivados
    click(panel, "[data-action=chargers-enabled]")
    panel.wait_for_function("banco.texto().includes('Usar el límite de carga')")
    assert "Límite de cada coche" not in panel.evaluate("banco.texto()")
    click(panel, "[data-action=limit-set][data-field=enabled]")
    panel.wait_for_function("banco.texto().includes('Límite de cada coche')")
    assert orders(panel)[-1] == {"type": "dec_deepal/panel/set_limit", "enabled": True}
    # Cada coche, su límite (selector debajo, a todo lo ancho).
    click(panel, "[data-action=limit-car][data-id=car2][data-value='80']")
    panel.wait_for_function("banco.ordenes().some(m => m.type === 'dec_deepal/chargers/car_limit')")
    assert orders(panel)[-1] == {"type": "dec_deepal/chargers/car_limit", "vehicle_id": "car2", "limit": 80}
    panel.wait_for_function("document.querySelector('dec-deepal-panel').shadowRoot.querySelector('[data-action=limit-car][data-id=car2][data-value=\"80\"]').classList.contains('on')")
    # Recordar cargar al 100 %: «Cada 3/4/5/6» y «sin preguntar» salen al activarlo.
    assert "Cada 4" not in panel.evaluate("banco.texto()")
    click(panel, "[data-action=limit-set][data-field=remind]")
    panel.wait_for_function("banco.texto().includes('Cada 4')")
    assert "Hacerla al 100 % sin preguntar" in panel.evaluate("banco.texto()")
    click(panel, "[data-action=limit-set][data-field=every][data-value='6']")
    panel.wait_for_function("banco.ordenes().some(m => m.every === 6)")
