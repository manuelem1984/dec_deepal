"""Lecturas: lista de vehículos, estado REST, capacidades y telemetría MQTT.

Los *comandos* (escribir en el coche) están aparte, en ``commands.py``.

Todas las llamadas pasan por :meth:`DeepalAccount.call`, que renueva la sesión
y reintenta una vez si el servidor dice que el token caducó.
"""

from __future__ import annotations

import logging
import ssl
import time
from typing import Any, Final

from . import endpoints
from .account import DeepalAccount
from .errors import (
    CA_TOKEN_ERROR_CODES,
    DeepalApiError,
    DeepalAuthError,
    DeepalError,
    DeepalRateLimitError,
)
from .models import Capabilities, VehicleInfo
from .mqtt.client import MqttReading, read_telemetry, wake_vehicle
from .mqtt.topics import MqttConnection, parse_connection_config

_LOGGER = logging.getLogger(__name__)

#: Categorías que se piden al endpoint REST de estado. Pedirlas todas cuesta lo
#: mismo y permite descubrir datos nuevos (temperatura exterior, etc.). La
#: clave ``vechileCriteria`` (sic) es una errata del propio servidor.
CONDITION_CATEGORIES: Final = (
    "seat",
    "door",
    "hvac",
    "charge",
    "lamp",
    "window",
    "tire",
    "vehicleStatus",
    "fuel",
)


class DeepalClient:
    """Lecturas de la cuenta y de sus vehículos."""

    def __init__(self, account: DeepalAccount) -> None:
        self.account = account

    @property
    def _transport(self):  # noqa: ANN202 - atajo interno
        return self.account.transport

    # ------------------------------------------------------------------
    # Vehículos
    # ------------------------------------------------------------------

    async def get_vehicles(self) -> list[VehicleInfo]:
        """Vehículos asociados a la cuenta (propios o compartidos). ✅"""
        data = await self.account.call(lambda: self._transport.post(endpoints.VEHICLES))
        items = data if isinstance(data, list) else (data or {}).get("list", [])
        vehicles = [
            vehicle
            for item in items
            if isinstance(item, dict) and (vehicle := VehicleInfo.from_api(item))
        ]
        return vehicles

    async def get_capabilities(self, vehicle: VehicleInfo) -> Capabilities | None:
        """Funciones que el servidor asocia al coche.

        ✅ En España funciona con ``{"vehicleId": ...}`` (con ``carId`` responde
        ``COMMON_1_1_01_005``), así que se prueba primero. Los demás
        candidatos quedan por si otra región los necesita. Nunca lanza error:
        si no hay forma, devuelve ``None``.
        """
        candidates: list[dict[str, Any]] = [
            {"vehicleId": vehicle.vehicle_id},
            {"carId": vehicle.vehicle_id},
        ]
        if vehicle.vin:
            candidates.append({"vin": vehicle.vin})
        for body in candidates:
            try:
                data = await self.account.call(
                    lambda body=body: self._transport.post(endpoints.FUNCTION_CONFIG, body)
                )
            except (DeepalRateLimitError, DeepalAuthError) as err:
                _LOGGER.debug("Capacidades no disponibles: %s", err)
                return None
            except DeepalApiError as err:
                _LOGGER.debug("Capacidades: cuerpo %s rechazado: %s", list(body), err)
                continue
            except DeepalError as err:
                _LOGGER.debug("Capacidades no disponibles: %s", err)
                return None
            codes = data.get("confList") if isinstance(data, dict) else None
            if isinstance(codes, list):
                return Capabilities(raw_codes=[str(code) for code in codes])
        return None

    # ------------------------------------------------------------------
    # Estado REST
    # ------------------------------------------------------------------

    async def get_condition(self, vehicle_id: str) -> dict[str, Any]:
        """Estado completo por REST, anidado por categoría.

        Respuesta (resumida)::

            {"vehicleStatus": {...}, "seat": {"leftFront": {...}}, "hvac": {...},
             "door": {...}, "window": {...}, "tire": {...}, "charge": {...},
             "lamp": {...}, "fuel": {...}, "lastUpdatedAt": ...}

        Qué campo alimenta cada entidad: ``telemetry/rest_map.py`` y
        ``docs/correlacion_endpoints_entidades.csv``.
        """
        payload = {
            "vechileCriteria": {category: "1" for category in CONDITION_CATEGORIES},
            "vehicleId": vehicle_id,
        }
        data = await self.account.call(
            lambda: self._transport.post(endpoints.VEHICLE_CONDITION, payload)
        )
        return data if isinstance(data, dict) else {}

    # ------------------------------------------------------------------
    # Telemetría MQTT
    # ------------------------------------------------------------------

    async def read_mqtt(
        self, vehicle: VehicleInfo, ssl_context: ssl.SSLContext
    ) -> MqttReading:
        """Lectura completa por MQTT (ver ``mqtt/__init__.py``). ✅

        Si la pasarela CA rechaza su token (``APIGW_...``), se renueva la
        sesión y se reintenta una vez.

        Raises:
            DeepalError / ConnectionError / TimeoutError / ValueError.
        """

        async def _read() -> MqttReading:
            connection, token = await self._mqtt_session(vehicle)
            return await read_telemetry(connection, token, ssl_context)

        return await self._with_ca_retry(_read)

    async def wake(self, vehicle: VehicleInfo, ssl_context: ssl.SSLContext) -> str:
        """Pide al coche que se despierte por MQTT (``TxWakeup``). ⚠️

        Devuelve el código de confirmación de la pasarela. Ver
        ``mqtt/client.wake_vehicle``. Los límites de uso (cuándo y cada
        cuánto) los pone el coordinador, no esta función.

        Raises:
            DeepalError / ConnectionError / TimeoutError / ValueError.
        """

        async def _wake() -> str:
            connection, token = await self._mqtt_session(vehicle)
            return await wake_vehicle(connection, token, ssl_context)

        return await self._with_ca_retry(_wake)

    async def _with_ca_retry(self, action):  # noqa: ANN001, ANN202
        """Ejecuta ``action``; si el token de la pasarela CA caducó, renueva y reintenta."""
        try:
            return await action()
        except DeepalApiError as err:
            if err.code not in CA_TOKEN_ERROR_CODES or not self.account.session.refresh_token:
                raise
            _LOGGER.debug("Token de la pasarela CA rechazado (%s); renovando", err.code)
            if not await self.account.refresh(force=True):
                raise
            return await action()

    async def _mqtt_session(self, vehicle: VehicleInfo) -> tuple[MqttConnection, str]:
        """Configuración del broker + token de acceso (sin reintentos propios)."""
        session = self.account.session
        if not session.user_id:
            raise DeepalAuthError("La sesión no tiene user_id; vuelve a iniciar sesión")

        config = await self.account.call(
            lambda: self._transport.post(
                endpoints.MQTT_CONN_CONF,
                {
                    "deviceId": session.device_id,
                    "carId": vehicle.vehicle_id,
                    "deviceType": 1,
                    "confTimestamp": 0,
                    "deviceTimestamp": str(int(time.time() * 1000)),
                },
                gateway=endpoints.GATEWAY_CA,
            )
        )
        if not isinstance(config, dict):
            raise DeepalApiError("getConnConf no devolvió un objeto")
        connection = parse_connection_config(config)

        token_data = await self.account.call(
            lambda: self._transport.post(
                endpoints.MQTT_AUTH_TOKEN,
                {"userId": session.user_id},
                gateway=endpoints.GATEWAY_CA,
            )
        )
        if not isinstance(token_data, dict) or not token_data.get("authToken"):
            raise DeepalApiError("getAuthTokenByUserId no devolvió authToken")
        return connection, str(token_data["authToken"])
