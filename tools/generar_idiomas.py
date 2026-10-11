#!/usr/bin/env python3
"""Genera todos los textos de la integración a partir de ``idiomas/``.

Los textos se escriben UNA vez, en ``custom_components/dec_deepal/idiomas/``:
un fichero por idioma (``es.json``, ``en.json``...) con cuatro secciones:

- ``integracion``  Configurar, entidades, errores y acciones (lo que Home
                   Assistant llama "translations").
- ``avisos``       Mensajes que se envían al móvil.
- ``tarjeta``      Textos de la tarjeta de los paneles.
- ``catalogo``     Nombres del catálogo (operaciones de mantenimiento...).

Este programa lee esos ficheros y escribe lo que usa cada parte:

- ``translations/<idioma>.json`` y ``strings.json`` (Home Assistant).
- ``textos_generados.py`` (avisos y catálogo, para el código Python).
- La tabla de textos de la tarjeta (``frontend_card/src/20_textos.js``) y,
  con ella, la tarjeta entera (``frontend_card/dec-deepal-card.js``; ver
  ``tools/construir_tarjeta.py``).

Reglas (``idiomas/idiomas.json``):

- El idioma **base** (inglés) debe estar completo. A los demás, lo que les
  falte se rellena con el texto del idioma base: se puede publicar un idioma
  a medias e ir completándolo.
- Un idioma **prestado** no tiene fichero: usa el de otro (catalán, gallego y
  euskera usan el español).

Uso (desde la raíz del repositorio, sin instalar nada)::

    python tools/generar_idiomas.py            # genera
    python tools/generar_idiomas.py --check    # falla si falta regenerar
    python tools/generar_idiomas.py --informe  # qué le falta a cada idioma

Guía: docs/idiomas.md
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import construir_tarjeta  # noqa: E402 - el otro programa de esta carpeta

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "dec_deepal"
SOURCES = INTEGRATION / "idiomas"
CONFIG = SOURCES / "idiomas.json"
SECTIONS = ("integracion", "avisos", "tarjeta", "catalogo")
PLACEHOLDER = re.compile(r"\{[a-z_]+\}")
CARD = construir_tarjeta.CARD
#: Módulo de la tarjeta con la tabla de textos (se genera entero).
CARD_TEXTS = "20_textos.js"
CARD_TEXTS_HEADER = """\
  // ---------------------------------------------------------------------------
  // Textos por idioma
  // ---------------------------------------------------------------------------
  // FICHERO GENERADO a partir de idiomas/<idioma>.json (sección "tarjeta") con
  // tools/generar_idiomas.py. Para cambiar un texto o añadir un idioma, editar
  // esos ficheros y volver a generar. Guía: docs/idiomas.md
  //
  //   BASE_LANGUAGE       idioma que se usa si el del usuario no está traducido
  //   BORROWED_LANGUAGES  idiomas sin traducción propia que usan la de otro
  //   TEXTS               { idioma: { clave: texto } }, ya completa (a un
  //                       idioma a medias se le rellena con el idioma base)
"""


class LanguageError(Exception):
    """Un fichero de idioma tiene un error (el mensaje dice cuál)."""


def flatten(tree: object, prefix: str = "") -> dict[str, str]:
    """``{"a": {"b": "x"}}`` → ``{"a.b": "x"}``."""
    if not isinstance(tree, dict):
        return {prefix: tree}
    flat: dict[str, str] = {}
    for key, value in tree.items():
        flat.update(flatten(value, f"{prefix}.{key}" if prefix else key))
    return flat


def fill(base: object, other: object) -> object:
    """Estructura y orden del idioma base, con los textos de ``other`` donde existan."""
    if isinstance(base, dict):
        other = other if isinstance(other, dict) else {}
        return {key: fill(value, other.get(key)) for key, value in base.items()}
    return base if other is None or isinstance(other, dict) else other


def load() -> tuple[dict, dict[str, dict]]:
    """Lee la configuración y los ficheros de idioma, y los valida."""
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    base = config["base"]
    languages = {code: json.loads((SOURCES / f"{code}.json").read_text(encoding="utf-8")) for code in config["idiomas"]}
    if base not in languages:
        raise LanguageError(f"El idioma base '{base}' no está en la lista de idiomas")
    for code, target in config.get("prestados", {}).items():
        if target not in languages or code in languages:
            raise LanguageError(f"Idioma prestado '{code}' → '{target}': el destino debe ser un idioma con fichero")
    reference = {section: flatten(languages[base].get(section, {})) for section in SECTIONS}
    for code, data in languages.items():
        unknown = set(data) - set(SECTIONS)
        if unknown:
            raise LanguageError(f"{code}.json: secciones desconocidas {sorted(unknown)}")
        for section in SECTIONS:
            texts = flatten(data.get(section, {}))
            extra = sorted(set(texts) - set(reference[section]))
            if extra:
                raise LanguageError(f"{code}.json → {section}: claves que no existen en {base}.json: {extra[:8]}")
            for key, text in texts.items():
                if not isinstance(text, str):
                    raise LanguageError(f"{code}.json → {section}.{key}: debe ser un texto")
                if sorted(PLACEHOLDER.findall(text)) != sorted(PLACEHOLDER.findall(reference[section][key])):
                    raise LanguageError(
                        f"{code}.json → {section}.{key}: los marcadores entre llaves no coinciden con {base}.json"
                    )
                if section == "integracion" and "<" in text:
                    raise LanguageError(f"{code}.json → {section}.{key}: Home Assistant no admite '<' en los textos")
    return config, languages


def missing(config: dict, languages: dict[str, dict]) -> dict[str, list[str]]:
    """Claves que le faltan a cada idioma (se rellenarán con el idioma base)."""
    base = languages[config["base"]]
    result = {}
    for code, data in languages.items():
        gaps = []
        for section in SECTIONS:
            have = flatten(data.get(section, {}))
            gaps += [f"{section}.{key}" for key in flatten(base.get(section, {})) if key not in have]
        result[code] = gaps
    return result


def dump(tree: object) -> str:
    return json.dumps(tree, ensure_ascii=False, indent=2) + "\n"


def outputs(config: dict, languages: dict[str, dict]) -> dict[Path, str]:
    """Contenido de cada fichero generado."""
    base_code = config["base"]
    base = languages[base_code]
    complete = {code: {section: fill(base.get(section, {}), data.get(section)) for section in SECTIONS} for code, data in languages.items()}
    borrowed = dict(sorted(config.get("prestados", {}).items()))
    files: dict[Path, str] = {}

    # --- Home Assistant -----------------------------------------------------
    for code, data in complete.items():
        files[INTEGRATION / "translations" / f"{code}.json"] = dump(data["integracion"])
    for code, target in borrowed.items():
        files[INTEGRATION / "translations" / f"{code}.json"] = dump(complete[target]["integracion"])
    files[INTEGRATION / "strings.json"] = dump(complete[base_code]["integracion"])

    # --- Python (avisos y catálogo) ------------------------------------------
    def literal(name: str, value: object, annotation: str) -> str:
        body = json.dumps(value, ensure_ascii=False, indent=4)
        return f"{name}: Final[{annotation}] = {body}\n"

    files[INTEGRATION / "textos_generados.py"] = (
        '"""Textos de los avisos y del catálogo, por idioma.\n\n'
        "FICHERO GENERADO: no editar. Los textos están en ``idiomas/<idioma>.json``;\n"
        "tras cambiarlos, ejecutar ``python tools/generar_idiomas.py``.\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        "from typing import Final\n\n"
        "#: Idioma que se usa cuando el del usuario no está traducido.\n"
        f'BASE_LANGUAGE: Final = "{base_code}"\n'
        "#: Idiomas sin traducción propia que usan la de otro.\n"
        + literal("BORROWED_LANGUAGES", borrowed, "dict[str, str]")
        + "#: Mensajes de los avisos al móvil: ``{idioma: {clave: texto}}``.\n"
        + literal("ALERT_TEXTS", {code: data["avisos"] for code, data in complete.items()}, "dict[str, dict[str, str]]")
        + "#: Nombres del catálogo: ``{idioma: {clave: texto}}``.\n"
        + literal("CATALOGUE_TEXTS", {code: data["catalogo"] for code, data in complete.items()}, "dict[str, dict[str, str]]")
    )

    # --- Tarjeta --------------------------------------------------------------
    # La tabla de textos es un módulo más de la tarjeta; con ella se reconstruye
    # el fichero único que carga Home Assistant.
    table = json.dumps({code: data["tarjeta"] for code, data in complete.items()}, ensure_ascii=False, indent=2)
    texts = (
        CARD_TEXTS_HEADER
        + f'  const BASE_LANGUAGE = "{base_code}";\n'
        + f"  const BORROWED_LANGUAGES = {json.dumps(borrowed, ensure_ascii=False)};\n"
        + "  const TEXTS = "
        + table.replace("\n", "\n  ")
        + ";\n"
    )
    files[construir_tarjeta.SRC / CARD_TEXTS] = texts
    try:
        files[CARD] = construir_tarjeta.build({**construir_tarjeta.read_sources(), CARD_TEXTS: texts})
    except construir_tarjeta.BuildError as err:
        raise LanguageError(str(err)) from err
    return files


def main(argv: list[str]) -> int:
    try:
        config, languages = load()
        generated = outputs(config, languages)
    except (LanguageError, OSError, json.JSONDecodeError, KeyError) as err:
        print(f"ERROR: {err}")
        return 2

    gaps = missing(config, languages)
    total = sum(len(flatten(languages[config["base"]].get(section, {}))) for section in SECTIONS)
    if "--informe" in argv:
        for code, keys in gaps.items():
            info = config["idiomas"][code]
            print(f"{code} ({info.get('nombre', code)}): {total - len(keys)} de {total} textos. Revisor: {info.get('revisor') or '—'}")
            for key in keys:
                print(f"    falta {key}")
        for code, target in config.get("prestados", {}).items():
            print(f"{code}: usa los textos de '{target}'")
        return 0

    stale = [path for path, content in generated.items() if not path.exists() or path.read_text(encoding="utf-8") != content]
    if "--check" in argv:
        for path in stale:
            print(f"Sin regenerar: {path.relative_to(ROOT)}")
        if stale:
            print("Ejecuta: python tools/generar_idiomas.py")
        return 1 if stale else 0
    for path in stale:
        path.write_text(content := generated[path], encoding="utf-8", newline="\n")
        print(f"Escrito {path.relative_to(ROOT)} ({len(content)} caracteres)")
    print(f"{len(generated) - len(stale)} ficheros ya estaban al día; {len(stale)} actualizados.")
    for code, keys in gaps.items():
        if keys:
            print(f"Aviso: a '{code}' le faltan {len(keys)} textos (se usa el de '{config['base']}'). Ver --informe.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
