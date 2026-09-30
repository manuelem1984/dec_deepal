"""Pruebas de api/crypto.py."""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from custom_components.dec_deepal.api import crypto


def test_app_public_key_loads() -> None:
    """La clave pública de la app es un DER válido (no se rompió al partirla)."""
    key = serialization.load_der_public_key(base64.b64decode(crypto.APP_PUBLIC_KEY_DER_B64))
    assert key.key_size == 2048


def test_encrypt_value_returns_base64() -> None:
    encrypted = crypto.encrypt_value("600000000")
    assert len(base64.b64decode(encrypted)) == 256


def test_keypair_and_private_decrypt_roundtrip() -> None:
    private_pem, public_body = crypto.generate_keypair()
    assert "BEGIN" not in public_body and public_body.endswith("\n")
    public_key = serialization.load_pem_public_key(
        f"-----BEGIN PUBLIC KEY-----\n{public_body}-----END PUBLIC KEY-----\n".encode()
    )
    ciphertext = base64.b64encode(public_key.encrypt(b"SERIAL123", padding.PKCS1v15())).decode()
    assert crypto.decrypt_with_private_key(private_pem, ciphertext) == "SERIAL123"


def test_mqtt_roundtrip() -> None:
    services = [{"service_code": "car_condition", "params": {"soc": 80}}]
    secret = "0123456789abcdef"
    encrypted = crypto.mqtt_encrypt(services, secret, "did_123")
    assert crypto.mqtt_decrypt(encrypted, secret, "did_123") == services


def test_canonical_string_rules() -> None:
    payload = {"command": "air", "sign": "x", "b": True, "a": None, "c": 5}
    assert crypto.canonical_string(payload) == "a=null&b=true&c=5"


def test_sign_payload_verifies() -> None:
    private_pem, _ = crypto.generate_keypair()
    payload = {"command": "air", "enabled": True, "vehicleId": "1"}
    signature = base64.b64decode(crypto.sign_payload(private_pem, payload))
    private_key = serialization.load_pem_private_key(private_pem.encode(), password=None)
    private_key.public_key().verify(
        signature,
        crypto.canonical_string(payload).encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
