"""Reparaciones: asistentes de los avisos de la integración.

- "Configura tu vehículo" (:class:`VehicleSetupFlow`), explicado abajo.
- "Revisa el modelo": el coche dice (por MQTT, ``b.mc``) ser EV o PHEV y está
  configurado como el otro. Abre el mismo asistente, con el modelo detectado
  como sugerencia (lo crea ``__init__.py``).
- "Coche nuevo en tu cuenta" y "Este coche ya no está en tu cuenta"
  (:class:`VehicleAddedFlow`, :class:`VehicleRemovedFlow`): los crea
  ``vehicle_sync.py``. Un solo paso de confirmación.

Configura tu vehículo
---------------------

Mientras un coche no tiene modelo elegido, funciona como "genérico" y aparece
un aviso en **Ajustes → Reparaciones** (lo crea ``__init__.py``). Al pulsar
"Enviar" se abre este asistente:

0. ``init``    → Solo redirige a ``model`` (HA lo llama con datos propios).
1. ``model``   → Modelo (por defecto, el que se reconoció por el nombre).
2. ``details`` → Versión y color (se salta si el modelo no tiene).

Al terminar se guardan las opciones; la integración se recarga sola, crea las
entidades que corresponden a ese modelo/versión y el aviso desaparece.

Es lo mismo que el panel DEC Deepal → Coches → Apariencia (ambos usan ``appearance.py``).
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir

from .api.models import VehicleInfo
from .appearance import details_schema, model_schema, needs_details, updated_options
from .const import CONF_VEHICLES, DOMAIN, OPT_APPEARANCE, OPT_MODEL
from .registries.vehicles import VehicleModel
from .runtime import DecDeepalConfigEntry, async_get_registries
from .vehicle_sync import KIND_ADDED, KIND_REMOVED, add_vehicle, remove_vehicle


class VehicleSetupFlow(RepairsFlow):
    """Asistente para elegir modelo, versión y color de un coche."""

    def __init__(self, entry_id: str, vehicle_id: str, suggested: str | None = None) -> None:
        self._entry_id = entry_id
        self._vehicle_id = vehicle_id
        #: Modelo que dice ser el coche (aviso "el coche dice ser otro modelo").
        self._suggested = suggested
        self._model: VehicleModel | None = None

    def _entry(self) -> DecDeepalConfigEntry | None:
        return self.hass.config_entries.async_get_entry(self._entry_id)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Entrada del asistente: salta directamente al formulario del modelo.

        ¡Ojo! Home Assistant llama a este paso con ``{"issue_id": ...}`` como
        ``user_input`` (no con ``None``). Por eso aquí no se procesa nada: si
        se tratara como un formulario enviado, faltaría el campo ``model`` y el
        asistente fallaría con un error 500 (fallo de la b2-b4).
        """
        return await self.async_step_model()

    async def async_step_model(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Paso 1: modelo."""
        entry = self._entry()
        if entry is None:
            return self.async_abort(reason="entry_not_found")
        registries = await async_get_registries(self.hass)

        if user_input is not None:
            self._model = registries.vehicles.get(user_input[OPT_MODEL])
            if needs_details(self._model):
                return await self.async_step_details()
            return self._save(entry, None)

        # La integración puede no estar cargada (p. ej. sin conexión); en ese
        # caso se ofrecen todos los modelos sin sugerencia.
        runtime = getattr(entry, "runtime_data", None)
        context = runtime.vehicles.get(self._vehicle_id) if runtime else None
        suggested = context.suggested_model.id if context and context.suggested_model else None
        suggested_name = context.suggested_model.name if context and context.suggested_model else "—"
        if self._suggested and self._suggested in registries.vehicles.models:
            suggested = self._suggested
            suggested_name = registries.vehicles.get(suggested).name
        models = (
            registries.vehicles.for_country(runtime.country.id)
            if runtime
            else list(registries.vehicles.models.values())
        )
        return self.async_show_form(
            step_id="model",
            data_schema=model_schema(models, suggested or models[0].id),
            description_placeholders={
                "vehicle": context.info.display_name if context else self._vehicle_id,
                "suggestion": suggested_name,
            },
        )

    async def async_step_details(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Paso 2: versión y color."""
        entry = self._entry()
        if entry is None or self._model is None:
            return self.async_abort(reason="entry_not_found")
        if user_input is not None:
            return self._save(entry, user_input)
        stored = entry.options.get(OPT_APPEARANCE, {}).get(self._vehicle_id, {})
        runtime = getattr(entry, "runtime_data", None)
        context = runtime.vehicles.get(self._vehicle_id) if runtime else None
        hint = context.capabilities.trim_hint if context and context.capabilities else None
        return self.async_show_form(
            step_id="details",
            data_schema=details_schema(self._model, stored, hint),
            description_placeholders={"model": self._model.name},
        )

    def _save(self, entry: DecDeepalConfigEntry, details: dict[str, Any] | None) -> FlowResult:
        """Guarda la elección. Cambiar opciones recarga la integración."""
        assert self._model is not None
        self.hass.config_entries.async_update_entry(
            entry, options=updated_options(entry.options, self._vehicle_id, self._model, details)
        )
        ir.async_delete_issue(self.hass, DOMAIN, f"model_mismatch_{self._vehicle_id}")
        return self.async_create_entry(data={})


class _ConfirmFlow(RepairsFlow):
    """Aviso de un coche de la cuenta que se resuelve con un solo "Enviar"."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Entrada (HA la llama con datos propios): al paso de confirmar."""
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Confirmar."""
        entry = self.hass.config_entries.async_get_entry(str(self._data.get("entry_id")))
        if entry is None:
            return self.async_abort(reason="entry_not_found")
        if user_input is not None:
            self._apply(entry)
            return self.async_create_entry(data={})
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"vehicle": self._vehicle_name(entry)},
        )

    def _vehicle_name(self, entry: Any) -> str:
        raise NotImplementedError

    def _apply(self, entry: Any) -> None:
        raise NotImplementedError


class VehicleAddedFlow(_ConfirmFlow):
    """Añadir a la integración un coche nuevo de la cuenta."""

    def _vehicle_name(self, entry: Any) -> str:
        return VehicleInfo.from_dict(self._data.get("vehicle") or {}).display_name

    def _apply(self, entry: Any) -> None:
        add_vehicle(self.hass, entry, self._data["vehicle"])


class VehicleRemovedFlow(_ConfirmFlow):
    """Quitar de la integración un coche que ya no está en la cuenta."""

    def _vehicle_name(self, entry: Any) -> str:
        for item in entry.data.get(CONF_VEHICLES, []):
            if item.get("vehicle_id") == self._data.get("vehicle_id"):
                return VehicleInfo.from_dict(item).display_name
        return str(self._data.get("vehicle_id"))

    def _apply(self, entry: Any) -> None:
        remove_vehicle(self.hass, entry, str(self._data["vehicle_id"]))


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    """Home Assistant llama aquí al pulsar "Enviar" en el aviso."""
    data = data or {}
    if data.get("kind") == KIND_ADDED:
        return VehicleAddedFlow(data)
    if data.get("kind") == KIND_REMOVED:
        return VehicleRemovedFlow(data)
    return VehicleSetupFlow(str(data.get("entry_id")), str(data.get("vehicle_id")), data.get("suggested"))
