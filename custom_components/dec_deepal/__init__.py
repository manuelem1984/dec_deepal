"""DEC Deepal — integración de Home Assistant de la Comunidad Deepal España.

Punto de entrada. Home Assistant llama a estas funciones:

- :func:`async_setup` — una vez al arrancar, haya o no cuentas configuradas:
  carga los catálogos, publica los iconos ``dec:`` y registra los servicios.
- :func:`async_setup_entry` — por cada cuenta configurada: crea la sesión, el
  cliente, un coordinador y un ejecutor de comandos por coche, y las
  entidades.
- :func:`async_unload_entry` — al quitar o recargar una cuenta.

Mapa de la integración: ``docs/arquitectura.md``.
"""

from __future__ import annotations

import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import config_validation as cv
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
    PLATFORMS,
)
from .coordinator import VehicleCoordinator
from .debug.recorder import DebugRecorder
from .frontend import async_register_frontend
from .registries import RegistryError
from .registries.vehicles import FEATURE_MQTT
from .runtime import (
    DecDeepalConfigEntry,
    DecDeepalRuntime,
    VehicleContext,
    async_get_registries,
)
from .services import async_register_services

_LOGGER = logging.getLogger(__name__)

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
    async_register_services(hass)
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
    recorder = DebugRecorder(DEBUG_BUFFER_SIZE, verbose=debug)
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
    await _refresh_vehicle_list(hass, entry, client)
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
        coordinator = VehicleCoordinator(
            hass,
            entry,
            account=account,
            client=client,
            recorder=recorder,
            vehicle=info,
            use_mqtt=info.uses_mqtt and model.has(FEATURE_MQTT, trim),
            scan_minutes=scan_minutes,
            wake_enabled=bool(options.get(OPT_WAKE, DEFAULT_WAKE)),
        )
        runner = CommandRunner(
            hass,
            coordinator=coordinator,
            commands=commands,
            recorder=recorder,
            pin_mode=options.get(OPT_PIN_MODE, DEFAULT_PIN_MODE),
            arm_seconds=int(options.get(OPT_ARM_SECONDS, DEFAULT_ARM_SECONDS)),
            arm_notify=bool(options.get(OPT_ARM_NOTIFY, DEFAULT_ARM_NOTIFY)),
        )
        runtime.vehicles[info.vehicle_id] = VehicleContext(
            info=info,
            model=model,
            trim=trim,
            color=appearance.get(OPT_COLOR),
            coordinator=coordinator,
            runner=runner,
            suggested_model=suggested,
            configured=configured,
            # Solo para diagnóstico: permite comprobar con datos reales si las
            # capacidades del servidor distinguen Pro de Max (hoy no se usan
            # para decidir nada; la primera prueba adivinó mal un Max).
            capabilities=await _fetch_capabilities(client, info),
        )
        _LOGGER.debug(
            "%s: modelo=%s versión=%s mqtt=%s",
            info.display_name,
            model.id,
            trim,
            coordinator.use_mqtt,
        )

    entry.runtime_data = runtime

    # Primera lectura de todos los coches a la vez. Si falla, Home Assistant
    # reintenta la carga más tarde (o pide volver a iniciar sesión).
    await asyncio.gather(
        *(
            vehicle.coordinator.async_config_entry_first_refresh()
            for vehicle in runtime.vehicles.values()
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Recargar SOLO si cambian las opciones. Guardar tokens nuevos también
    # "actualiza" la entrada, y eso no debe provocar una recarga.
    options_snapshot = dict(entry.options)

    async def _on_entry_updated(hass: HomeAssistant, updated: DecDeepalConfigEntry) -> None:
        if dict(updated.options) != options_snapshot:
            await hass.config_entries.async_reload(updated.entry_id)

    entry.async_on_unload(entry.add_update_listener(_on_entry_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DecDeepalConfigEntry) -> bool:
    """Descarga una cuenta."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        for vehicle in entry.runtime_data.vehicles.values():
            vehicle.runner.async_shutdown()
        _set_debug_logging(hass, entry.entry_id, False)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: DecDeepalConfigEntry) -> None:
    """Al borrar la cuenta, borra también sus avisos de Reparaciones."""
    for raw_vehicle in entry.data.get(CONF_VEHICLES, []):
        ir.async_delete_issue(hass, DOMAIN, issue_id(str(raw_vehicle.get("vehicle_id"))))


async def _refresh_vehicle_list(
    hass: HomeAssistant, entry: DecDeepalConfigEntry, client: DeepalClient
) -> None:
    """Actualiza los datos guardados de cada coche (matrícula, imagen, apodo...).

    Los datos se guardaron al configurar la cuenta; si el servidor ha añadido
    o cambiado algo (p. ej. la matrícula, que versiones anteriores no
    guardaban), se actualizan sin recargar (no cambian las opciones). Solo se
    tocan los coches ya elegidos. Nunca falla: si no hay red, se sigue con lo
    guardado.
    """
    try:
        fresh = {vehicle.vehicle_id: vehicle for vehicle in await client.get_vehicles()}
    except DeepalError as err:
        _LOGGER.debug("No se pudo actualizar la lista de vehículos: %s", err)
        return
    stored = entry.data[CONF_VEHICLES]
    updated = [
        {**item, **fresh[item["vehicle_id"]].to_dict()} if item.get("vehicle_id") in fresh else item
        for item in stored
    ]
    if updated != stored:
        hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_VEHICLES: updated})


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
