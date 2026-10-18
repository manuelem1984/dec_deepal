"""La tarjeta del cargador y la ventana de carga con un cargador, en un navegador."""

from __future__ import annotations

from playwright.sync_api import Page

DEVICE = "page.evaluate('banco.hass.entities')"


def _charger(**more) -> dict:  # noqa: ANN003
    base = {
        "id": "g", "name": "Garaje", "plugged": True, "charging": False, "locked": True, "has_lock": True,
        "power": 0, "unlock": "confirm", "coverage": "no", "loss": 10, "price": 0.114,
        "vehicles": [
            {"id": "car1", "name": "Changote", "device_id": "coche1"},
            {"id": "car2", "name": "Changuito", "device_id": "otro"},
        ],
        "session": None, "last": None, "history": [], "can_control": True,
        "month": {"count": 0, "energy": 0, "cost": 0, "by_vehicle": {}},
    }
    return base | more


SESSION = {
    "since": "2026-10-17T20:10:00+00:00", "charging_since": "2026-10-17T20:12:00+00:00", "finished_at": None,
    "vehicle_id": "car1", "vehicle": "Changote", "device_id": None, "assigned": "user", "waiting": False,
    "energy": 4.2, "battery_energy": 3.78, "cost": 0.48, "soc_start": 65, "level": 72.3, "estimated": True,
    "minutes_left": 455, "balance": 15,
}


def mount_charger(page: Page, chargers: list, **more) -> None:  # noqa: ANN003
    data = {"enabled": more.pop("enabled", True), "chargers": chargers}
    page.evaluate(
        "options => banco.montar(options)",
        {"tarjeta": "dec-deepal-charger-card", "config": {"charger": "g"}, "cargadores": data, **more},
    )
    page.wait_for_function("banco.card.shadowRoot.querySelector('ha-card') && !banco.card.shadowRoot.textContent.includes('…')")


def card_text(page: Page) -> str:
    return " ".join(page.evaluate("banco.card.shadowRoot.querySelector('ha-card').textContent").split())


def test_waiting_for_the_car(page: Page) -> None:
    """Enchufado y bloqueado: los coches son botones; elegir uno pregunta y desbloquea."""
    mount_charger(page, [_charger(session={**SESSION, "vehicle_id": None, "vehicle": None, "waiting": True, "level": None, "estimated": False})])
    text = card_text(page)
    assert "Garaje" in text and "Enchufado · esperando confirmación" in text and "Toca el tuyo" in text
    picks = page.evaluate("Array.from(banco.card.shadowRoot.querySelectorAll('.pick button')).map(b => b.textContent.trim())")
    assert picks == ["Changote", "Changuito"]
    page.evaluate("banco.card.shadowRoot.querySelector('.pick button[data-car=car1]').click()")
    assert "¿Desbloquear Garaje para Changote?" in page.evaluate("banco.ventana().textContent")
    page.evaluate("banco.ventana().querySelector('[data-action=ok]').click()")
    page.wait_for_function("banco.registro.some(line => line.includes('chargers/confirm'))")
    assert 'ws dec_deepal/chargers/confirm {"charger_id":"g","vehicle_id":"car1"}' in page.evaluate("banco.registro")


def test_charging_without_coverage(page: Page) -> None:
    """Cargando sin cobertura: % estimado, kW, kWh, € y tiempo con el equilibrado."""
    mount_charger(page, [_charger(charging=True, locked=False, power=3900, session=SESSION)])
    text = card_text(page)
    assert "Cargando · lleno hacia las" in text and "Changote · sin cobertura" in text
    # De qué % a cuál (con la marca del % al enchufar en la barra) y cuánto lleva.
    assert "65 % → ≈ 72 %estimado" in text
    assert page.evaluate("banco.card.shadowRoot.querySelector('.lvl .gain').classList.contains('anim')")
    tiles = page.evaluate("Array.from(banco.card.shadowRoot.querySelectorAll('.t3 .v')).map(v => v.textContent)")
    assert tiles == ["3,9 kW", "+4,2 kWh", "0,48 €"]
    buttons = page.evaluate("Array.from(banco.card.shadowRoot.querySelectorAll('.acts .b')).map(b => b.textContent.trim())")
    # 455 min del cálculo + 15 de equilibrado.
    assert buttons == ["Desbloqueado", "7 h 50 min", "Cargas"]
    # Un cambio de la suscripción se pinta al momento.
    last = {
        "start": "2026-10-17T20:10:00+00:00", "end": "2026-10-18T04:05:00+00:00", "energy": 22.1, "cost": 2.52,
        "soc_start": 65, "soc_end": 100, "estimated": True, "vehicle": "Changote",
    }
    page.evaluate("data => banco.cargadores(data)", {"enabled": True, "chargers": [_charger(plugged=False, locked=True, last=last)]})
    text = card_text(page)
    assert "Libre · Bloqueado" in text and "Última: Changote" in text and "65 % → ≈ 100 % · +22,1 kWh · 2,52 €" in text


def test_lock_needs_permission(page: Page) -> None:
    mount_charger(page, [_charger(plugged=False, can_control=False)])
    assert page.evaluate("banco.card.shadowRoot.querySelector('[data-action=lock]').disabled") is True
    mount_charger(page, [_charger(plugged=False)])
    page.evaluate("banco.card.shadowRoot.querySelector('[data-action=lock]').click()")
    assert "¿Desbloquear Garaje? Podrá empezar a cargar." in page.evaluate("banco.ventana().textContent")
    page.evaluate("banco.ventana().querySelector('[data-action=ok]').click()")
    page.wait_for_function("banco.registro.some(line => line.includes('chargers/lock'))")
    assert 'ws dec_deepal/chargers/lock {"charger_id":"g","locked":false}' in page.evaluate("banco.registro")


def test_disabled_and_missing(page: Page) -> None:
    mount_charger(page, [], enabled=False)
    assert "Los cargadores están desactivados" in card_text(page)
    mount_charger(page, [])
    assert "No hay ese cargador" in card_text(page)


def test_charge_window_with_a_charger(page: Page) -> None:
    """La ventana de carga del coche enseña el cargador y, sin cobertura, el % estimado."""
    device = page.evaluate("() => { banco.montar({}); return Object.values(banco.hass.entities)[0].device_id; }")
    station = _charger(charging=True, locked=False, power=3900, session={**SESSION, "device_id": device})
    page.evaluate(
        "options => banco.montar(options)",
        {"cargadores": {"enabled": True, "chargers": [station]}, "estados": {"binary_sensor.charging": ["off"]}},
    )
    page.wait_for_function("banco.suscripciones.length > 0")
    page.wait_for_timeout(50)
    page.evaluate("banco.card.shadowRoot.querySelector('.energy').click()")
    window = "banco.ventana()"
    assert page.evaluate(f"{window}.querySelector('.pct b').textContent") == "≈ 72 %"
    assert page.evaluate(f"{window}.querySelector('.pct span').textContent") == "estimado"
    first = page.evaluate(f"['.k', '.n', '.d'].map(part => {window}.querySelector('.st ' + part).textContent.trim())")
    assert first == ["Cargador", "Garaje · 3,9 kW", "+4,2 kWh · 0,48 € · sin cobertura"]
    # Sin cobertura manda el cargador: carga aunque el coche diga que no.
    assert "Cargando · AC" in " ".join(page.evaluate(f"{window}.querySelector('.dlg').textContent").split())


def test_finished_and_locks_soon(page: Page) -> None:
    """Terminada: ✓, barra quieta, «En la batería», «Sin precio» y cuenta atrás del bloqueo."""
    from datetime import UTC, datetime, timedelta

    lock_at = (datetime.now(UTC) + timedelta(minutes=28, seconds=30)).isoformat()
    session = {**SESSION, "finished_at": "2026-10-18T12:05:00+00:00", "level": 100, "soc_start": 88, "energy": 9.1,
               "battery_energy": 8.19, "cost": None, "minutes_left": None, "duration": 163, "lock_at": lock_at}
    mount_charger(page, [_charger(charging=False, locked=False, price=None, session=session)])
    text = card_text(page)
    assert "Carga terminada · " in text and "88 % → ≈ 100 %estimado · 2 h 43 min" in text
    assert not page.evaluate("banco.card.shadowRoot.querySelector('.lvl .gain').classList.contains('anim')")
    tiles = page.evaluate("Array.from(banco.card.shadowRoot.querySelectorAll('.t3')).map(t => t.textContent.trim().replace(/\\s+/g, ' '))")
    assert tiles == ["Energía+9,1 kWh", "En la batería≈ 8,2 kWh", "CosteSin precio"]
    buttons = page.evaluate("Array.from(banco.card.shadowRoot.querySelectorAll('.acts .b')).map(b => b.textContent.trim())")
    assert buttons == ["Desbloqueado", "Se bloquea en 29 min", "Cargas"]


def test_car_card_shows_the_estimate(page: Page) -> None:
    """Sin cobertura: la tarjeta del coche enseña «≈ 100 %», «estimado» y el estado del cargador."""
    device = page.evaluate("() => { banco.montar({}); return Object.values(banco.hass.entities)[0].device_id; }")
    data = {"enabled": True, "show_estimate": True, "chargers": [],
            "estimates": {device: {"level": 99.6, "energy": 9.1, "state": "finished", "charger": "V2C Trydan"}}}
    page.evaluate("options => banco.montar(options)", {"cargadores": data})
    page.wait_for_function("banco.card.shadowRoot.querySelector('.km').textContent.includes('≈')")
    root = "banco.card.shadowRoot"
    assert page.evaluate(f"{root}.querySelector('.km').textContent") == "≈ 100 %"
    assert page.evaluate(f"{root}.querySelector('.estb').textContent") == "estimado"
    assert page.evaluate(f"{root}.querySelector('.charge span').textContent") == "Carga terminada"
    assert page.evaluate(f"{root}.querySelector('.upd').textContent").endswith("· % estimado por V2C Trydan")
    # Sin el ajuste (o cuando el coche vuelve a informar), el dato real.
    page.evaluate("data => banco.cargadores(data)", {**data, "show_estimate": False})
    assert page.evaluate(f"{root}.querySelector('.estb').hidden") is True
    assert "≈" not in page.evaluate(f"{root}.querySelector('.km').textContent")
