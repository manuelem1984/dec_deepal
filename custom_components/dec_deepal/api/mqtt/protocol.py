"""Paquetes MQTT 3.1.1 (el subconjunto mínimo que necesita la lectura).

Referencia: especificación MQTT 3.1.1 (OASIS). Solo se implementa lo que se
usa: CONNECT, SUBSCRIBE, PUBLISH (QoS 0 al enviar), PUBACK y DISCONNECT, más
la lectura de paquetes entrantes.

Nota: Deepal Alternative usa MQTT 5.0 contra el mismo broker. Aquí se mantiene
3.1.1 porque es lo que está verificado ✅ con el S05 en España desde el primer
día; el broker acepta ambos.
"""

from __future__ import annotations

import asyncio
import json
import struct
from typing import Any, Final

#: Tipos de paquete (4 bits altos del primer byte).
PACKET_CONNACK: Final = 2
PACKET_PUBLISH: Final = 3
PACKET_SUBACK: Final = 9

#: Segundos de "keepalive" anunciados al broker. La lectura dura menos.
KEEPALIVE_SECONDS: Final = 60


def encode_string(value: str) -> bytes:
    """Cadena MQTT: 2 bytes de longitud + UTF-8."""
    data = value.encode()
    return struct.pack("!H", len(data)) + data


def encode_remaining_length(length: int) -> bytes:
    """Campo "remaining length" de longitud variable (1-4 bytes)."""
    output = bytearray()
    while True:
        byte = length % 128
        length //= 128
        if length:
            byte |= 0x80
        output.append(byte)
        if not length:
            return bytes(output)


def _packet(first_byte: int, body: bytes) -> bytes:
    """Une cabecera fija + longitud + cuerpo."""
    return bytes([first_byte]) + encode_remaining_length(len(body)) + body


def build_connect(client_id: str, username: str, password: str) -> bytes:
    """CONNECT con usuario y contraseña y "clean session".

    Flags 0xC2 = usuario (0x80) + contraseña (0x40) + clean session (0x02).
    """
    variable_header = (
        encode_string("MQTT") + bytes([4, 0xC2]) + struct.pack("!H", KEEPALIVE_SECONDS)
    )
    payload = encode_string(client_id) + encode_string(username) + encode_string(password)
    return _packet(0x10, variable_header + payload)


def build_subscribe(packet_id: int, topics: list[str]) -> bytes:
    """SUBSCRIBE a varios topics con QoS 1."""
    payload = b"".join(encode_string(topic) + b"\x01" for topic in topics)
    return _packet(0x82, struct.pack("!H", packet_id) + payload)


def build_publish(topic: str, payload: dict[str, Any]) -> bytes:
    """PUBLISH QoS 0 con un JSON compacto."""
    body = encode_string(topic) + json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ).encode()
    return _packet(0x30, body)


def build_puback(packet_id: int) -> bytes:
    """PUBACK: confirma un mensaje QoS 1 recibido."""
    return bytes([0x40, 0x02]) + struct.pack("!H", packet_id)


def build_disconnect() -> bytes:
    """DISCONNECT: cierre ordenado (el broker no espera respuesta)."""
    return bytes([0xE0, 0x00])


async def read_packet(reader: asyncio.StreamReader) -> tuple[int, bytes]:
    """Lee un paquete completo. Devuelve ``(primer_byte, cuerpo)``.

    Raises:
        ValueError: longitud mal formada.
        asyncio.IncompleteReadError: el broker cerró la conexión.
    """
    first_byte = (await reader.readexactly(1))[0]
    multiplier = 1
    remaining = 0
    while True:
        byte = (await reader.readexactly(1))[0]
        remaining += (byte & 0x7F) * multiplier
        if not byte & 0x80:
            break
        multiplier *= 128
        if multiplier > 128**3:
            raise ValueError("Longitud MQTT mal formada")
    return first_byte, await reader.readexactly(remaining)


def packet_type(first_byte: int) -> int:
    """Tipo de paquete a partir del primer byte."""
    return first_byte >> 4


def parse_connack(first_byte: int, body: bytes) -> int | None:
    """Código de retorno del CONNACK (0 = aceptado), o ``None`` si no es CONNACK."""
    if first_byte != 0x20 or len(body) < 2:
        return None
    return body[1]


def parse_publish(first_byte: int, body: bytes) -> tuple[str, dict[str, Any], int | None]:
    """Lee un PUBLISH entrante.

    Returns:
        ``(topic, payload_json, packet_id)``. ``packet_id`` es ``None`` en QoS 0.

    Raises:
        ValueError: paquete corto o payload que no es un objeto JSON.
    """
    if len(body) < 2:
        raise ValueError("PUBLISH demasiado corto")
    position = 0
    topic_length = struct.unpack("!H", body[position : position + 2])[0]
    position += 2
    if len(body) < position + topic_length:
        raise ValueError("PUBLISH con topic inválido")
    topic = body[position : position + topic_length].decode(errors="replace")
    position += topic_length

    packet_id: int | None = None
    if (first_byte >> 1) & 0x03:  # QoS > 0 → lleva identificador
        if len(body) < position + 2:
            raise ValueError("PUBLISH sin identificador de paquete")
        packet_id = struct.unpack("!H", body[position : position + 2])[0]
        position += 2

    payload = json.loads(body[position:].decode())
    if not isinstance(payload, dict):
        raise ValueError("El payload del PUBLISH no es un objeto JSON")
    return topic, payload, packet_id
