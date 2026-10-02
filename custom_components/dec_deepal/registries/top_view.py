"""Cargador de la **vista de planta**: ``vehicles/vista_planta/<carpeta>/capas.yaml``.

La vista de planta es el coche visto desde arriba, montado con capas PNG
transparentes que se ponen una encima de otra según el estado (puertas,
capó, maletero, ventanillas, luces). Este módulo:

- lee y valida ``capas.yaml`` (:func:`load_top_view`);
- decide **qué imágenes** se ponen para un estado dado
  (:meth:`TopViewLayers.select`), sin dibujar nada. El dibujo (con Pillow)
  está en ``top_view.py``, fuera de los catálogos.

Es Python puro (sin Home Assistant ni Pillow): se prueba con ``pytest``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .errors import RegistryError, as_dict, read_yaml

#: Nombre del fichero de capas dentro de la carpeta de cada modelo.
LAYERS_FILE: Final = "capas.yaml"


@dataclass(frozen=True, slots=True)
class Layer:
    """Una capa de la vista de planta.

    Una capa fija solo tiene ``image``. Una capa con señal pone ``when_on``
    o ``when_off`` según el valor de ``signal`` (``None`` = nada).
    """

    image: str | None = None
    signal: str | None = None
    when_on: str | None = None
    when_off: str | None = None
    #: Si esta señal está a "sí", la capa no se pone.
    unless: str | None = None


@dataclass(frozen=True, slots=True)
class Selection:
    """Resultado de :meth:`TopViewLayers.select`."""

    #: Imágenes a poner, de abajo arriba.
    images: tuple[str, ...]
    #: Señales que están a "sí" (abierto / encendido).
    active: tuple[str, ...]
    #: Señales sin dato (se han dibujado como último valor o "no").
    unknown: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TopViewLayers:
    """Capas de la vista de planta de un modelo."""

    directory: Path
    layers: tuple[Layer, ...]

    @property
    def signals(self) -> tuple[str, ...]:
        """Señales que usa la vista (sin repetir, en orden)."""
        names: list[str] = []
        for layer in self.layers:
            for name in (layer.signal, layer.unless):
                if name and name not in names:
                    names.append(name)
        return tuple(names)

    @property
    def images(self) -> tuple[str, ...]:
        """Todas las imágenes que puede usar la vista (sin repetir)."""
        names: list[str] = []
        for layer in self.layers:
            for name in (layer.image, layer.when_on, layer.when_off):
                if name and name not in names:
                    names.append(name)
        return tuple(names)

    def image_path(self, name: str, color_id: str | None) -> Path:
        """Ruta de una imagen: la del color elegido si existe, o la de por defecto."""
        if color_id:
            candidate = self.directory / color_id / name
            if candidate.is_file():
                return candidate
        return self.directory / name

    def select(self, value: Callable[[str], bool | None]) -> Selection:
        """Elige las imágenes para un estado.

        Args:
            value: devuelve el valor de una señal: ``True``, ``False`` o
                ``None`` si no se conoce. Quien llama decide qué hacer con
                los desconocidos (``top_view.py`` usa el último valor
                conocido); aquí ``None`` se dibuja como "no".
        """
        images: list[str] = []
        active: list[str] = []
        unknown: list[str] = []
        for name in self.signals:
            state = value(name)
            if state is None:
                unknown.append(name)
            elif state:
                active.append(name)
        for layer in self.layers:
            if layer.image:
                images.append(layer.image)
                continue
            if layer.unless and layer.unless in active:
                continue
            image = layer.when_on if layer.signal in active else layer.when_off
            if image:
                images.append(image)
        return Selection(tuple(images), tuple(active), tuple(unknown))


def _optional_str(raw: dict, key: str) -> str | None:
    value = raw.get(key)
    return None if value in (None, "") else str(value)


def load_top_view(directory: Path) -> TopViewLayers:
    """Lee y valida ``<directory>/capas.yaml``.

    Comprueba que cada capa es fija o tiene señal con al menos una imagen, y
    que todas las imágenes existen en la carpeta.

    Raises:
        RegistryError: falta el fichero, una imagen o un campo.
    """
    path = directory / LAYERS_FILE
    data = read_yaml(path)
    where_file = f"vista_planta/{directory.name}/{LAYERS_FILE}"
    raw_layers = data.get("capas")
    if not isinstance(raw_layers, list) or not raw_layers:
        raise RegistryError(f"{where_file}: 'capas' debe ser una lista no vacía")

    layers: list[Layer] = []
    for index, raw in enumerate(raw_layers):
        where = f"{where_file} → capas[{index}]"
        raw = as_dict(raw, where)
        layer = Layer(
            image=_optional_str(raw, "imagen"),
            signal=_optional_str(raw, "senal"),
            when_on=_optional_str(raw, "si_activo"),
            when_off=_optional_str(raw, "si_inactivo"),
            unless=_optional_str(raw, "salvo_si"),
        )
        if layer.image and layer.signal:
            raise RegistryError(f"{where}: usa 'imagen' o 'senal', no las dos")
        if not layer.image and not (layer.signal and (layer.when_on or layer.when_off)):
            raise RegistryError(
                f"{where}: falta 'imagen', o 'senal' con 'si_activo'/'si_inactivo'"
            )
        layers.append(layer)

    result = TopViewLayers(directory=directory, layers=tuple(layers))
    missing = [name for name in result.images if not (directory / name).is_file()]
    if missing:
        raise RegistryError(f"{where_file}: faltan imágenes {missing}")
    return result
