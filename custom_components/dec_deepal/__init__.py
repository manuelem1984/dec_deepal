"""DEC Deepal — integración de Home Assistant de la Comunidad Deepal España.

Punto de entrada. Home Assistant llama a estas funciones:

- :func:`async_setup` — una vez al arrancar, haya o no cuentas configuradas:
  carga los catálogos, publica los iconos ``dec:`` y registra los servicios.
- :func:`async_setup_entry` — por cada cuenta configurada: crea la sesión, el
  cliente, un coordinador y un ejecutor de comandos por coche, y las
  entidades.
- :func:`async_unload_entry` — al quitar o recargar una cuenta.

Al final del arranque de cada cuenta se pone en marcha el gestor de avisos y
mantenimiento (``alerts.py``).

Mapa de la integración: ``docs/arquitectura.md``.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api.account import DeepalAccount
from .api.client import DeepalClient
from .api.commands import DeepalCommands
from .api.errors import DeepalError
from .api.models import Capabilities, VehicleInfo
from .api.session import DeepalSession
from .appearance import issue_id
from .api.transport import DeepalTransport
from . import vehicle_data as vd
from .alerts import AlertManager
from .command_runner import CommandRunner
from .const import (
    CONF_COUNTRY,
    CONF_SESSION,
    CONF_VEHICLES,
    DEBUG_BUFFER_SIZE,
    DEFAULT_ARM_NOTIFY,
    DEFAULT_ARM_SECONDS,
    DEFAULT_PIN_MODE,
    DEFAULT_SCAN_MINUTES,
    DOMAIN,
    OPT_APPEARANCE,
    OPT_CHARGE_BALANCE,
    CHARGE_BALANCE_MINUTES,
    DEFAULT_CHARGE_BALANCE,
    OPT_ARM_NOTIFY,
    OPT_ARM_SECONDS,
    OPT_COLOR,
    OPT_DEBUG,
    OPT_WAKE,
    DEFAULT_WAKE,
    OPT_MODEL,
    OPT_PIN,
    OPT_PIN_ENABLED,
    OPT_PIN_MODE,
    OPT_SCAN_MINUTES,
    OPT_TRIM,
    OPT_WHEELS,
    PLATFORMS,
)
from .coordinator import VehicleCoordinator
from .debug.history import changes as signal_changes
from .debug.recorder import DebugRecorder, VehicleRecorder
from .frontend import async_register_frontend, async_remove_early_loader
from .manual import async_register_manual
from .chargers import async_get_manager
from .panel import async_register_panel, async_unregister_panel
from .registries import RegistryError
from .registries.vehicles import FEATURE_FUEL, FEATURE_MQTT, POWERTRAIN_PHEV, powertrain
from .runtime import (
    DecDeepalConfigEntry,
    DecDeepalRuntime,
    VehicleContext,
    async_get_registries,
)
from .services import async_register_services
from .vehicle_store import async_get_store, async_register_export
from .vehicle_sync import async_schedule_sync, async_sync_vehicles, delete_issues

_LOGGER = logging.getLogger(__name__)

#: Registros de depuración de cada cuenta, en ``hass.data[DOMAIN]``.
_RECORDERS_KEY = "recorders"

# Solo se configura desde la interfaz: una línea "dec_deepal:" en
# configuration.yaml se rechaza con un aviso claro.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

#: Logger raíz de la integración (para el modo depuración).
_PACKAGE_LOGGER = logging.getLogger(__package__)
_DEBUG_ENTRIES_KEY = "debug_entries"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Arranque global (una vez): catálogos, iconos y servicios."""
    try:
        registries = await async_get_registries(hass)
    except RegistryError as err:
        _LOGGER.error("Catálogo con errores, la integración no puede arrancar: %s", err)
        return False
    await async_register_frontend(hass, registries.icons)
    async_register_manual(hass)
    async_register_export(hass)
    async_register_services(hass)
    await async_get_manager(hass).async_load()
    return True


#: Conectores AC y DC (ver ``async_migrate_entry``).
_CONNECTORS = ("_binary_sensor_ac_connector", "_binary_sensor_dc_connector")


async def async_migrate_entry(hass: HomeAssistant, entry: DecDeepalConfigEntry) -> bool:
    """Pone al día una cuenta añadida con una versión anterior.

    - Versión menor 2 (2.5.0b7): los conectores AC y DC se desactivaron
      porque no eran fiables.
    - Versión menor 3 (2.5.1b1): salen del estado de carga del coche y se
      vuelven a activar. Solo los que desactivó la integración: si alguien los
      desactivó a mano, se respeta. Se hace una sola vez.
    """
    if entry.version == 1 and entry.minor_version < 3:
        registry = er.async_get(hass)
        for item in er.async_entries_for_config_entry(registry, entry.entry_id):
            if (
                item.unique_id.endswith(_CONNECTORS)
                and item.disabled_by is er.RegistryEntryDisabler.INTEGRATION
            ):
                registry.async_update_entity(item.entity_id, disabled_by=None)
        hass.config_entries.async_update_entry(entry, minor_version=3)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: DecDeepalConfigEntry) -> bool:
    """Arranca una cuenta configurada."""
    try:
        registries = await async_get_registries(hass)
        country = registries.countries.get(entry.data[CONF_COUNTRY])
    except RegistryError as err:
        raise ConfigEntryError(str(err)) from err

    options = entry.options
    debug = bool(options.get(OPT_DEBUG, False))
    _set_debug_logging(hass, entry.entry_id, debug)

    # --- Cliente de la API ---------------------------------------------------
    # El registro sobrevive a las recargas de la cuenta (cambiar una opción la
    # recarga): si no, el historial se perdería justo antes de mirarlo.
    recorders = hass.data.setdefault(DOMAIN, {}).setdefault(_RECORDERS_KEY, {})
    recorder = recorders.setdefault(entry.entry_id, DebugRecorder(DEBUG_BUFFER_SIZE))
    recorder.verbose = debug
    session = DeepalSession.from_dict(entry.data[CONF_SESSION])
    transport = DeepalTransport(
        async_get_clientsession(hass),
        country.profile(),
        session,
        on_exchange=recorder.record_http,
    )

    def _persist_session(updated: DeepalSession) -> None:
        """Guarda los tokens renovados (sin recargar la integración)."""
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_SESSION: updated.to_dict()}
        )

    account = DeepalAccount(transport, on_session_changed=_persist_session)
    client = DeepalClient(account)
    commands = DeepalCommands(account)
    if options.get(OPT_PIN_ENABLED):
        commands.control_pin = options.get(OPT_PIN)

    runtime = DecDeepalRuntime(
        country=country,
        account=account,
        client=client,
        commands=commands,
        recorder=recorder,
        registries=registries,
    )

    # --- Un contexto por coche -----------------------------------------------
    await async_sync_vehicles(hass, entry, client)
    await _restore_appearance(hass, entry, registries.vehicles.models)
    options = entry.options
    if options.get(OPT_CHARGE_BALANCE, DEFAULT_CHARGE_BALANCE):
        runtime.charge_balance_minutes = CHARGE_BALANCE_MINUTES
    appearance_by_vehicle: dict = options.get(OPT_APPEARANCE, {})
    scan_minutes = int(options.get(OPT_SCAN_MINUTES, DEFAULT_SCAN_MINUTES))
    for raw_vehicle in entry.data[CONF_VEHICLES]:
        info = VehicleInfo.from_dict(raw_vehicle)
        appearance = appearance_by_vehicle.get(info.vehicle_id, {})
        # Modelo reconocido por el nombre que da el servidor: solo es una
        # SUGERENCIA para el usuario. Hasta que elija su modelo, el coche
        # funciona como "genérico" y se le avisa en Reparaciones.
        suggested = registries.vehicles.match(info, country.id)
        configured = bool(appearance.get(OPT_MODEL))
        model = registries.vehicles.get(appearance.get(OPT_MODEL)) if configured else registries.vehicles.generic
        trim = appearance.get(OPT_TRIM)
        _update_setup_issue(hass, entry, info, suggested.name, configured)
        vehicle_recorder = recorder.for_vehicle(info.display_name)
        coordinator = VehicleCoordinator(
            hass,
            entry,
            account=account,
            client=client,
            recorder=vehicle_recorder,
            vehicle=info,
            use_mqtt=info.uses_mqtt and model.has(FEATURE_MQTT, trim),
            scan_minutes=scan_minutes,
            wake_enabled=bool(options.get(OPT_WAKE, DEFAULT_WAKE)),
        )
        runner = CommandRunner(
            hass,
            coordinator=coordinator,
            commands=commands,
            recorder=vehicle_recorder,
            pin_mode=options.get(OPT_PIN_MODE, DEFAULT_PIN_MODE),
            arm_seconds=int(options.get(OPT_ARM_SECONDS, DEFAULT_ARM_SECONDS)),
            arm_notify=bool(options.get(OPT_ARM_NOTIFY, DEFAULT_ARM_NOTIFY)),
        )
        runtime.vehicles[info.vehicle_id] = VehicleContext(
            info=info,
            model=model,
            trim=trim,
            color=appearance.get(OPT_COLOR),
            wheels=appearance.get(OPT_WHEELS),
            coordinator=coordinator,
            runner=runner,
            suggested_model=suggested,
            configured=configured,
            # Solo para diagnóstico: permite comprobar con datos reales si las
            # capacidades del servidor distinguen Pro de Max (hoy no se usan
            # para decidir nada; la primera prueba adivinó mal un Max).
            capabilities=await _fetch_capabilities(client, info),
        )
        entry.async_on_unload(_track_changes(coordinator, vehicle_recorder))
        entry.async_on_unload(_watch_model_code(hass, entry, runtime.vehicles[info.vehicle_id], registries))
        _LOGGER.debug(
            "%s: modelo=%s versión=%s mqtt=%s",
            info.display_name,
            model.id,
            trim,
            coordinator.use_mqtt,
        )

    entry.runtime_data = runtime

    # Primera lectura de cada coche, UNO DETRÁS DE OTRO (no a la vez): el
    # MQTT de la cuenta solo admite una conexión simultánea (ver el candado
    # de api/client.py). Si falla, Home Assistant reintenta la carga más tarde
    # (o pide volver a iniciar sesión).
    for vehicle in runtime.vehicles.values():
        await vehicle.coordinator.async_config_entry_first_refresh()

    # Avisos y mantenimiento: se lee lo guardado antes de crear las entidades
    # (las de mantenimiento solo existen en los coches que lo tienen activado)
    # y se empieza a vigilar después.
    runtime.alerts = AlertManager(
        hass,
        entry.entry_id,
        dict(options),
        runtime.vehicles,
        country.rules,
        itv_available=country.itv,
        recorder=recorder,
    )
    await runtime.alerts.async_load()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    runtime.alerts.async_start()
    # Panel de la barra lateral (una vez, con la primera cuenta).
    await async_register_panel(hass)

    # Recargar SOLO si cambian las opciones. Guardar tokens nuevos también
    # "actualiza" la entrada, y eso no debe provocar una recarga.
    options_snapshot = dict(entry.options)

    async def _on_entry_updated(hass: HomeAssistant, updated: DecDeepalConfigEntry) -> None:
        if dict(updated.options) != options_snapshot:
            await hass.config_entries.async_reload(updated.entry_id)

    entry.async_on_unload(entry.add_update_listener(_on_entry_updated))

    # Coches nuevos o retirados de la cuenta (avisos en Reparaciones).
    entry.async_on_unload(async_schedule_sync(hass, entry, client))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DecDeepalConfigEntry) -> bool:
    """Descarga una cuenta."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        for vehicle in entry.runtime_data.vehicles.values():
            vehicle.runner.async_shutdown()
        if entry.runtime_data.alerts is not None:
            await entry.runtime_data.alerts.async_stop()
        _set_debug_logging(hass, entry.entry_id, False)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: DecDeepalConfigEntry) -> None:
    """Al borrar la cuenta, borra sus avisos de Reparaciones.

    Si era la última cuenta, quita también el cargador temprano de iconos
    (recurso de los paneles y copia en ``www``).

    Los datos de los coches (mantenimiento, ITV, seguro) **se conservan**:
    son del coche, y vuelven solos si se añade la cuenta otra vez. Se borran
    desde el panel DEC Deepal → Datos.
    """
    for raw_vehicle in entry.data.get(CONF_VEHICLES, []):
        ir.async_delete_issue(hass, DOMAIN, issue_id(str(raw_vehicle.get("vehicle_id"))))
    delete_issues(hass, entry)
    # Si la cuenta aún tenía el almacén antiguo (de la 2.3.0), se pasa al de
    # coches antes de perder la relación entre cada coche y su bastidor.
    hass.data.get(DOMAIN, {}).get(_RECORDERS_KEY, {}).pop(entry.entry_id, None)
    store = async_get_store(hass)
    await store.async_load()
    await store.async_adopt_legacy(
        entry.entry_id,
        {
            str(raw.get("vehicle_id")): vd.car_key(raw.get("vin"), str(raw.get("vehicle_id")))
            for raw in entry.data.get(CONF_VEHICLES, [])
        },
    )
    if not hass.config_entries.async_entries(DOMAIN):
        await async_remove_early_loader(hass)
        async_unregister_panel(hass)


def _track_changes(coordinator: VehicleCoordinator, recorder: VehicleRecorder):  # noqa: ANN202
    """Apunta en el registro qué señales cambian en cada lectura de un coche."""
    previous: dict[str, object] | None = None

    def on_update() -> None:
        nonlocal previous
        if coordinator.data is None:
            return
        current = dict(coordinator.data.values)
        changed = signal_changes(previous, current)
        previous = current
        if changed:
            recorder.record("change", changes=changed)

    return coordinator.async_add_listener(on_update)


async def _restore_appearance(
    hass: HomeAssistant, entry: DecDeepalConfigEntry, models: dict
) -> None:
    """Devuelve a cada coche sin modelo elegido la apariencia que tenía guardada.

    Pasa al volver a añadir una cuenta que se quitó: la apariencia se guardó
    con el coche (por bastidor). Se hace antes de vigilar los cambios de
    opciones, así que no provoca una recarga.
    """
    store = async_get_store(hass)
    await store.async_load()
    appearance = dict(entry.options.get(OPT_APPEARANCE, {}))
    restored = False
    for raw in entry.data.get(CONF_VEHICLES, []):
        vehicle_id = str(raw.get("vehicle_id"))
        if appearance.get(vehicle_id, {}).get(OPT_MODEL):
            continue
        saved = vd.clean_appearance(
            store.car(vd.car_key(raw.get("vin"), vehicle_id)).get(vd.APPEARANCE), models
        )
        if saved is not None:
            appearance[vehicle_id] = saved
            restored = True
    if restored:
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, OPT_APPEARANCE: appearance}
        )


async def _fetch_capabilities(client: DeepalClient, info: VehicleInfo) -> Capabilities | None:
    """Capacidades del servidor (``function-config``), solo para diagnóstico.

    Nunca falla: si el endpoint no responde, devuelve ``None``.
    """
    try:
        return await client.get_capabilities(info)
    except DeepalError:
        return None


def _update_setup_issue(
    hass: HomeAssistant,
    entry: DecDeepalConfigEntry,
    info: VehicleInfo,
    suggestion: str,
    configured: bool,
) -> None:
    """Crea o borra el aviso "Configura tu vehículo" en Reparaciones.

    Aparece en Ajustes → Reparaciones mientras el coche no tenga modelo
    elegido. Tiene un asistente ("Enviar") que pide modelo, versión y color
    (ver ``repairs.py``); al terminar, el aviso desaparece solo.
    """
    issue = issue_id(info.vehicle_id)
    if configured:
        ir.async_delete_issue(hass, DOMAIN, issue)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue,
        is_fixable=True,
        is_persistent=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="vehicle_not_configured",
        translation_placeholders={"vehicle": info.display_name, "suggestion": suggestion},
        data={"entry_id": entry.entry_id, "vehicle_id": info.vehicle_id},
    )


#: Aviso de Reparaciones "el coche dice ser otro modelo" (uno por coche).
MODEL_MISMATCH_PREFIX = "model_mismatch_"
#: Modelo del catálogo que corresponde a cada tipo de motor.
_MODEL_BY_POWERTRAIN = {"ev": "s05_2024", "phev": "s05_phev"}


def update_model_issue(hass: HomeAssistant, entry: DecDeepalConfigEntry, vehicle: VehicleContext, registries) -> None:  # noqa: ANN001
    """Avisa en Reparaciones si el coche dice ser EV o PHEV y está configurado como el otro.

    Solo con el modelo ya elegido (el genérico ya tiene su aviso "Configura tu
    vehículo") y con el código de modelo que da el coche por MQTT (``b.mc``).
    """
    issue = f"{MODEL_MISMATCH_PREFIX}{vehicle.info.vehicle_id}"
    detected = powertrain(vehicle.coordinator.model_code)
    if detected is None or not vehicle.configured or not vehicle.model.id.startswith("s05"):
        ir.async_delete_issue(hass, DOMAIN, issue)
        return
    chosen = POWERTRAIN_PHEV if vehicle.has(FEATURE_FUEL) else "ev"
    if detected == chosen:
        ir.async_delete_issue(hass, DOMAIN, issue)
        return
    model = registries.vehicles.get(_MODEL_BY_POWERTRAIN[detected])
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue,
        is_fixable=True,
        is_persistent=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="vehicle_model_mismatch",
        translation_placeholders={
            "vehicle": vehicle.info.display_name,
            "detected": model.name,
            "chosen": vehicle.model.name,
            "code": str(vehicle.coordinator.model_code),
        },
        data={"entry_id": entry.entry_id, "vehicle_id": vehicle.info.vehicle_id, "suggested": model.id},
    )


def _watch_model_code(hass: HomeAssistant, entry: DecDeepalConfigEntry, vehicle: VehicleContext, registries):  # noqa: ANN001, ANN202
    """Comprueba el modelo cada vez que cambia el código que da el coche."""
    seen: str | None = None

    def on_update() -> None:
        nonlocal seen
        code = vehicle.coordinator.model_code
        if code and code != seen:
            seen = code
            update_model_issue(hass, entry, vehicle, registries)

    return vehicle.coordinator.async_add_listener(on_update)


def _set_debug_logging(hass: HomeAssistant, entry_id: str, enabled: bool) -> None:
    """Activa/desactiva el nivel DEBUG del logger de la integración.

    Con varias cuentas, el DEBUG se mantiene mientras al menos una lo tenga
    activado. Al desactivarlo en todas, se vuelve al nivel heredado de la
    configuración de Home Assistant (``NOTSET``).
    """
    debug_entries: set[str] = hass.data.setdefault(DOMAIN, {}).setdefault(
        _DEBUG_ENTRIES_KEY, set()
    )
    if enabled:
        debug_entries.add(entry_id)
    else:
        debug_entries.discard(entry_id)
    _PACKAGE_LOGGER.setLevel(logging.DEBUG if debug_entries else logging.NOTSET)
