"""Cargador de ``icons/icons.yaml`` y de la carpeta ``icons/svg``.

Resuelve qué icono lleva cada entidad según su estado, con esta prioridad
(la misma que se explica en la cabecera de ``icons.yaml``):

1. ``svg/<entidad>_<sufijo>.svg``  → ``"dec:<entidad>_<sufijo>"``
2. ``svg/<entidad>.svg``           → ``"dec:<entidad>"``
3. ``mdi`` del estado en el YAML
4. ``defecto`` del YAML
5. ``None`` → Home Assistant pone el icono estándar del tipo de entidad.

Los SVG se **descubren al arrancar** mirando la carpeta: añadir un icono es
solo copiar el archivo y reiniciar. El navegador los descarga directamente
(ver ``frontend.py`` y ``icons/dec-icons.js``).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from .errors import RegistryError, as_dict, read_yaml, state_key

_LOGGER = logging.getLogger(__name__)

#: Nombres de archivo válidos: minúsculas, números y guion bajo.
VALID_NAME: Final = re.compile(r"^[a-z0-9_]+$")

#: Etiquetas SVG que el sistema de iconos NO puede representar (solo admite
#: rellenos planos de un color). Si aparecen, se avisa en el registro.
UNSUPPORTED_SVG_TAGS: Final = ("<mask", "<animate", "<image", "<text", "<linearGradient")


@dataclass(frozen=True, slots=True)
class IconState:
    """Configuración de un estado: sufijo del archivo e icono de respaldo."""

    suffix: str
    mdi: str | None


@dataclass(frozen=True, slots=True)
class IconEntry:
    """Bloque de una entidad en ``icons.yaml``."""

    key: str
    platform: str
    description: str
    states: dict[str, IconState] = field(default_factory=dict)
    default: str | None = None

    def expected_files(self) -> list[str]:
        """Nombres de archivo que acepta esta entidad (para documentación)."""
        names = [f"{self.key}.svg"]
        names.extend(f"{self.key}_{state.suffix}.svg" for state in self.states.values())
        return names


@dataclass(slots=True)
class IconRegistry:
    """Registro de iconos: entradas del YAML + SVG disponibles."""

    entries: dict[str, IconEntry]
    svg_dir: Path
    available: frozenset[str]
    warnings: list[str] = field(default_factory=list)

    def resolve(self, key: str, state: str | None = None) -> str | None:
        """Icono para la entidad ``key`` en el estado ``state``.

        Args:
            key: clave de la entidad (p. ej. ``"windows"``).
            state: estado de HA ya en texto (``"open"``, ``"on"``, ``"2"``...)
                o ``None`` si la entidad no tiene estados con icono propio.
        """
        entry = self.entries.get(key)
        state_config = entry.states.get(state) if entry and state is not None else None

        if state is not None:
            suffix = state_config.suffix if state_config else state
            if f"{key}_{suffix}" in self.available:
                return f"dec:{key}_{suffix}"
        if key in self.available:
            return f"dec:{key}"
        if state_config and state_config.mdi:
            return state_config.mdi
        if entry and entry.default:
            return entry.default
        return None


def _svg_warnings(path: Path) -> list[str]:
    """Comprueba que un SVG es compatible y devuelve avisos si no lo es."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        return [f"{path.name}: no se puede leer ({err})"]
    warnings = []
    if "<path" not in text:
        warnings.append(f"{path.name}: no tiene ningún <path>; no se verá")
    found = [tag for tag in UNSUPPORTED_SVG_TAGS if tag in text]
    if found:
        warnings.append(
            f"{path.name}: contiene {', '.join(found)}; solo se admiten trazados "
            "rellenos de un color (ver docs/iconos.md)"
        )
    if 'stroke="' in text and "stroke=\"none\"" not in text:
        warnings.append(
            f"{path.name}: usa trazos (stroke); conviértelos en relleno "
            "(Inkscape: Trayecto → Trazo a trayecto) o no se verán"
        )
    return warnings


def load_icons(icons_dir: Path) -> IconRegistry:
    """Lee ``icons.yaml`` y descubre los SVG de ``icons/svg``.

    Los problemas con archivos SVG concretos NO impiden arrancar: se guardan
    como avisos (``warnings``) y se escriben en el registro de Home Assistant.
    Un ``icons.yaml`` mal formado sí lanza :class:`RegistryError`.
    """
    path = icons_dir / "icons.yaml"
    data = read_yaml(path)
    entries: dict[str, IconEntry] = {}

    for key, raw in data.items():
        where = f"{path.name} → {key}"
        raw = as_dict(raw, where)
        key = str(key)
        if not VALID_NAME.match(key):
            raise RegistryError(f"{where}: usa solo minúsculas, números y '_'")
        states: dict[str, IconState] = {}
        for state, state_raw in as_dict(raw.get("estados"), f"{where}.estados").items():
            state_raw = as_dict(state_raw, f"{where}.estados.{state}")
            name = state_key(state)
            states[name] = IconState(
                suffix=str(state_raw.get("archivo") or name),
                mdi=state_raw.get("mdi"),
            )
        entries[key] = IconEntry(
            key=key,
            platform=str(raw.get("plataforma") or ""),
            description=str(raw.get("descripcion") or ""),
            states=states,
            default=raw.get("defecto"),
        )

    svg_dir = icons_dir / "svg"
    available: set[str] = set()
    warnings: list[str] = []
    if svg_dir.is_dir():
        known_files = {name for entry in entries.values() for name in entry.expected_files()}
        for svg in sorted(svg_dir.glob("*.svg")):
            name = svg.stem
            if not VALID_NAME.match(name):
                warnings.append(
                    f"{svg.name}: nombre no válido (usa minúsculas, números y '_'); se ignora"
                )
                continue
            available.add(name)
            warnings.extend(_svg_warnings(svg))
            if svg.name not in known_files:
                warnings.append(
                    f"{svg.name}: no corresponde a ninguna entidad/estado de icons.yaml "
                    "(¿errata en el nombre?)"
                )

    return IconRegistry(
        entries=entries, svg_dir=svg_dir, available=frozenset(available), warnings=warnings
    )
