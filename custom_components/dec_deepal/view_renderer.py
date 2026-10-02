"""Dibujo de las **vistas por capas** (planta, isométrica...): pone las capas
PNG una encima de otra.

Qué capas se ponen lo decide :mod:`.registries.views` (a partir del
``capas.yaml`` de la vista); aquí solo se dibujan, con Pillow (viene con Home
Assistant, no hace falta instalar nada).

Para que sea ligero:

- Cada capa se lee **una vez** y se recorta a su parte visible (casi toda la
  capa es transparente); al dibujar se pega en su sitio.
- Se guardan las últimas imágenes montadas: el coche suele alternar entre
  pocos estados (todo cerrado, una puerta abierta...), así que casi siempre
  se reutiliza una ya hecha.

Todo es **bloqueante** (disco y CPU): Home Assistant lo llama en un hilo
aparte (``hass.async_add_executor_job``).
"""

from __future__ import annotations

import io
from collections import OrderedDict
from typing import Final

from PIL import Image

from .registries.views import ViewLayers

#: Cuántas imágenes montadas se guardan en memoria.
CACHE_SIZE: Final = 8


class ViewRenderer:
    """Monta una vista de un coche (una vista, un modelo y un color)."""

    def __init__(self, layers: ViewLayers, color_id: str | None) -> None:
        self._layers = layers
        self._color_id = color_id
        #: Capa recortada y su posición: ``{imagen: (recorte, (x, y))}``.
        self._pieces: dict[str, tuple[Image.Image, tuple[int, int]]] = {}
        self._size: tuple[int, int] | None = None
        self._cache: OrderedDict[tuple[str, ...], bytes] = OrderedDict()

    def _piece(self, name: str) -> tuple[Image.Image, tuple[int, int]]:
        """Capa ``name`` recortada a su parte visible (leída una vez)."""
        if name not in self._pieces:
            path = self._layers.image_path(name, self._color_id)
            with Image.open(path) as source:
                image = source.convert("RGBA")
            if self._size is None:
                self._size = image.size
            box = image.getchannel("A").getbbox()
            if box is None:  # capa vacía
                self._pieces[name] = (Image.new("RGBA", (1, 1)), (0, 0))
            else:
                self._pieces[name] = (image.crop(box), (box[0], box[1]))
        return self._pieces[name]

    def render(self, images: tuple[str, ...]) -> bytes:
        """PNG con las capas ``images`` (de abajo arriba)."""
        cached = self._cache.get(images)
        if cached is not None:
            self._cache.move_to_end(images)
            return cached

        pieces = [self._piece(name) for name in images]
        canvas = Image.new("RGBA", self._size or (1, 1), (0, 0, 0, 0))
        for piece, position in pieces:
            canvas.alpha_composite(piece, dest=position)
        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG")
        data = buffer.getvalue()

        self._cache[images] = data
        while len(self._cache) > CACHE_SIZE:
            self._cache.popitem(last=False)
        return data
