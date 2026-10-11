#!/usr/bin/env python3
"""Une los módulos de la tarjeta en el fichero que carga Home Assistant.

El código de la tarjeta está repartido en
``custom_components/dec_deepal/frontend_card/src/`` (un fichero por parte:
constantes, estilos, la tarjeta, cada ventana...). Home Assistant y HACS
necesitan **un solo fichero**, ``frontend_card/dec-deepal-card.js``: este
programa lo escribe uniendo los módulos por orden de nombre, dentro de una
función para que nada se escape al resto de la página.

No hace falta Node ni instalar nada. No transforma el código: lo que hay en
``src/`` es lo que se ejecuta.

Uso (desde la raíz del repositorio)::

    python tools/construir_tarjeta.py           # escribe dec-deepal-card.js
    python tools/construir_tarjeta.py --check   # falla si falta reconstruir

``tools/generar_idiomas.py`` también reconstruye la tarjeta (los textos son
uno de sus módulos), así que tras tocar un idioma basta con ese.

Guía: docs/tarjeta.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD_DIR = ROOT / "custom_components" / "dec_deepal" / "frontend_card"
SRC = CARD_DIR / "src"
CARD = CARD_DIR / "dec-deepal-card.js"
#: Comentario de cabecera: va fuera de la función, al principio del fichero.
HEADER = "00_cabecera.js"
#: Los módulos se unen por orden de nombre: dos cifras, guion bajo y nombre.
MODULE_NAME = re.compile(r"^\d\d_[a-z_]+\.js$")
BANNER = (
    "// FICHERO GENERADO — no editar. El código está en frontend_card/src/;\n"
    "// tras cambiarlo, ejecutar: python tools/construir_tarjeta.py\n"
)


class BuildError(Exception):
    """Los módulos no se pueden unir (el mensaje dice por qué)."""


def read_sources() -> dict[str, str]:
    """Contenido de cada módulo de ``src/``."""
    return {path.name: path.read_text(encoding="utf-8") for path in sorted(SRC.glob("*.js"))}


def build(sources: dict[str, str]) -> str:
    """Contenido de ``dec-deepal-card.js`` a partir de los módulos."""
    if HEADER not in sources:
        raise BuildError(f"Falta src/{HEADER}")
    parts = [BANNER, sources[HEADER], "\n(() => {\n"]
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


def main(argv: list[str]) -> int:
    try:
        content = build(read_sources())
    except (BuildError, OSError) as err:
        print(f"ERROR: {err}")
        return 2
    stale = not CARD.exists() or CARD.read_text(encoding="utf-8") != content
    if "--check" in argv:
        if stale:
            print(f"Sin reconstruir: {CARD.relative_to(ROOT)}")
            print("Ejecuta: python tools/construir_tarjeta.py")
        return 1 if stale else 0
    if stale:
        CARD.write_text(content, encoding="utf-8", newline="\n")
        print(f"Escrito {CARD.relative_to(ROOT)} ({len(content)} caracteres)")
    else:
        print(f"{CARD.relative_to(ROOT)} ya estaba al día.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
