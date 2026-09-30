"""Asistente de opciones ("Configurar" en la ficha de la integración).

Menú con tres apartados:

- **Apariencia** (``appearance`` → ``appearance_details``): modelo, versión y
  color de cada coche. Decide la "Foto DEC" y qué entidades se crean (p. ej.
  ventilación de asientos solo en versiones que la tienen).
- **Control con PIN** (``pin``): activar puertas/ventanillas/maletero. El PIN
  se **comprueba contra el servidor** antes de guardarlo: un PIN incorrecto o
  de otra cuenta se rechaza aquí mismo.
- **Avanzado** (``advanced``): intervalo de lectura y modo depuración.

Guardar cualquier apartado recarga la integración para aplicar los cambios.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState, ConfigFlowResult, OptionsFlow
from homeassistant.helpers import selector

from .api.errors import DeepalConnectionError, DeepalError, DeepalPinError, DeepalRateLimitError
from .const import (
    ARM_SECONDS_CHOICES,
    DEFAULT_ARM_NOTIFY,
    DEFAULT_ARM_SECONDS,
    DEFAULT_PIN_MODE,
    DEFAULT_SCAN_MINUTES,
    MAX_SCAN_MINUTES,
    MIN_SCAN_MINUTES,
    OPT_APPEARANCE,
    OPT_ARM_NOTIFY,
    OPT_ARM_SECONDS,
    OPT_DEBUG,
    OPT_MODEL,
    OPT_PIN,
    OPT_PIN_ENABLED,
    OPT_PIN_MODE,
    OPT_SCAN_MINUTES,
    PIN_MODE_ARMED,
    PIN_MODE_DIRECT,
)
from .appearance import details_schema, model_schema, needs_details, updated_options
from .runtime import DecDeepalRuntime

_LOGGER = logging.getLogger(__name__)

_VEHICLE = "vehicle"


def _select(options: list[selector.SelectOptionDict]) -> selector.SelectSelector:
    """Desplegable sencillo."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN)
    )


class DecDeepalOptionsFlow(OptionsFlow):
    """Opciones de una cuenta."""

    def __init__(self) -> None:
        self._vehicle_id: str | None = None
        self._model_id: str | None = None

    @property
    def _runtime(self) -> DecDeepalRuntime:
        """Objetos vivos de la cuenta (la integración debe estar cargada)."""
        return self.config_entry.runtime_data

    def _save(self, changes: dict[str, Any]) -> ConfigFlowResult:
        """Guarda las opciones actuales + los cambios de este apartado."""
        return self.async_create_entry(data={**self.config_entry.options, **changes})

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Menú principal.

        Las opciones necesitan la integración cargada (para comprobar el PIN
        y conocer los coches). Si no lo está, se avisa en vez de fallar.
        """
        if self.config_entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="not_loaded")
        return self.async_show_menu(step_id="init", menu_options=["appearance", "pin", "advanced"])

    # ------------------------------------------------------------------
    # Apariencia
    # ------------------------------------------------------------------

    async def async_step_appearance(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Paso 1: qué coche y qué modelo del catálogo.

        Por defecto se propone el modelo ya elegido o, si el coche aún no está
        configurado, el que se reconoció por el nombre que da el servidor.
        """
        runtime = self._runtime
        if user_input is not None:
            self._vehicle_id = user_input.get(_VEHICLE) or next(iter(runtime.vehicles))
            self._model_id = user_input[OPT_MODEL]
            return await self.async_step_appearance_details()

        vehicles = list(runtime.vehicles.values())
        current = vehicles[0]
        default_model = (
            current.model.id
            if current.configured or current.suggested_model is None
            else current.suggested_model.id
        )
        models = runtime.registries.vehicles.for_country(runtime.country.id)
        schema = model_schema(models, default_model).schema.copy()
        if len(vehicles) > 1:
            schema = {
                vol.Required(_VEHICLE, default=current.info.vehicle_id): _select(
                    [
                        selector.SelectOptionDict(
                            value=vehicle.info.vehicle_id, label=vehicle.info.display_name
                        )
                        for vehicle in vehicles
                    ]
                ),
                **schema,
            }
        return self.async_show_form(step_id="appearance", data_schema=vol.Schema(schema))

    async def async_step_appearance_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Paso 2: versión y color (según el modelo elegido)."""
        runtime = self._runtime
        assert self._vehicle_id is not None
        model = runtime.registries.vehicles.get(self._model_id)

        if user_input is not None or not needs_details(model):
            return self.async_create_entry(
                data=updated_options(self.config_entry.options, self._vehicle_id, model, user_input)
            )

        stored = self.config_entry.options.get(OPT_APPEARANCE, {}).get(self._vehicle_id, {})
        capabilities = runtime.vehicles[self._vehicle_id].capabilities
        hint = capabilities.trim_hint if capabilities else None
        return self.async_show_form(
            step_id="appearance_details",
            data_schema=details_schema(model, stored, hint),
            description_placeholders={"model": model.name},
        )

    # ------------------------------------------------------------------
    # PIN
    # ------------------------------------------------------------------

    async def async_step_pin(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Bloque de control remoto con PIN (desactivado por defecto)."""
        options = self.config_entry.options
        errors: dict[str, str] = {}

        if user_input is not None:
            enabled = bool(user_input.get(OPT_PIN_ENABLED))
            pin = str(user_input.get(OPT_PIN) or "").strip()
            if not enabled:
                # Desactivar siempre empieza de cero la próxima vez.
                return self._save(
                    {
                        OPT_PIN_ENABLED: False,
                        OPT_PIN: None,
                        OPT_PIN_MODE: DEFAULT_PIN_MODE,
                        OPT_ARM_SECONDS: DEFAULT_ARM_SECONDS,
                        OPT_ARM_NOTIFY: DEFAULT_ARM_NOTIFY,
                    }
                )
            if not pin:
                errors[OPT_PIN] = "pin_required"
            else:
                error = await self._verify_pin(pin, changed=pin != options.get(OPT_PIN))
                if error:
                    errors["base"] = error
                else:
                    return self._save(
                        {
                            OPT_PIN_ENABLED: True,
                            OPT_PIN: pin,
                            OPT_PIN_MODE: user_input[OPT_PIN_MODE],
                            OPT_ARM_SECONDS: int(user_input[OPT_ARM_SECONDS]),
                            OPT_ARM_NOTIFY: bool(user_input[OPT_ARM_NOTIFY]),
                        }
                    )

        schema = vol.Schema(
            {
                vol.Required(
                    OPT_PIN_ENABLED, default=bool(options.get(OPT_PIN_ENABLED, False))
                ): selector.BooleanSelector(),
                vol.Optional(
                    OPT_PIN, description={"suggested_value": options.get(OPT_PIN)}
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Required(
                    OPT_PIN_MODE, default=options.get(OPT_PIN_MODE, DEFAULT_PIN_MODE)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[PIN_MODE_DIRECT, PIN_MODE_ARMED],
                        translation_key="pin_mode",
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    OPT_ARM_SECONDS, default=str(options.get(OPT_ARM_SECONDS, DEFAULT_ARM_SECONDS))
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[str(seconds) for seconds in ARM_SECONDS_CHOICES],
                        translation_key="arm_seconds",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    OPT_ARM_NOTIFY, default=bool(options.get(OPT_ARM_NOTIFY, DEFAULT_ARM_NOTIFY))
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="pin", data_schema=schema, errors=errors)

    async def _verify_pin(self, pin: str, *, changed: bool) -> str | None:
        """Comprueba el PIN contra el servidor.

        Solo si es nuevo o distinto del guardado (no se gastan intentos al
        volver a guardar el mismo). Si va bien, el ``rcToken`` queda en caché
        y el primer comando no tiene que pedir otro.

        Returns:
            ``None`` si es válido, o la clave del error.
        """
        if not changed:
            return None
        try:
            await self._runtime.commands.check_pin(pin)
        except DeepalRateLimitError:
            return "pin_rate_limited"
        except DeepalPinError:
            return "pin_invalid"
        except DeepalConnectionError:
            return "cannot_connect"
        except DeepalError as err:
            _LOGGER.debug("Comprobación de PIN fallida: %s", err)
            return "pin_invalid"
        return None

    # ------------------------------------------------------------------
    # Avanzado
    # ------------------------------------------------------------------

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Intervalo de lectura y modo depuración."""
        options = self.config_entry.options
        if user_input is not None:
            return self._save(
                {
                    OPT_SCAN_MINUTES: int(user_input[OPT_SCAN_MINUTES]),
                    OPT_DEBUG: bool(user_input[OPT_DEBUG]),
                }
            )
        schema = vol.Schema(
            {
                vol.Required(
                    OPT_SCAN_MINUTES, default=options.get(OPT_SCAN_MINUTES, DEFAULT_SCAN_MINUTES)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_SCAN_MINUTES,
                        max=MAX_SCAN_MINUTES,
                        step=1,
                        unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    OPT_DEBUG, default=bool(options.get(OPT_DEBUG, False))
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="advanced", data_schema=schema)
