"""Conexión MQTT permanente (experimental, 2.6.0b17; desactivada de fábrica).

La lectura de siempre (``client.py``) abre, pide el estado y cierra en cada
actualización. Con la conexión permanente, la sesión se queda **abierta**:
el coche manda sus informes en cuanto cambia algo (estados completos y
trocitos), y se acumulan para que un trocito no borre lo demás (como hace
Deepal Alternative 1.9).

Reglas:

- **Una sola conexión por cuenta** (el broker no admite más): solo se usa si
  la cuenta tiene un único coche por MQTT. La conexión tiene el candado MQTT
  de la cuenta mientras está abierta.
- Las órdenes que necesitan su propia conexión (despertar el coche) y la
  lectura de siempre **pausan** la permanente (:meth:`LiveSession.paused`):
  se cierra, hacen lo suyo y se vuelve a abrir.
- Si se cae, se reintenta con esperas cada vez más largas (de 5 s a 5 min).
  Si se cae nada más abrirse varias veces seguidas (otro cliente con la
  misma cuenta la está echando), se espera 5 minutos.
- Cada 45 s sin mensajes se manda un PINGREQ (el *keepalive* es de 60 s).
- Sin Home Assistant: el coordinador recibe los datos con ``on_params``.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Any, Final

from . import protocol
from .client import MqttReading, _condition_payload, _extract, _request_id, _secret_key, model_code
from .topics import MqttConnection

_LOGGER = logging.getLogger(__name__)

PING_SECONDS: Final = 45
BACKOFF_FIRST: Final = 5.0
BACKOFF_MAX: Final = 300.0
#: Una conexión que dura menos que esto cuenta como "echada".
SHORT_SESSION: Final = 10.0
#: Tantas echadas seguidas → otro cliente usa la cuenta: se espera más.
KICKS_BEFORE_PAUSE: Final = 3
KICKED_WAIT: Final = 300.0
#: Una conexión que dura más que esto vuelve a empezar las esperas.
STABLE_AFTER: Final = 60.0
PINGREQ: Final = bytes([0xC0, 0x00])

#: Abre la sesión: ``async with open_session() as (reader, writer, connection)``.
SessionOpener = Callable[[], AbstractAsyncContextManager[tuple[asyncio.StreamReader, asyncio.StreamWriter, MqttConnection]]]


@dataclass
class LiveStats:
    """Para el diagnóstico."""

    connected: bool = False
    connections: int = 0
    messages: int = 0
    last_message: float | None = None
    last_error: str | None = None
    kicked: int = 0
    params: int = 0
    unknown_services: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Para el diagnóstico (antigüedad del último mensaje en segundos)."""
        age = None if self.last_message is None else round(time.monotonic() - self.last_message)
        return {
            "conectada": self.connected,
            "conexiones": self.connections,
            "mensajes": self.messages,
            "segundos_desde_el_ultimo": age,
            "ultimo_error": self.last_error,
            "echada_seguidas": self.kicked,
            "claves": self.params,
        }


class LiveSession:
    """Una conexión MQTT que se queda abierta para un coche."""

    def __init__(
        self,
        open_session: SessionOpener,
        on_params: Callable[[MqttReading], None],
        *,
        on_error: Callable[[BaseException], None] | None = None,
    ) -> None:
        self._open = open_session
        self._on_params = on_params
        self._on_error = on_error
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._resume = asyncio.Event()
        self._resume.set()
        self._closed = asyncio.Event()
        self._closed.set()
        self._pauses = 0
        self._writer: asyncio.StreamWriter | None = None
        self._connection: MqttConnection | None = None
        self._secret: str | None = None
        self.reading = MqttReading()
        self.stats = LiveStats()

    @property
    def connected(self) -> bool:
        """¿Abierta y con la sesión del coche lista?"""
        return self.stats.connected and self._secret is not None

    def start(self, create_task: Callable[..., asyncio.Task[None]] = asyncio.create_task) -> None:
        """Empieza (en segundo plano)."""
        if self._task is None:
            self._task = create_task(self._supervise())

    async def stop(self) -> None:
        """Cierra y termina."""
        self._stop.set()
        self._resume.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    @contextlib.asynccontextmanager
    async def paused(self) -> AsyncIterator[None]:
        """Cierra la conexión mientras dura el bloque (para usar el MQTT de otra forma)."""
        self._pauses += 1
        self._resume.clear()
        if self._writer is not None:
            self._writer.close()
        try:
            await asyncio.wait_for(self._closed.wait(), timeout=10)
            yield
        finally:
            self._pauses -= 1
            if not self._pauses:
                self._resume.set()

    async def request_condition(self) -> bool:
        """Pide el estado completo por la conexión abierta (llega como un mensaje más)."""
        if not self.connected or self._writer is None or self._connection is None:
            return False
        connection = self._connection
        request_id = _request_id(connection.vehicle_device_id)
        self._writer.write(
            protocol.build_publish(
                connection.properties_topic,
                _condition_payload(connection.vehicle_device_id, connection.login_device_id, self._secret, request_id),
            )
        )
        await self._writer.drain()
        return True

    # ------------------------------------------------------------------

    async def _supervise(self) -> None:
        backoff = BACKOFF_FIRST
        while not self._stop.is_set():
            await self._resume.wait()
            if self._stop.is_set():
                return
            started = time.monotonic()
            try:
                await self._run_once()
            except asyncio.CancelledError:
                raise
            except (ConnectionError, TimeoutError, OSError, ValueError, asyncio.IncompleteReadError) as err:
                self.stats.last_error = f"{type(err).__name__}: {err}"
                _LOGGER.debug("Conexión MQTT permanente caída: %s", err)
                if self._on_error is not None:
                    self._on_error(err)
            except Exception as err:  # noqa: BLE001 - la sesión nunca debe tumbar la integración
                self.stats.last_error = f"{type(err).__name__}: {err}"
                _LOGGER.warning("Conexión MQTT permanente: error inesperado: %s", err)
            if self._stop.is_set():
                return
            if not self._resume.is_set():
                continue  # pausada a propósito: no es una caída
            lasted = time.monotonic() - started
            if lasted >= STABLE_AFTER:
                backoff, self.stats.kicked = BACKOFF_FIRST, 0
            elif lasted < SHORT_SESSION:
                self.stats.kicked += 1
            wait = KICKED_WAIT if self.stats.kicked >= KICKS_BEFORE_PAUSE else backoff
            backoff = min(BACKOFF_MAX, backoff * 2)
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stop.wait(), timeout=wait)

    async def _run_once(self) -> None:
        self._closed.clear()
        try:
            async with self._open() as (reader, writer, connection):
                self._writer, self._connection, self._secret = writer, connection, None
                self.stats.connected = True
                self.stats.connections += 1
                await self._read_loop(reader, writer)
        finally:
            self._writer = self._connection = self._secret = None
            self.stats.connected = False
            self._closed.set()

    async def _read_loop(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        while not self._stop.is_set() and self._resume.is_set():
            try:
                first_byte, body = await asyncio.wait_for(protocol.read_packet(reader), timeout=PING_SECONDS)
            except TimeoutError:
                writer.write(PINGREQ)
                await writer.drain()
                continue
            if protocol.packet_type(first_byte) != protocol.PACKET_PUBLISH:
                continue
            try:
                _topic, payload, packet_id = protocol.parse_publish(first_byte, body)
            except ValueError as err:
                _LOGGER.debug("Mensaje MQTT mal formado, se ignora: %s", err)
                continue
            if packet_id is not None:
                writer.write(protocol.build_puback(packet_id))
                await writer.drain()
            self.stats.messages += 1
            self.stats.last_message = time.monotonic()
            if self._secret is None:
                self._secret = _secret_key(payload)
                if self._secret is not None:
                    await self.request_condition()  # un estado completo al empezar
                continue
            if self.reading.model_code is None:
                self.reading.model_code = model_code(payload)
            if _extract(payload, self._secret, self.reading):
                self.stats.params = len(self.reading.params)
                self._on_params(self.reading)
