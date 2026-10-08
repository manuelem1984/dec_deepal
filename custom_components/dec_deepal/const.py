"""Constantes compartidas de la integración DEC Deepal.

Este módulo solo contiene *valores fijos* (nombres de claves, tiempos,
dominios...). No contiene lógica ni datos que un usuario/colaborador deba
editar a menudo: esos viven en ficheros de datos YAML, cada uno en su carpeta:

- ``countries/countries.yaml``  → países soportados y su servidor.
- ``vehicles/vehicles.yaml``    → modelos, versiones, colores y fotos.
- ``icons/icons.yaml``          → iconos de cada entidad.

Así, añadir un país, un coche o un icono no obliga a tocar este fichero.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Identidad de la integración
# ---------------------------------------------------------------------------

#: Dominio de Home Assistant. Debe coincidir con ``manifest.json`` y con el
#: nombre de la carpeta ``custom_components/dec_deepal``.
DOMAIN: Final = "dec_deepal"

#: Nombre visible de la integración.
NAME: Final = "DEC Deepal"

#: Quién aparece como "fabricante" en la ficha del dispositivo. No es Deepal
#: ni Changan: la integración es un proyecto de la comunidad.
MANUFACTURER: Final = "Comunidad Deepal España (DEC)"

#: Enlace que aparece en "Visitar" en la ficha del dispositivo.
COMMUNITY_URL: Final = "https://t.me/deepalespana_general"

#: Carpeta raíz de la integración, útil para localizar los ficheros de datos.
INTEGRATION_DIR: Final = Path(__file__).parent

# La versión se lee de manifest.json para que haya una única fuente de verdad.
# Se hace una sola vez al importar el módulo (lectura pequeña y local).
VERSION: Final[str] = json.loads(
    (INTEGRATION_DIR / "manifest.json").read_text(encoding="utf-8")
)["version"]

# ---------------------------------------------------------------------------
# Claves guardadas en la entrada de configuración (entry.data)
# ---------------------------------------------------------------------------
# Todo lo que hace falta para reconectar con la cuenta sin volver a pedir un
# código. Son datos sensibles: diagnostics.py los oculta siempre.

CONF_COUNTRY: Final = "country"  # id del país en countries.yaml (p. ej. "es")
CONF_LOGIN_METHOD: Final = "login_method"  # "sms" o "email"
CONF_SESSION: Final = "session"  # dict con tokens y clave privada (ver api/session.py)
CONF_VEHICLES: Final = "vehicles"  # lista de vehículos elegidos (ver api/models.py)

# Campos que solo existen durante el asistente de configuración (no se guardan).
CONF_EMAIL: Final = "email"
CONF_MOBILE: Final = "mobile"
CONF_AUTH_CODE: Final = "auth_code"
CONF_SELECTED_VEHICLES: Final = "selected_vehicles"

LOGIN_METHOD_SMS: Final = "sms"
LOGIN_METHOD_EMAIL: Final = "email"

# ---------------------------------------------------------------------------
# Claves de las opciones (entry.options) — se cambian en "Configurar"
# ---------------------------------------------------------------------------

#: Apariencia por vehículo: {vehicle_id: {"model": ..., "trim": ..., "color": ...}}
OPT_APPEARANCE: Final = "appearance"
OPT_MODEL: Final = "model"
OPT_TRIM: Final = "trim"
OPT_COLOR: Final = "color"

#: Bloque de control remoto con PIN (puertas, ventanillas, maletero).
OPT_PIN_ENABLED: Final = "pin_enabled"
OPT_PIN: Final = "pin"
OPT_PIN_MODE: Final = "pin_mode"
OPT_ARM_SECONDS: Final = "arm_seconds"
OPT_ARM_NOTIFY: Final = "arm_notify"

#: Opciones avanzadas.
OPT_SCAN_MINUTES: Final = "scan_minutes"
OPT_DEBUG: Final = "debug"
#: Permitir despertar el coche (botón Actualizar y órdenes con PIN).
OPT_WAKE: Final = "wake"
DEFAULT_WAKE: Final = True

#: Opción A: los comandos con PIN se ejecutan directamente.
PIN_MODE_DIRECT: Final = "direct"
#: Opción B: hay que "armar" antes (candado "Desbloqueo acciones con PIN").
PIN_MODE_ARMED: Final = "armed"

DEFAULT_PIN_MODE: Final = PIN_MODE_DIRECT
ARM_SECONDS_CHOICES: Final = (10, 20, 30, 60)
DEFAULT_ARM_SECONDS: Final = 30
DEFAULT_ARM_NOTIFY: Final = False

#: Intervalo de lectura del coche. 5 min es lo que se ha usado siempre; bajar
#: mucho aumenta el riesgo de que el servidor limite la cuenta.
DEFAULT_SCAN_MINUTES: Final = 5
MIN_SCAN_MINUTES: Final = 2
MAX_SCAN_MINUTES: Final = 60

# ---------------------------------------------------------------------------
# Plataformas de Home Assistant que crea la integración
# ---------------------------------------------------------------------------

PLATFORMS: Final = (
    "binary_sensor",
    "button",
    "climate",
    "cover",
    "device_tracker",
    "image",
    "lock",
    "number",
    "sensor",
    "switch",
)

# ---------------------------------------------------------------------------
# Iconos personalizados (ver icons/README.md y registries/icons.py)
# ---------------------------------------------------------------------------

#: Prefijo de los iconos propios: una entidad usa "dec:nombre".
ICON_PREFIX: Final = "dec"
#: URL desde la que el navegador descarga cada SVG: <URL>/<nombre>.svg
ICONS_SVG_URL: Final = "/dec_deepal/icons"
#: URL del script que registra el prefijo "dec:" en el navegador.
ICONS_JS_URL: Final = "/dec_deepal/frontend"
ICONS_JS_FILE: Final = "dec-icons.js"
#: API que devuelve la lista de iconos disponibles (para el selector de iconos).
ICONS_LIST_API: Final = "/api/dec_deepal/icons"
#: Todos los SVG en una sola respuesta JSON (lo usa dec-icons.js).
ICONS_BUNDLE_API: Final = "/api/dec_deepal/icons_bundle"

# ---------------------------------------------------------------------------
# Depuración (ver docs/depuracion.md)
# ---------------------------------------------------------------------------

#: Prefijo del aviso de Reparaciones "Configura tu vehículo" (uno por coche).
VEHICLE_ISSUE_PREFIX: Final = "vehicle_not_configured_"

#: Carpeta (dentro de /config) donde el servicio de captura guarda los JSON.
CAPTURES_DIR: Final = "dec_deepal_capturas"
#: Eventos que guarda en memoria el registro de depuración (los más recientes).
DEBUG_BUFFER_SIZE: Final = 300
