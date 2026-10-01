"""Coordinador de un vehículo: lecturas periódicas y valores optimistas.

Hay **un coordinador por coche**. Cada ``scan_minutes`` (5 por defecto):

1. Renueva la sesión si el token está a punto de caducar.
2. Lee por **MQTT** (si el coche es "MQTT", como el S05).
3. Lee el **REST** ``condition`` (siempre): aporta asientos/volante/desempañado
   fiables y rellena huecos. Si MQTT falla, el REST sirve de respaldo.
4. Fusiona todo (``telemetry/state.py``) y aplica los valores optimistas de
   comandos recientes.

Todas las entidades del coche se suscriben a este coordinador y se redibujan
cuando hay datos nuevos.

Errores:
- Sesión rechazada y sin forma de renovarla → se pide al usuario que vuelva a
  iniciar sesión (``ConfigEntryAuthFailed``).
- Cualquier otro fallo (sin red, coche sin responder...) → ``UpdateFailed``:
  las entidades quedan "no disponibles" hasta la siguiente lectura correcta.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import ssl
import time
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.account import DeepalAccount
from .api.client import DeepalClient
from .api.errors import DeepalAuthError, DeepalError
from .api.models import VehicleInfo
from .api.mqtt.client import MqttReading
from .debug.recorder import DebugRecorder
from .telemetry import signals as s
from .telemetry.state import OptimisticHold, VehicleState, apply_holds, build_state

_LOGGER = logging.getLogger(__name__)

#: Segundos que se mantiene un valor optimista si el coche no lo confirma.
#: El coche aplica los comandos con retraso y a veces informa datos viejos
#: justo después; sin esto la entidad "rebotaría" al valor anterior.
OPTIMISTIC_HOLD_SECONDS: Final = 120.0

# --- Despertar el coche (ver api/mqtt/client.wake_vehicle) -------------------
#: Solo se despierta si el último informe tiene más de estos segundos.
WAKE_STALE_AFTER: Final = 120.0
#: Como mucho un despertar cada estos segundos por coche (batería de 12 V).
WAKE_COOLDOWN: Final = 300.0
#: Segundos esperando el informe nuevo tras despertar (botón de actualizar).
WAKE_REPORT_TIMEOUT: Final = 60.0
#: Segundos esperando el informe nuevo antes de una orden con PIN.
WAKE_BEFORE_COMMAND_TIMEOUT: Final = 30.0
#: Cada cuántos segundos se relee mientras se espera el informe nuevo.
WAKE_POLL_INTERVAL: Final = 5.0


class WakeResult(StrEnum):
    """Resultado de :meth:`VehicleCoordinator.async_wake_and_wait`."""

    NOT_NEEDED = "no_hace_falta"  # datos recientes, MQTT no usado o desactivado
    THROTTLED = "limitado"  # ya se despertó hace menos de WAKE_COOLDOWN
    FRESH = "informe_nuevo"  # se despertó y llegó un informe nuevo
    NO_REPORT = "sin_informe"  # la pasarela aceptó, pero el coche no informó a tiempo
    FAILED = "fallo"  # no se pudo enviar el despertar


#: Errores de la lectura MQTT que permiten seguir con el REST.
_MQTT_RECOVERABLE: Final = (DeepalError, ConnectionError, TimeoutError, OSError, ValueError)


class VehicleCoordinator(DataUpdateCoordinator[VehicleState]):
    """Lecturas periódicas de un coche."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        *,
        account: DeepalAccount,
        client: DeepalClient,
        recorder: DebugRecorder,
        vehicle: VehicleInfo,
        use_mqtt: bool,
        scan_minutes: int,
        wake_enabled: bool = True,
    ) -> None:
        """Crea el coordinador.

        Args:
            account: sesión compartida de la cuenta.
            client: lecturas de la API.
            recorder: registro de depuración.
            vehicle: el coche.
            use_mqtt: leer por MQTT (según el modelo del catálogo y el
                ``protocolType`` que indica el servidor).
            scan_minutes: intervalo entre lecturas.
            wake_enabled: permitir despertar el coche (botón de actualizar y
                antes de órdenes con PIN). Opción "Despertar el coche".
        """
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"DEC Deepal {vehicle.display_name}",
            update_interval=timedelta(minutes=scan_minutes),
        )
        self.account = account
        self.client = client
        self.recorder = recorder
        self.vehicle = vehicle
        self.use_mqtt = use_mqtt
        # El contexto TLS lee certificados del disco (bloqueante): se crea una
        # vez en un hilo aparte y se reutiliza en cada lectura MQTT.
        self._ssl_context: ssl.SSLContext | None = None
        self._holds: dict[str, OptimisticHold] = {}
        self.wake_enabled = wake_enabled
        self._last_wake: float | None = None
        self._wake_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> VehicleState:
        """Lectura periódica (la llama Home Assistant)."""
        await self.account.ensure_fresh()
        try:
            state = await self._fetch()
        except DeepalAuthError as err:
            self.recorder.record("update", ok=False, error=str(err))
            raise ConfigEntryAuthFailed(
                f"La sesión de Deepal ya no es válida: {err}"
            ) from err
        except UpdateFailed as err:
            self.recorder.record("update", ok=False, error=str(err))
            raise
        except DeepalError as err:
            self.recorder.record("update", ok=False, error=str(err))
            raise UpdateFailed(f"No se pudo leer el vehículo: {err}") from err

        self.recorder.record(
            "update",
            ok=True,
            signals=len(state.values),
            mqtt=state.mqtt_raw is not None,
            rest=state.rest_raw is not None,
            warnings=state.warnings,
        )
        return state

    async def _fetch(self) -> VehicleState:
        """MQTT + REST + fusión. Ver el docstring del módulo."""
        warnings: list[str] = []

        reading: MqttReading | None = None
        if self.use_mqtt:
            try:
                reading = await self.client.read_mqtt(self.vehicle, await self._ssl())
            except DeepalAuthError:
                raise
            except _MQTT_RECOVERABLE as err:
                warnings.append(f"MQTT falló: {err}")
                _LOGGER.warning(
                    "%s: lectura MQTT fallida (%s); se usa solo el REST",
                    self.vehicle.display_name,
                    err,
                )
            else:
                self.recorder.record(
                    "mqtt",
                    params=len(reading.params),
                    duration_ms=reading.duration_ms,
                    unknown_services=reading.unknown_services
                    if self.recorder.verbose
                    else sorted(reading.unknown_services),
                )

        rest: dict[str, Any] | None = None
        try:
            rest = await self.client.get_condition(self.vehicle.vehicle_id)
        except DeepalAuthError:
            raise
        except DeepalError as err:
            if reading is None:
                raise UpdateFailed(
                    f"No se pudo leer el vehículo ni por MQTT ni por REST: {err}"
                ) from err
            warnings.append(f"REST falló: {err}")
            _LOGGER.debug("%s: REST fallido: %s", self.vehicle.display_name, err)

        if reading is None and not rest:
            raise UpdateFailed("El vehículo no devolvió datos")

        state = build_state(
            mqtt_params=reading.params if reading else None,
            rest_raw=rest,
            previous=self.data,
        )
        if reading is not None:
            state.mqtt_unknown = dict(reading.unknown_services)
        state.warnings = warnings
        apply_holds(state, self._holds, time.monotonic())
        return state

    async def _ssl(self) -> ssl.SSLContext:
        """Contexto TLS para MQTT (creado una sola vez)."""
        if self._ssl_context is None:
            self._ssl_context = await self.hass.async_add_executor_job(
                ssl.create_default_context
            )
        return self._ssl_context

    # ------------------------------------------------------------------
    # Despertar el coche
    # ------------------------------------------------------------------

    def _report_age(self) -> float | None:
        """Segundos desde el último informe del coche (``None`` si no se sabe)."""
        report = self.data.get(s.REPORT_TIME) if self.data else None
        if report is None:
            return None
        return (datetime.now(UTC) - report).total_seconds()

    async def async_wake_and_wait(
        self, *, timeout: float = WAKE_REPORT_TIMEOUT
    ) -> WakeResult:
        """Despierta el coche si sus datos están viejos y espera un informe nuevo.

        Reglas (mismas que Deepal Alternative, para cuidar la batería de 12 V):
        - Solo coches MQTT (el S05) y con la opción activada.
        - Solo si el último informe tiene más de ``WAKE_STALE_AFTER`` s.
        - Como mucho uno cada ``WAKE_COOLDOWN`` s por coche (el límite cuenta
          desde que la pasarela acepta el despertar, llegue o no el informe).
        - Nunca lo llama la lectura periódica: solo el botón "Actualizar" y
          las órdenes con PIN.

        Tras despertar, relee cada ``WAKE_POLL_INTERVAL`` s hasta ``timeout``
        y publica el estado en cuanto el informe es más nuevo que el anterior.
        Nunca lanza excepciones: el resultado dice qué pasó.
        """
        async with self._wake_lock:
            if not (self.use_mqtt and self.wake_enabled):
                return WakeResult.NOT_NEEDED
            age = self._report_age()
            if age is not None and age <= WAKE_STALE_AFTER:
                return WakeResult.NOT_NEEDED
            if self._last_wake is not None and time.monotonic() - self._last_wake < WAKE_COOLDOWN:
                return WakeResult.THROTTLED

            previous = self.data.get(s.REPORT_TIME) if self.data else None
            try:
                code = await self.client.wake(self.vehicle, await self._ssl())
            except (DeepalError, ConnectionError, TimeoutError, OSError, ValueError) as err:
                _LOGGER.warning("%s: no se pudo despertar el coche: %s", self.vehicle.display_name, err)
                self.recorder.record("wake", ok=False, error=str(err))
                return WakeResult.FAILED
            self._last_wake = time.monotonic()
            self.recorder.record("wake", ok=True, code=code, report_age_s=age)

            loop = asyncio.get_running_loop()
            deadline = loop.time() + timeout
            while loop.time() < deadline:
                await asyncio.sleep(WAKE_POLL_INTERVAL)
                try:
                    state = await self._fetch()
                except (DeepalError, UpdateFailed) as err:
                    _LOGGER.debug("Relectura tras despertar fallida: %s", err)
                    continue
                report = state.get(s.REPORT_TIME)
                if report is not None and (previous is None or report > previous):
                    self.async_set_updated_data(state)
                    self.recorder.record("wake", stage="informe_nuevo")
                    return WakeResult.FRESH
            self.recorder.record("wake", stage="sin_informe", timeout_s=timeout)
            return WakeResult.NO_REPORT

    # ------------------------------------------------------------------
    # Valores optimistas (los usa command_runner.py)
    # ------------------------------------------------------------------

    def apply_optimistic(self, values: dict[str, Any]) -> dict[str, Any]:
        """Muestra ya el resultado esperado de un comando.

        Args:
            values: ``{señal: valor_esperado}``.

        Returns:
            Los valores que había antes, para poder deshacer si el coche
            rechaza el comando (:meth:`revert_optimistic`).
        """
        if self.data is None:
            return {}
        now = time.monotonic()
        previous = {signal: self.data.values.get(signal) for signal in values}
        for signal, value in values.items():
            self._holds[signal] = OptimisticHold(value, now + OPTIMISTIC_HOLD_SECONDS)
        state = dataclasses.replace(
            self.data, values=dict(self.data.values), sources=dict(self.data.sources)
        )
        apply_holds(state, self._holds, now)
        self.async_set_updated_data(state)
        return previous

    def revert_optimistic(self, previous: dict[str, Any]) -> None:
        """Deshace un valor optimista (el coche rechazó el comando)."""
        if self.data is None or not previous:
            return
        for signal in previous:
            self._holds.pop(signal, None)
        state = dataclasses.replace(
            self.data, values=dict(self.data.values), sources=dict(self.data.sources)
        )
        for signal, value in previous.items():
            if value is None:
                state.values.pop(signal, None)
                state.sources.pop(signal, None)
            else:
                state.values[signal] = value
        self.async_set_updated_data(state)
