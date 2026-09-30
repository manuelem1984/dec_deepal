"""Registro en memoria de los últimos intercambios con la nube.

Guarda los últimos N eventos (``const.DEBUG_BUFFER_SIZE``) en un búfer
circular: los más viejos se descartan solos, así que nunca crece sin límite.

Tipos de evento (campo ``kind``):

- ``http``     — una petición REST: ruta, duración, error; y en modo
  depuración, también cuerpo enviado y recibido (con datos ocultos).
- ``mqtt``     — una lectura MQTT: nº de parámetros, duración, servicios
  desconocidos.
- ``command``  — ciclo de vida de un comando: enviado, resultado, error.
- ``update``   — resultado de cada actualización del coordinador.
- ``note``     — cualquier otro aviso interno.

Todo se guarda ya pasado por :func:`~.redact.redact`.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from typing import Any

from .redact import redact


class DebugRecorder:
    """Búfer circular de eventos de depuración."""

    def __init__(self, size: int, *, verbose: bool = False) -> None:
        """Crea el registro.

        Args:
            size: nº máximo de eventos guardados.
            verbose: modo depuración. ``True`` guarda también los cuerpos
                completos de peticiones y respuestas.
        """
        self._events: deque[dict[str, Any]] = deque(maxlen=size)
        self.verbose = verbose

    def record(self, kind: str, **data: Any) -> None:
        """Añade un evento. Los datos se ocultan antes de guardarse."""
        event = {"time": datetime.now(UTC).isoformat(), "kind": kind, **data}
        self._events.append(redact(event))

    def record_http(self, exchange: dict[str, Any]) -> None:
        """Adaptador para ``DeepalTransport.on_exchange``.

        Sin modo depuración se guarda solo el resumen (ruta, duración, error);
        los cuerpos pueden ser grandes y casi nunca hacen falta.
        """
        summary = {
            "gateway": exchange.get("gateway"),
            "path": exchange.get("path"),
            "duration_ms": exchange.get("duration_ms"),
            "error": exchange.get("error"),
        }
        if self.verbose:
            summary["request"] = exchange.get("request")
            summary["response"] = exchange.get("response")
        self.record("http", **summary)

    def events(self) -> list[dict[str, Any]]:
        """Copia de los eventos, del más antiguo al más reciente."""
        return list(self._events)

    def clear(self) -> None:
        """Vacía el registro."""
        self._events.clear()
