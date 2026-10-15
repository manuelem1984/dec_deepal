#!/usr/bin/env python3
"""Genera la "Vista lateral" del S05 Max sin tapacubos, en cada color.

Las fotos laterales del catálogo (``vehicles/photos/s05_2024/max_<color>.png``)
llevan el tapacubos. Este programa pone encima la llanta de una foto real
(``tools/fuentes/llanta_max_sin_tapacubos.jpg``, cedida por la Comunidad):

1. **Mide el tapacubos** de cada foto: su borde claro sobre el neumático
   oscuro, en todas direcciones, y un círculo ajustado a esos puntos.
2. **Endereza la llanta**: la foto está algo ladeada y la llanta sale como
   una elipse; el recorte de ``fuentes/`` es justo esa elipse y se convierte
   en un círculo del tamaño del tapacubos.
3. **La pasa a negro brillante**: los radios negros con sus reflejos; lo que
   se ve entre ellos (disco, pinza), apagado.

Escribe ``max_<color>_open.png`` junto a cada foto. Se ejecuta a mano cuando
cambie la foto de la llanta o las del catálogo (no hace falta en cada versión)::

    python tools/generar_vista_lateral_llanta.py

Necesita Pillow y numpy (vienen con Home Assistant).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
PHOTOS = ROOT / "custom_components" / "dec_deepal" / "vehicles" / "photos" / "s05_2024"
SOURCE = ROOT / "tools" / "fuentes" / "llanta_max_sin_tapacubos.jpg"
COLORS = ("andromeda_blue", "deep_space_black", "ganymade_grey", "mercury_silver", "moonlight_white")
#: Centro aproximado de cada rueda en las fotos laterales (de aquí se busca el tapacubos).
WHEEL_GUESSES = ((603, 485), (1700, 485))
#: Se trabaja a 4x y se reduce al final: bordes suaves.
SS = 4


def measure_hubcap(photo: Image.Image, guess: tuple[int, int]) -> tuple[float, float, float]:
    """Centro y radio del tapacubos: círculo ajustado a su borde claro."""
    lum = np.asarray(photo.convert("L"), float)
    alpha = np.asarray(photo)[:, :, 3]
    edge = []
    for degree in range(360):
        angle = math.radians(degree)
        last = None
        for radius in range(60, 140):
            x = int(round(guess[0] + radius * math.cos(angle)))
            y = int(round(guess[1] + radius * math.sin(angle)))
            if 0 <= y < lum.shape[0] and 0 <= x < lum.shape[1] and alpha[y, x] > 0 and lum[y, x] > 150:
                last = (x, y)
        if last:
            edge.append(last)

    def fit(points: list[tuple[int, int]]) -> tuple[float, float, float]:
        xs = np.array([p[0] for p in points], float)
        ys = np.array([p[1] for p in points], float)
        a = np.c_[2 * xs, 2 * ys, np.ones(len(xs))]
        cx, cy, c = np.linalg.lstsq(a, xs**2 + ys**2, rcond=None)[0]
        return cx, cy, math.sqrt(c + cx**2 + cy**2)

    cx, cy, radius = fit(edge)
    # Segunda pasada sin los puntos sueltos (letras del neumático, reflejos).
    return fit([p for p in edge if abs(math.dist(p, (cx, cy)) - radius) < 6])


def black_rim(source: Image.Image, radius: float) -> Image.Image:
    """La llanta enderezada a círculo y en negro brillante (a ``SS`` aumentos)."""
    size = int(round(radius * 2 * SS))
    rim = source.resize((size, size), Image.LANCZOS)
    lum = np.asarray(rim.convert("L"), float) / 255
    tone = (np.clip(lum, 0, 1) ** 2.2 * 0.92 * 255).astype(np.uint8)
    # Un punto azulado muy leve, como el negro de las fotos del catálogo.
    rgb = np.stack([tone, tone, np.clip(tone.astype(int) + 3, 0, 255).astype(np.uint8)], axis=-1)
    rim = Image.fromarray(rgb, "RGB").convert("RGBA")
    # Sombra en el borde: la pestaña de la llanta junto al neumático.
    shade = Image.new("L", rim.size, 0)
    ImageDraw.Draw(shade).ellipse((0, 0, size - 1, size - 1), outline=170, width=3 * SS)
    shade = shade.filter(ImageFilter.GaussianBlur(2 * SS))
    rim = Image.composite(Image.new("RGBA", rim.size, (8, 8, 10, 255)), rim, shade)
    mask = Image.new("L", rim.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    rim.putalpha(mask.filter(ImageFilter.GaussianBlur(0.8 * SS)))
    return rim


def open_wheels(photo: Image.Image, source: Image.Image) -> tuple[Image.Image, list]:
    """La foto con las dos llantas sin tapacubos.

    Solo se toca lo de dentro de cada tapacubos: las llantas se montan en una
    capa aparte a ``SS`` aumentos, que se reduce y se pone encima de la foto
    original (que no se reescala: sin halos alrededor del coche).
    """
    layer = Image.new("RGBA", (photo.width * SS, photo.height * SS), (0, 0, 0, 0))
    wheels = []
    for guess in WHEEL_GUESSES:
        cx, cy, radius = measure_hubcap(photo, guess)
        radius += 0.6  # un pelo más: tapa el borde claro del tapacubos
        wheels.append((cx, cy, radius))
        layer.alpha_composite(black_rim(source, radius), (int(round((cx - radius) * SS)), int(round((cy - radius) * SS))))
    result = photo.convert("RGBA")
    result.alpha_composite(layer.resize(photo.size, Image.BOX))
    return result, wheels


def save_like(original: Image.Image, result: Image.Image, target: Path) -> None:
    """Guarda como las fotos del catálogo: PNG con paleta de 256 colores (ligero).

    La paleta se calcula para la foto ya con las llantas (la original apenas
    tiene grises oscuros y la llanta saldría con ruido). Fuera de las ruedas,
    la diferencia con la original es inapreciable.
    """
    if original.mode != "P":
        raise SystemExit(f"{target.name}: la foto original debería ser PNG con paleta")
    result.quantize(colors=256, method=Image.Quantize.FASTOCTREE).save(target, optimize=True)


def main() -> int:
    source = Image.open(SOURCE).convert("RGB")
    for color in COLORS:
        original = Image.open(PHOTOS / f"max_{color}.png")
        result, _wheels = open_wheels(original.convert("RGBA"), source)
        target = PHOTOS / f"max_{color}_open.png"
        save_like(original, result, target)
        print(f"Escrito {target.relative_to(ROOT)} ({target.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
