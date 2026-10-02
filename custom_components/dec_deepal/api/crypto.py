"""Criptografía que exige la nube de Deepal.

Hay cuatro piezas, todas reconstruidas a partir de la app oficial y probadas
con el coche real (✅) salvo que se indique lo contrario:

1. **Cifrar datos sensibles del login** (correo, móvil, PIN) con la clave
   pública RSA de la app — :func:`encrypt_value`.
2. **Par de claves propio**: al iniciar sesión se genera un par RSA-1024 y se
   envía la mitad pública (``pubKey``). La privada se guarda en la entrada de
   configuración y sirve para dos cosas:

   - descifrar el número de serie que devuelve ``serial-no/get``
     (:func:`decrypt_with_private_key`);
   - firmar cada comando remoto (:func:`sign_payload`).
3. **Cifrado de los mensajes MQTT**: AES-128-CBC con IV = MD5(requestId), sobre
   un texto que a su vez es base64(gzip(JSON)) — :func:`mqtt_decrypt` y
   :func:`mqtt_encrypt`.
4. **Firma de comandos**: RSA-SHA256 (PKCS#1 v1.5) sobre una cadena canónica.

Este módulo no importa Home Assistant.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
from typing import Any, Final

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives import padding as symmetric_padding
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

#: Clave pública RSA (DER en base64) que la app usa para cifrar correo, móvil
#: y PIN antes de enviarlos. Es la misma en todas las regiones conocidas.
APP_PUBLIC_KEY_DER_B64: Final = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAkyhr43cBPTJ3jLiYsmbUwUp74cMJIOju"
    "5vqVzgtuK63Q99qV6iVT8wN5cXlyMtWI2mfOmhIao/fUN821im69MfOHsWXdqQEo5e9v654GPw+b"
    "ju0pCphEPtD1I0VcyS34QkAu04urSun2U1q3Dr2OICLVWSnLa+01ioKxkaB0D209zXcls2eFQpvR"
    "AWm7xxVsoqzSwqp+neu5quOpn+eO/bW0TxcSQ8VZcDEUvadRTLSR0eOWgRuHIBiD2RGqPIPzKCm5"
    "A14q1qhxUZ8U0pmYe0Sx7eMy4RVe2iW7fnjc6pxTUMBkercSL26mevYouuCKqyie+LVQAtGa29RM"
    "l/lyiwIDAQAB"
)

#: Claves que la app NUNCA incluye al calcular la firma de un comando.
SIGNATURE_EXCLUDED_KEYS: Final = frozenset({"sign", "class", "command"})


# ---------------------------------------------------------------------------
# 1. Datos sensibles del login
# ---------------------------------------------------------------------------


def encrypt_value(value: str) -> str:
    """Cifra un valor (correo, móvil o PIN) con la clave pública de la app.

    RSA con relleno PKCS#1 v1.5, resultado en base64. Es lo que el servidor
    espera en los campos ``email``, ``mobile`` y ``safeCode``.
    """
    public_key = serialization.load_der_public_key(
        base64.b64decode(APP_PUBLIC_KEY_DER_B64)
    )
    encrypted = public_key.encrypt(value.encode(), padding.PKCS1v15())
    return base64.b64encode(encrypted).decode()


# ---------------------------------------------------------------------------
# 2. Par de claves propio
# ---------------------------------------------------------------------------


def generate_keypair() -> tuple[str, str]:
    """Genera el par RSA que se registra en el servidor al iniciar sesión.

    Returns:
        ``(clave_privada_pem, clave_publica_para_pubKey)``. La pública va sin
        las líneas ``BEGIN``/``END`` y terminada en salto de línea, que es el
        formato exacto que manda la app en el campo ``pubKey``.
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return private_pem, _public_key_body(private_key.public_key())


def _public_key_body(public_key: rsa.RSAPublicKey) -> str:
    """Devuelve la clave pública en el formato del campo ``pubKey``."""
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    # Solo se quitan las líneas "-----BEGIN/END ...-----": el cuerpo base64
    # es aleatorio y puede contener "END" (p. ej. "...xENDq..."); filtrar por
    # subcadena perdía esa línea y la clave registrada quedaba rota.
    lines = [line for line in public_pem.splitlines() if not line.startswith("-----")]
    return "\n".join(lines) + "\n"


def decode_base64(value: str) -> bytes:
    """Decodifica base64 tolerando saltos de línea y relleno ``=`` ausente."""
    compact = "".join(value.split())
    return base64.b64decode(compact + "=" * ((4 - len(compact) % 4) % 4))


def decrypt_with_private_key(private_key_pem: str, ciphertext_b64: str) -> str:
    """Descifra con nuestra clave privada (RSA PKCS#1 v1.5).

    Se usa para el número de serie cifrado que devuelve ``serial-no/get``
    justo antes de firmar un comando.

    Raises:
        ValueError: si no se puede descifrar (la clave no es la registrada).
    """
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(), password=None
    )
    try:
        plaintext = private_key.decrypt(decode_base64(ciphertext_b64), padding.PKCS1v15())
    except ValueError as err:
        raise ValueError("No se pudo descifrar con la clave privada guardada") from err
    return plaintext.decode().strip()


# ---------------------------------------------------------------------------
# 3. Mensajes MQTT
# ---------------------------------------------------------------------------


def _mqtt_cipher(secret_key: str, request_id: str) -> Cipher:
    """AES-CBC con la clave de la sesión MQTT e IV = MD5(requestId)."""
    iv = hashlib.md5(request_id.encode()).digest()  # noqa: S324 - lo impone el protocolo
    return Cipher(algorithms.AES(secret_key.encode()), modes.CBC(iv))


def mqtt_decrypt(encrypted_b64: str, secret_key: str, request_id: str) -> list[dict[str, Any]]:
    """Descifra el campo ``rs``/``sers`` de un mensaje MQTT.

    Pasos: base64 → AES-CBC → quitar relleno PKCS7 → base64 → gunzip → JSON.
    El resultado es una lista de "servicios" (``{"service_code", "params"}``).
    Si el JSON no es una lista, devuelve lista vacía.
    """
    decryptor = _mqtt_cipher(secret_key, request_id).decryptor()
    padded = decryptor.update(decode_base64(encrypted_b64)) + decryptor.finalize()
    unpadder = symmetric_padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded) + unpadder.finalize()
    decoded = json.loads(gzip.decompress(decode_base64(plaintext.decode().strip())).decode())
    return decoded if isinstance(decoded, list) else []


def mqtt_encrypt(services: list[dict[str, Any]], secret_key: str, request_id: str) -> str:
    """Operación inversa a :func:`mqtt_decrypt` (para pedir el estado)."""
    compressed_b64 = base64.b64encode(
        gzip.compress(
            json.dumps(services, ensure_ascii=False, separators=(",", ":")).encode()
        )
    )
    padder = symmetric_padding.PKCS7(128).padder()
    padded = padder.update(compressed_b64) + padder.finalize()
    encryptor = _mqtt_cipher(secret_key, request_id).encryptor()
    return base64.b64encode(encryptor.update(padded) + encryptor.finalize()).decode()


# ---------------------------------------------------------------------------
# 4. Firma de comandos
# ---------------------------------------------------------------------------


def canonical_string(payload: dict[str, Any]) -> str:
    """Construye la cadena que se firma, igual que la app oficial.

    Reglas:
    - Todas las claves del payload **excepto** ``sign``, ``class`` y ``command``.
    - Ordenadas alfabéticamente.
    - Unidas como ``clave=valor&clave=valor``.
    - Booleanos en minúscula (``true``/``false``); ``None`` como ``null``.
    """
    parts: list[str] = []
    for key in sorted(payload):
        if key in SIGNATURE_EXCLUDED_KEYS:
            continue
        value = payload[key]
        if isinstance(value, bool):
            value = str(value).lower()
        elif value is None:
            value = "null"
        parts.append(f"{key}={value}")
    return "&".join(parts)


def sign_payload(private_key_pem: str, payload: dict[str, Any]) -> str:
    """Firma un payload de comando: RSA-SHA256 (PKCS#1 v1.5) en base64.

    Verificado ✅ con climatización, luces y claxon en un S05 de España.
    """
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(), password=None
    )
    signature = private_key.sign(
        canonical_string(payload).encode(), padding.PKCS1v15(), hashes.SHA256()
    )
    return base64.b64encode(signature).decode()
