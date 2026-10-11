#!/usr/bin/env python3
"""Une los módulos de la tarjeta y del panel en los ficheros que carga Home Assistant.

El código de la tarjeta está repartido en
``custom_components/dec_deepal/frontend_card/src/`` (un fichero por parte:
constantes, estilos, la tarjeta, cada ventana...). Home Assistant y HACS
necesitan **un solo fichero**, ``frontend_card/dec-deepal-card.js``: este
programa lo escribe uniendo los módulos por orden de nombre, dentro de una
función para que nada se escape al resto de la página.

Lo mismo con el panel de la barra lateral: ``frontend_panel/src/`` →
``frontend_panel/dec-deepal-panel.js``.

No hace falta Node ni instalar nada. No transforma el código: lo que hay en
``src/`` es lo que se ejecuta.

Uso (desde la raíz del repositorio)::

    python tools/construir_tarjeta.py           # escribe la tarjeta y el panel
    python tools/construir_tarjeta.py --check   # falla si falta reconstruir

``tools/generar_idiomas.py`` también reconstruye la tarjeta (los textos son
uno de sus módulos), así que tras tocar un idioma basta con ese.

Guía: docs/tarjeta.md y docs/panel.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD_DIR = ROOT / "custom_components" / "dec_deepal" / "frontend_card"
SRC = CARD_DIR / "src"
CARD = CARD_DIR / "dec-deepal-card.js"
PANEL_DIR = ROOT / "custom_components" / "dec_deepal" / "frontend_panel"
PANEL_SRC = PANEL_DIR / "src"
PANEL = PANEL_DIR / "dec-deepal-panel.js"
#: Lo que se construye: ``(carpeta de módulos, fichero resultante)``.
TARGETS = ((SRC, CARD), (PANEL_SRC, PANEL))
#: Comentario de cabecera: va fuera de la función, al principio del fichero.
HEADER = "00_cabecera.js"
#: Los módulos se unen por orden de nombre: dos cifras, guion bajo y nombre.
MODULE_NAME = re.compile(r"^\d\d_[a-z_]+\.js$")
BANNER = (
    "// FICHERO GENERADO — no editar. El código está en frontend_card/src/;\n"
    "// tras cambiarlo, ejecutar: python tools/construir_tarjeta.py\n"
)
PANEL_BANNER = BANNER.replace("frontend_card", "frontend_panel")


class BuildError(Exception):
    """Los módulos no se pueden unir (el mensaje dice por qué)."""


def read_sources(src: Path = SRC) -> dict[str, str]:
    """Contenido de cada módulo de una carpeta ``src/`` (por defecto, la de la tarjeta)."""
    return {path.name: path.read_text(encoding="utf-8") for path in sorted(src.glob("*.js"))}


def build(sources: dict[str, str], banner: str = BANNER) -> str:
    """Contenido del fichero único (tarjeta o panel) a partir de sus módulos."""
    if HEADER not in sources:
        raise BuildError(f"Falta src/{HEADER}")
    parts = [banner, sources[HEADER], "\n(() => {\n"]
    for name in sorted(sources):
        if name == HEADER:
            continue
        if not MODULE_NAME.match(name):
            raise BuildError(f"src/{name}: el nombre debe ser como '62_itv.js'")
        content = sources[name]
        if not content.endswith("\n"):
            raise BuildError(f"src/{name}: debe terminar con un salto de línea")
        label = f"  // ── src/{name} "
        parts.append(f"{label}{'─' * max(3, 79 - len(label))}\n{content}\n")
    parts[-1] = parts[-1][:-1]  # sin línea en blanco antes del cierre
    parts.append("})();\n")
    return "".join(parts)


def outputs() -> dict[Path, str]:
    """Contenido de cada fichero que se construye."""
    return {
        target: build(read_sources(src), PANEL_BANNER if target == PANEL else BANNER)
        for src, target in TARGETS
    }


def main(argv: list[str]) -> int:
    try:
        built = outputs()
    except (BuildError, OSError) as err:
        print(f"ERROR: {err}")
        return 2
    stale = [
        target
        for target, content in built.items()
        if not target.exists() or target.read_text(encoding="utf-8") != content
    ]
    if "--check" in argv:
        for target in stale:
            print(f"Sin reconstruir: {target.relative_to(ROOT)}")
        if stale:
            print("Ejecuta: python tools/construir_tarjeta.py")
        return 1 if stale else 0
    for target, content in built.items():
        if target in stale:
            target.write_text(content, encoding="utf-8", newline="\n")
            print(f"Escrito {target.relative_to(ROOT)} ({len(content)} caracteres)")
        else:
            print(f"{target.relative_to(ROOT)} ya estaba al día.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
