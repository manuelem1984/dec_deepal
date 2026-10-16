"""Asistente de configuración: añadir una cuenta (y volver a iniciar sesión).

Pasos (los que no tienen elección posible se saltan solos):

1. ``user``      → País (de ``countries/countries.yaml``).
2. ``email``     → Correo de la cuenta; se pide el código de verificación.
3. ``code``      → Se entra con el código y se piden los vehículos.
4. ``vehicles``  → Qué coches añadir (si la cuenta tiene más de uno).

Solo se entra con correo electrónico. El acceso con teléfono (SMS) se quitó
en la 2.5.0b4: Deepal dejó de entregar esos SMS en septiembre de 2026.

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
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigFlow,
    ConfigFlowResult,
)
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
    CONF_SELECTED_VEHICLES,
    CONF_SESSION,
    CONF_VEHICLES,
    DOMAIN,
    NAME,
)
from .debug.redact import redact
from .registries import RegistryError
from .registries.countries import Country
from .runtime import async_get_registries

_LOGGER = logging.getLogger(__name__)


class DecDeepalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Asistente de alta de una cuenta."""

    VERSION = 1
    #: 2 = conectores AC/DC desactivados (ver ``async_migrate_entry``).
    MINOR_VERSION = 3

    def __init__(self) -> None:
        self._country: Country | None = None
        self._email: str | None = None
        self._device_id: str | None = None  # se reutiliza al reautenticar
        self._transport: DeepalTransport | None = None
        self._vehicles: list[VehicleInfo] = []

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
            return await self.async_step_email()

        # Por defecto, el país de Home Assistant (Ajustes → Sistema → General).
        home = (self.hass.config.country or "").upper()
        default = next(
            (country.id for country in enabled if country.sales_country == home),
            "es" if any(country.id == "es" for country in enabled) else enabled[0].id,
        )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COUNTRY, default=default): selector.SelectSelector(
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
    # 2. Pedir código
    # ------------------------------------------------------------------

    async def async_step_email(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Pedir el código por correo."""
        if user_input is None:
            return self._email_form()
        self._email = str(user_input[CONF_EMAIL]).strip().lower()
        error = await self._send_code()
        if error:
            return self._email_form({"base": error})
        return await self.async_step_code_menu()

    def _email_form(self, errors: dict[str, str] | None = None) -> ConfigFlowResult:
        """Formulario del correo (también para mostrar errores al reenviar)."""
        return self.async_show_form(
            step_id="email",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=self._email or vol.UNDEFINED): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
                    )
                }
            ),
            errors=errors or {},
        )

    async def _send_code(self) -> str | None:
        """Crea el transporte (si hace falta) y pide el código.

        Deja constancia en el registro de Home Assistant (nivel INFO) de que
        el servidor aceptó la petición: si el correo no llega, así se sabe
        que el problema no está en la integración sino en el envío.

        Returns:
            ``None`` si fue bien, o la clave del error a mostrar.
        """
        assert self._country is not None and self._email is not None
        if self._transport is None:
            self._device_id = self._device_id or secrets.token_hex(16)
            self._transport = DeepalTransport(
                async_get_clientsession(self.hass),
                self._country.profile(),
                DeepalSession(device_id=self._device_id),
                on_exchange=_log_login_exchange,
            )
        try:
            await DeepalAuth(self._transport).send_email_code(self._email)
        except DeepalRateLimitError:
            return "too_many_codes"
        except DeepalConnectionError:
            return "cannot_connect"
        except DeepalError as err:
            _LOGGER.warning("Deepal rechazó la petición de código: %s", err)
            return "send_code_failed"
        _LOGGER.info("Deepal aceptó la petición de código para %s", _mask(self._email))
        return None

    async def async_step_code_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Tras pedir el código: introducirlo, reenviarlo o corregir el correo.

        Home Assistant no tiene botón "atrás" en los formularios; este menú
        es la forma de volver si el código no llega.
        """
        return self.async_show_menu(
            step_id="code_menu",
            menu_options=["code", "resend_code", "change_email"],
            description_placeholders={"destination": _mask(self._email or "")},
        )

    async def async_step_resend_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Volver a pedir el código al mismo correo."""
        error = await self._send_code()
        if error:
            return self._email_form({"base": error})
        return await self.async_step_code_menu()

    async def async_step_change_email(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Volver a escribir el correo (el anterior queda de sugerencia)."""
        return self._email_form()

    # ------------------------------------------------------------------
    # 4. Entrar con el código
    # ------------------------------------------------------------------

    async def async_step_code(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Introducir el código recibido."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if self._transport is None or self._email is None:
                return self.async_abort(reason="flow_state_lost")
            code = str(user_input[CONF_AUTH_CODE]).strip()
            auth = DeepalAuth(self._transport)
            try:
                await auth.login_email(self._email, code)
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
        self._device_id = (entry_data.get(CONF_SESSION) or {}).get("device_id")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Aviso previo antes de pedir un código nuevo."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_email()

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
                CONF_VEHICLES: [vehicle.to_dict() for vehicle in kept],
            },
        )


def _account_unique_id(session: DeepalSession, vehicles: list[VehicleInfo]) -> str:
    """Identificador único de la cuenta.

    Se usa el ``userId`` de Deepal; si el servidor no lo diera, el id del
    primer coche (así no se puede añadir dos veces la misma cuenta).
    """
    return str(session.user_id or vehicles[0].vehicle_id)


def _log_login_exchange(exchange: dict[str, Any]) -> None:
    """Registra (INFO) la respuesta COMPLETA del servidor a cada paso del login.

    Sirve para investigar por qué no llega el correo con el código: el servidor
    puede responder "success: true" pero con un aviso en ``msg`` o ``data``.
    Los datos personales (correo, tokens...) salen ocultos. Busca en el
    registro de Home Assistant: ``DEC Deepal login``.

    Se usa nivel WARNING (y no INFO) a propósito: muchas instalaciones solo
    muestran avisos por defecto, y esto solo ocurre durante el asistente de
    login (pocas líneas). Es informativo, no un error.
    """
    _LOGGER.warning(
        "DEC Deepal login (informativo): %s → respuesta=%s error=%s (%s ms)",
        exchange.get("path"),
        redact(exchange.get("response")),
        exchange.get("error"),
        exchange.get("duration_ms"),
    )


def _mask(email: str) -> str:
    """Oculta casi todo el correo: ``m•••@gmail.com``."""
    user, _, domain = email.partition("@")
    return f"{user[:1]}•••@{domain}" if domain else "•••"


def _vehicle_label(vehicle: VehicleInfo) -> str:
    """Texto de un coche en la lista: nombre + últimos 6 del VIN."""
    suffix = f" (…{vehicle.vin[-6:]})" if vehicle.vin else ""
    return f"{vehicle.display_name}{suffix}"
