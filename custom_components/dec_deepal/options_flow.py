"""Asistente de opciones ("Configurar" en la ficha de la integración).

Menú con siete apartados:

- **Apariencia** (``appearance`` → ``appearance_details``): modelo, versión y
  color de cada coche. Decide la "Imagen DEC" y qué entidades se crean (p. ej.
  ventilación de asientos solo en versiones que la tienen).
- **Control con PIN** (``pin``): activar puertas/ventanillas/maletero. El PIN
  se **comprueba contra el servidor** antes de guardarlo: un PIN incorrecto o
  de otra cuenta se rechaza aquí mismo.
- **Avisos** (``alerts``): a qué móviles avisar y de qué (carga, testigos,
  neumáticos, pila del mando, mantenimiento).
- **Mantenimiento** (``maintenance`` → ``maintenance_menu`` →
  ``maintenance_setup`` / ``maintenance_register``): la ficha de cada coche.
  No se guarda en las opciones sino en el almacén de ``alerts.py``, para que
  registrar una revisión no recargue la integración.
- **ITV** (``itv`` → ``itv_setup``) y **Seguro** (``insurance`` →
  ``insurance_setup``): la ficha de cada coche, guardada igual que la de
  mantenimiento (``documents.py``).
- **Avanzado** (``advanced``): intervalo de lectura y modo depuración.

Guardar un apartado recarga la integración para aplicar los cambios (salvo
registrar una revisión o corregir la ficha de mantenimiento).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState, ConfigFlowResult, OptionsFlow
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .api.errors import DeepalConnectionError, DeepalError, DeepalPinError, DeepalRateLimitError
from .alert_rules import ALERT_ITV, ALERT_TYPES, enabled_types, format_date, maintenance_text
from .const import (
    ARM_SECONDS_CHOICES,
    DEFAULT_ALERT_PERSISTENT,
    DEFAULT_ARM_NOTIFY,
    DEFAULT_ARM_SECONDS,
    DEFAULT_PIN_MODE,
    DEFAULT_SCAN_MINUTES,
    MAX_SCAN_MINUTES,
    MIN_SCAN_MINUTES,
    OPT_ALERT_KNOWN,
    OPT_ALERT_PERSISTENT,
    OPT_ALERT_TARGETS,
    OPT_ALERT_TYPES,
    OPT_ALERTS,
    OPT_APPEARANCE,
    OPT_ARM_NOTIFY,
    OPT_ARM_SECONDS,
    OPT_DEBUG,
    OPT_WAKE,
    DEFAULT_WAKE,
    OPT_MANUAL_URLS,
    OPT_MODEL,
    OPT_PIN,
    OPT_PIN_ENABLED,
    OPT_PIN_MODE,
    OPT_SCAN_MINUTES,
    PIN_MODE_ARMED,
    PIN_MODE_DIRECT,
)
from .appearance import details_schema, model_schema, needs_details, updated_options
from .documents import (
    INSURANCE_KINDS,
    InsuranceRecord,
    ItvRecord,
    itv_calculated,
)
from .maintenance import MaintenanceRecord
from .manual import is_valid_url
from .runtime import DecDeepalRuntime

_LOGGER = logging.getLogger(__name__)

_VEHICLE = "vehicle"
#: Campo "Enlace del manual" de Avanzado (se guarda en OPT_MANUAL_URLS).
_MANUAL_URL = "manual_url"

# Campos de los formularios de mantenimiento (no son opciones guardadas).
_MT_ENABLED = "maintenance_enabled"
_MT_SERVICES_DONE = "services_done"
_MT_LAST_DATE = "last_date"
_MT_LAST_KM = "last_km"
_MT_INTERVAL_KM = "interval_km"
_MT_INTERVAL_MONTHS = "interval_months"
_MT_SERVICE_DATE = "service_date"
_MT_SERVICE_KM = "service_km"

# Campos de los formularios de ITV y de seguro.
_ENABLED = "enabled"
_ITV_REGISTRATION = "registration_date"
_ITV_LAST = "last_itv_date"
_ITV_NEXT = "next_itv_date"
_INS_COMPANY = "company"
_INS_POLICY = "policy"
_INS_KIND = "insurance_kind"
_INS_RENEWAL = "renewal_date"
_INS_NOTICE = "notice_days"
_INS_PHONE_ASSISTANCE = "phone_assistance"
_INS_PHONE_COMPANY = "phone_company"

#: Servicios de "notify" que no son un destino (son genéricos de HA).
_NOT_A_TARGET = frozenset({"send_message", "persistent_notification", "notify"})


def _number(minimum: float, maximum: float, step: float, unit: str | None = None):  # noqa: ANN202
    """Casilla numérica.

    La unidad solo se pasa si la hay: Home Assistant rechaza ``None``.
    """
    config = selector.NumberSelectorConfig(
        min=minimum, max=maximum, step=step, mode=selector.NumberSelectorMode.BOX
    )
    if unit:
        config["unit_of_measurement"] = unit
    return selector.NumberSelector(config)


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
        menu = ["appearance", "pin", "alerts", "maintenance", "itv", "insurance", "advanced"]
        if not self._runtime.alerts.itv_available:
            menu.remove("itv")  # la ITV solo existe en los países que la tienen dada de alta
        return self.async_show_menu(step_id="init", menu_options=menu)

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
    # Avisos
    # ------------------------------------------------------------------

    async def async_step_alerts(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """A qué móviles avisar y de qué.

        Los destinos son los servicios ``notify.*`` de Home Assistant (cada
        móvil con la app tiene el suyo, ``notify.mobile_app_<nombre>``). Se
        guarda el nombre del servicio, pero se enseña el del dispositivo
        ("iPhone de Manuel"), como en Ajustes → Aplicación móvil.
        """
        stored = self.config_entry.options.get(OPT_ALERTS, {})
        if user_input is not None:
            return self._save(
                {
                    OPT_ALERTS: {
                        OPT_ALERT_TARGETS: list(user_input.get(OPT_ALERT_TARGETS, [])),
                        OPT_ALERT_TYPES: list(user_input.get(OPT_ALERT_TYPES, [])),
                        OPT_ALERT_KNOWN: list(ALERT_TYPES),
                        OPT_ALERT_PERSISTENT: bool(user_input[OPT_ALERT_PERSISTENT]),
                    }
                }
            )

        chosen = list(stored.get(OPT_ALERT_TARGETS, []))
        available = set(self.hass.services.async_services().get("notify", {})) - _NOT_A_TARGET
        # Los móviles primero; los ya elegidos se mantienen aunque hoy no existan.
        targets = sorted(
            available | set(chosen), key=lambda name: (not name.startswith("mobile_app_"), name)
        )
        device_names = self._mobile_device_names()
        schema: dict[Any, Any] = {}
        if targets:
            schema[vol.Optional(OPT_ALERT_TARGETS, default=chosen)] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=name, label=device_names.get(name, f"notify.{name}")
                        )
                        for name in targets
                    ],
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            )
        schema[
            vol.Optional(
                OPT_ALERT_TYPES,
                default=[
                    kind
                    for kind in ALERT_TYPES
                    if kind
                    in enabled_types(stored.get(OPT_ALERT_TYPES), stored.get(OPT_ALERT_KNOWN))
                    and (kind != ALERT_ITV or self._runtime.alerts.itv_available)
                ],
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    kind
                    for kind in ALERT_TYPES
                    if kind != ALERT_ITV or self._runtime.alerts.itv_available
                ],
                translation_key="alert_type",
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
            )
        )
        schema[
            vol.Required(
                OPT_ALERT_PERSISTENT,
                default=bool(stored.get(OPT_ALERT_PERSISTENT, DEFAULT_ALERT_PERSISTENT)),
            )
        ] = selector.BooleanSelector()
        return self.async_show_form(step_id="alerts", data_schema=vol.Schema(schema))

    def _mobile_device_names(self) -> dict[str, str]:
        """Nombre visible de cada móvil: ``{"mobile_app_iphone_de_x": "iPhone de X"}``.

        La app móvil llama a su servicio ``mobile_app_`` + el nombre con que se
        registró el dispositivo, en minúsculas y con guiones bajos. Ese nombre
        es el título de su entrada en Ajustes → Aplicación móvil.
        """
        names: dict[str, str] = {}
        for entry in self.hass.config_entries.async_entries("mobile_app"):
            registered = entry.data.get("device_name") or entry.title
            if registered:
                names[slugify(f"mobile_app_{registered}")] = entry.title or registered
        return names

    # ------------------------------------------------------------------
    # Mantenimiento
    # ------------------------------------------------------------------

    async def async_step_maintenance(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Qué coche (si hay más de uno) y, después, qué hacer."""
        vehicles = self._runtime.vehicles
        if user_input is None and len(vehicles) > 1:
            schema = vol.Schema(
                {
                    vol.Required(_VEHICLE, default=next(iter(vehicles))): _select(
                        [
                            selector.SelectOptionDict(
                                value=vehicle.info.vehicle_id, label=vehicle.info.display_name
                            )
                            for vehicle in vehicles.values()
                        ]
                    )
                }
            )
            return self.async_show_form(step_id="maintenance", data_schema=schema)
        self._vehicle_id = (user_input or {}).get(_VEHICLE) or next(iter(vehicles))
        if self._runtime.alerts.record(self._vehicle_id) is None:
            return await self.async_step_maintenance_setup()
        return await self.async_step_maintenance_menu()

    def _maintenance_placeholders(self) -> dict[str, str]:
        """Nombre del coche y resumen de su próxima revisión."""
        assert self._vehicle_id is not None
        runtime = self._runtime
        language = self.hass.config.language
        current = runtime.alerts.status(self._vehicle_id)
        summary = ""
        if current is not None:
            summary = maintenance_text(
                "overdue" if current.level == "overdue" else "remaining",
                number=current.number,
                days_left=current.days_left,
                km_left=current.km_left,
                due_date=format_date(current.due_date, language),
                due_km=current.due_km,
                language=language,
            )
        return {
            "vehicle": runtime.vehicles[self._vehicle_id].info.display_name,
            "summary": summary,
        }

    async def async_step_maintenance_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Coche con mantenimiento activado: registrar una revisión o corregir."""
        return self.async_show_menu(
            step_id="maintenance_menu",
            menu_options=["maintenance_register", "maintenance_setup"],
            description_placeholders=self._maintenance_placeholders(),
        )

    async def async_step_maintenance_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ficha del coche: última revisión (o matriculación) e intervalo."""
        assert self._vehicle_id is not None
        alerts = self._runtime.alerts
        vehicle = self._runtime.vehicles[self._vehicle_id]
        record = alerts.record(self._vehicle_id)
        plan = vehicle.model.maintenance

        if user_input is not None:
            if not user_input[_MT_ENABLED]:
                await alerts.async_set_record(self._vehicle_id, None)
            else:
                await alerts.async_set_record(
                    self._vehicle_id,
                    MaintenanceRecord(
                        services_done=int(user_input[_MT_SERVICES_DONE]),
                        last_date=date.fromisoformat(user_input[_MT_LAST_DATE]),
                        last_km=int(user_input[_MT_LAST_KM]),
                        interval_km=int(user_input[_MT_INTERVAL_KM]),
                        interval_months=int(user_input[_MT_INTERVAL_MONTHS]),
                        history=list(record.history) if record else [],
                    ),
                )
            # Las entidades de mantenimiento se crean o se borran al arrancar.
            if (record is None) == bool(user_input[_MT_ENABLED]):
                self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
            return self.async_create_entry(data=dict(self.config_entry.options))

        date_key = (
            vol.Required(_MT_LAST_DATE, default=record.last_date.isoformat())
            if record
            else vol.Required(_MT_LAST_DATE)
        )
        schema = vol.Schema(
            {
                vol.Required(_MT_ENABLED, default=True): selector.BooleanSelector(),
                vol.Required(
                    _MT_SERVICES_DONE, default=record.services_done if record else 0
                ): _number(0, 50, 1),
                date_key: selector.DateSelector(),
                vol.Required(_MT_LAST_KM, default=record.last_km if record else 0): _number(
                    0, 2000000, 1, "km"
                ),
                vol.Required(
                    _MT_INTERVAL_KM, default=record.interval_km if record else plan.interval_km
                ): _number(1000, 100000, 500, "km"),
                vol.Required(
                    _MT_INTERVAL_MONTHS,
                    default=record.interval_months if record else plan.interval_months,
                ): _number(1, 60, 1),
            }
        )
        return self.async_show_form(
            step_id="maintenance_setup",
            data_schema=schema,
            description_placeholders=self._maintenance_placeholders(),
        )

    async def async_step_maintenance_register(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Anotar una revisión hecha (por defecto, hoy y con los km actuales)."""
        assert self._vehicle_id is not None
        alerts = self._runtime.alerts
        if user_input is not None:
            await alerts.async_register_service(
                self._vehicle_id,
                date.fromisoformat(user_input[_MT_SERVICE_DATE]),
                int(user_input[_MT_SERVICE_KM]),
            )
            return self.async_create_entry(data=dict(self.config_entry.options))

        odometer = alerts.odometer(self._vehicle_id)
        km_key = (
            vol.Required(_MT_SERVICE_KM, default=round(odometer))
            if odometer is not None
            else vol.Required(_MT_SERVICE_KM)
        )
        schema = vol.Schema(
            {
                vol.Required(
                    _MT_SERVICE_DATE, default=dt_util.now().date().isoformat()
                ): selector.DateSelector(),
                km_key: _number(0, 2000000, 1, "km"),
            }
        )
        return self.async_show_form(
            step_id="maintenance_register",
            data_schema=schema,
            description_placeholders=self._maintenance_placeholders(),
        )

    # ------------------------------------------------------------------
    # ITV y seguro
    # ------------------------------------------------------------------

    def _vehicle_form(self, step_id: str) -> ConfigFlowResult:
        """Formulario para elegir coche (cuando hay más de uno)."""
        vehicles = self._runtime.vehicles
        schema = vol.Schema(
            {
                vol.Required(_VEHICLE, default=next(iter(vehicles))): _select(
                    [
                        selector.SelectOptionDict(
                            value=vehicle.info.vehicle_id, label=vehicle.info.display_name
                        )
                        for vehicle in vehicles.values()
                    ]
                )
            }
        )
        return self.async_show_form(step_id=step_id, data_schema=schema)

    def _done(self, was_enabled: bool, enabled: bool) -> ConfigFlowResult:
        """Cierra un apartado guardado en el almacén (las opciones no cambian).

        Activar o desactivar crea o borra entidades: eso sí recarga.
        """
        if was_enabled != enabled:
            self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
        return self.async_create_entry(data=dict(self.config_entry.options))

    async def async_step_itv(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """ITV: qué coche."""
        vehicles = self._runtime.vehicles
        if user_input is None and len(vehicles) > 1:
            return self._vehicle_form("itv")
        self._vehicle_id = (user_input or {}).get(_VEHICLE) or next(iter(vehicles))
        return await self.async_step_itv_setup()

    async def async_step_itv_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ficha de ITV: matriculación, última ITV y, si se quiere, la próxima a mano."""
        assert self._vehicle_id is not None
        alerts = self._runtime.alerts
        record = alerts.itv_record(self._vehicle_id)

        if user_input is not None:
            enabled = bool(user_input[_ENABLED])
            if not enabled:
                await alerts.async_set_itv(self._vehicle_id, None)
            else:
                last = user_input.get(_ITV_LAST)
                new = ItvRecord(
                    registration_date=date.fromisoformat(user_input[_ITV_REGISTRATION]),
                    last_date=date.fromisoformat(last) if last else None,
                    history=list(record.history) if record else [],
                )
                chosen = user_input.get(_ITV_NEXT)
                # Solo se guarda como "a mano" si no coincide con la calculada.
                if chosen and date.fromisoformat(chosen) != itv_calculated(new, alerts.rules):
                    new.next_override = date.fromisoformat(chosen)
                await alerts.async_set_itv(self._vehicle_id, new)
            return self._done(record is not None, enabled)

        # Si el coche tiene mantenimiento sin revisiones, su fecha es la de matriculación.
        maintenance = alerts.record(self._vehicle_id)
        registration = (
            record.registration_date
            if record
            else maintenance.last_date
            if maintenance and maintenance.services_done == 0
            else None
        )

        def suggested(value: date | None) -> dict[str, Any]:
            return {"suggested_value": value.isoformat()} if value else {}

        schema = vol.Schema(
            {
                vol.Required(_ENABLED, default=True): selector.BooleanSelector(),
                vol.Required(
                    _ITV_REGISTRATION, description=suggested(registration)
                ): selector.DateSelector(),
                vol.Optional(
                    _ITV_LAST, description=suggested(record.last_date if record else None)
                ): selector.DateSelector(),
                vol.Optional(
                    _ITV_NEXT, description=suggested(record.next_override if record else None)
                ): selector.DateSelector(),
            }
        )
        return self.async_show_form(
            step_id="itv_setup",
            data_schema=schema,
            description_placeholders={
                "vehicle": self._runtime.vehicles[self._vehicle_id].info.display_name
            },
        )

    async def async_step_insurance(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Seguro: qué coche."""
        vehicles = self._runtime.vehicles
        if user_input is None and len(vehicles) > 1:
            return self._vehicle_form("insurance")
        self._vehicle_id = (user_input or {}).get(_VEHICLE) or next(iter(vehicles))
        return await self.async_step_insurance_setup()

    async def async_step_insurance_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ficha del seguro: compañía, póliza, tipo, renovación, desistimiento y teléfonos."""
        assert self._vehicle_id is not None
        alerts = self._runtime.alerts
        record = alerts.insurance_record(self._vehicle_id)

        if user_input is not None:
            enabled = bool(user_input[_ENABLED])
            if not enabled:
                await alerts.async_set_insurance(self._vehicle_id, None)
            else:
                await alerts.async_set_insurance(
                    self._vehicle_id,
                    InsuranceRecord(
                        renewal_date=date.fromisoformat(user_input[_INS_RENEWAL]),
                        company=str(user_input.get(_INS_COMPANY) or "").strip(),
                        policy=str(user_input.get(_INS_POLICY) or "").strip(),
                        kind=user_input[_INS_KIND],
                        notice_days=int(user_input[_INS_NOTICE]),
                        phone_assistance=str(user_input.get(_INS_PHONE_ASSISTANCE) or "").strip(),
                        phone_company=str(user_input.get(_INS_PHONE_COMPANY) or "").strip(),
                    ),
                )
            return self._done(record is not None, enabled)

        def text(key: str, value: str, kind: selector.TextSelectorType) -> dict[Any, Any]:
            return {
                vol.Optional(key, description={"suggested_value": value}): selector.TextSelector(
                    selector.TextSelectorConfig(type=kind)
                )
            }

        plain, phone = selector.TextSelectorType.TEXT, selector.TextSelectorType.TEL
        renewal = (
            vol.Required(_INS_RENEWAL, default=record.renewal_date.isoformat())
            if record
            else vol.Required(_INS_RENEWAL)
        )
        schema = vol.Schema(
            {
                vol.Required(_ENABLED, default=True): selector.BooleanSelector(),
                **text(_INS_COMPANY, record.company if record else "", plain),
                **text(_INS_POLICY, record.policy if record else "", plain),
                vol.Required(
                    _INS_KIND, default=record.kind if record else INSURANCE_KINDS[0]
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(INSURANCE_KINDS),
                        translation_key="insurance_kind",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                renewal: selector.DateSelector(),
                vol.Required(
                    _INS_NOTICE,
                    default=record.notice_days if record else alerts.rules.insurance_notice_days,
                ): _number(0, 180, 1),
                **text(_INS_PHONE_ASSISTANCE, record.phone_assistance if record else "", phone),
                **text(_INS_PHONE_COMPANY, record.phone_company if record else "", phone),
            }
        )
        return self.async_show_form(
            step_id="insurance_setup",
            data_schema=schema,
            description_placeholders={
                "vehicle": self._runtime.vehicles[self._vehicle_id].info.display_name
            },
        )

    # ------------------------------------------------------------------
    # Avanzado
    # ------------------------------------------------------------------

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Intervalo de lectura, modo depuración y enlace del manual.

        El enlace del manual es por modelo de coche. Solo se ofrece si todos
        los coches de la cuenta son del mismo modelo (lo normal); se guarda
        únicamente si es distinto del que trae el catálogo.
        """
        options = self.config_entry.options
        models = {
            vehicle.model.id: vehicle.model
            for vehicle in self._runtime.vehicles.values()
            if vehicle.configured
        }
        model = next(iter(models.values())) if len(models) == 1 else None
        manual_urls: dict[str, str] = dict(options.get(OPT_MANUAL_URLS, {}))
        errors: dict[str, str] = {}

        if user_input is not None:
            url = str(user_input.get(_MANUAL_URL) or "").strip()
            if url and not is_valid_url(url):
                errors[_MANUAL_URL] = "invalid_url"
            else:
                if model is not None:
                    if url and url != model.manual_url:
                        manual_urls[model.id] = url
                    else:
                        manual_urls.pop(model.id, None)
                return self._save(
                    {
                        OPT_SCAN_MINUTES: int(user_input[OPT_SCAN_MINUTES]),
                        OPT_DEBUG: bool(user_input[OPT_DEBUG]),
                        OPT_WAKE: bool(user_input[OPT_WAKE]),
                        OPT_MANUAL_URLS: manual_urls,
                    }
                )

        manual_field: dict[Any, Any] = {}
        if model is not None:
            current = manual_urls.get(model.id) or model.manual_url
            manual_field[
                vol.Optional(_MANUAL_URL, description={"suggested_value": current})
            ] = selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
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
                    OPT_WAKE, default=bool(options.get(OPT_WAKE, DEFAULT_WAKE))
                ): selector.BooleanSelector(),
                vol.Required(
                    OPT_DEBUG, default=bool(options.get(OPT_DEBUG, False))
                ): selector.BooleanSelector(),
                **manual_field,
            }
        )
        return self.async_show_form(step_id="advanced", data_schema=schema, errors=errors)
