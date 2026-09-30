"""Inicio de sesión con código (SMS o correo) y renovación de la sesión.

Flujo completo, verificado ✅ en España:

1. Pedir código: :meth:`DeepalAuth.send_sms_code` o :meth:`DeepalAuth.send_email_code`.
2. Entrar con el código: :meth:`DeepalAuth.login_sms` o :meth:`DeepalAuth.login_email`.
   En este paso se genera el par de claves RSA propio y se manda la pública
   (``pubKey``). La privada queda en la sesión: sin ella no se pueden firmar
   comandos.
3. Más adelante, renovar la sesión sin pedir código: :meth:`DeepalAuth.refresh`.

El correo, el móvil y el PIN nunca viajan en claro: se cifran con la clave
pública de la app (``crypto.encrypt_value``).
"""

from __future__ import annotations

from typing import Any

from . import endpoints
from .crypto import encrypt_value, generate_keypair
from .errors import DeepalAuthError
from .session import DeepalSession
from .transport import DeepalTransport


class DeepalAuth:
    """Operaciones de autenticación sobre un transporte."""

    def __init__(self, transport: DeepalTransport) -> None:
        self._transport = transport

    @property
    def session(self) -> DeepalSession:
        """La sesión que se está rellenando / renovando."""
        return self._transport.session

    # ------------------------------------------------------------------
    # Pedir código
    # ------------------------------------------------------------------

    async def send_sms_code(self, mobile: str) -> None:
        """Pide un código por SMS al móvil indicado (sin prefijo de país)."""
        await self._transport.post(
            endpoints.SEND_SMS_CODE,
            {
                "countryCode": self._transport.country.dial_code,
                "mobile": encrypt_value(mobile.strip()),
            },
            with_auth=False,
        )

    async def send_email_code(self, email: str) -> None:
        """Pide un código por correo electrónico."""
        await self._transport.post(
            endpoints.SEND_EMAIL_CODE,
            {"type": "0", "email": encrypt_value(email.strip())},
            with_auth=False,
        )

    # ------------------------------------------------------------------
    # Entrar con el código
    # ------------------------------------------------------------------

    async def login_sms(self, mobile: str, code: str) -> DeepalSession:
        """Completa el login con móvil + código SMS."""
        private_pem, public_body = generate_keypair()
        data = await self._transport.post(
            endpoints.LOGIN_BY_SMS_CODE,
            {
                "authCode": code.strip(),
                "countryCode": self._transport.country.dial_code,
                "mobile": encrypt_value(mobile.strip()),
                "salesCountry": self._transport.country.sales_country,
                "pubKey": public_body,
            },
            with_auth=False,
        )
        return self._store_login(data, private_pem)

    async def login_email(self, email: str, code: str) -> DeepalSession:
        """Completa el login con correo + código."""
        private_pem, public_body = generate_keypair()
        data = await self._transport.post(
            endpoints.LOGIN_BY_EMAIL_CODE,
            {
                "authCode": code.strip(),
                "salesCountry": self._transport.country.sales_country,
                "email": encrypt_value(email.strip()),
                "pubKey": public_body,
            },
            with_auth=False,
        )
        return self._store_login(data, private_pem)

    def _store_login(self, data: Any, private_pem: str) -> DeepalSession:
        """Copia la respuesta del login a la sesión (modificándola en sitio).

        Se modifica la misma instancia que usa el transporte, para que las
        peticiones siguientes (lista de vehículos) ya vayan autenticadas.
        """
        if not isinstance(data, dict) or not data.get("token"):
            raise DeepalAuthError("El login no devolvió un token de acceso")
        session = self.session
        session.access_token = str(data["token"])
        session.refresh_token = data.get("refreshToken")
        session.cac_token = data.get("cacToken")
        session.user_id = _optional_str(data.get("userId"))
        session.ca_user_id = _optional_str(data.get("caUserId"))
        session.cac_user_id = _optional_str(data.get("cacUserId"))
        session.private_key_pem = private_pem
        return session

    # ------------------------------------------------------------------
    # Renovar
    # ------------------------------------------------------------------

    async def refresh(self) -> DeepalSession:
        """Renueva el access token con el refresh token guardado.

        Los campos que el servidor no devuelve se conservan (algunas
        respuestas no traen ``cacToken`` ni ``userId``).

        Raises:
            DeepalAuthError: no hay refresh token o el servidor lo rechaza.
        """
        session = self.session
        if not session.refresh_token:
            raise DeepalAuthError("No hay refresh token para renovar la sesión")

        data = await self._transport.post(
            endpoints.REFRESH_TOKEN, {"refreshToken": session.refresh_token}
        )
        if not isinstance(data, dict) or not data.get("token"):
            raise DeepalAuthError("La renovación no devolvió un token de acceso")

        session.access_token = str(data["token"])
        session.refresh_token = data.get("refreshToken") or session.refresh_token
        session.cac_token = data.get("cacToken") or session.cac_token
        session.user_id = _optional_str(data.get("userId")) or session.user_id
        session.ca_user_id = _optional_str(data.get("caUserId")) or session.ca_user_id
        session.cac_user_id = _optional_str(data.get("cacUserId")) or session.cac_user_id
        return session


def _optional_str(value: Any) -> str | None:
    """Convierte a texto si hay valor; ``None`` si no."""
    return None if value is None or value == "" else str(value)
