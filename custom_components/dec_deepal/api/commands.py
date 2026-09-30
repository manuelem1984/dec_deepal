"""Comandos remotos firmados.

Cómo se envía cualquier comando (verificado ✅ con clima, luces y claxon):

1. ``serial-no/get`` → el servidor devuelve un número de serie **cifrado con
   nuestra clave pública** (la que registramos en el login).
2. Se descifra con nuestra clave privada.
3. Se construye el payload: datos del comando + ``seriralNo`` (sic, errata del
   servidor) + ``vehicleId`` (+ ``rcToken`` solo en los comandos con PIN).
4. Se firma (``crypto.sign_payload``) y la firma va en el campo ``sign``.
5. Se envía. La respuesta trae un ``commandId``.
6. Con ese ``commandId`` se consulta ``control-result`` para saber si **el
   coche** (no solo el servidor) lo aceptó. Eso lo hace Home Assistant (ver
   ``command_runner.py``), no este módulo.

Comandos con PIN (puertas, ventanillas, maletero)
-------------------------------------------------
Necesitan un ``rcToken``, que se obtiene canjeando el PIN de control remoto
(``security-code/check-code``). El ``rcToken`` se guarda y se reutiliza; si el
servidor rechaza uno reutilizado, se pide otro con el PIN y se reintenta una
vez. **El rcToken solo se incluye en esos tres comandos**: incluirlo en los
demás provoca errores ``COMMON_1_1_01_008`` (hallazgo de Deepal Alternative).
"""

from __future__ import annotations

import logging
from typing import Any, Final

from . import endpoints
from .account import DeepalAccount
from .crypto import decrypt_with_private_key, encrypt_value, sign_payload
from .errors import (
    DeepalApiError,
    DeepalAuthError,
    DeepalCommandNotReady,
    DeepalPinError,
    DeepalRateLimitError,
    DeepalSigningError,
)
from .models import CommandResult

_LOGGER = logging.getLogger(__name__)

# Acciones de flashing-honking.
FLASH_HONK_OFF: Final = 0
FLASH_HONK_FLASH: Final = 1
FLASH_HONK_HORN: Final = 2
FLASH_HONK_BOTH: Final = 3

#: Valor de ``openType`` que usa la app para "todas las ventanillas".
WINDOWS_OPEN_TYPE_ALL: Final = 10


class DeepalCommands:
    """Envío de comandos firmados para una cuenta."""

    def __init__(self, account: DeepalAccount) -> None:
        self.account = account
        #: PIN de control remoto. Lo pone Home Assistant desde las opciones;
        #: ``None`` si el bloque de PIN está desactivado.
        self.control_pin: str | None = None
        #: rcToken en caché (obtenido canjeando el PIN).
        self.rc_token: str | None = None

    @property
    def _transport(self):  # noqa: ANN202 - atajo interno
        return self.account.transport

    # ------------------------------------------------------------------
    # PIN de control remoto
    # ------------------------------------------------------------------

    async def check_pin(self, pin: str) -> str:
        """Canjea el PIN por un ``rcToken`` (y lo deja en caché).

        Antes consulta cuántos intentos quedan (como hace la app). Si no queda
        ninguno, se rechaza aquí mismo, sin gastar un intento que alargaría el
        bloqueo del servidor.

        Raises:
            DeepalRateLimitError: sin intentos o bloqueo temporal.
            DeepalPinError: PIN incorrecto, caducado o inexistente en la cuenta.
        """
        status = await self.account.call(
            lambda: self._transport.post(endpoints.SECURITY_CODE_STATUS, {})
        )
        retry_quantity = status.get("retryQuantity") if isinstance(status, dict) else None
        try:
            remaining = int(retry_quantity) if retry_quantity is not None else None
        except (TypeError, ValueError):
            remaining = None
        if remaining is not None and remaining <= 0:
            raise DeepalRateLimitError("No quedan intentos de PIN; espera o restablécelo en la app")

        try:
            data = await self.account.call(
                lambda: self._transport.post(
                    endpoints.CHECK_CONTROL_CODE, {"safeCode": encrypt_value(pin)}
                )
            )
        except (DeepalRateLimitError, DeepalAuthError, DeepalPinError):
            raise
        except DeepalApiError as err:
            # Cualquier otro rechazo del check-code es, en la práctica, un PIN
            # incorrecto o creado con otra cuenta.
            raise DeepalPinError(f"PIN rechazado: {err}", code=err.code) from err

        if not isinstance(data, dict) or not data.get("rcToken"):
            raise DeepalPinError("La comprobación del PIN no devolvió rcToken")
        self.rc_token = str(data["rcToken"])
        return self.rc_token

    # ------------------------------------------------------------------
    # Núcleo: firmar y enviar
    # ------------------------------------------------------------------

    async def _serial_number(self) -> str:
        """Pide y descifra el número de serie para firmar."""
        encrypted = await self.account.call(
            lambda: self._transport.post(endpoints.SERIAL_NO, {"type": "1"})
        )
        if not isinstance(encrypted, str) or not encrypted:
            raise DeepalApiError("serial-no/get no devolvió texto")
        try:
            return decrypt_with_private_key(self._private_key(), encrypted)
        except ValueError as err:
            raise DeepalSigningError(
                "No se pudo descifrar el número de serie; vuelve a iniciar sesión"
            ) from err

    def _private_key(self) -> str:
        """Clave privada de la sesión, o error claro si no existe."""
        key = self.account.session.private_key_pem
        if not key:
            raise DeepalCommandNotReady(
                "Falta la clave de firma; vuelve a iniciar sesión en la integración"
            )
        return key

    async def send(
        self,
        path: str,
        vehicle_id: str,
        payload: dict[str, Any],
        *,
        needs_pin: bool = False,
    ) -> str:
        """Firma y envía un comando. Devuelve su ``commandId``.

        Args:
            path: endpoint del comando.
            vehicle_id: ``carId`` del vehículo.
            payload: datos propios del comando (incluido ``command``).
            needs_pin: ``True`` para puertas, ventanillas y maletero.
        """
        self._private_key()  # falla pronto y claro si no hay clave
        reused_token = False
        if needs_pin:
            if self.rc_token:
                reused_token = True
            elif self.control_pin:
                await self.check_pin(self.control_pin)
            else:
                raise DeepalCommandNotReady(
                    "Este comando necesita el PIN de control remoto (Configurar → PIN)"
                )

        async def _build_and_post() -> Any:
            serial = await self._serial_number()
            signed: dict[str, Any] = {**payload, "seriralNo": serial, "vehicleId": vehicle_id}
            if needs_pin and self.rc_token:
                signed["rcToken"] = self.rc_token
            signed["sign"] = sign_payload(self._private_key(), signed)
            return await self._transport.post(path, signed)

        try:
            data = await self.account.call(_build_and_post)
        except DeepalApiError as err:
            if isinstance(err, (DeepalRateLimitError, DeepalSigningError, DeepalAuthError)):
                # Estos no se arreglan pidiendo otro rcToken.
                raise
            if not (needs_pin and reused_token and self.control_pin):
                raise
            # El rcToken guardado caducó (la app lo pide de nuevo más o menos
            # cada semana). Se pide uno nuevo con el PIN y se reintenta 1 vez.
            _LOGGER.debug("rcToken reutilizado rechazado (%s); pidiendo otro", err)
            self.rc_token = None
            await self.check_pin(self.control_pin)
            data = await self.account.call(_build_and_post)

        if not isinstance(data, dict) or not data.get("commandId"):
            raise DeepalApiError(f"El comando no devolvió commandId ({path})")
        return str(data["commandId"])

    async def result(self, vehicle_id: str, command_id: str) -> CommandResult:
        """Consulta si el coche aceptó el comando (POST sin firma). ✅"""
        data = await self.account.call(
            lambda: self._transport.post(
                endpoints.CONTROL_RESULT, {"vehicleId": vehicle_id, "commandId": command_id}
            )
        )
        return CommandResult.from_payload(data if isinstance(data, dict) else {})

    # ------------------------------------------------------------------
    # Comandos sin PIN
    # ------------------------------------------------------------------

    async def air_conditioner(
        self,
        vehicle_id: str,
        *,
        enabled: bool,
        target_c: float,
        run_minutes: int = 30,
        wind_mode: int = 1,
    ) -> str:
        """Encender/apagar la climatización y fijar la temperatura. ✅

        ``targetTemp`` va en **décimas de grado** (22,5 °C → 225), al revés que
        la lectura, que llega en grados. ``windMode`` y ``runTime`` fijos: no se
        han investigado otros valores.
        """
        return await self.send(
            endpoints.AIR_CONDITIONER,
            vehicle_id,
            {
                "command": "air",
                "enabled": enabled,
                "runTime": run_minutes,
                "targetTemp": int(round(target_c * 10)),
                "windMode": wind_mode,
            },
        )

    async def condition_inquiry(self, vehicle_id: str) -> str:
        """Pide al coche que envíe datos frescos ya. ✅"""
        return await self.send(
            endpoints.CONDITION_INQUIRY, vehicle_id, {"command": "COMMAND_GET_NEW_CONDITION"}
        )

    async def flash_honk(self, vehicle_id: str, action: int) -> str:
        """Luces (1), claxon (2), ambos (3) o parar (0). Luces y claxon ✅; ambos ⚠️."""
        return await self.send(
            endpoints.FLASHING_HONKING, vehicle_id, {"command": "flash_bee", "type": action}
        )

    @staticmethod
    def _seat_payload(command: str, *, driver: bool, level: int) -> dict[str, Any]:
        """Payload de asiento. Conductor = "master", acompañante = "copilot".

        Para **apagar** se envía ``switch: 0`` **sin** campo de nivel: un nivel
        0 explícito lo rechaza el servidor (``COMMON_1_1_01_005``).
        """
        prefix = "master" if driver else "copilot"
        payload: dict[str, Any] = {"command": command, f"{prefix}Switch": 1 if level > 0 else 0}
        if level > 0:
            payload[f"{prefix}Level"] = level
        return payload

    async def seat_heat(self, vehicle_id: str, *, driver: bool, level: int) -> str:
        """Calefacción de asiento delantero, nivel 0-3. ⚠️"""
        return await self.send(
            endpoints.SEATS_HEAT, vehicle_id, self._seat_payload("seats_heat", driver=driver, level=level)
        )

    async def seat_vent(self, vehicle_id: str, *, driver: bool, level: int) -> str:
        """Ventilación de asiento delantero, nivel 0-3. ⚠️"""
        return await self.send(
            endpoints.SEATS_WIND, vehicle_id, self._seat_payload("seats_wind", driver=driver, level=level)
        )

    async def steering_wheel_heat(self, vehicle_id: str, enabled: bool) -> str:
        """Volante calefactado on/off. ⚠️"""
        return await self.send(
            endpoints.STEERING_WHEEL_HEAT,
            vehicle_id,
            {"command": "steering_wheel_heating", "open": enabled},
        )

    async def defrost(self, vehicle_id: str, enabled: bool) -> str:
        """Desempañado delantero on/off. ⚠️"""
        return await self.send(
            endpoints.DEFROST, vehicle_id, {"command": "defrost", "enabled": enabled}
        )

    # ------------------------------------------------------------------
    # Comandos con PIN
    # ------------------------------------------------------------------

    async def doors(self, vehicle_id: str, *, unlock: bool) -> str:
        """Cierre centralizado: bloquear (``unlock=False``) o desbloquear. ⚠️

        Formato de Deepal Alternative: ``{"command": "lock", "open": <bool>}``
        (``open=True`` = desbloquear). Sustituye al formato que usaba la
        versión anterior (``"doors"``/``"lock"``), que nunca se verificó.
        """
        return await self.send(
            endpoints.DOORS, vehicle_id, {"command": "lock", "open": unlock}, needs_pin=True
        )

    async def windows(self, vehicle_id: str, *, open_windows: bool) -> str:
        """Todas las ventanillas a la vez: abrir o cerrar. ⚠️

        Formato de Deepal Alternative: ``{"command": "window", "open": <bool>,
        "openType": 10}``. No existe mando por ventanilla individual conocido.
        """
        return await self.send(
            endpoints.WINDOWS,
            vehicle_id,
            {"command": "window", "open": open_windows, "openType": WINDOWS_OPEN_TYPE_ALL},
            needs_pin=True,
        )

    async def trunk(self, vehicle_id: str, *, open_trunk: bool) -> str:
        """Abrir o cerrar el maletero. ⚠️"""
        return await self.send(
            endpoints.TRUNK, vehicle_id, {"command": "trunk", "open": open_trunk}, needs_pin=True
        )
