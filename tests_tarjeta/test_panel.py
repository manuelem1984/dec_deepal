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


def test_gear_configures_the_insurance(panel: Page) -> None:
    mount(panel)
    click(panel, "[data-action=gear][data-kind=insurance][data-car=car2]")
    assert "Seguro — Changuito" in window_text(panel)
    # Sin la fecha de renovación no se guarda.
    click_window(panel, "ok")
    assert "Faltan datos" in window_text(panel) and orders(panel) == []
    fill(panel, "company", " Mutua ")
    fill(panel, "renewal_date", "2027-03-14")
    fill(panel, "kind", "comprehensive")
    click_window(panel, "ok")
    panel.wait_for_function("banco.ordenes().length === 1")
    assert orders(panel)[0] == {
        "type": "dec_deepal/panel/set_insurance", "vehicle_id": "car2", "enabled": True,
        "renewal_date": "2027-03-14", "company": " Mutua ", "policy": "", "kind": "comprehensive",
        "notice_days": 30, "phone_assistance": "", "phone_company": "",
    }
    # El panel se repinta con lo que dice la integración.
    panel.wait_for_function("!banco.raiz().querySelectorAll('.card')[1].textContent.includes('Añadir el seguro')")
    assert panel.evaluate("banco.avisos") == ["Guardado"]


def test_gear_disables_and_registers(panel: Page) -> None:
    mount(panel)
    # Registrar una revisión hecha: hoy y los kilómetros del coche, por defecto.
    click(panel, "[data-action=gear][data-kind=maintenance][data-car=car1]")
    click_window(panel, "extra")
    assert "1ª revisión de Changote" in window_text(panel)
    assert panel.evaluate("banco.ventana().querySelector('[name=km]').value") == "3499"
    fill(panel, "date", "2026-10-11")
    click_window(panel, "ok")
    panel.wait_for_function("banco.ordenes().length === 1")
    assert orders(panel)[0] == {
        "type": "dec_deepal/panel/register_maintenance", "vehicle_id": "car1", "date": "2026-10-11", "km": 3499,
    }
    # Desactivar un apartado: basta desmarcar "Activado".
    click(panel, "[data-action=gear][data-kind=itv][data-car=car1]")
    panel.evaluate("() => { const box = banco.ventana().querySelector('[name=enabled]'); box.checked = false; box.dispatchEvent(new Event('change')); }")
    assert panel.evaluate("banco.ventana().querySelector('.fields').hidden") is True
    click_window(panel, "ok")
    panel.wait_for_function("banco.ordenes().length === 2")
    assert orders(panel)[1] == {"type": "dec_deepal/panel/set_itv", "vehicle_id": "car1", "enabled": False}


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
    assert panel.evaluate("banco.texto('.tabs')") == "VehiclesNotificationsDataDiagnostics"
    # Catalán, gallego y euskera, en español; un idioma aún sin traducir, en inglés.
    for language, expected in (("ca", "Coches"), ("pt", "Vehicles"), ("fr", "Vehicles")):
        mount(panel, idioma=language)
        assert panel.evaluate("banco.texto('.tabs')").startswith(expected), language


def test_errors_and_no_cars(panel: Page) -> None:
    mount(panel, sin_coches=True)
    assert "No hay ningún coche" in panel.evaluate("banco.texto()")
    panel.evaluate("banco.montar({ fallo: 'Sin conexión' })")
    panel.wait_for_function("banco.texto().includes('Sin conexión')")
    assert "Reintentar" in panel.evaluate("banco.texto()")
