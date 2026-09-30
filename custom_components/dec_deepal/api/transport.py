"""Transporte HTTP: una única función para hablar con cualquier pasarela.

Todas las peticiones a la nube pasan por :meth:`DeepalTransport.post`. Así hay
un único sitio donde:

- se ponen las cabeceras que imitan a la app oficial;
- se elige el servidor según el país y la pasarela (intl / ca / sda);
- se traducen los errores del servidor a excepciones (ver ``errors.py``);
- se avisa al registro de depuración de cada intercambio (ver ``debug/``).

Detalle importante: el servidor casi siempre contesta HTTP 200 aunque haya un
error; el error real va dentro del JSON (``"success": false``).
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

import aiohttp

from .endpoints import GATEWAY_CA, GATEWAY_INTL, GATEWAY_SDA
from .errors import (
    DeepalApiError,
    DeepalAuthError,
    DeepalConnectionError,
    error_from_response,
)
from .session import DeepalSession

_LOGGER = logging.getLogger(__name__)

#: Segundos máximos de espera por respuesta HTTP.
REQUEST_TIMEOUT: Final = 30

# Identidad que se presenta al servidor: la de la app Android oficial. Cambiar
# estos valores puede hacer que el servidor rechace las peticiones.
APP_ID: Final = "ca"
APP_TYPE: Final = "Android"
# V1.12.0 (antes V1.11.0): es la versión que usa Deepal Alternative, a quien
# le llegan los SMS de login. Con V1.11.0 el servidor aceptaba la petición de
# código por SMS pero el SMS no llegaba (el correo sí). Ver b4 en CHANGELOG.
APP_VERSION: Final = "V1.12.0"
DEVICE_TYPE: Final = "samsung"
OS_VERSION: Final = "9"
USER_AGENT: Final = "okhttp/4.12.0"


@dataclass(frozen=True, slots=True)
class CountryProfile:
    """Lo que el cliente necesita saber del país de la cuenta.

    Se construye a partir de ``countries/countries.yaml`` (ver
    ``registries/countries.py``). El cliente no lee el YAML directamente para
    no depender de ficheros ni de Home Assistant.
    """

    country_id: str  # id interno ("es")
    sales_country: str  # código que espera el servidor ("ES")
    dial_code: str  # prefijo telefónico sin "+" ("34")
    api_language: str  # cabecera "language" ("en_US")
    intl_base_url: str
    ca_base_url: str
    sda_base_url: str


#: Firma de la función que recibe cada intercambio para depuración. Recibe un
#: dict con: kind, gateway, path, request, response, error, duration_ms.
ExchangeHook = Callable[[dict[str, Any]], None]


class DeepalTransport:
    """Envía peticiones POST JSON a la nube de Deepal."""

    def __init__(
        self,
        http: aiohttp.ClientSession,
        country: CountryProfile,
        session: DeepalSession,
        *,
        on_exchange: ExchangeHook | None = None,
    ) -> None:
        """Crea el transporte.

        Args:
            http: sesión aiohttp compartida de Home Assistant.
            country: perfil del país de la cuenta.
            session: sesión de la cuenta. Se guarda por referencia: si la
                cuenta renueva los tokens, el transporte los usa al momento.
            on_exchange: función opcional que recibe cada intercambio
                (petición + respuesta) para el registro de depuración.
        """
        self._http = http
        self.country = country
        self.session = session
        self.on_exchange = on_exchange

    # ------------------------------------------------------------------
    # Cabeceras
    # ------------------------------------------------------------------

    def _headers(self, *, with_auth: bool, with_tsp: bool) -> dict[str, str]:
        """Cabeceras idénticas a las de la app oficial.

        Args:
            with_auth: añade ``authorization`` si hay sesión. Si no, la
                cabecera no se envía en absoluto (ni siquiera vacía).
            with_tsp: añade ``X-Tsp-User-Token`` = access token. Lo exige la
                pasarela CA (MQTT). Comprobado ✅ que debe ser el *access token*
                y no el ``cac_token``.
        """
        # Sin sesión (pasos de login) NO se envía "authorization": la app
        # oficial no la manda. La versión anterior mandaba una cadena vacía.
        headers = {
            "appid": APP_ID,
            "language": self.country.api_language,
            "appversion": APP_VERSION,
            "apptype": APP_TYPE,
            "devicetype": DEVICE_TYPE,
            "deviceid": self.session.device_id,
            "selectcountry": self.country.sales_country,
            "x-os-version": OS_VERSION,
            "accept-language": self.country.api_language,
            "content-type": "application/json; charset=UTF-8",
            "user-agent": USER_AGENT,
        }
        if with_auth and self.session.access_token:
            headers["authorization"] = self.session.authorization
        if with_tsp:
            if not self.session.access_token:
                raise DeepalAuthError("La pasarela CA necesita una sesión iniciada")
            headers["X-Tsp-User-Token"] = self.session.access_token
        return headers

    def _base_url(self, gateway: str) -> str:
        """URL del servidor de la pasarela pedida, según el país."""
        if gateway == GATEWAY_CA:
            return self.country.ca_base_url
        if gateway == GATEWAY_SDA:
            return self.country.sda_base_url
        return self.country.intl_base_url

    # ------------------------------------------------------------------
    # Petición
    # ------------------------------------------------------------------

    async def post(
        self,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        gateway: str = GATEWAY_INTL,
        with_auth: bool = True,
    ) -> Any:
        """Envía un POST y devuelve el campo ``data`` de la respuesta.

        Args:
            path: ruta del endpoint (ver ``endpoints.py``).
            payload: cuerpo JSON. ``None`` equivale a ``{}``.
            gateway: ``"intl"`` (por defecto), ``"ca"`` o ``"sda"``. La
                pasarela CA añade automáticamente ``X-Tsp-User-Token``.
            with_auth: ``False`` solo para los pasos de login.

        Raises:
            DeepalConnectionError: no se pudo conectar.
            DeepalAuthError: sesión no válida (HTTP 401/403 o código de sesión).
            DeepalApiError: cualquier otro error del servidor.
        """
        url = f"{self._base_url(gateway)}{path}"
        body = json.dumps(payload or {}, separators=(",", ":"), ensure_ascii=False)
        headers = self._headers(with_auth=with_auth, with_tsp=gateway == GATEWAY_CA)
        started = time.monotonic()
        response_body: Any = None
        error: Exception | None = None

        try:
            try:
                async with self._http.post(
                    url,
                    data=body,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ) as response:
                    if response.status in (401, 403):
                        raise DeepalAuthError(
                            f"HTTP {response.status} en {path}", status=response.status
                        )
                    try:
                        response_body = await response.json(content_type=None)
                    except (json.JSONDecodeError, aiohttp.ContentTypeError) as err:
                        raise DeepalApiError(
                            f"Respuesta no JSON en {path} (HTTP {response.status})",
                            status=response.status,
                        ) from err
                    status = response.status
            except (aiohttp.ClientError, TimeoutError) as err:
                raise DeepalConnectionError(f"No se pudo conectar ({path}): {err}") from err

            if not isinstance(response_body, dict):
                raise DeepalApiError(f"Respuesta inesperada en {path}", status=status)

            if response_body.get("success") is False:
                raise error_from_response(
                    path,
                    response_body.get("code"),
                    str(response_body.get("msg") or response_body.get("message") or ""),
                    status,
                )
            if status >= 400:
                raise DeepalApiError(
                    f"HTTP {status} en {path}", code=response_body.get("code"), status=status
                )
            return response_body.get("data")
        except Exception as err:
            error = err
            raise
        finally:
            self._notify(gateway, path, payload, response_body, error, started)

    def _notify(
        self,
        gateway: str,
        path: str,
        request: dict[str, Any] | None,
        response: Any,
        error: Exception | None,
        started: float,
    ) -> None:
        """Pasa el intercambio al registro de depuración, si hay uno.

        Nunca deja que un fallo del registro rompa la petición real.
        """
        duration_ms = int((time.monotonic() - started) * 1000)
        if error is None:
            _LOGGER.debug("POST %s OK (%s ms)", path, duration_ms)
        else:
            _LOGGER.debug("POST %s falló (%s ms): %s", path, duration_ms, error)
        if self.on_exchange is None:
            return
        try:
            self.on_exchange(
                {
                    "kind": "http",
                    "gateway": gateway,
                    "path": path,
                    "request": request or {},
                    "response": response,
                    "error": None if error is None else f"{type(error).__name__}: {error}",
                    "duration_ms": duration_ms,
                }
            )
        except Exception:  # noqa: BLE001 - la depuración nunca debe romper nada
            _LOGGER.exception("El registro de depuración falló")
