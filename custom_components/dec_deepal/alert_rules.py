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
- **ITV** y **seguro.** Los calcula ``documents.py``.

A quién se avisa
----------------
Cada coche reparte sus avisos en cuatro **grupos**, cada uno con su lista de
destinos: los del coche (carga, testigos, neumáticos, pila del mando),
mantenimiento, ITV y seguro. Así, en una casa con dos coches, cada conductor
recibe los avisos de su coche y uno de los dos, los papeles de ambos. Un
grupo sin destinos no avisa. Ver :func:`route_for`.

Ningún aviso es crítico: son notificaciones normales.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, Final

from .const import (
    OPT_ALERT_CAR_KNOWN,
    OPT_ALERT_CAR_TYPES,
    OPT_ALERT_KNOWN,
    OPT_ALERT_PERSISTENT,
    OPT_ALERT_TARGETS,
    OPT_ALERT_TYPES,
    OPT_ALERT_VEHICLES,
)
from .telemetry import signals as s
from .textos_generados import ALERT_TEXTS, BASE_LANGUAGE, BORROWED_LANGUAGES

ALERT_CHARGE_STARTED: Final = "charge_started"
ALERT_CHARGE_INTERRUPTED: Final = "charge_interrupted"
ALERT_CHARGE_FINISHED: Final = "charge_finished"
ALERT_WARNINGS: Final = "warnings"
ALERT_TIRES: Final = "tires"
ALERT_KEY_BATTERY: Final = "key_battery"
ALERT_MAINTENANCE: Final = "maintenance"
ALERT_ITV: Final = "itv"
ALERT_INSURANCE: Final = "insurance"

#: Todos los tipos, en el orden en que se ofrecen en Configurar.
ALERT_TYPES: Final = (
    ALERT_CHARGE_STARTED,
    ALERT_CHARGE_INTERRUPTED,
    ALERT_CHARGE_FINISHED,
    ALERT_WARNINGS,
    ALERT_TIRES,
    ALERT_KEY_BATTERY,
    ALERT_MAINTENANCE,
    ALERT_ITV,
    ALERT_INSURANCE,
)
#: Tipos que existían en la primera versión de los avisos. Quien los configuró
#: entonces no pudo elegir los posteriores: esos nacen activados (ver
#: :func:`enabled_types`).
ORIGINAL_ALERT_TYPES: Final = ALERT_TYPES[:7]


#: Grupos de avisos: cada uno tiene su lista de destinos en cada coche.
GROUP_CAR: Final = "car"
GROUP_MAINTENANCE: Final = "maintenance"
GROUP_ITV: Final = "itv"
GROUP_INSURANCE: Final = "insurance"
GROUPS: Final = (GROUP_CAR, GROUP_MAINTENANCE, GROUP_ITV, GROUP_INSURANCE)
#: Avisos del grupo "coche": los únicos que se activan uno a uno.
CAR_ALERT_TYPES: Final = ALERT_TYPES[:6]
#: Grupo de cada tipo de aviso.
GROUP_OF: Final[dict[str, str]] = {
    **dict.fromkeys(CAR_ALERT_TYPES, GROUP_CAR),
    ALERT_MAINTENANCE: GROUP_MAINTENANCE,
    ALERT_ITV: GROUP_ITV,
    ALERT_INSURANCE: GROUP_INSURANCE,
}
#: Destino especial: el panel de notificaciones de Home Assistant.
TARGET_PANEL: Final = "persistent_notification"


@dataclass(frozen=True, slots=True)
class Route:
    """A quién avisa un coche de cada cosa."""

    #: Destinos de cada grupo (servicios ``notify.*`` o :data:`TARGET_PANEL`).
    targets: Mapping[str, tuple[str, ...]]
    #: Avisos del coche activados (carga iniciada, testigos...).
    car_types: frozenset[str]

    def targets_for(self, alert: str) -> tuple[str, ...]:
        """Destinos de un tipo de aviso (vacío = no se avisa)."""
        group = GROUP_OF[alert]
        if group == GROUP_CAR and alert not in self.car_types:
            return ()
        return self.targets.get(group, ())

    def to_dict(self) -> dict[str, list[str]]:
        """Como se guarda en las opciones."""
        return {
            **{group: list(self.targets.get(group, ())) for group in GROUPS},
            OPT_ALERT_CAR_TYPES: [kind for kind in CAR_ALERT_TYPES if kind in self.car_types],
            # Para activar solos los tipos que se añadan en versiones futuras.
            OPT_ALERT_CAR_KNOWN: list(CAR_ALERT_TYPES),
        }


#: Coche sin ningún aviso.
NO_ROUTE: Final = Route(targets={}, car_types=frozenset())


def _unique(names: Iterable[Any]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(name) for name in names if name))


def route_for(config: Mapping[str, Any] | None, vehicle_id: str) -> Route:
    """A quién avisa un coche, según las opciones de la cuenta.

    Args:
        config: ``options["alerts"]``. Admite el formato por coche (2.4.0) y
            el anterior, con una sola lista para toda la cuenta: en ese caso
            todos los coches avisan a esa lista de los tipos que estuvieran
            activados, que es lo que hacían antes de actualizar.
        vehicle_id: coche.
    """
    if not config:
        return NO_ROUTE
    vehicles = config.get(OPT_ALERT_VEHICLES)
    if isinstance(vehicles, Mapping):
        stored = vehicles.get(vehicle_id)
        if not isinstance(stored, Mapping):
            return NO_ROUTE
        known = stored.get(OPT_ALERT_CAR_KNOWN)
        chosen = set(stored.get(OPT_ALERT_CAR_TYPES) or ())
        # Tipos nuevos (que no existían al guardar) nacen activados.
        new = set(CAR_ALERT_TYPES) - set(CAR_ALERT_TYPES if known is None else known)
        return Route(
            targets={group: _unique(stored.get(group) or ()) for group in GROUPS},
            car_types=frozenset((chosen & set(CAR_ALERT_TYPES)) | new),
        )

    targets = list(config.get(OPT_ALERT_TARGETS) or ())
    if config.get(OPT_ALERT_PERSISTENT):
        targets.append(TARGET_PANEL)
    types = enabled_types(config.get(OPT_ALERT_TYPES), config.get(OPT_ALERT_KNOWN))
    return Route(
        targets={
            GROUP_CAR: _unique(targets),
            **{
                GROUP_OF[alert]: _unique(targets) if alert in types else ()
                for alert in (ALERT_MAINTENANCE, ALERT_ITV, ALERT_INSURANCE)
            },
        },
        car_types=frozenset(types & set(CAR_ALERT_TYPES)),
    )


def enabled_types(stored: Iterable[str] | None, known: Iterable[str] | None) -> set[str]:
    """Avisos activados: los elegidos más los tipos nuevos que aún no se han ofrecido.

    Args:
        stored: tipos marcados en Configurar (``None`` = nunca configurado: todos).
        known: tipos que existían cuando se guardó (``None`` = los originales).
    """
    if stored is None:
        return set(ALERT_TYPES)
    offered = set(ORIGINAL_ALERT_TYPES if known is None else known)
    return (set(stored) & set(ALERT_TYPES)) | (set(ALERT_TYPES) - offered)

#: Señal de problema → tipo de aviso. La clave del sensor binario que la
#: muestra coincide con el nombre de la señal (de ahí sale el nombre visible).
#: Un coche puede tener testigos que enciende sin motivo (el S05, el del
#: airbag al despertar): los dice su ficha (``testigos_sin_aviso`` en
#: ``vehicles.yaml``) y no avisan (ver :func:`new_problems`).
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


def new_problems(
    current: Mapping[str, Any], active: set[str], silent: Iterable[str] = ()
) -> list[str]:
    """Testigos que se acaban de encender; actualiza ``active``.

    ``active`` son los que ya estaban encendidos (y avisados). Un testigo sale
    de ahí al apagarse; sin dato (``None``) se queda como estaba. Los de
    ``silent`` (los que la ficha del coche dice que no avisan) no cuentan.
    """
    fresh: list[str] = []
    silent = set(silent)
    for signal in PROBLEM_SIGNALS:
        if signal in silent:
            active.discard(signal)
            continue
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
# Los mensajes están en idiomas/<idioma>.json → "avisos" (ver docs/idiomas.md).

#: ``{idioma: {clave: texto}}``. Sale de ``idiomas/<idioma>.json`` → ``avisos``.
TEXTS: Final = ALERT_TEXTS


ENGLISH_SUFFIXES: Final = {1: "st", 2: "nd", 3: "rd"}


def language_base(language: str) -> str:
    """Idioma de los textos: ``"pt-BR"`` → ``"pt"``; un idioma prestado → el que le presta.

    Qué idiomas hay y cuáles usan los de otro lo dice ``idiomas/idiomas.json``.
    """
    base = language.replace("_", "-").split("-")[0].lower()
    return BORROWED_LANGUAGES.get(base, base)


def _texts(language: str) -> dict[str, str]:
    """Textos del idioma; si no está traducido, los del idioma base."""
    return TEXTS.get(language_base(language), TEXTS[BASE_LANGUAGE])


def panel_name(language: str) -> str:
    """Nombre del destino "panel de notificaciones de Home Assistant"."""
    return _texts(language)["panel_target"]


def backup_text(key: str, language: str) -> str:
    """Textos de la copia de los datos: ``download`` (enlace) y ``notification`` (aviso)."""
    return _texts(language)[f"backup_{key}"]


def format_number(value: float, language: str) -> str:
    """Entero con separador de miles del idioma: ``2.000``, ``2,000``, ``2 000``."""
    return f"{round(value):,}".replace(",", _texts(language)["thousands"])


def ordinal(number: int, language: str) -> str:
    """``2ª`` en español, ``2.ª`` en portugués, ``2nd`` en inglés...

    El formato de cada idioma está en sus textos (clave ``ordinal``); el
    inglés es el único con sufijos que cambian (1st, 2nd, 3rd).
    """
    if _texts(language) is TEXTS["en"]:
        if 10 <= number % 100 <= 20:
            return f"{number}th"
        return f"{number}{ENGLISH_SUFFIXES.get(number % 10, 'th')}"
    return _texts(language)["ordinal"].format(number=number)


def format_date(value: date, language: str) -> str:
    """Fecha corta con el formato del idioma (``10/03/2027``, ``10.03.2027``)."""
    return value.strftime(_texts(language)["date_format"])


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


def _days(count: int, texts: dict[str, str]) -> str:
    return texts["day"] if count == 1 else texts["days"].format(value=count)


def itv_text(kind: str, *, days_left: int, due_date: str, language: str) -> str:
    """Texto del aviso de ITV (``kind``: ``"remaining"`` u ``"overdue"``)."""
    texts = _texts(language)
    if kind == "overdue":
        return texts["itv_overdue"].format(date=due_date)
    if days_left <= 0:
        return texts["itv_today"]
    return texts["itv_remaining"].format(days=_days(days_left, texts), date=due_date)


def insurance_text(
    kind: str, *, days_to_cancel: int, deadline: str, renewal: str, company: str, language: str
) -> str:
    """Texto del aviso de seguro (``kind``: ``"cancel"``, ``"last_day"`` o ``"renewed"``)."""
    texts = _texts(language)
    if kind == "renewed":
        return texts["insurance_renewed"].format(renewal=renewal)
    if kind == "last_day":
        return texts["insurance_last_day"].format(company=company or texts["your_insurer"])
    return texts["insurance_cancel"].format(
        days=_days(days_to_cancel, texts), deadline=deadline, renewal=renewal
    )
