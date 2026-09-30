"""Ejecución de comandos: la "aduana" por la que pasa cualquier orden al coche.

Todas las entidades que actúan sobre el coche (clima, asientos, luces,
puertas...) llaman a :meth:`CommandRunner.run`. Centralizarlo aquí garantiza
las mismas protecciones venga el comando de un botón, una automatización o un
asistente de voz:

1. **Armado (Opción B del PIN):** puertas, ventanillas y maletero se rechazan
   si no se ha desbloqueado antes "Desbloqueo acciones con PIN".
2. **Tiempo de espera físico:** parpadear luces (30 s) y claxon (6 s). Repetir
   antes muestra cuántos segundos faltan en vez del rechazo críptico del coche.
3. **Cola por vehículo:** los comandos que cambian estado (clima, asientos,
   cierres...) esperan su turno (máx. 30 s) en vez de pisarse.
4. **Optimista:** la entidad cambia al momento al valor esperado.
5. **Confirmación:** se consulta ``control-result`` hasta 15 s. Si el coche lo
   rechaza, se **deshace** el valor optimista y se muestra un error claro.
6. **Refresco:** se pide al coche que informe (``condition-inquiry``) y se
   relee dos veces (a los 5 s y a los 25 s).

Basado en el diseño del proyecto anterior y en Deepal Alternative (MIT).
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections.abc import Awaitable, Callable
from typing import Any, Final

from homeassistant.components import persistent_notification
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later

from .api.commands import DeepalCommands
from .api.errors import (
    DeepalAuthError,
    DeepalCommandNotReady,
    DeepalConnectionError,
    DeepalError,
    DeepalPinError,
    DeepalRateLimitError,
    DeepalSigningError,
)
from .api.models import CommandStatus
from .const import DOMAIN, PIN_MODE_ARMED
from .coordinator import VehicleCoordinator
from .debug.recorder import DebugRecorder

_LOGGER = logging.getLogger(__name__)

#: Segundos que el coche tarda en completar el ciclo físico de un comando
#: (medido con el coche real por Deepal Alternative). Clima, asientos y
#: volante no tienen espera.
COOLDOWN_SECONDS: Final[dict[str, float]] = {
    "flash_lights": 30.0,
    "honk_horn": 6.0,
    "flash_and_honk": 30.0,
}

RESULT_TIMEOUT: Final = 15.0  # s máximos esperando control-result
RESULT_INTERVAL: Final = 1.0  # s entre consultas
LOCK_TIMEOUT: Final = 30.0  # s máximos esperando turno en la cola
REFRESH_DELAYS: Final = (5.0, 20.0)  # s antes de cada relectura tras un comando


def to_ha_error(err: DeepalError) -> HomeAssistantError:
    """Convierte un error del cliente en un error traducible de Home Assistant.

    Los textos están en ``strings.json`` → ``exceptions``, así se traducen
    al idioma del usuario.
    """
    if isinstance(err, DeepalAuthError):
        key = "session_expired"
    elif isinstance(err, DeepalRateLimitError):
        key = "rate_limited"
    elif isinstance(err, DeepalPinError):
        key = "pin_problem"
    elif isinstance(err, DeepalSigningError):
        key = "signing_key_invalid"
    elif isinstance(err, DeepalCommandNotReady):
        key = "command_not_ready"
    elif isinstance(err, DeepalConnectionError):
        key = "connection_error"
    else:
        key = "command_failed"
    return HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders={"error": str(err)},
    )


class CommandRunner:
    """Ejecuta comandos de un vehículo con todas las protecciones."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        coordinator: VehicleCoordinator,
        commands: DeepalCommands,
        recorder: DebugRecorder,
        pin_mode: str,
        arm_seconds: int,
        arm_notify: bool,
    ) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self.commands = commands
        self.recorder = recorder
        self.pin_mode = pin_mode
        self.arm_seconds = arm_seconds
        self.arm_notify = arm_notify
        self._lock = asyncio.Lock()
        self._cooldowns: dict[str, float] = {}
        self._armed = False
        self._arm_unsub: CALLBACK_TYPE | None = None

    @property
    def vehicle_id(self) -> str:
        """``carId`` del coche."""
        return self.coordinator.vehicle.vehicle_id

    # ------------------------------------------------------------------
    # Armado (Opción B)
    # ------------------------------------------------------------------

    @property
    def is_armed(self) -> bool:
        """¿Están permitidos ahora los comandos con PIN? (solo Opción B)."""
        return self._armed

    @callback
    def arm(self) -> None:
        """Permite comandos con PIN durante ``arm_seconds``.

        Se pueden enviar varios dentro de la ventana. Volver a armar reinicia
        la cuenta atrás. **Nunca** se recuerda armado tras reiniciar.
        """
        self._cancel_arm_timer()
        self._armed = True
        self._arm_unsub = async_call_later(self.hass, self.arm_seconds, self._on_arm_expired)
        if self.arm_notify:
            persistent_notification.async_create(
                self.hass,
                f"Comandos con PIN permitidos durante {self.arm_seconds} segundos.",
                title=f"DEC Deepal — {self.coordinator.vehicle.display_name}",
                notification_id=f"{DOMAIN}_arm_{self.vehicle_id}",
            )
        self.recorder.record("command", name="pin_arm", stage="armed", seconds=self.arm_seconds)
        self.coordinator.async_update_listeners()

    @callback
    def disarm(self) -> None:
        """Vuelve a bloquear los comandos con PIN."""
        self._cancel_arm_timer()
        self._armed = False
        self.coordinator.async_update_listeners()

    @callback
    def _on_arm_expired(self, _now: Any) -> None:
        self._arm_unsub = None
        self.disarm()

    def _cancel_arm_timer(self) -> None:
        if self._arm_unsub is not None:
            self._arm_unsub()
            self._arm_unsub = None

    @callback
    def async_shutdown(self) -> None:
        """Limpia temporizadores al descargar la integración."""
        self._cancel_arm_timer()

    # ------------------------------------------------------------------
    # Ejecución
    # ------------------------------------------------------------------

    async def run(
        self,
        name: str,
        send: Callable[[], Awaitable[str]],
        *,
        optimistic: dict[str, Any] | None = None,
        needs_arming: bool = False,
        serialize: bool | None = None,
        refresh_after: bool = True,
    ) -> None:
        """Ejecuta un comando.

        Args:
            name: nombre corto (``"flash_lights"``...). Se usa para la espera
                física y para el registro de depuración.
            send: función que envía el comando y devuelve su ``commandId``
                (p. ej. ``lambda: commands.flash_honk(id, 1)``).
            optimistic: ``{señal: valor}`` que se muestra al momento.
            needs_arming: ``True`` en puertas, ventanillas y maletero.
            serialize: esperar turno en la cola. Por defecto, solo si hay
                valor optimista (luces y claxon nunca esperan).
            refresh_after: releer el coche después.

        Raises:
            HomeAssistantError: con un mensaje traducido si algo falla.
        """
        if needs_arming and self.pin_mode == PIN_MODE_ARMED and not self._armed:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="pin_not_armed")
        self._check_cooldown(name)

        if serialize is None:
            serialize = optimistic is not None
        if not serialize:
            await self._run(name, send, optimistic, refresh_after)
            return

        try:
            async with asyncio.timeout(LOCK_TIMEOUT):
                await self._lock.acquire()
        except TimeoutError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_busy"
            ) from err
        try:
            await self._run(name, send, optimistic, refresh_after)
        finally:
            self._lock.release()

    async def _run(
        self,
        name: str,
        send: Callable[[], Awaitable[str]],
        optimistic: dict[str, Any] | None,
        refresh_after: bool,
    ) -> None:
        """Pasos 4-6 del docstring del módulo."""
        self.recorder.record("command", name=name, stage="enviando", optimistic=optimistic)
        try:
            command_id = await send()
        except DeepalError as err:
            self.recorder.record("command", name=name, stage="error_envio", error=str(err))
            raise to_ha_error(err) from err

        previous = self.coordinator.apply_optimistic(optimistic) if optimistic else {}
        try:
            await self._wait_result(name, command_id)
        except HomeAssistantError:
            self.coordinator.revert_optimistic(previous)
            raise

        self._start_cooldown(name)
        if refresh_after:
            self.hass.async_create_background_task(
                self._refresh_after_command(),
                name=f"{DOMAIN}_refresh_{self.vehicle_id}",
            )

    async def _wait_result(self, name: str, command_id: str) -> None:
        """Consulta ``control-result`` hasta éxito, fallo o tiempo agotado.

        Tiempo agotado sin respuesta NO es error: se da por enviado y la
        siguiente lectura confirmará o corregirá el estado.
        """
        deadline = time.monotonic() + RESULT_TIMEOUT
        while True:
            try:
                result = await self.commands.result(self.vehicle_id, command_id)
            except DeepalError as err:
                # La consulta es informativa: si falla, no se bloquea el comando.
                self.recorder.record("command", name=name, stage="resultado_no_disponible", error=str(err))
                return
            if result.status is CommandStatus.FAILED:
                self.recorder.record(
                    "command", name=name, stage="rechazado", code=result.code, error=result.error_message
                )
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key=(
                        "command_rejected_asleep" if result.vehicle_asleep_hint else "command_rejected"
                    ),
                    translation_placeholders={"error": result.error_message or str(result.code)},
                )
            if result.status in (CommandStatus.SUCCESS, CommandStatus.ALREADY_DONE):
                self.recorder.record("command", name=name, stage=str(result.status), code=result.code)
                return
            if time.monotonic() >= deadline:
                self.recorder.record("command", name=name, stage="pendiente_sin_respuesta")
                return
            await asyncio.sleep(RESULT_INTERVAL)

    async def _refresh_after_command(self) -> None:
        """Pide datos frescos al coche y relee (en segundo plano)."""
        try:
            await self.commands.condition_inquiry(self.vehicle_id)
        except DeepalError as err:
            _LOGGER.debug("condition-inquiry tras comando falló: %s", err)
        for delay in REFRESH_DELAYS:
            await asyncio.sleep(delay)
            await self.coordinator.async_request_refresh()

    # ------------------------------------------------------------------
    # Tiempos de espera físicos
    # ------------------------------------------------------------------

    def _check_cooldown(self, name: str) -> None:
        """Rechaza el comando si el coche aún está con el ciclo anterior."""
        until = self._cooldowns.get(name)
        if until is None:
            return
        remaining = until - time.monotonic()
        if remaining > 0:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_cooldown",
                translation_placeholders={"seconds": str(math.ceil(remaining))},
            )

    def _start_cooldown(self, name: str) -> None:
        """Arranca la espera física de un comando que no falló."""
        seconds = COOLDOWN_SECONDS.get(name)
        if seconds:
            self._cooldowns[name] = time.monotonic() + seconds
