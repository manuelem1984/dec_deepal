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
- ``wake``     — intento de despertar el coche.
- ``change``   — señales que han cambiado entre dos lecturas (``history.py``).
- ``alert``    — aviso enviado al móvil (tipo y nº de destinos, sin el texto).
- ``note``     — cualquier otro aviso interno.

Historial
---------
El búfer general se llena en un par de horas con lecturas rutinarias, así
que lo importante se guarda **además** aparte y dura mucho más
(:data:`KEPT`): órdenes, despertares, cambios de señales, avisos y cualquier
evento con error. Es lo que cuenta "qué pasó" en un diagnóstico.

Todo se guarda ya pasado por :func:`~.redact.redact`.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from typing import Any, Final

from .redact import redact

#: Eventos que se conservan aparte: ``{tipo: cuántos}``.
KEPT: Final = {"command": 80, "wake": 40, "change": 400, "alert": 60}
#: Eventos con error (de cualquier tipo) que se conservan aparte.
KEPT_ERRORS: Final = 60


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
        self._kept: dict[str, deque[dict[str, Any]]] = {
            kind: deque(maxlen=count) for kind, count in KEPT.items()
        }
        self._errors: deque[dict[str, Any]] = deque(maxlen=KEPT_ERRORS)
        self.verbose = verbose

    def record(self, kind: str, **data: Any) -> None:
        """Añade un evento. Los datos se ocultan antes de guardarse."""
        event = redact({"time": datetime.now(UTC).isoformat(), "kind": kind, **data})
        self._events.append(event)
        if kind in self._kept:
            self._kept[kind].append(event)
        if data.get("error") or data.get("ok") is False:
            self._errors.append(event)

    def for_vehicle(self, name: str) -> VehicleRecorder:
        """Registro que apunta cada evento a nombre de un coche."""
        return VehicleRecorder(self, name)

    def history(self) -> dict[str, list[dict[str, Any]]]:
        """Lo que se conserva aparte, del más antiguo al más reciente."""
        orders = sorted(
            [*self._kept["command"], *self._kept["wake"]], key=lambda event: event["time"]
        )
        return {
            "cambios": list(self._kept["change"]),
            "ordenes": orders,
            "avisos": list(self._kept["alert"]),
            "errores": list(self._errors),
        }

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
        for kept in self._kept.values():
            kept.clear()
        self._errors.clear()


class VehicleRecorder:
    """El registro de la cuenta, visto desde un coche.

    Con varios coches en la cuenta, una orden o un cambio sin nombre no se
    sabría de cuál es: esta vista añade ``vehicle`` a cada evento.
    """

    def __init__(self, recorder: DebugRecorder, name: str) -> None:
        self._recorder = recorder
        self._name = name

    @property
    def verbose(self) -> bool:
        """Modo depuración (el de la cuenta)."""
        return self._recorder.verbose

    def record(self, kind: str, **data: Any) -> None:
        """Añade un evento de este coche."""
        self._recorder.record(kind, vehicle=self._name, **data)
