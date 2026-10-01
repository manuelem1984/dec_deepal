"""Modelos de datos sencillos que devuelve el cliente.

Son ``dataclass`` normales (sin pydantic) para no añadir dependencias.

- :class:`VehicleInfo`      — un vehículo de la cuenta (de ``car/vehicles``).
- :class:`CommandResult`    — resultado de un comando (``control-result``).
- :class:`Capabilities`     — funciones que el servidor dice que tiene el coche.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Final


# ---------------------------------------------------------------------------
# Vehículo
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class VehicleInfo:
    """Datos de un vehículo tal como los devuelve ``car/vehicles``.

    Se guarda en ``entry.data["vehicles"]`` para no tener que pedir la lista
    en cada arranque.
    """

    vehicle_id: str  # "carId": identificador interno usado en todas las peticiones
    vin: str | None = None
    model_name: str | None = None  # "modelName", p. ej. "Deepal S05 ..."
    model_code: str | None = None
    series_name: str | None = None
    series_code: str | None = None
    nickname: str | None = None  # apodo puesto por el usuario en la app
    image_url: str | None = None  # foto oficial del modelo, si la hay
    protocol_type: str | None = None  # "MQTT" en el S05
    license_plate: str | None = None  # matrícula, si el servidor la tiene

    @property
    def uses_mqtt(self) -> bool:
        """``True`` si el coche envía su telemetría por MQTT (caso del S05)."""
        return (self.protocol_type or "").upper() == "MQTT"

    @property
    def display_name(self) -> str:
        """Nombre legible para el dispositivo de Home Assistant."""
        return (
            self.nickname
            or self.model_name
            or self.series_name
            or (f"Deepal {self.vin[-6:]}" if self.vin else f"Deepal {self.vehicle_id}")
        )

    def to_dict(self) -> dict[str, Any]:
        """Dict apto para guardar en la entrada de configuración."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VehicleInfo:
        """Reconstruye desde lo guardado, ignorando claves desconocidas."""
        known = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        return cls(**{key: value for key, value in data.items() if key in known})

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> VehicleInfo | None:
        """Crea un vehículo desde un elemento de la respuesta de ``car/vehicles``.

        Devuelve ``None`` si el elemento no trae ``carId`` (no se puede usar).
        Para la imagen se prueban varios nombres de campo porque cambian según
        la región y la versión del servidor.
        """
        vehicle_id = item.get("carId") or item.get("car_id")
        if vehicle_id in (None, ""):
            return None
        return cls(
            vehicle_id=str(vehicle_id),
            vin=_text(item.get("vin")),
            model_name=_text(item.get("modelName")),
            model_code=_text(item.get("modelCode")),
            series_name=_text(item.get("seriesName")),
            series_code=_text(item.get("seriesCode")),
            nickname=_text(item.get("nickName") or item.get("carName")),
            image_url=_text(
                item.get("vehicleImageUrl")
                or item.get("imgUrl")
                or item.get("imageUrl")
                or item.get("carImageUrl")
                or item.get("modelImageUrl")
            ),
            protocol_type=_text(item.get("protocolType")),
            license_plate=_text(item.get("licensePlate") or item.get("plateNumber")),
        )


def _text(value: Any) -> str | None:
    """Texto limpio o ``None``."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


# ---------------------------------------------------------------------------
# Resultado de un comando
# ---------------------------------------------------------------------------


class CommandStatus(StrEnum):
    """Estado normalizado de un comando enviado al coche."""

    PENDING = "pending"  # el coche aún no ha contestado
    SUCCESS = "success"  # el coche lo ejecutó
    ALREADY_DONE = "already_done"  # ya estaba así (p. ej. ya cerrado)
    FAILED = "failed"  # el coche lo rechazó


#: ``resultCode`` → estado. Cualquier código no listado se trata como fallo
#: (por prudencia: mejor avisar que dar por bueno algo desconocido).
RESULT_CODES: Final[dict[int, CommandStatus]] = {
    -100: CommandStatus.PENDING,
    0: CommandStatus.SUCCESS,
    1201: CommandStatus.SUCCESS,
    1015: CommandStatus.ALREADY_DONE,
    -1: CommandStatus.FAILED,
    -2: CommandStatus.FAILED,
}


@dataclass(slots=True)
class CommandResult:
    """Resultado de consultar ``control/control-result``."""

    status: CommandStatus
    code: int | None = None
    error_message: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> CommandResult:
        """Clasifica la respuesta según su ``resultCode``.

        Sin ``resultCode`` → pendiente (el coche aún no contestó).
        """
        raw_code = payload.get("resultCode")
        if raw_code is None:
            return cls(CommandStatus.PENDING, raw=payload)
        try:
            code = int(raw_code)
        except (TypeError, ValueError):
            return cls(CommandStatus.FAILED, error_message=str(raw_code), raw=payload)
        message = payload.get("errorMsg")
        return cls(
            RESULT_CODES.get(code, CommandStatus.FAILED),
            code=code,
            error_message=None if message is None else str(message),
            raw=payload,
        )

    @property
    def vehicle_asleep_hint(self) -> bool:
        """``True`` si el error parece "coche dormido/ocupado" (``TBOX_...``)."""
        return "TBOX_" in (self.error_message or "")


# ---------------------------------------------------------------------------
# Capacidades del vehículo
# ---------------------------------------------------------------------------

#: Códigos que indican ventilación de asientos delanteros.
#: - ``#driverSeatVent`` / ``#passengerSeatVent``: los que documenta Deepal
#:   Alternative (otras regiones).
#: - ``FronSeatVentilationSW``, ``FronSeatVentilationLevel``,
#:   ``DriverSeatVentilatorSW``, ``DriverSeatVentilatorLevel``, ``#vent3``:
#:   los que manda el servidor europeo para un S05 **Max** de España
#:   (diagnóstico real, 30-09-2026). ⚠️ Falta un diagnóstico de un **Pro** para
#:   confirmar que el Pro NO los manda.
SEAT_VENT_CODES: Final = frozenset(
    {
        "#driverSeatVent",
        "#passengerSeatVent",
        "FronSeatVentilationSW",
        "FronSeatVentilationLevel",
        "DriverSeatVentilatorSW",
        "DriverSeatVentilatorLevel",
        "#vent3",
    }
)
FUEL_CODE: Final = "#oilMileage"


@dataclass(slots=True)
class Capabilities:
    """Lista de funciones que el servidor asocia al vehículo.

    ✅ El endpoint ``function-config`` responde en España (cuerpo con
    ``vehicleId``). Solo se usa como **sugerencia** de versión en el asistente
    de Configurar / Reparaciones; nunca decide nada por sí solo.
    """

    raw_codes: list[str] = field(default_factory=list)

    @property
    def has_front_seat_ventilation(self) -> bool:
        """Ventilación de asientos delanteros. En el S05 solo la tiene el Max."""
        return bool(SEAT_VENT_CODES & set(self.raw_codes))

    @property
    def has_fuel(self) -> bool:
        """Depósito de combustible (híbridos enchufables / autonomía extendida)."""
        return FUEL_CODE in self.raw_codes

    @property
    def trim_hint(self) -> str | None:
        """Pista de versión del S05: ``"max"`` si tiene ventilación, si no ``"pro"``.

        Idea de Deepal Alternative. Solo es una pista: se propone por defecto
        en el asistente y el usuario la confirma o la cambia.
        """
        if not self.raw_codes:
            return None
        return "max" if self.has_front_seat_ventilation else "pro"
