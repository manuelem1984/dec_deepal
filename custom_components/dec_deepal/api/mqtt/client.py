"""Una lectura completa de telemetría por MQTT (conectar, pedir, desconectar).

No se mantiene una conexión permanente: en cada actualización se abre, se pide
el estado y se cierra. Es lo que está verificado ✅ y evita problemas de
reconexión. Duración típica: 2-6 segundos.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import logging
import ssl
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final

from ..crypto import mqtt_decrypt, mqtt_encrypt
from . import protocol
from .topics import MqttConnection

_LOGGER = logging.getLogger(__name__)

#: Segundos máximos para abrir la conexión y recibir CONNACK/SUBACK.
CONNECT_TIMEOUT: Final = 15
#: Segundos máximos para recibir el estado completo tras el login.
TELEMETRY_TIMEOUT: Final = 18

#: "service_code" cuyos parámetros forman el estado del coche. Lo que llegue
#: con otro código se guarda aparte (``unknown_services``) para investigarlo.
KNOWN_SERVICE_CODES: Final = frozenset(
    {None, "car_condition", "BDC_Service", "BMS_Service", "OBC_Service", "THU_Service"}
)


@dataclass(slots=True)
class MqttReading:
    """Resultado de una lectura MQTT."""

    #: Diccionario plano de parámetros del coche (``{"soc": 80, ...}``).
    params: dict[str, Any] = field(default_factory=dict)
    #: Servicios con código desconocido: ``{service_code: params}`` (depuración).
    unknown_services: dict[str, Any] = field(default_factory=dict)
    #: Milisegundos que tardó la lectura.
    duration_ms: int = 0


def _iso_now() -> str:
    """Fecha actual en el formato ISO que usa la app (terminada en Z)."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _request_id(device_id: str) -> str:
    """Identificador de petición; también es la semilla del IV de AES."""
    return f"{device_id}_{int(time.time() * 1_000_000)}"


def _login_payload(login_did: str, request_id: str) -> dict[str, Any]:
    """Mensaje "loginout" que devuelve la ``secretKey`` de la sesión MQTT."""
    return {
        "did": login_did,
        "r": request_id,
        "v": "v1.0.0",
        "mt": "loginout",
        "z": "unzip",
        "a": 0,
        "e": 0,
        "tf": 0,
        "dt": _iso_now(),
        "pl": True,
        "sers": [
            {
                "service_code": "login",
                "params": {"encryptEnable": 1, "zipType": "gzip", "ts": int(time.time() * 1000)},
            }
        ],
    }


def _condition_payload(
    vehicle_did: str, login_did: str, secret_key: str, request_id: str
) -> dict[str, Any]:
    """Petición cifrada del estado completo (``car_condition``)."""
    services = [{"service_code": "car_condition", "params": {"fetchPropertyType": 0}}]
    return {
        "did": vehicle_did,
        "r": request_id,
        "v": "v1.0.0",
        "mt": "properties",
        "e": 1,
        "z": "gzip",
        "tf": 0,
        "dt": _iso_now(),
        "b": {"ruid": login_did},
        "sers": mqtt_encrypt(services, secret_key, request_id),
        "rt": "",
    }


def _secret_key(payload: dict[str, Any]) -> str | None:
    """Busca ``secretKey`` en la respuesta al login MQTT."""
    for item in payload.get("rs") or []:
        if not isinstance(item, dict):
            continue
        for key in ("params", "data"):
            value = item.get(key)
            if isinstance(value, dict) and value.get("secretKey"):
                return str(value["secretKey"])
    return None


def _extract(payload: dict[str, Any], secret_key: str, reading: MqttReading) -> int:
    """Descifra ``rs``/``sers`` de un mensaje y acumula en ``reading``.

    Returns:
        Número de parámetros nuevos añadidos.
    """
    request_id = payload.get("r")
    if not isinstance(request_id, str):
        return 0
    added = 0
    for field_name in ("rs", "sers"):
        encrypted = payload.get(field_name)
        if not isinstance(encrypted, str) or not encrypted:
            continue
        try:
            services = mqtt_decrypt(encrypted, secret_key, request_id)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError, gzip.BadGzipFile):
            continue
        for service in services:
            if not isinstance(service, dict):
                continue
            code = service.get("service_code")
            params = service.get("params")
            if code not in KNOWN_SERVICE_CODES:
                reading.unknown_services[str(code)] = params
                continue
            if isinstance(params, dict):
                before = len(reading.params)
                reading.params.update(params)
                added += len(reading.params) - before
    return added


async def read_telemetry(
    connection: MqttConnection,
    auth_token: str,
    ssl_context: ssl.SSLContext,
) -> MqttReading:
    """Hace una lectura completa y devuelve los parámetros del coche.

    Args:
        connection: broker y topics (de :func:`topics.parse_connection_config`).
        auth_token: token de ``getAuthTokenByUserId``.
        ssl_context: contexto TLS ya creado. Crearlo lee certificados del disco
            (operación bloqueante), así que Home Assistant lo crea una vez en
            un hilo aparte y lo reutiliza.

    Raises:
        ConnectionError: el broker rechazó la conexión o la suscripción.
        TimeoutError: no llegó ningún dato a tiempo.
    """
    started = time.monotonic()
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(
            connection.host,
            connection.port,
            ssl=ssl_context,
            server_hostname=connection.host,
        ),
        timeout=CONNECT_TIMEOUT,
    )
    reading = MqttReading()
    try:
        await _connect(reader, writer, connection, auth_token)
        await _subscribe(reader, writer, connection)

        writer.write(
            protocol.build_publish(
                connection.login_topic,
                _login_payload(
                    connection.login_device_id, _request_id(connection.login_device_id)
                ),
            )
        )
        await writer.drain()

        secret_key: str | None = None
        requested = False
        deadline = time.monotonic() + TELEMETRY_TIMEOUT

        while time.monotonic() < deadline:
            try:
                first_byte, body = await asyncio.wait_for(
                    protocol.read_packet(reader),
                    timeout=max(1.0, deadline - time.monotonic()),
                )
            except TimeoutError:
                # Se acabó el tiempo esperando más mensajes: nos quedamos con
                # lo recibido hasta ahora (si hay algo).
                break
            if protocol.packet_type(first_byte) != protocol.PACKET_PUBLISH:
                continue
            topic, payload, packet_id = protocol.parse_publish(first_byte, body)
            if packet_id is not None:
                writer.write(protocol.build_puback(packet_id))
                await writer.drain()

            if secret_key is None:
                secret_key = _secret_key(payload)
                if secret_key:
                    request_id = _request_id(connection.vehicle_device_id)
                    writer.write(
                        protocol.build_publish(
                            connection.properties_topic,
                            _condition_payload(
                                connection.vehicle_device_id,
                                connection.login_device_id,
                                secret_key,
                                request_id,
                            ),
                        )
                    )
                    await writer.drain()
                    requested = True
                continue

            if not _extract(payload, secret_key, reading):
                continue
            # Criterios de "ya está completo" (verificados en la práctica):
            # la respuesta directa trae >10 claves; si llegan por trozos, se
            # acepta en cuanto se juntan >30.
            if topic.endswith("/properties/get/res") and len(reading.params) > 10:
                break
            if requested and len(reading.params) > 30:
                break

        if not reading.params:
            raise TimeoutError("No llegó la telemetría por MQTT a tiempo")
        return reading
    finally:
        reading.duration_ms = int((time.monotonic() - started) * 1000)
        try:
            writer.write(protocol.build_disconnect())
            await writer.drain()
        except (ConnectionError, OSError, ssl.SSLError):
            pass
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, TimeoutError, OSError, ssl.SSLError):
            pass


async def _connect(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    connection: MqttConnection,
    auth_token: str,
) -> None:
    """CONNECT + espera del CONNACK."""
    did = connection.login_device_id
    writer.write(protocol.build_connect(did, did, auth_token))
    await writer.drain()
    first_byte, body = await asyncio.wait_for(
        protocol.read_packet(reader), timeout=CONNECT_TIMEOUT
    )
    return_code = protocol.parse_connack(first_byte, body)
    if return_code != 0:
        raise ConnectionError(f"El broker MQTT rechazó la conexión (código {return_code})")


async def _subscribe(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    connection: MqttConnection,
) -> None:
    """SUBSCRIBE + espera del SUBACK."""
    writer.write(protocol.build_subscribe(1, list(connection.subscribe_topics)))
    await writer.drain()
    first_byte, _ = await asyncio.wait_for(
        protocol.read_packet(reader), timeout=CONNECT_TIMEOUT
    )
    if protocol.packet_type(first_byte) != protocol.PACKET_SUBACK:
        raise ConnectionError("El broker MQTT no confirmó la suscripción")
