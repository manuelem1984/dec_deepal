"""Sesión de la cuenta: tokens, identificadores y clave de firma.

Una :class:`DeepalSession` es todo lo que hace falta para seguir hablando con
el servidor sin volver a pedir un código al usuario. Se guarda (como dict) en
``entry.data["session"]`` y se reconstruye al arrancar Home Assistant.

Campos y para qué sirve cada uno:

================  ============================================================
Campo             Uso
================  ============================================================
access_token      Cabecera ``authorization`` de casi todas las peticiones.
refresh_token     Renovar ``access_token`` sin pedir código (``refresh-token``).
cac_token         Se concatena al access token: ``"<access>|<cac>"``.
user_id           Necesario para pedir el token del broker MQTT.
ca_user_id        Guardado por si se necesita; hoy no se usa.
cac_user_id       Guardado por si se necesita; hoy no se usa.
device_id         Identificador de "este teléfono" (aleatorio, fijo por cuenta).
private_key_pem   Clave RSA privada: descifra el nº de serie y firma comandos.
================  ============================================================
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class DeepalSession:
    """Estado de autenticación de una cuenta."""

    device_id: str
    access_token: str = ""
    refresh_token: str | None = None
    cac_token: str | None = None
    user_id: str | None = None
    ca_user_id: str | None = None
    cac_user_id: str | None = None
    private_key_pem: str | None = None

    # -- Serialización (para guardarla en la entrada de configuración) --------

    def to_dict(self) -> dict[str, Any]:
        """Convierte la sesión en un dict apto para ``entry.data``."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeepalSession:
        """Reconstruye la sesión desde ``entry.data["session"]``.

        Ignora claves desconocidas, para que una versión antigua no falle si
        una versión nueva guardó campos adicionales.
        """
        known = {field for field in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{key: value for key, value in data.items() if key in known})

    # -- Cabecera de autorización ---------------------------------------------

    @property
    def authorization(self) -> str:
        """Valor de la cabecera ``authorization`` tal como lo envía la app.

        Si hay ``cac_token`` y el access token aún no lo lleva, se concatenan
        con una barra vertical: ``"<access>|<cac>"``.
        """
        if self.cac_token and "|" not in self.access_token:
            return f"{self.access_token}|{self.cac_token}"
        return self.access_token

    # -- Caducidad ------------------------------------------------------------

    @property
    def expires_at(self) -> int | None:
        """Instante (epoch, segundos) en que caduca el access token, si se sabe.

        El access token es un JWT; su campo ``exp`` indica la caducidad. Si no
        es un JWT o no se puede leer, devuelve ``None`` (caducidad desconocida).
        """
        return jwt_expiry(self.access_token)

    def expires_soon(self, margin_seconds: int = 300) -> bool:
        """``True`` si el token caduca en menos de ``margin_seconds``.

        Con caducidad desconocida devuelve ``False``: en ese caso se renueva
        solo cuando el servidor rechaza el token.
        """
        expires_at = self.expires_at
        return expires_at is not None and time.time() >= expires_at - margin_seconds


def jwt_expiry(token: str | None) -> int | None:
    """Lee el campo ``exp`` de un JWT sin verificar su firma.

    No hace falta verificarla: solo queremos saber *cuándo* caduca nuestro
    propio token para renovarlo un poco antes.
    """
    if not token or token.count(".") < 2:
        return None
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp")
        return int(exp) if exp is not None else None
    except (ValueError, TypeError, AttributeError):
        return None
