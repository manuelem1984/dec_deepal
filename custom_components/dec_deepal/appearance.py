"""Formularios comunes para elegir modelo, versión y color de un coche.

Los usan dos sitios, para que se comporten exactamente igual:

- Configurar → **Apariencia del vehículo** (``options_flow.py``).
- El aviso de **Reparaciones** "Configura tu vehículo" (``repairs.py``), que
  aparece mientras un coche no tiene modelo elegido.

Todo coche arranca como **modelo genérico** hasta que el usuario elige su
modelo: así nunca se crean entidades de funciones que su coche no tiene (y
nunca se adivina mal la versión). Ver ``docs/imagenes.md``.

La elección se guarda en ``entry.options["appearance"][vehicle_id]``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

import voluptuous as vol
from homeassistant.helpers import selector

from .const import (
    OPT_APPEARANCE,
    OPT_COLOR,
    OPT_MODEL,
    OPT_TRIM,
    OPT_WHEELS,
    VEHICLE_ISSUE_PREFIX,
)
from .registries.vehicles import VehicleModel

#: Valor de "sin elegir" en los desplegables de versión/color.
NONE_CHOICE: Final = "_ninguno"


def issue_id(vehicle_id: str) -> str:
    """Id del aviso de Reparaciones "Configura tu vehículo" de un coche."""
    return f"{VEHICLE_ISSUE_PREFIX}{vehicle_id}"


def _dropdown(options: list[selector.SelectOptionDict]) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN)
    )


def model_schema(models: list[VehicleModel], default_model: str) -> vol.Schema:
    """Formulario: elegir modelo del catálogo."""
    return vol.Schema(
        {
            vol.Required(OPT_MODEL, default=default_model): _dropdown(
                [selector.SelectOptionDict(value=model.id, label=model.name) for model in models]
            )
        }
    )


def details_schema(
    model: VehicleModel,
    stored: Mapping[str, Any],
    suggested_trim: str | None = None,
) -> vol.Schema:
    """Formulario: versión y color del modelo elegido.

    Args:
        model: modelo elegido en el paso anterior.
        stored: lo guardado antes para este coche (para rellenar por defecto).
        suggested_trim: versión deducida de las capacidades del servidor; se
            propone por defecto si no había nada guardado. Solo es una
            propuesta: el usuario la confirma o la cambia.
    """
    none_option = selector.SelectOptionDict(value=NONE_CHOICE, label="—")
    trim = stored.get(OPT_TRIM) if stored.get(OPT_MODEL) == model.id else None
    trim = trim or suggested_trim
    color = stored.get(OPT_COLOR) if stored.get(OPT_MODEL) == model.id else None
    wheels = stored.get(OPT_WHEELS) if stored.get(OPT_MODEL) == model.id else None
    wheel_field: dict[Any, Any] = {}
    if len(model.wheel_options) > 1:
        # Solo cuenta en las versiones sin llanta fija (lo dice el texto de ayuda).
        wheel_field[
            vol.Required(
                OPT_WHEELS,
                default=wheels if wheels in model.wheel_options else model.wheel_options[0],
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=list(model.wheel_options),
                translation_key="wheels",
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )
    return vol.Schema(
        {
            vol.Required(OPT_TRIM, default=trim if trim in model.trims else NONE_CHOICE): _dropdown(
                [none_option]
                + [
                    selector.SelectOptionDict(value=item.id, label=model.display_name(item.id))
                    for item in model.trims.values()
                ]
            ),
            vol.Required(
                OPT_COLOR, default=color if color in model.colors else NONE_CHOICE
            ): _dropdown(
                [none_option]
                + [
                    selector.SelectOptionDict(value=item.id, label=item.name)
                    for item in model.colors.values()
                ]
            ),
            **wheel_field,
        }
    )


def needs_details(model: VehicleModel) -> bool:
    """¿Tiene sentido el paso de versión/color? (el genérico no tiene)."""
    return bool(model.trims or model.colors)


def updated_options(
    options: Mapping[str, Any],
    vehicle_id: str,
    model: VehicleModel,
    details: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Opciones nuevas con la apariencia de un coche actualizada."""
    details = details or {}
    trim = details.get(OPT_TRIM)
    color = details.get(OPT_COLOR)
    wheels = details.get(OPT_WHEELS)
    appearance = dict(options.get(OPT_APPEARANCE, {}))
    appearance[vehicle_id] = {
        OPT_MODEL: model.id,
        OPT_TRIM: None if trim in (None, NONE_CHOICE) else trim,
        OPT_COLOR: None if color in (None, NONE_CHOICE) else color,
    }
    if wheels in model.wheel_options:
        appearance[vehicle_id][OPT_WHEELS] = wheels
    return {**options, OPT_APPEARANCE: appearance}
