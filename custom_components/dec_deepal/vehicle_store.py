"""Almacén de los datos de cada coche (mantenimiento, ITV, seguro).

Uno solo para toda la integración (``.storage/dec_deepal.vehicles``), con los
coches por bastidor: los datos son del coche, no de la cuenta. Quitar la
cuenta **no** los borra; al volver a añadirla, cada coche recupera lo suyo.
Se borran desde el panel DEC Deepal → Datos.

Formato, migración y copias: ``vehicle_data.py`` (lógica pura). Aquí solo
está lo que necesita Home Assistant: leer y escribir en disco, adoptar el
almacén antiguo (uno por cuenta, hasta la 2.3.0) y la descarga de la copia.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping
from datetime import timedelta
from typing import Any, Final

from aiohttp import web
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.components.http.auth import async_sign_path
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import vehicle_data as vd
from .const import DATA, DOMAIN, EXPORT_API

_LOGGER = logging.getLogger(__name__)

_STORE_KEY: Final = "vehicle_store"
#: Tiempo de validez del enlace de descarga de la copia.
EXPORT_LINK_MINUTES: Final = 10


def legacy_storage_key(entry_id: str) -> str:
    """Nombre del almacén antiguo de una cuenta (hasta la 2.3.0)."""
    return f"{DOMAIN}.{entry_id}"


class _Store(Store[dict[str, Any]]):
    """Almacén con migración: los formatos antiguos pasan por ``vehicle_data.migrate``."""

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, Any]:
        return vd.migrate(old_data, old_major_version)


class VehicleStore:
    """Datos de todos los coches, en memoria y en disco."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store = _Store(hass, vd.DATA_VERSION, f"{DOMAIN}.vehicles")
        self._cars: dict[str, dict[str, Any]] = {}
        self._loaded = False

    async def async_load(self) -> None:
        """Lee el disco (solo la primera vez)."""
        if self._loaded:
            return
        self._loaded = True
        data = await self._store.async_load()
        self._cars = vd.migrate(data, vd.DATA_VERSION)["cars"]

    async def async_adopt_legacy(self, entry_id: str, keys: Mapping[str, str]) -> None:
        """Pasa a este almacén los datos del almacén antiguo de una cuenta.

        Se hace una vez: después el antiguo se borra. Lo que ya esté aquí
        para un coche no se pisa.

        Args:
            entry_id: cuenta cuyos datos se adoptan.
            keys: clave (bastidor) de cada identificador de coche de la cuenta.
        """
        legacy = Store[dict[str, Any]](self.hass, 1, legacy_storage_key(entry_id))
        data = await legacy.async_load()
        if data is None:
            return
        adopted = 0
        for key, car in vd.from_legacy(data, keys).items():
            if key not in self._cars:
                self._cars[key] = car
                adopted += 1
        await self.async_save()
        await legacy.async_remove()
        _LOGGER.info("Datos de %d coche(s) pasados al almacén por bastidor", adopted)

    # ------------------------------------------------------------------
    # Lectura y escritura
    # ------------------------------------------------------------------

    def car(self, key: str) -> dict[str, Any]:
        """Datos de un coche (vacío si no hay nada guardado)."""
        return dict(self._cars.get(key, {}))

    def cars(self) -> dict[str, dict[str, Any]]:
        """Todos los coches guardados."""
        return {key: dict(car) for key, car in self._cars.items()}

    @callback
    def set_car(self, key: str, car: dict[str, Any]) -> None:
        """Cambia los datos de un coche (en memoria; falta guardar)."""
        self._cars[key] = car

    async def async_save(self) -> None:
        """Escribe en disco ya."""
        await self._store.async_save({"cars": self._cars})

    @callback
    def async_delay_save(self) -> None:
        """Escribe en disco dentro de un momento (varios cambios seguidos, una escritura)."""
        self._store.async_delay_save(lambda: {"cars": self._cars}, 2)

    async def async_delete(self, keys: Iterable[str]) -> None:
        """Borra los datos de unos coches."""
        for key in keys:
            self._cars.pop(key, None)
        await self.async_save()

    # ------------------------------------------------------------------
    # Copia de seguridad
    # ------------------------------------------------------------------

    def export(self) -> dict[str, Any]:
        """Contenido de la copia (ver ``vehicle_data.export_payload``)."""
        return vd.export_payload(self._cars, dt_util.now())

    async def async_import(self, cars: Mapping[str, dict[str, Any]]) -> None:
        """Carga una copia ya comprobada: sustituye las fichas de esos coches.

        Del coche se conserva lo que no viaja en la copia (testigos avisados)
        y la apariencia, si la copia no trae una.
        """
        for key, imported in cars.items():
            current = self._cars.get(key, {})
            car = {field: value for field, value in current.items() if field not in vd.RECORDS}
            car.update(imported)
            self._cars[key] = car
        await self.async_save()


@callback
def async_get_store(hass: HomeAssistant) -> VehicleStore:
    """El almacén de la integración (se crea la primera vez)."""
    domain_data = hass.data.setdefault(DATA, {})
    if _STORE_KEY not in domain_data:
        domain_data[_STORE_KEY] = VehicleStore(hass)
    return domain_data[_STORE_KEY]


# ---------------------------------------------------------------------------
# Descarga de la copia
# ---------------------------------------------------------------------------


class ExportView(HomeAssistantView):
    """``GET /api/dec_deepal/export`` → la copia, como fichero para descargar."""

    url = EXPORT_API
    name = "api:dec_deepal:export"

    async def get(self, request: web.Request) -> web.Response:
        """Devuelve la copia de los datos de los coches."""
        hass = request.app[KEY_HASS]
        store = async_get_store(hass)
        await store.async_load()
        name = f"dec_deepal_datos_{dt_util.now():%Y-%m-%d}.json"
        return web.Response(
            text=json.dumps(store.export(), ensure_ascii=False, indent=2),
            content_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{name}"',
                "Cache-Control": "no-store",
            },
        )


@callback
def async_export_url(hass: HomeAssistant, *, absolute: bool = False) -> str:
    """Enlace de descarga de la copia, válido unos minutos y sin iniciar sesión.

    Va firmado (como las descargas de Home Assistant): quien no tenga el
    enlace no puede descargar nada, y el enlace caduca.

    Args:
        absolute: con la dirección de Home Assistant delante (para mandarlo
            en una notificación). Se usa la dirección con la que el usuario
            está entrando ahora; si no se sabe, la configurada en Ajustes →
            Sistema → Red; y si tampoco hay, el enlace sale sin dirección.
    """
    try:
        path = async_sign_path(hass, EXPORT_API, timedelta(minutes=EXPORT_LINK_MINUTES))
    except (KeyError, RuntimeError):  # sin servidor web (pruebas): enlace sin firmar
        path = EXPORT_API
    if not absolute:
        return path
    for current in (True, False):
        try:
            return get_url(hass, require_current_request=current).rstrip("/") + path
        except NoURLAvailableError:
            continue
    return path


@callback
def async_register_export(hass: HomeAssistant) -> None:
    """Registra la vista de descarga (una vez por arranque)."""
    hass.http.register_view(ExportView())
