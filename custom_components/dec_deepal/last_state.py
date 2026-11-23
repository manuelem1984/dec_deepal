"""Último estado conocido de cada coche, guardado para después de reiniciar.

Las señales que se conservan entre lecturas (``KEEP_LAST``: confort, clima,
testigos, combustible, ruedas...) y el cuentakilómetros se guardan en
``.storage/dec_deepal.last_state``. Al arrancar Home Assistant con el coche
dormido, la primera lectura no trae esas señales; sin esto saldrían como
"Desconocido" hasta que el coche se despierte.

Solo se guardan valores sencillos (números, textos, sí/no): nada de la cuenta
ni del coche más allá de su estado.
"""

from __future__ import annotations

from typing import Any, Final

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .telemetry import signals as s
from .telemetry.state import KEEP_LAST, SOURCE_PREVIOUS, VehicleState

STORAGE_KEY: Final = f"{DOMAIN}.last_state"
STORAGE_VERSION: Final = 1
#: Segundos que se espera antes de escribir (agrupa varias lecturas seguidas).
SAVE_DELAY: Final = 30
#: Señales que se guardan.
SAVED_SIGNALS: Final = KEEP_LAST | {s.ODOMETER_KM}


def _plain(value: Any) -> bool:
    """¿Se puede guardar tal cual en JSON?"""
    return isinstance(value, bool | int | float | str)


class LastStateStore:
    """Lee y guarda el último estado de los coches (uno por vehículo)."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Crea el almacén (aún sin leer)."""
        self._store: Store[dict[str, dict[str, Any]]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        """Lee lo guardado (una vez, al cargar la integración)."""
        loaded = await self._store.async_load()
        self._data = loaded if isinstance(loaded, dict) else {}

    def restored(self, vehicle_id: str) -> VehicleState | None:
        """Estado guardado de un coche, como lectura anterior; ``None`` si no hay."""
        saved = self._data.get(vehicle_id)
        if not isinstance(saved, dict):
            return None
        values = {signal: value for signal, value in saved.items() if signal in SAVED_SIGNALS and _plain(value)}
        if not values:
            return None
        return VehicleState(values=values, sources=dict.fromkeys(values, SOURCE_PREVIOUS))

    def remember(self, vehicle_id: str, state: VehicleState) -> None:
        """Apunta el estado de un coche y programa la escritura."""
        values = {
            signal: value
            for signal, value in state.values.items()
            if signal in SAVED_SIGNALS and _plain(value)
        }
        if not values or self._data.get(vehicle_id) == values:
            return
        self._data[vehicle_id] = values
        self._store.async_delay_save(lambda: self._data, SAVE_DELAY)
