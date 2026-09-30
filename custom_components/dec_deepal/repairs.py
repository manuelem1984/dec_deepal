"""Reparaciones: asistente "Configura tu vehículo".

Mientras un coche no tiene modelo elegido, funciona como "genérico" y aparece
un aviso en **Ajustes → Reparaciones** (lo crea ``__init__.py``). Al pulsar
"Enviar" se abre este asistente:

1. ``init``    → Modelo (por defecto, el que se reconoció por el nombre).
2. ``details`` → Versión y color (se salta si el modelo no tiene).

Al terminar se guardan las opciones; la integración se recarga sola, crea las
entidades que corresponden a ese modelo/versión y el aviso desaparece.

Es lo mismo que Configurar → Apariencia (ambos usan ``appearance.py``).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .appearance import details_schema, model_schema, needs_details, updated_options
from .const import OPT_APPEARANCE, OPT_MODEL
from .registries.vehicles import VehicleModel
from .runtime import DecDeepalConfigEntry, async_get_registries


class VehicleSetupFlow(RepairsFlow):
    """Asistente para elegir modelo, versión y color de un coche."""

    def __init__(self, entry_id: str, vehicle_id: str) -> None:
        self._entry_id = entry_id
        self._vehicle_id = vehicle_id
        self._model: VehicleModel | None = None

    def _entry(self) -> DecDeepalConfigEntry | None:
        return self.hass.config_entries.async_get_entry(self._entry_id)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
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
        models = (
            registries.vehicles.for_country(runtime.country.id)
            if runtime
            else list(registries.vehicles.models.values())
        )
        return self.async_show_form(
            step_id="init",
            data_schema=model_schema(models, suggested or models[0].id),
            description_placeholders={
                "vehicle": context.info.display_name if context else self._vehicle_id,
                "suggestion": (
                    context.suggested_model.name
                    if context and context.suggested_model
                    else "—"
                ),
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
        return self.async_create_entry(data={})


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    """Home Assistant llama aquí al pulsar "Enviar" en el aviso."""
    data = data or {}
    return VehicleSetupFlow(str(data.get("entry_id")), str(data.get("vehicle_id")))
