"""Avisos al móvil: qué cambios del coche merecen un aviso y con qué texto.

Lógica pura (sin Home Assistant), para poder probarla sola. El envío y la
configuración están en ``alerts.py``.

Tipos de aviso (el usuario activa los que quiera en Configurar → Avisos):

- **Carga iniciada / interrumpida / terminada.** Se detectan comparando la
  lectura anterior con la nueva (ver :func:`charge_event`).
- **Testigos del cuadro**, **neumáticos** y **pila del mando.** Un aviso
  cuando el coche enciende el testigo, y no se repite hasta que se apague y
  vuelva a encenderse (ver :func:`new_problems`).
- **Mantenimiento.** Lo calcula ``maintenance.py``.

Ningún aviso es crítico: son notificaciones normales.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Final

from .telemetry import signals as s

ALERT_CHARGE_STARTED: Final = "charge_started"
ALERT_CHARGE_INTERRUPTED: Final = "charge_interrupted"
ALERT_CHARGE_FINISHED: Final = "charge_finished"
ALERT_WARNINGS: Final = "warnings"
ALERT_TIRES: Final = "tires"
ALERT_KEY_BATTERY: Final = "key_battery"
ALERT_MAINTENANCE: Final = "maintenance"

#: Todos los tipos, en el orden en que se ofrecen en Configurar.
ALERT_TYPES: Final = (
    ALERT_CHARGE_STARTED,
    ALERT_CHARGE_INTERRUPTED,
    ALERT_CHARGE_FINISHED,
    ALERT_WARNINGS,
    ALERT_TIRES,
    ALERT_KEY_BATTERY,
    ALERT_MAINTENANCE,
)

#: Señal de problema → tipo de aviso. La clave del sensor binario que la
#: muestra coincide con el nombre de la señal (de ahí sale el nombre visible).
PROBLEM_SIGNALS: Final[dict[str, str]] = {
    s.WARNING_BRAKE: ALERT_WARNINGS,
    s.WARNING_BRAKE_FLUID: ALERT_WARNINGS,
    s.WARNING_AIRBAG: ALERT_WARNINGS,
    s.WARNING_12V_BATTERY: ALERT_WARNINGS,
    s.WARNING_COOLANT_TEMPERATURE: ALERT_WARNINGS,
    s.WARNING_POWER_SYSTEM: ALERT_WARNINGS,
    s.WARNING_ABS: ALERT_WARNINGS,
    s.WARNING_EPS: ALERT_WARNINGS,
    s.WARNING_POWER_LIMIT: ALERT_WARNINGS,
    s.WARNING_TRACTION_BATTERY_LOW: ALERT_WARNINGS,
    s.WARNING_TPMS: ALERT_TIRES,
    s.TIRE_ALARM_FRONT_LEFT: ALERT_TIRES,
    s.TIRE_ALARM_FRONT_RIGHT: ALERT_TIRES,
    s.TIRE_ALARM_REAR_LEFT: ALERT_TIRES,
    s.TIRE_ALARM_REAR_RIGHT: ALERT_TIRES,
    s.KEY_BATTERY_LOW: ALERT_KEY_BATTERY,
}

#: Señales que se guardan de cada lectura para compararla con la siguiente.
WATCHED_SIGNALS: Final = (s.CHARGING, s.BATTERY_LEVEL, s.REMAINING_CHARGE_MIN, *PROBLEM_SIGNALS)

#: Una carga que se para con la batería así de llena, o cuando al coche le
#: quedaban como mucho estos minutos, se considera terminada (no interrumpida).
FINISHED_LEVEL: Final = 99
FINISHED_REMAINING_MIN: Final = 15


def charge_event(previous: Mapping[str, Any] | None, current: Mapping[str, Any]) -> str | None:
    """Aviso de carga que corresponde al pasar de ``previous`` a ``current``.

    Solo hay aviso si se conocen los dos estados (así, arrancar Home Assistant
    con el coche ya cargando no avisa de "carga iniciada").

    ⚠️ Sin verificar con el coche: distinguir "terminada" de "interrumpida".
    El coche no dice por qué dejó de cargar, así que se deduce: terminada si
    la batería está llena o si en la lectura anterior quedaban pocos minutos;
    en otro caso, interrumpida (corte, o cable desenchufado a media carga).
    """
    if previous is None:
        return None
    before, now = previous.get(s.CHARGING), current.get(s.CHARGING)
    if before is False and now is True:
        return ALERT_CHARGE_STARTED
    if before is True and now is False:
        level = current.get(s.BATTERY_LEVEL)
        remaining = previous.get(s.REMAINING_CHARGE_MIN)
        full = level is not None and level >= FINISHED_LEVEL
        nearly_done = remaining is not None and remaining <= FINISHED_REMAINING_MIN
        return ALERT_CHARGE_FINISHED if full or nearly_done else ALERT_CHARGE_INTERRUPTED
    return None


def new_problems(current: Mapping[str, Any], active: set[str]) -> list[str]:
    """Testigos que se acaban de encender; actualiza ``active``.

    ``active`` son los que ya estaban encendidos (y avisados). Un testigo sale
    de ahí al apagarse; sin dato (``None``) se queda como estaba.
    """
    fresh: list[str] = []
    for signal in PROBLEM_SIGNALS:
        value = current.get(signal)
        if value is True and signal not in active:
            active.add(signal)
            fresh.append(signal)
        elif value is False:
            active.discard(signal)
    return fresh


# ---------------------------------------------------------------------------
# Textos
# ---------------------------------------------------------------------------
# El título es siempre "DEC Deepal <nombre del coche>" (lo pone alerts.py).

TEXTS: Final[dict[str, dict[str, str]]] = {
    "es": {
        ALERT_CHARGE_STARTED: "Carga iniciada{battery}.",
        ALERT_CHARGE_INTERRUPTED: "Carga interrumpida{battery}.",
        ALERT_CHARGE_FINISHED: "Carga terminada{battery}.",
        "battery": " (batería al {level} %)",
        ALERT_WARNINGS: "Testigo encendido: {names}.",
        ALERT_TIRES: "Aviso de neumáticos: {names}.",
        ALERT_KEY_BATTERY: "Pila del mando baja. Cámbiala por una CR2032.",
        "maintenance_remaining": "Quedan {parts} para la {ordinal} revisión.",
        "maintenance_overdue": "Mantenimiento vencido: la {ordinal} revisión tocaba el {date} o a los {km} km.",
        "km": "{value} km",
        "days": "{value} días",
        "day": "1 día",
        "or": " o ",
        "and": " y ",
    },
    "en": {
        ALERT_CHARGE_STARTED: "Charging started{battery}.",
        ALERT_CHARGE_INTERRUPTED: "Charging interrupted{battery}.",
        ALERT_CHARGE_FINISHED: "Charging finished{battery}.",
        "battery": " (battery at {level}%)",
        ALERT_WARNINGS: "Warning light on: {names}.",
        ALERT_TIRES: "Tyre warning: {names}.",
        ALERT_KEY_BATTERY: "Key fob battery low. Replace it with a CR2032.",
        "maintenance_remaining": "{parts} left until the {ordinal} service.",
        "maintenance_overdue": "Service overdue: the {ordinal} service was due on {date} or at {km} km.",
        "km": "{value} km",
        "days": "{value} days",
        "day": "1 day",
        "or": " or ",
        "and": " and ",
    },
}


ENGLISH_SUFFIXES: Final = {1: "st", 2: "nd", 3: "rd"}


def _texts(language: str) -> dict[str, str]:
    return TEXTS.get(language.split("-")[0].lower(), TEXTS["es"])


def format_number(value: float, language: str) -> str:
    """Entero con separador de miles: ``2.000`` en español, ``2,000`` en inglés."""
    text = f"{round(value):,}"
    return text if language.lower().startswith("en") else text.replace(",", ".")


def ordinal(number: int, language: str) -> str:
    """``2ª`` en español; ``2nd`` en inglés."""
    if not language.lower().startswith("en"):
        return f"{number}ª"
    if 10 <= number % 100 <= 20:
        return f"{number}th"
    return f"{number}{ENGLISH_SUFFIXES.get(number % 10, 'th')}"


def charge_text(alert: str, level: float | None, language: str) -> str:
    """Texto de un aviso de carga, con el nivel de batería si se conoce."""
    texts = _texts(language)
    battery = "" if level is None else texts["battery"].format(level=round(level))
    return texts[alert].format(battery=battery)


def problem_text(alert: str, names: Iterable[str], language: str) -> str:
    """Texto de un aviso de testigos, neumáticos o pila del mando."""
    texts = _texts(language)
    return texts[alert].format(names=texts["and"].join(names))


def maintenance_text(
    kind: str,
    *,
    number: int,
    days_left: int,
    km_left: int | None,
    due_date: str,
    due_km: int,
    language: str,
) -> str:
    """Texto del aviso de mantenimiento.

    Args:
        kind: ``"remaining"`` ("Quedan 2.000 km o 47 días para la 2ª
            revisión.") u ``"overdue"`` (vencido).
        due_date: fecha prevista, ya con el formato del idioma.
    """
    texts = _texts(language)
    if kind == "overdue":
        return texts["maintenance_overdue"].format(
            ordinal=ordinal(number, language), date=due_date, km=format_number(due_km, language)
        )
    parts = []
    if km_left is not None:
        parts.append(texts["km"].format(value=format_number(km_left, language)))
    parts.append(texts["day"] if days_left == 1 else texts["days"].format(value=days_left))
    return texts["maintenance_remaining"].format(
        parts=texts["or"].join(parts), ordinal=ordinal(number, language)
    )
