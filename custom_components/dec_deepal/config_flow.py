"""Asistente de configuración: añadir una cuenta (y volver a iniciar sesión).

Pasos (los que no tienen elección posible se saltan solos):

1. ``user``          → País (de ``countries/countries.yaml``).
2. ``login_method``  → SMS o correo (según el país).
3. ``email`` / ``sms`` → Se pide el código de verificación.
4. ``code``          → Se entra con el código y se piden los vehículos.
5. ``vehicles``      → Qué coches añadir (si la cuenta tiene más de uno).

Se crea **una entrada por cuenta**, con todos sus coches dentro. Deepal solo
permite una sesión activa por cuenta: por eso se recomienda una cuenta
secundaria con el coche compartido (ver README).

Reautenticación: si la sesión deja de valer, Home Assistant avisa y este
mismo asistente se reabre (paso ``reauth``), reutilizando el mismo país y el
mismo identificador de dispositivo.
"""

from __future__ import annotations

import logging
import secrets
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.account import DeepalAccount
from .api.auth import DeepalAuth
from .api.client import DeepalClient
from .api.errors import DeepalConnectionError, DeepalError, DeepalRateLimitError
from .api.models import VehicleInfo
from .api.session import DeepalSession
from .api.transport import DeepalTransport
from .const import (
    CONF_AUTH_CODE,
    CONF_COUNTRY,
    CONF_EMAIL,
    CONF_LOGIN_METHOD,
    CONF_MOBILE,
    CONF_SELECTED_VEHICLES,
    CONF_SESSION,
    CONF_VEHICLES,
    DOMAIN,
    LOGIN_METHOD_SMS,
    NAME,
)
from .registries import RegistryError
from .registries.countries import Country
from .runtime import async_get_registries

_LOGGER = logging.getLogger(__name__)


class DecDeepalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Asistente de alta de una cuenta."""

    VERSION = 1

    def __init__(self) -> None:
        self._country: Country | None = None
        self._method: str | None = None
        self._identifier: str | None = None  # correo o móvil normalizado
        self._device_id: str | None = None  # se reutiliza al reautenticar
        self._transport: DeepalTransport | None = None
        self._vehicles: list[VehicleInfo] = []
        # Función que pide el código (se guarda para poder "Reenviar").
        self._resend: Callable[[DeepalAuth], Awaitable[Any]] | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Asistente de opciones (ver ``options_flow.py``)."""
        from .options_flow import DecDeepalOptionsFlow  # noqa: PLC0415 - evita importación circular

        return DecDeepalOptionsFlow()

    # ------------------------------------------------------------------
    # 1. País
    # ------------------------------------------------------------------

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Elegir país (se salta si solo hay uno activo)."""
        try:
            countries = (await async_get_registries(self.hass)).countries
        except RegistryError as err:
            _LOGGER.error("Catálogo de países con errores: %s", err)
            return self.async_abort(reason="catalog_error")

        enabled = countries.enabled()
        if user_input is not None or len(enabled) == 1:
            country_id = user_input[CONF_COUNTRY] if user_input else enabled[0].id
            self._country = countries.get(country_id)
            return await self.async_step_login_method()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COUNTRY): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=country.id, label=country.name)
                                for country in enabled
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    # ------------------------------------------------------------------
    # 2. Método de acceso
    # ------------------------------------------------------------------

    async def async_step_login_method(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """SMS o correo (se salta si el país solo admite uno)."""
        assert self._country is not None
        methods = self._country.login_methods
        if user_input is not None or len(methods) == 1:
            self._method = user_input[CONF_LOGIN_METHOD] if user_input else methods[0]
            if self._method == LOGIN_METHOD_SMS:
                return await self.async_step_sms()
            return await self.async_step_email()

        return self.async_show_form(
            step_id="login_method",
            data_schema=self._login_method_schema(),
            description_placeholders={"country": self._country.name},
        )

    def _login_method_schema(self) -> vol.Schema:
        """Formulario SMS / correo (por defecto, el último usado)."""
        assert self._country is not None
        methods = self._country.login_methods
        default = self._method if self._method in methods else methods[0]
        return vol.Schema(
            {
                vol.Required(CONF_LOGIN_METHOD, default=default): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(methods),
                        translation_key="login_method",
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )

    # ------------------------------------------------------------------
    # 3. Pedir código
    # ------------------------------------------------------------------

    async def async_step_email(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Pedir el código por correo."""
        if user_input is None:
            return self._email_form()
        email = str(user_input[CONF_EMAIL]).strip().lower()
        self._identifier = email
        self._resend = lambda auth: auth.send_email_code(email)
        error = await self._send_code()
        if error:
            return self._email_form({"base": error})
        return await self.async_step_code_menu()

    async def async_step_sms(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Pedir el código por SMS."""
        assert self._country is not None
        if user_input is None:
            return self._sms_form()
        mobile = self._country.normalize_mobile(str(user_input[CONF_MOBILE]))
        if not self._country.is_valid_mobile(mobile):
            return self._sms_form({CONF_MOBILE: "invalid_mobile"})
        self._identifier = mobile
        self._resend = lambda auth: auth.send_sms_code(mobile)
        error = await self._send_code()
        if error:
            return self._sms_form({"base": error})
        return await self.async_step_code_menu()

    def _email_form(self, errors: dict[str, str] | None = None) -> ConfigFlowResult:
        """Formulario del correo (también para mostrar errores al reenviar)."""
        return self.async_show_form(
            step_id="email",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=self._identifier or vol.UNDEFINED): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
                    )
                }
            ),
            errors=errors or {},
        )

    def _sms_form(self, errors: dict[str, str] | None = None) -> ConfigFlowResult:
        """Formulario del móvil (también para mostrar errores al reenviar)."""
        assert self._country is not None
        return self.async_show_form(
            step_id="sms",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MOBILE, default=self._identifier or vol.UNDEFINED): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEL)
                    )
                }
            ),
            errors=errors or {},
            description_placeholders={
                "prefix": f"+{self._country.dial_code}",
                "digits": str(self._country.mobile_digits or ""),
            },
        )

    async def _send_code(self) -> str | None:
        """Crea el transporte (si hace falta) y pide el código.

        Deja constancia en el registro de Home Assistant (nivel INFO) de que
        el servidor aceptó la petición: si el SMS o el correo no llegan, así
        se sabe que el problema no está en la integración sino en el envío.

        Returns:
            ``None`` si fue bien, o la clave del error a mostrar.
        """
        assert self._country is not None and self._resend is not None
        if self._transport is None:
            self._device_id = self._device_id or secrets.token_hex(16)
            self._transport = DeepalTransport(
                async_get_clientsession(self.hass),
                self._country.profile(),
                DeepalSession(device_id=self._device_id),
            )
        try:
            await self._resend(DeepalAuth(self._transport))
        except DeepalRateLimitError:
            return "too_many_codes"
        except DeepalConnectionError:
            return "cannot_connect"
        except DeepalError as err:
            _LOGGER.warning("Deepal rechazó la petición de código (%s): %s", self._method, err)
            return "send_code_failed"
        _LOGGER.info(
            "Deepal aceptó la petición de código por %s para %s",
            self._method,
            _mask(self._identifier or ""),
        )
        return None

    async def async_step_code_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Tras pedir el código: introducirlo, reenviarlo o cambiar de método.

        Home Assistant no tiene botón "atrás" en los formularios; este menú
        es la forma de volver si el código no llega.
        """
        return self.async_show_menu(
            step_id="code_menu",
            menu_options=["code", "resend_code", "change_method"],
            description_placeholders={"destination": _mask(self._identifier or "")},
        )

    async def async_step_resend_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Volver a pedir el código al mismo destino."""
        error = await self._send_code()
        if error:
            if self._method == LOGIN_METHOD_SMS:
                return self._sms_form({"base": error})
            return self._email_form({"base": error})
        return await self.async_step_code_menu()

    async def async_step_change_method(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Volver a elegir SMS o correo (o corregir el dato)."""
        self._identifier = None
        self._resend = None
        assert self._country is not None
        if len(self._country.login_methods) == 1:
            # Solo hay un método: "cambiar" es volver a escribir el dato.
            return self._sms_form() if self._method == LOGIN_METHOD_SMS else self._email_form()
        return self.async_show_form(
            step_id="login_method",
            data_schema=self._login_method_schema(),
            description_placeholders={"country": self._country.name},
        )

    # ------------------------------------------------------------------
    # 4. Entrar con el código
    # ------------------------------------------------------------------

    async def async_step_code(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Introducir el código recibido."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if self._transport is None or self._identifier is None:
                return self.async_abort(reason="flow_state_lost")
            code = str(user_input[CONF_AUTH_CODE]).strip()
            auth = DeepalAuth(self._transport)
            try:
                if self._method == LOGIN_METHOD_SMS:
                    await auth.login_sms(self._identifier, code)
                else:
                    await auth.login_email(self._identifier, code)
                self._vehicles = await DeepalClient(DeepalAccount(self._transport)).get_vehicles()
            except DeepalRateLimitError:
                errors["base"] = "too_many_codes"
            except DeepalConnectionError:
                errors["base"] = "cannot_connect"
            except DeepalError as err:
                _LOGGER.debug("Login fallido: %s", err)
                errors["base"] = "login_failed"
            else:
                if not self._vehicles:
                    errors["base"] = "no_vehicles"
                else:
                    return await self.async_step_vehicles()

        return self.async_show_form(
            step_id="code",
            data_schema=vol.Schema({vol.Required(CONF_AUTH_CODE): str}),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # 5. Elegir vehículos
    # ------------------------------------------------------------------

    async def async_step_vehicles(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Qué coches añadir (se salta si solo hay uno)."""
        errors: dict[str, str] = {}
        if self.source == SOURCE_REAUTH:
            return await self._finish_reauth()

        if len(self._vehicles) == 1:
            return await self._create_entry(self._vehicles)
        if user_input is not None:
            chosen = set(user_input.get(CONF_SELECTED_VEHICLES) or [])
            selected = [vehicle for vehicle in self._vehicles if vehicle.vehicle_id in chosen]
            if selected:
                return await self._create_entry(selected)
            errors["base"] = "no_vehicle_selected"

        return self.async_show_form(
            step_id="vehicles",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SELECTED_VEHICLES,
                        default=[vehicle.vehicle_id for vehicle in self._vehicles],
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=vehicle.vehicle_id,
                                    label=_vehicle_label(vehicle),
                                )
                                for vehicle in self._vehicles
                            ],
                            multiple=True,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def _create_entry(self, vehicles: list[VehicleInfo]) -> ConfigFlowResult:
        """Crea la entrada de la cuenta."""
        assert self._transport is not None and self._country is not None
        session = self._transport.session
        await self.async_set_unique_id(_account_unique_id(session, vehicles))
        self._abort_if_unique_id_configured()
        title = vehicles[0].display_name if len(vehicles) == 1 else f"{NAME} ({len(vehicles)})"
        return self.async_create_entry(
            title=title,
            data={
                CONF_COUNTRY: self._country.id,
                CONF_LOGIN_METHOD: self._method,
                CONF_SESSION: session.to_dict(),
                CONF_VEHICLES: [vehicle.to_dict() for vehicle in vehicles],
            },
        )

    # ------------------------------------------------------------------
    # Reautenticación
    # ------------------------------------------------------------------

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """La sesión caducó: volver a entrar con la misma cuenta."""
        try:
            countries = (await async_get_registries(self.hass)).countries
            self._country = countries.get(entry_data[CONF_COUNTRY])
        except (RegistryError, KeyError):
            return self.async_abort(reason="catalog_error")
        self._method = entry_data.get(CONF_LOGIN_METHOD)
        self._device_id = (entry_data.get(CONF_SESSION) or {}).get("device_id")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Aviso previo antes de pedir un código nuevo."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_login_method()

    async def _finish_reauth(self) -> ConfigFlowResult:
        """Guarda la sesión nueva, manteniendo los coches ya elegidos."""
        assert self._transport is not None
        entry = self._get_reauth_entry()
        session = self._transport.session
        previous_ids = {item["vehicle_id"] for item in entry.data.get(CONF_VEHICLES, [])}
        kept = [vehicle for vehicle in self._vehicles if vehicle.vehicle_id in previous_ids]
        if not kept:
            return self.async_abort(reason="reauth_account_mismatch")
        await self.async_set_unique_id(_account_unique_id(session, kept))
        self._abort_if_unique_id_mismatch(reason="reauth_account_mismatch")
        return self.async_update_reload_and_abort(
            entry,
            data_updates={
                CONF_SESSION: session.to_dict(),
                CONF_LOGIN_METHOD: self._method,
                CONF_VEHICLES: [vehicle.to_dict() for vehicle in kept],
            },
        )


def _account_unique_id(session: DeepalSession, vehicles: list[VehicleInfo]) -> str:
    """Identificador único de la cuenta.

    Se usa el ``userId`` de Deepal; si el servidor no lo diera, el id del
    primer coche (así no se puede añadir dos veces la misma cuenta).
    """
    return str(session.user_id or vehicles[0].vehicle_id)


def _mask(identifier: str) -> str:
    """Oculta casi todo un correo o móvil: ``m•••@gmail.com``, ``•••••6789``."""
    if "@" in identifier:
        user, _, domain = identifier.partition("@")
        return f"{user[:1]}•••@{domain}"
    return f"•••••{identifier[-4:]}" if len(identifier) > 4 else "•••••"


def _vehicle_label(vehicle: VehicleInfo) -> str:
    """Texto de un coche en la lista: nombre + últimos 6 del VIN."""
    suffix = f" (…{vehicle.vin[-6:]})" if vehicle.vin else ""
    return f"{vehicle.display_name}{suffix}"
