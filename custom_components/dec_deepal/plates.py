"""Matrícula con el formato de su país, para pintarla como una placa.

El servidor manda la matrícula tal cual la guardó (a menudo pegada:
``6545NPD``). Aquí se le pone el formato del país de la cuenta:

=========  ==============  ==========================================
País       Formato         Ejemplo
=========  ==============  ==========================================
España     ``0000 AAA``    ``6545 NPD``
Portugal   ``AA-00-AA``    ``AA-00-AA`` (letras o cifras en cada par)
Italia     ``AA 000 AA``   ``AB 123 CD``
Francia    ``AA-000-AA``   ``AB-123-CD``
Alemania   ciudad · resto  ``M`` · ``AB 1234`` (los sellos van entre medias)
=========  ==============  ==========================================

Si la matrícula no encaja con el patrón (antigua, especial, de otro país...)
se enseña tal cual: nunca se inventa. La placa es la genérica europea: franja
azul con la letra del país (``code``) y el texto.

Lógica pura (sin Home Assistant), para poder probarla sola.
"""

from __future__ import annotations

import re
from typing import Any, Final

#: Letra del país en la franja europea (código internacional de vehículos).
EU_CODES: Final = {"ES": "E", "PT": "P", "IT": "I", "DE": "D", "FR": "F"}

_ES: Final = re.compile(r"^(\d{4})([A-Z]{3})$")
_PT: Final = re.compile(r"^([A-Z0-9]{2})([A-Z0-9]{2})([A-Z0-9]{2})$")
_IT: Final = re.compile(r"^([A-Z]{2})(\d{3})([A-Z]{2})$")
_FR: Final = re.compile(r"^([A-Z]{2})(\d{3})([A-Z]{2})$")
# Alemania: la ciudad (1-3 letras) solo se distingue si viene separada.
_DE: Final = re.compile(r"^([A-ZÄÖÜ]{1,3})[- ]+([A-Z]{1,2})[- ]*(\d{1,4}[EH]?)$")


def plate(raw: str | None, country: str) -> dict[str, Any] | None:
    """Placa de una matrícula: ``{"code": "E", "parts": ["6545 NPD"]}``.

    Args:
        raw: matrícula tal cual la manda el servidor (``None`` = no la tiene).
        country: país de la cuenta, en mayúsculas (``"ES"``).

    Returns:
        ``code``: letra de la franja europea. ``parts``: el texto; con dos
        partes (Alemania), entre ellas van los sellos. ``None`` sin matrícula.
    """
    text = " ".join(str(raw or "").upper().split())
    if not text:
        return None
    country = country.upper()
    code = EU_CODES.get(country, country)
    compact = text.replace(" ", "").replace("-", "")
    if country == "ES" and (match := _ES.match(compact)):
        return {"code": code, "parts": [f"{match[1]} {match[2]}"]}
    if country == "PT" and (match := _PT.match(compact)):
        return {"code": code, "parts": ["-".join(match.groups())]}
    if country == "IT" and (match := _IT.match(compact)):
        return {"code": code, "parts": [" ".join(match.groups())]}
    if country == "FR" and (match := _FR.match(compact)):
        return {"code": code, "parts": ["-".join(match.groups())]}
    if country == "DE" and (match := _DE.match(text)):
        return {"code": code, "parts": [match[1], f"{match[2]} {match[3]}"]}
    return {"code": code, "parts": [text]}
