"""Excepciones del cliente y clasificación de los códigos de error del servidor.

El servidor de Deepal casi siempre responde HTTP 200 y mete el error dentro
del JSON::

    {"success": false, "code": "APP_1_1_02_004", "msg": "..."}

Este módulo convierte esos códigos en excepciones con significado, para que el
resto de la integración pueda reaccionar bien (renovar la sesión, pedir el PIN,
avisar de que hay que esperar...).

Jerarquía::

    DeepalError
    ├── DeepalConnectionError      sin red, timeout, DNS...
    └── DeepalApiError             el servidor respondió con un error
        ├── DeepalAuthError        sesión caducada o expulsada → renovar
        ├── DeepalRateLimitError   demasiadas peticiones / intentos
        ├── DeepalPinError         problema con el PIN de control remoto
        ├── DeepalSigningError     la clave de firma ya no vale → volver a iniciar sesión
        └── DeepalCommandNotReady  falta algo local para enviar el comando

Este módulo no importa aiohttp ni Home Assistant, para poder probarlo solo.
"""

from __future__ import annotations

from typing import Any, Final


class DeepalError(Exception):
    """Base de todos los errores del cliente."""


class DeepalConnectionError(DeepalError):
    """No se pudo hablar con el servidor (red caída, timeout, DNS...)."""


class DeepalApiError(DeepalError):
    """El servidor respondió, pero con un error.

    Atributos:
        code: código del servidor tal cual (``"APP_1_1_02_004"``), o ``None``.
        status: código HTTP de la respuesta, o ``None``.
    """

    def __init__(
        self,
        message: str,
        *,
        code: Any = None,
        status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = None if code is None else str(code)
        self.status = status


class DeepalAuthError(DeepalApiError):
    """La sesión no es válida: caducó o se inició sesión en otro sitio.

    Deepal solo permite **una sesión activa por cuenta**: si se entra en la
    app oficial con la misma cuenta, el token de Home Assistant deja de valer.
    Lanzar esta excepción (y no la genérica) es lo que permite intentar una
    renovación silenciosa y, si falla, pedir al usuario que vuelva a entrar.
    """


class DeepalRateLimitError(DeepalApiError):
    """El servidor pide esperar: demasiados códigos, peticiones o intentos de PIN."""


class DeepalPinError(DeepalApiError):
    """El PIN de control remoto no es válido, caducó o no existe en la cuenta."""


class DeepalSigningError(DeepalApiError):
    """La clave usada para firmar comandos ya no vale.

    Pasa si la clave privada guardada no corresponde a la registrada en el
    servidor (por ejemplo, tras iniciar sesión desde otro sitio). Solución:
    volver a iniciar sesión en la integración, que genera y registra una nueva.
    """


class DeepalCommandNotReady(DeepalApiError):
    """Falta algo local para poder enviar el comando (clave de firma, PIN...)."""


# ---------------------------------------------------------------------------
# Tablas de códigos conocidos
# ---------------------------------------------------------------------------

#: Códigos que significan "la sesión ya no vale". Los ``APP_1_1_02_00x`` y
#: ``CAC_1_1_01_045`` los usa la app para expulsar sesiones; ``46000`` lo
#: documenta Deepal Alternative (CaErrorCode de la app).
AUTH_ERROR_CODES: Final = frozenset(
    {
        "APP_1_1_02_003",
        "APP_1_1_02_004",
        "APP_1_1_02_005",
        "APP_1_1_02_006",
        "CAC_1_1_01_045",
        "46000",
    }
)

#: Códigos de la pasarela CA (la que da acceso a MQTT) que indican que su
#: token caducó. Se arreglan renovando la sesión y reintentando una vez.
CA_TOKEN_ERROR_CODES: Final = frozenset({"APIGW_-1_7_01_004", "APIGW_1_7_02_001"})

#: Demasiados códigos de verificación pedidos.
RATE_LIMIT_CODE: Final = "CAC_1_1_01_033"

#: Demasiados intentos de PIN: bloqueo temporal en el servidor.
PIN_ATTEMPTS_CODE: Final = "HW_1_1_01_047"

#: El PIN de control caducó (073) o la cuenta no tiene PIN creado (074).
PIN_EXPIRED_CODE: Final = "HW_1_1_01_073"
PIN_NOT_SET_CODE: Final = "HW_1_1_01_074"

#: Al ENVIAR una orden: el coche no la aceptó porque está dormido o sin
#: conexión (observado por Deepal Alternative en un S05 real, 30-09-2026).
COMMAND_ASLEEP_CODE: Final = "APP_1_1_05_001"

#: Respuesta de ``serial-no/get`` cuando la clave de firma no es la registrada.
SIGNING_REJECTED_CODE: Final = "COMMON_1_1_01_001"


def is_auth_error(code: Any, message: str = "") -> bool:
    """Devuelve ``True`` si el error significa "hay que renovar la sesión".

    Cubre tanto códigos estructurados como mensajes de texto libre que el
    servidor envía a veces, por ejemplo ``"APIGW_-1_7_01_004 invalided token"``
    (sí, *invalided*: así lo escribe el servidor).
    """
    normalized_code = "" if code is None else str(code).upper()
    normalized_message = (message or "").lower()

    if "AUTH" in normalized_code:
        return True
    if normalized_code.startswith("401"):
        return True
    if normalized_code in AUTH_ERROR_CODES:
        return True
    return "token" in normalized_message and any(
        word in normalized_message for word in ("invalid", "expired", "caduc")
    )


def error_from_response(
    path: str,
    code: Any,
    message: str,
    status: int | None,
) -> DeepalApiError:
    """Convierte un ``{"success": false, ...}`` en la excepción adecuada.

    Args:
        path: ruta del endpoint (sirve para distinguir casos concretos, como
            el rechazo de la firma, que solo tiene sentido en ``serial-no/get``).
        code: campo ``code`` de la respuesta.
        message: campo ``msg`` (o ``message``) de la respuesta.
        status: código HTTP.
    """
    code_str = "" if code is None else str(code)
    detail = f"{code_str} {message}".strip()

    if code_str == RATE_LIMIT_CODE:
        return DeepalRateLimitError(
            f"Demasiadas peticiones: {detail}", code=code, status=status
        )
    if code_str == PIN_ATTEMPTS_CODE:
        return DeepalRateLimitError(
            f"Demasiados intentos de PIN: {detail}", code=code, status=status
        )
    if code_str in (PIN_EXPIRED_CODE, PIN_NOT_SET_CODE):
        return DeepalPinError(
            f"PIN de control no disponible: {detail}", code=code, status=status
        )
    if code_str == SIGNING_REJECTED_CODE and path.endswith("/serial-no/get"):
        return DeepalSigningError(
            f"Firma de comandos rechazada: {detail}", code=code, status=status
        )
    if is_auth_error(code, message):
        return DeepalAuthError(
            f"Sesión no válida: {detail}", code=code, status=status
        )
    return DeepalApiError(f"Error del servidor en {path}: {detail}", code=code, status=status)
