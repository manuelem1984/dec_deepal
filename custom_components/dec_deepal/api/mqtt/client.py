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


# ---------------------------------------------------------------------------
# Despertar el coche
# ---------------------------------------------------------------------------
#
# Descubierto por Deepal Alternative (v1.3.2-beta.1, comprobado con un coche
# real el 30-09-2026): la app oficial despierta el coche publicando el servicio
# "TxWakeup" con la orden "Cnr_ReWakeup" en el topic ``.../properties/set/req``.
# La pasarela confirma con ``code: "000000"`` y el coche publica un informe
# nuevo en unos 20 segundos. ⚠️ Pendiente de comprobar con un S05 de España.
#
# Cada despertar consume algo de la batería de 12 V: quien llama a esta
# función (coordinator.py) limita cuándo y cada cuánto se usa.

WAKE_SERVICE_CODE: Final = "TxWakeup"
WAKE_COMMAND_CODE: Final = "Cnr_ReWakeup"
#: Código con el que la pasarela confirma que aceptó el despertar.
WAKE_OK_CODES: Final = frozenset({"000000", "0", "00000"})
#: Segundos máximos esperando la confirmación de la pasarela.
WAKE_ACK_TIMEOUT: Final = 20


def _wake_payload(
    vehicle_did: str, login_did: str, secret_key: str, request_id: str
) -> dict[str, Any]:
    """Mensaje cifrado que pide al coche que se despierte."""
    services = [
        {
            "service_code": WAKE_SERVICE_CODE,
            "command_code": WAKE_COMMAND_CODE,
            "service_req_id": request_id,
            "params": {},
        }
    ]
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
    }


def _service_result(payload: dict[str, Any], secret_key: str) -> tuple[str, bool] | None:
    """Primer resultado ``(code, success)`` de una respuesta cifrada, si lo hay."""
    request_id = payload.get("r")
    if not isinstance(request_id, str):
        return None
    for field_name in ("rs", "sers"):
        encrypted = payload.get(field_name)
        if not isinstance(encrypted, str) or not encrypted:
            continue
        try:
            items = mqtt_decrypt(encrypted, secret_key, request_id)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError, gzip.BadGzipFile):
            continue
        for item in items:
            if isinstance(item, dict) and item.get("code"):
                return str(item["code"]), bool(item.get("success"))
    return None


async def wake_vehicle(
    connection: MqttConnection,
    auth_token: str,
    ssl_context: ssl.SSLContext,
) -> str:
    """Pide al coche que se despierte. Devuelve el código de la pasarela.

    Solo espera la **confirmación** de la pasarela, no el informe nuevo del
    coche: eso lo comprueba quien llama, releyendo el estado.

    Raises:
        ConnectionError: el broker rechazó la conexión, o falta el topic.
        TimeoutError: no llegó la confirmación a tiempo.
        ValueError: la pasarela rechazó el despertar (el mensaje trae el código).
    """
    if not connection.properties_set_topic:
        raise ConnectionError("La configuración MQTT no trae el topic de órdenes (set)")
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(
            connection.host,
            connection.port,
            ssl=ssl_context,
            server_hostname=connection.host,
        ),
        timeout=CONNECT_TIMEOUT,
    )
    try:
        await _connect(reader, writer, connection, auth_token)
        await _subscribe(reader, writer, connection)
        writer.write(
            protocol.build_publish(
                connection.login_topic,
                _login_payload(connection.login_device_id, _request_id(connection.login_device_id)),
            )
        )
        await writer.drain()

        secret_key: str | None = None
        wake_request_id: str | None = None
        deadline = time.monotonic() + WAKE_ACK_TIMEOUT
        while time.monotonic() < deadline:
            try:
                first_byte, body = await asyncio.wait_for(
                    protocol.read_packet(reader),
                    timeout=max(1.0, deadline - time.monotonic()),
                )
            except TimeoutError:
                break
            if protocol.packet_type(first_byte) != protocol.PACKET_PUBLISH:
                continue
            _topic, payload, packet_id = protocol.parse_publish(first_byte, body)
            if packet_id is not None:
                writer.write(protocol.build_puback(packet_id))
                await writer.drain()

            if secret_key is None:
                secret_key = _secret_key(payload)
                if secret_key:
                    wake_request_id = _request_id(connection.vehicle_device_id)
                    writer.write(
                        protocol.build_publish(
                            connection.properties_set_topic,
                            _wake_payload(
                                connection.vehicle_device_id,
                                connection.login_device_id,
                                secret_key,
                                wake_request_id,
                            ),
                        )
                    )
                    await writer.drain()
                continue

            if payload.get("r") != wake_request_id:
                continue
            result = _service_result(payload, secret_key)
            if result is None:
                continue
            code, success = result
            if success or code in WAKE_OK_CODES:
                return code
            raise ValueError(f"La pasarela rechazó el despertar (código {code})")

        raise TimeoutError("No llegó la confirmación del despertar")
    finally:
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
