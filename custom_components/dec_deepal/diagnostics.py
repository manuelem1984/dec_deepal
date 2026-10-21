"""Diagnósticos: el JSON de "Descargar diagnósticos" (ficha de la integración).

Pensado para adjuntarlo a un Issue sin miedo: todo pasa por
:func:`~.debug.redact.redact` (tokens, VIN, móvil, PIN, identificadores...).

Contenido:

- ``integracion``: versión, país, opciones (sin PIN).
- ``catalogos``: modelos cargados y avisos de iconos.
- ``vehiculos``: por coche →
    - ``modelo``/``version``/``color`` reconocidos,
    - ``ficha``: qué ficha del catálogo se le aplica, de dónde sale (su
      versión o el modelo) y si está verificada en un coche real,
    - ``senales`` (valores interpretados) y ``origen`` de cada una,
    - ``mqtt`` en bruto y ``mqtt_sin_mapear`` (candidatas a nuevas entidades),
    - ``rest`` en bruto,
    - ``avisos`` de la última lectura.
    - ``entidades``: las entidades creadas para el coche, con su estado y si
      están desactivadas.
- ``historial``: lo que pasó, conservado aparte del registro general para
  que la rutina no lo borre (``debug/recorder.py``):
    - ``cambios``: señales que cambiaron en cada lectura, con su hora.
    - ``ordenes``: órdenes enviadas y despertares, con la respuesta del servidor.
    - ``avisos``: avisos enviados al móvil (tipo y nº de destinos, sin texto).
    - ``errores``: cualquier evento que acabó en error.
- ``registro_depuracion``: últimos eventos (HTTP, MQTT, comandos...). Con el
  modo depuración activo incluye los cuerpos completos.
- ``capturas``: las capturas hechas con ``dec_deepal.capture_snapshot``.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, OPT_ALERTS, OPT_APPEARANCE, OPT_PIN, VERSION
from .debug.capture import build_snapshot
from .debug.redact import redact
from .frontend import LOADER_STATUS_KEY
from .runtime import DecDeepalConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DecDeepalConfigEntry
) -> dict[str, Any]:
    """Construye el informe de diagnóstico de una cuenta."""
    runtime = entry.runtime_data
    # Opciones sin el PIN ni la apariencia (que va indexada por id de
    # vehículo; versión y color ya aparecen en cada vehículo). No se pasan por
    # redact() para que "pin_enabled"/"pin_mode" sigan siendo legibles.
    options = {
        key: value
        for key, value in entry.options.items()
        if key not in (OPT_PIN, OPT_APPEARANCE, OPT_ALERTS)
    }
    # De los avisos, solo el resumen: los destinos llevan el nombre del móvil.
    if runtime.alerts is not None:
        options["avisos"] = runtime.alerts.config_summary()

    entities = _entities_by_vehicle(hass, entry)
    vehicles: dict[str, Any] = {}
    for vehicle in runtime.vehicles.values():
        snapshot = build_snapshot("diagnostico", vehicle.info.display_name, vehicle.coordinator.data)
        vehicles[vehicle.info.display_name] = {
            "info": vehicle.info.to_dict(),
            "modelo": vehicle.model.id,
            "version": vehicle.trim,
            "color": vehicle.color,
            "configurado": vehicle.configured,
            # Qué ficha del catálogo se le aplica y si está verificada.
            "ficha": vehicle.model.sheet(vehicle.trim),
            "modelo_sugerido": vehicle.suggested_model.id if vehicle.suggested_model else None,
            # Para validar si el servidor distingue Pro/Max: lista de funciones
            # que dice tener el coche y la versión que se deduciría de ella.
            "capacidades": (
                {
                    "codigos": vehicle.capabilities.raw_codes,
                    "version_deducida": vehicle.capabilities.trim_hint,
                }
                if vehicle.capabilities
                else "no disponibles"
            ),
            "imagen_oficial": vehicle.official_image_status,
            "usa_mqtt": vehicle.coordinator.use_mqtt,
            "ultima_lectura_ok": vehicle.coordinator.last_update_success,
            "armado": vehicle.runner.is_armed,
            **(runtime.alerts.diagnostics(vehicle.info.vehicle_id) if runtime.alerts else {}),
            **snapshot,
        }
        # Fuera de redact(): son claves de entidad ("lock.pin_arm"), no datos.
        vehicles[vehicle.info.display_name]["entidades"] = entities.get(
            vehicle.info.vehicle_id, {}
        )

    report = redact(
        {
            "integracion": {
                "version": VERSION,
                "pais": runtime.country.id,
                "modo_depuracion": runtime.recorder.verbose,
            },
            "catalogos": {
                "modelos": sorted(runtime.registries.vehicles.models),
                "iconos_svg": sorted(runtime.registries.icons.available),
                "avisos_iconos": runtime.registries.icons.warnings,
                # Cargador temprano de iconos (recurso de paneles, ruta propia).
                "cargador_iconos": hass.data.get(DOMAIN, {}).get(LOADER_STATUS_KEY),
            },
            "vehiculos": vehicles,
            "historial": runtime.recorder.history(),
            "registro_depuracion": runtime.recorder.events(),
            "capturas": list(runtime.captures.values()),
        }
    )
    report["integracion"]["opciones"] = options
    for name, data in vehicles.items():
        report["vehiculos"][name]["entidades"] = data["entidades"]
    return report


def _entities_by_vehicle(
    hass: HomeAssistant, entry: DecDeepalConfigEntry
) -> dict[str, dict[str, str]]:
    """Entidades de cada coche: ``{id del coche: {"sensor.range": "276", ...}}``.

    La clave es la interna de la integración (no cambia aunque el usuario
    renombre la entidad). El valor es su estado; ``desactivada`` si el
    usuario o Home Assistant la tienen desactivada, y ``sin estado`` si
    todavía no ha dado ninguno.
    """
    devices = dr.async_get(hass)
    result: dict[str, dict[str, str]] = {}
    for entity in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        device = devices.async_get(entity.device_id) if entity.device_id else None
        vehicle_id = next(
            (value for domain, value in (device.identifiers if device else ()) if domain == DOMAIN),
            None,
        )
        if vehicle_id is None:
            continue
        state = hass.states.get(entity.entity_id)
        if entity.disabled_by is not None:
            value = "desactivada"
        else:
            value = state.state if state is not None else "sin estado"
        key = f"{entity.domain}.{entity.translation_key or entity.unique_id}"
        result.setdefault(vehicle_id, {})[key] = value
    return {vehicle_id: dict(sorted(found.items())) for vehicle_id, found in result.items()}
