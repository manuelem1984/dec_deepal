"""Prueba del panel de la barra lateral: registro y órdenes (lado de la integración).

Lo que pinta el panel se prueba en un navegador (``tests_tarjeta/test_panel.py``);
aquí, que cada orden hace en la integración lo mismo que Configurar.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.dec_deepal import panel
from custom_components.dec_deepal.alert_rules import NOTICES, route_for
from custom_components.dec_deepal.alerts import AlertManager
from custom_components.dec_deepal.api.errors import DeepalPinError
from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.const import DOMAIN, OPT_ALERTS, PANEL_URL_PATH
from custom_components.dec_deepal.debug.recorder import DebugRecorder
from custom_components.dec_deepal.registries import load_all
from custom_components.dec_deepal.telemetry import signals as s
from custom_components.dec_deepal.vehicle_store import async_register_export

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "dec_deepal"
VIN = "LS5A3ABE0RA000001"
ME = "mobile_app_iphone_de_manuel"


def _vehicle(model, vehicle_id: str, name: str, vin: str, trim: str):  # noqa: ANN001, ANN202
    values = {s.ODOMETER_KM: 37500, s.BATTERY_LEVEL: 56, s.RANGE_KM: 276}
    return SimpleNamespace(
        info=VehicleInfo(
            vehicle_id=vehicle_id, nickname=name, vin=vin,
            license_plate="6545NPD" if vehicle_id == "car1" else None,
        ),
        coordinator=SimpleNamespace(
            data=SimpleNamespace(get=values.get), async_add_listener=lambda _cb: lambda: None
        ),
        model=model,
        trim=trim,
        color=next(iter(model.colors)),
        wheels=None,
        wheel=model.wheel_for(trim, None),
        configured=True,
    )


@pytest.mark.usefixtures("enable_custom_integrations", "hass_storage")
async def test_panel_commands(hass: HomeAssistant, hass_ws_client, hass_client_no_auth, freezer) -> None:  # noqa: ANN001
    # La descarga de la copia se registra antes de arrancar el servidor web.
    assert await async_setup_component(hass, "http", {})
    async_register_export(hass)
    # La sesión se abre antes de mover el reloj: su permiso caduca a la media hora.
    client = await hass_ws_client(hass)
    freezer.move_to("2027-01-22 20:00:00+00:00")
    assert await async_setup_component(hass, "websocket_api", {})
    for command in panel.COMMANDS:
        websocket_api.async_register_command(hass, command)
    sent = async_mock_service(hass, "notify", ME)
    MockConfigEntry(
        domain="mobile_app", title="iPhone de Manuel", data={"device_name": "iPhone de Manuel"}
    ).add_to_hass(hass)

    registries = load_all(INTEGRATION)
    model = registries.vehicles.get("s05_2024")
    vehicles = {
        "car1": _vehicle(model, "car1", "Changote", VIN, "max"),
        "car2": _vehicle(model, "car2", "Changuito", "LS5A3ABE0RA000002", "pro"),
    }
    # Avisos configurados antes de la 2.4.0: una lista para toda la cuenta.
    old = {OPT_ALERTS: {"targets": [ME], "types": ["charge_finished", "maintenance"], "persistent": False}}
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=old)
    entry.add_to_hass(hass)
    recorder = DebugRecorder(50)
    manager = AlertManager(hass, entry.entry_id, old, vehicles, recorder=recorder)
    await manager.async_load()
    checked: list[str] = []

    async def check_pin(pin: str) -> None:
        checked.append(pin)
        if pin == "0000":
            raise DeepalPinError("PIN incorrecto")

    entry.runtime_data = SimpleNamespace(
        vehicles=vehicles,
        alerts=manager,
        recorder=recorder,
        registries=registries,
        country=SimpleNamespace(id="es"),
        commands=SimpleNamespace(check_pin=check_pin),
    )
    counter = iter(range(1, 1000))

    async def call(command: str, **data):  # noqa: ANN003, ANN202
        await client.send_json({"id": next(counter), "type": f"dec_deepal/panel/{command}", **data})
        return await client.receive_json()

    # --- Estado: todo lo que pinta el panel ---------------------------------------------
    state = (await call("state"))["result"]
    assert [car["name"] for car in state["cars"]] == ["Changote", "Changuito"]
    first, second = state["cars"]
    assert first["model"] == "Deepal S05 EV RWD Max" and first["key"] == VIN
    assert (first["battery"], first["range"]) == (56, 276)
    assert first["sheet"]["verificada"] is True and second["sheet"]["funciones"]["porton_electrico"] is False
    assert first["maintenance"] is None and first["itv"] is None and first["insurance"] is None
    # Lo que necesitan las fichas y los formularios: normas de la ITV y manual.
    assert first["itv_rules"] == {
        "first_months": 48, "interval_months": 24, "reduced_from_months": 120, "reduced_interval_months": 12,
    }
    assert first["manual_url"] == model.manual_url
    # Los avisos de antes se ven ya aviso a aviso, cada uno con los destinos de su grupo.
    assert first["alerts"]["notices"]["charge_finished"] == [ME]
    assert first["alerts"]["notices"]["charge_started"] == []
    assert first["alerts"]["notices"]["maintenance_t1"] == [ME] and first["alerts"]["thresholds"] == {}
    assert [notice["id"] for notice in state["notices"]] == [notice.id for notice in NOTICES]
    assert state["notices"][14] == {
        "id": "maintenance_k1", "section": "maintenance", "unit": "km", "threshold": 5000, "limits": [100, 20000],
    }
    assert state["targets"] == [
        {"id": ME, "name": "iPhone de Manuel", "kind": "mobile"},
        {"id": "persistent_notification", "name": "Home Assistant notifications", "kind": "panel"},
    ]
    assert state["stored"] == [] and state["version"] and state["admin"] is True
    # Sin personas asignadas: el coche no es de nadie en concreto.
    assert first["people"] == [] and first["mine"] is False
    # Matrícula con el formato del país de la cuenta; sin ella, sin placa.
    assert first["plate"] == {"code": "E", "parts": ["6545 NPD"]} and second["plate"] is None
    # Para elegir la apariencia: los modelos del país, con sus versiones, colores y fotos.
    assert [item["id"] for item in state["models"]] == ["s05_2024", "s05_phev"]
    ev = state["models"][0]
    assert [(trim["id"], trim["equipped"], trim["wheel"]) for trim in ev["trims"]] == [
        ("pro", 0, "pro"), ("max", 4, ""), ("max_awd", 4, ""),
    ]
    assert ev["colors"][2] == {"id": "ganymade_grey", "name": "Ganymede Grey", "swatch": "#5d6166"}
    assert ev["photos"]["max|ganymade_grey"].startswith("/dec_deepal/photos/s05_2024/max_ganymade_grey.png?v=")
    assert ev["photos"]["|"].startswith("/dec_deepal/photos/s05_2024/default.png")
    # La llanta sin tapacubos del Max tiene foto propia (solo donde la hay).
    assert ev["photos"]["max|ganymade_grey|open"].startswith("/dec_deepal/photos/s05_2024/max_ganymade_grey_open.png")
    assert "pro|ganymade_grey|open" not in ev["photos"]
    assert state["models"][1]["fuel"] is True
    assert first["appearance"] == {"model": "s05_2024", "trim": "max", "color": first["appearance"]["color"], "wheels": None}
    # Los ajustes de la cuenta, sin el PIN (solo si lo hay).
    account = state["accounts"][0]
    assert account["pin_enabled"] is False and account["pin_set"] is False and "pin" not in account
    assert account["scan_minutes"] == 5 and account["manual"]["kind"] == "bev"
    assert account["manual"]["url"] == account["manual"]["official"] == model.manual_url

    # --- Avisos: aviso a aviso, con plazos ------------------------------------------------
    notices = {**first["alerts"]["notices"], "insurance_r1": [ME, "persistent_notification"]}
    bad = await call("set_alerts", vehicle_id="car1", notices=notices, thresholds={"maintenance_k2": 6000})
    assert bad["success"] is False and bad["error"]["code"] == "threshold_order"
    assert "vehicles" not in entry.options[OPT_ALERTS]  # no se ha guardado nada
    assert (await call("set_alerts", vehicle_id="no-existe", notices={}))["error"]["code"] == "not_found"
    ok = await call("set_alerts", vehicle_id="car1", notices=notices, thresholds={"maintenance_k1": 4000})
    assert ok["success"] is True
    saved = entry.options[OPT_ALERTS]
    mine, other = route_for(saved, "car1"), route_for(saved, "car2")
    assert mine.targets_for("insurance_r1") == (ME, "persistent_notification")
    assert mine.steps("maintenance", "k") == (4000, 2500, 1000)
    # El otro coche se escribe como estaba: sigue avisando igual que antes.
    assert other.targets_for("charge_finished") == (ME,) and other.thresholds == {}

    # --- Engranajes: mantenimiento, ITV y seguro -----------------------------------------
    with patch.object(hass.config_entries, "async_schedule_reload") as reload:
        result = await call(
            "set_maintenance", vehicle_id="car1", enabled=True, services_done=1,
            last_date="2026-03-10", last_km=19500, interval_km=20000, interval_months=12,
        )
        assert result["success"] is True
        reload.assert_called_once_with(entry.entry_id)  # aparecen sus entidades
        assert manager.record("car1").last_km == 19500 and manager.status("car1").days_left == 47
        assert (await call("register_maintenance", vehicle_id="car1", date="2027-01-22", km=37500))["success"]
        assert manager.record("car1").services_done == 2
        # Sin ficha no hay nada que registrar.
        assert (await call("register_maintenance", vehicle_id="car2", date="2027-01-22", km=1))["success"] is False

        assert (await call("set_itv", vehicle_id="car1", enabled=True, registration_date="2022-11-26"))["success"]
        assert manager.itv_status("car1").due_date == date(2026, 11, 26)
        # Una fecha a mano igual a la calculada no se guarda.
        await call("set_itv", vehicle_id="car1", enabled=True, registration_date="2022-11-26", next_date="2026-11-26")
        assert manager.itv_record("car1").next_override is None
        assert (await call("register_itv", vehicle_id="car1", date="2027-01-22"))["success"]
        assert manager.itv_record("car1").history == ["2027-01-22"]

        assert (await call(
            "set_insurance", vehicle_id="car1", enabled=True, renewal_date="2027-06-01", company=" Mutua ",
            policy="0123", kind="comprehensive", notice_days=30,
        ))["success"]
        assert manager.insurance_record("car1").company == "Mutua"
        assert (await call("set_insurance", vehicle_id="car1", enabled=True, renewal_date="mal"))["success"] is False
        assert (await call("set_insurance", vehicle_id="car1", enabled=False))["success"]
        assert manager.insurance_record("car1") is None

    state = (await call("state"))["result"]
    car = state["cars"][0]
    assert car["maintenance"]["number"] == 3 and car["maintenance"]["record"]["services_done"] == 2
    assert "notified" not in car["maintenance"]["record"]
    # La ficha enseña qué toca y qué se añade en la siguiente (sin repetir lo de esta).
    assert car["maintenance"]["operations"] and isinstance(car["maintenance"]["next_extra"], list)
    assert not set(car["maintenance"]["next_extra"]) & set(car["maintenance"]["operations"])
    assert [item["number"] for item in car["maintenance"]["record"]["history"]] == [2]
    assert car["itv"]["due_date"] == "2029-01-22" and car["insurance"] is None

    # --- Apariencia -----------------------------------------------------------------------
    assert (await call("set_appearance", vehicle_id="car2", model="no-existe"))["error"]["code"] == "unknown_model"
    assert (await call(
        "set_appearance", vehicle_id="car2", model="s05_phev", trim="limited_edition", color="rosa", wheels="open",
    ))["success"]
    # Lo que el modelo no tiene (ese color) se descarta; lo demás se guarda en las opciones.
    assert entry.options["appearance"]["car2"] == {
        "model": "s05_phev", "trim": "limited_edition", "color": None, "wheels": "open",
    }

    # --- Ajustes: PIN y lectura de datos -----------------------------------------------------
    base = {"entry_id": entry.entry_id, "scan_minutes": 10, "wake": False, "debug": True}
    assert (await call("set_settings", **base, pin_enabled=True))["error"]["code"] == "pin_required"
    assert (await call("set_settings", **base, pin_enabled=True, pin="0000"))["error"]["code"] == "pin_invalid"
    assert (await call("set_settings", **base, pin_enabled=True, pin="1"))["success"]
    assert (await call(
        "set_settings", **base, pin_enabled=True, pin=" 2468 ", pin_mode="armed", arm_seconds=60,
        manual_url="https://example.com/otro.pdf",
    ))["success"]
    options = entry.options
    assert (options["pin_enabled"], options["pin"], options["pin_mode"], options["arm_seconds"]) == (True, "2468", "armed", 60)
    assert (options["scan_minutes"], options["wake"], options["debug"]) == (10, False, True)
    assert options["manual_urls"] == {"s05_2024": "https://example.com/otro.pdf"}
    # Guardar otra cosa con el PIN vacío: se conserva y no se vuelve a comprobar.
    before = list(checked)
    assert (await call("set_settings", **base, pin_enabled=True, manual_url=""))["success"]
    assert entry.options["pin"] == "2468" and checked == before and entry.options["manual_urls"] == {}
    assert (await call("set_settings", **base, pin_enabled=True, manual_url="mal"))["error"]["code"] == "invalid_url"
    assert (await call("set_settings", entry_id="otra", pin_enabled=False, scan_minutes=5, wake=True, debug=False))["success"] is False
    # Desactivar el PIN lo borra: la próxima vez se empieza de cero.
    assert (await call("set_settings", **base, pin_enabled=False))["success"]
    assert entry.options["pin"] is None and entry.options["pin_mode"] == "direct"
    account = (await call("state"))["result"]["accounts"][0]
    assert account["pin_set"] is False and account["scan_minutes"] == 10
    # Sumar el equilibrado: activado de fábrica; se puede quitar.
    assert account["charge_balance"] is True
    assert (await call("set_settings", **base, pin_enabled=False, charge_balance=False))["success"]
    assert entry.options["charge_balance"] is False
    assert (await call("state"))["result"]["accounts"][0]["charge_balance"] is False

    # --- Personas: a quién pertenece cada coche ---------------------------------------------
    hass.states.async_set("person.ana", "home", {"friendly_name": "Ana", "user_id": "otro"})
    assert (await call("set_people", vehicle_id="car1", people=["person.nadie"]))["error"]["code"] == "unknown_person"
    assert (await call("set_people", vehicle_id="car1", people=["person.ana", "person.ana"]))["success"]
    assert manager.people("car1") == ["person.ana"]
    state = (await call("state"))["result"]
    assert state["cars"][0]["people"] == [{"id": "person.ana", "name": "Ana"}]
    assert state["people"] == [{"id": "person.ana", "name": "Ana"}]
    assert "people" in state["stored"][0]["has"]

    # --- Datos: copia, envío a un móvil, carga y borrado -----------------------------------
    link = (await call("export_url"))["result"]
    assert link["url"].startswith("/api/dec_deepal/export?authSig=")
    # La copia se descarga sin iniciar sesión con el enlace firmado; sin firma, no.
    anonymous = await hass_client_no_auth()
    backup = await (await anonymous.get(link["url"])).json()
    assert backup["coches"][VIN]["people"] == ["person.ana"]
    assert (await anonymous.get("/api/dec_deepal/export")).status == 401
    # El enlace completo usa la dirección con la que el usuario está entrando ahora.
    assert link["absolute"].startswith("http://127.0.0.1") and link["absolute"].endswith(link["url"])
    assert (await call("send_backup", target=ME))["success"]
    await hass.async_block_till_done()
    assert "/api/dec_deepal/export?authSig=" in sent[-1].data["data"]["url"]
    assert sent[-1].data["data"]["url"].startswith("http://127.0.0.1")
    assert (await call("send_backup", target="mobile_app_no_existe"))["success"] is False

    state = (await call("state"))["result"]
    assert [(item["label"], item["in_account"]) for item in state["stored"]][0] == ("Changote", True)
    assert "maintenance" in state["stored"][0]["has"] and "appearance" in state["stored"][0]["has"]
    with patch.object(hass.config_entries, "async_schedule_reload"):
        assert (await call("import_backup", backup={"otra": "cosa"}))["error"]["code"] == "invalid_file"
        backup = {
            "formato": "dec_deepal.datos", "version": 1,
            "coches": {VIN: {"insurance": {"renewal_date": "2028-01-01", "company": "Otra"}}},
        }
        loaded = await call("import_backup", backup=backup)
        assert loaded["result"] == {"cars": ["Deepal …000001"]}
        # La copia manda: el coche queda como en el fichero.
        assert manager.insurance_record("car1").company == "Otra" and manager.record("car1") is None
        assert (await call("delete_data", keys=[VIN]))["success"]
        assert manager.insurance_record("car1") is None
    await manager.async_stop()


async def test_panel_is_registered_once_and_removed(hass: HomeAssistant) -> None:
    """El panel se añade con la primera cuenta y se quita con la última."""
    assert await async_setup_component(hass, "http", {})
    with (
        patch.object(panel.panel_custom, "async_register_panel", AsyncMock()) as register,
        patch.object(panel.frontend, "async_remove_panel") as remove,
    ):
        await panel.async_register_panel(hass)
        await panel.async_register_panel(hass)  # segunda cuenta: no se repite
        register.assert_awaited_once()
        options = register.await_args.kwargs
        assert options["frontend_url_path"] == PANEL_URL_PATH == "dec-deepal-panel"
        # Lo ven todos; quien no es administrador, en solo lectura (ver test_read_only_panel).
        assert options["webcomponent_name"] == "dec-deepal-panel" and options["require_admin"] is False
        assert options["module_url"].startswith("/dec_deepal/frontend/dec-deepal-panel.js?v=")
        # El botón Configurar de la integración abre el panel (como en Alarmo).
        assert options["config_panel_domain"] == DOMAIN
        panel.async_unregister_panel(hass)
        panel.async_unregister_panel(hass)
        remove.assert_called_once_with(hass, PANEL_URL_PATH)
    assert (INTEGRATION / "frontend_panel" / "dec-deepal-panel.js").is_file()


@pytest.mark.usefixtures("enable_custom_integrations", "hass_storage")
async def test_read_only_panel(
    hass: HomeAssistant, hass_ws_client, hass_read_only_access_token: str, hass_read_only_user
) -> None:  # noqa: ANN001
    """Quien no es administrador ve Coches y Avisos, y no puede cambiar nada."""
    assert await async_setup_component(hass, "websocket_api", {})
    for command in panel.COMMANDS:
        websocket_api.async_register_command(hass, command)
    registries = load_all(INTEGRATION)
    model = registries.vehicles.get("s05_2024")
    vehicles = {"car1": _vehicle(model, "car1", "Changote", VIN, "max")}
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    manager = AlertManager(hass, entry.entry_id, {}, vehicles, recorder=DebugRecorder(10))
    await manager.async_load()
    await manager.async_set_people("car1", ["person.lucia"])
    hass.states.async_set(
        "person.lucia", "home", {"friendly_name": "Lucía", "user_id": hass_read_only_user.id}
    )
    entry.runtime_data = SimpleNamespace(
        vehicles=vehicles, alerts=manager, recorder=DebugRecorder(10), registries=registries,
        country=SimpleNamespace(id="es"),
    )
    client = await hass_ws_client(hass, hass_read_only_access_token)

    await client.send_json({"id": 1, "type": "dec_deepal/panel/state"})
    state = (await client.receive_json())["result"]
    assert state["admin"] is False and [car["name"] for car in state["cars"]] == ["Changote"]
    # Es suyo: Lucía es la persona de este usuario.
    assert state["cars"][0]["mine"] is True
    assert state["notices"] and state["targets"]
    # Nada de administración: ajustes, catálogo, personas, datos guardados ni historial.
    assert not {"accounts", "models", "people", "stored", "history"} & set(state)

    await client.send_json(
        {"id": 2, "type": "dec_deepal/panel/set_people", "vehicle_id": "car1", "people": []}
    )
    refused = await client.receive_json()
    assert refused["success"] is False and refused["error"]["code"] == "unauthorized"
    assert manager.people("car1") == ["person.lucia"]
    await manager.async_stop()
