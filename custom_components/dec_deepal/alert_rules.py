"""Avisos al móvil: qué cambios del coche merecen un aviso y con qué texto.

Lógica pura (sin Home Assistant), para poder probarla sola. El envío y la
configuración están en ``alerts.py``.

Tipos de aviso (el usuario activa los que quiera en el panel DEC Deepal → Avisos):

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


#: Grupos de avisos del apartado clásico de Configurar (hasta la 2.4.0 se
#: elegían los destinos por grupo; el panel los elige aviso a aviso).
GROUP_CAR: Final = "car"
GROUP_MAINTENANCE: Final = "maintenance"
GROUP_ITV: Final = "itv"
GROUP_INSURANCE: Final = "insurance"
GROUPS: Final = (GROUP_CAR, GROUP_MAINTENANCE, GROUP_ITV, GROUP_INSURANCE)
#: Avisos del grupo "coche" (carga, testigos, neumáticos y pila del mando).
CAR_ALERT_TYPES: Final = ALERT_TYPES[:6]
#: Destino especial: el panel de notificaciones de Home Assistant.
TARGET_PANEL: Final = "persistent_notification"

#: Apartados del panel, en su orden.
SECTION_CHARGE: Final = "charge"
SECTION_WARNINGS: Final = "warnings"
#: Avisos de los cargadores (``chargers.py``). Si un coche no tiene destinos
#: aquí, el cargador usa los de sus avisos de carga.
SECTION_CHARGER: Final = "charger"
SECTIONS: Final = (
    SECTION_CHARGE, SECTION_WARNINGS, SECTION_CHARGER, GROUP_MAINTENANCE, GROUP_ITV, GROUP_INSURANCE,
)  # fmt: skip
UNIT_DAYS: Final = "days"
UNIT_KM: Final = "km"


@dataclass(frozen=True, slots=True)
class Notice:
    """Un aviso concreto: con sus destinos y, si tiene plazo, cuándo salta."""

    id: str
    section: str
    #: Plazo de fábrica (días o km que quedan); ``None`` = no tiene plazo.
    threshold: int | None = None
    unit: str | None = None
    #: Nuevo en la 2.5.0: nace sin destinos (no lo recibía nadie antes).
    opt_in: bool = False

    @property
    def group(self) -> str:
        """Grupo del apartado clásico de Configurar."""
        return GROUP_CAR if self.section in (SECTION_CHARGE, SECTION_WARNINGS) else self.section

    @property
    def limits(self) -> tuple[int, int] | None:
        """Mínimo y máximo que se puede poner de plazo."""
        if self.unit == UNIT_DAYS:
            return (1, 365)
        return (100, 20000) if self.unit == UNIT_KM else None


def _due(section: str, step: str, threshold: int | None = None, unit: str | None = None, **more: Any) -> Notice:
    return Notice(f"{section}_{step}", section, threshold, unit, **more)


#: Todos los avisos, en el orden del panel. El id de los de mantenimiento,
#: ITV y seguro es ``<apartado>_<escalón>`` (los escalones los calculan
#: ``maintenance.py`` y ``documents.py``).
NOTICES: Final[tuple[Notice, ...]] = (
    Notice(ALERT_CHARGE_STARTED, SECTION_CHARGE),
    Notice(ALERT_CHARGE_INTERRUPTED, SECTION_CHARGE),
    Notice(ALERT_CHARGE_FINISHED, SECTION_CHARGE),
    Notice(ALERT_WARNINGS, SECTION_WARNINGS),
    Notice(ALERT_TIRES, SECTION_WARNINGS),
    Notice(ALERT_KEY_BATTERY, SECTION_WARNINGS),
    _due(SECTION_CHARGER, "confirm"),
    _due(SECTION_CHARGER, "unlocked"),
    _due(SECTION_CHARGER, "not_charging"),
    _due(SECTION_CHARGER, "finished"),
    _due(SECTION_CHARGER, "locked"),
    _due(GROUP_MAINTENANCE, "t1", 60, UNIT_DAYS),
    _due(GROUP_MAINTENANCE, "t2", 30, UNIT_DAYS),
    _due(GROUP_MAINTENANCE, "t3", 15, UNIT_DAYS),
    _due(GROUP_MAINTENANCE, "k1", 5000, UNIT_KM),
    _due(GROUP_MAINTENANCE, "k2", 2500, UNIT_KM),
    _due(GROUP_MAINTENANCE, "k3", 1000, UNIT_KM),
    _due(GROUP_MAINTENANCE, "overdue"),
    _due(GROUP_ITV, "t1", 60, UNIT_DAYS),
    _due(GROUP_ITV, "t2", 30, UNIT_DAYS),
    _due(GROUP_ITV, "t3", 15, UNIT_DAYS),
    _due(GROUP_ITV, "overdue"),
    _due(GROUP_INSURANCE, "c1", 30, UNIT_DAYS),
    _due(GROUP_INSURANCE, "c2", 15, UNIT_DAYS),
    _due(GROUP_INSURANCE, "last_day"),
    _due(GROUP_INSURANCE, "r1", 30, UNIT_DAYS, opt_in=True),
    _due(GROUP_INSURANCE, "r2", 15, UNIT_DAYS, opt_in=True),
    _due(GROUP_INSURANCE, "renewed"),
)
NOTICE: Final[dict[str, Notice]] = {notice.id: notice for notice in NOTICES}
#: Plazos que deben ir de mayor a menor (el aviso 1 salta antes que el 2).
THRESHOLD_CHAINS: Final = (
    ("maintenance_t1", "maintenance_t2", "maintenance_t3"),
    ("maintenance_k1", "maintenance_k2", "maintenance_k3"),
    ("itv_t1", "itv_t2", "itv_t3"),
    ("insurance_c1", "insurance_c2"),
    ("insurance_r1", "insurance_r2"),
)
#: Claves de lo guardado por coche (``options["alerts"]["vehicles"][<id>]``).
KEY_NOTICES: Final = "notices"
KEY_THRESHOLDS: Final = "thresholds"

#: Motivos por los que se rechazan unos plazos (claves de texto del panel).
ERROR_THRESHOLD_RANGE: Final = "threshold_range"
ERROR_THRESHOLD_ORDER: Final = "threshold_order"


class ThresholdError(ValueError):
    """Plazos que no valen. ``code`` dice por qué y ``notice`` cuál."""

    def __init__(self, code: str, notice: str) -> None:
        super().__init__(f"{code}: {notice}")
        self.code = code
        self.notice = notice


def clean_thresholds(raw: Mapping[str, Any] | None) -> dict[str, int]:
    """Plazos válidos a partir de lo que manda el panel (solo los distintos de fábrica).

    Raises:
        ThresholdError: un plazo fuera de sus límites, o un aviso que saltaría
            después que el siguiente (p. ej. aviso 1 a 20 días y aviso 2 a 30).
    """
    values = {notice.id: notice.threshold for notice in NOTICES if notice.threshold is not None}
    for notice_id, value in (raw or {}).items():
        notice = NOTICE.get(str(notice_id))
        if notice is None or notice.limits is None:
            continue
        low, high = notice.limits
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise ThresholdError(ERROR_THRESHOLD_RANGE, notice.id)
        values[notice.id] = int(value)
    for chain in THRESHOLD_CHAINS:
        for earlier, later in zip(chain, chain[1:], strict=False):
            if values[earlier] <= values[later]:
                raise ThresholdError(ERROR_THRESHOLD_ORDER, later)
    return {
        notice_id: value for notice_id, value in values.items() if value != NOTICE[notice_id].threshold
    }


def _unique(names: Iterable[Any]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(name) for name in names if name))


@dataclass(frozen=True, slots=True)
class Route:
    """A quién avisa un coche de cada cosa, y con qué plazos."""

    #: Destinos de cada aviso (servicios ``notify.*`` o :data:`TARGET_PANEL`).
    targets: Mapping[str, tuple[str, ...]]
    #: Plazos cambiados respecto a los de fábrica: ``{aviso: días o km}``.
    thresholds: Mapping[str, int]

    def targets_for(self, alert: str) -> tuple[str, ...]:
        """Destinos de un aviso (vacío = no se avisa).

        También admite un apartado entero (``"maintenance"``): devuelve los
        destinos de cualquiera de sus avisos.
        """
        if alert in NOTICE:
            return self.targets.get(alert, ())
        return self.group_targets(alert)

    def group_targets(self, group: str) -> tuple[str, ...]:
        """Destinos de un grupo o apartado: los de todos sus avisos, sin repetir."""
        return _unique(
            target
            for notice in NOTICES
            if group in (notice.group, notice.section)
            for target in self.targets.get(notice.id, ())
        )

    @property
    def car_types(self) -> frozenset[str]:
        """Avisos del coche (carga, testigos...) que tienen algún destino."""
        return frozenset(kind for kind in CAR_ALERT_TYPES if self.targets.get(kind))

    def threshold(self, notice_id: str) -> int:
        """Plazo de un aviso: el del coche o, si no lo ha cambiado, el de fábrica."""
        return int(self.thresholds.get(notice_id, NOTICE[notice_id].threshold or 0))

    def steps(self, section: str, kind: str) -> tuple[int, ...]:
        """Plazos de una serie (``("maintenance", "k")`` → ``(5000, 2500, 1000)``)."""
        return tuple(
            self.threshold(notice.id)
            for notice in NOTICES
            if notice.section == section and notice.threshold is not None
            and notice.id.removeprefix(f"{section}_").startswith(kind)
        )  # fmt: skip

    def to_dict(self) -> dict[str, Any]:
        """Como se guarda en las opciones."""
        return {
            KEY_NOTICES: {notice.id: list(self.targets.get(notice.id, ())) for notice in NOTICES},
            KEY_THRESHOLDS: dict(self.thresholds),
        }

    @classmethod
    def from_groups(
        cls,
        groups: Mapping[str, Iterable[str]],
        car_types: Iterable[str],
        base: Route | None = None,
    ) -> Route:
        """A partir de lo elegido por grupos (apartado clásico de Configurar).

        Todos los avisos de un grupo reciben sus destinos; del grupo "coche",
        solo los activados. Lo que el apartado clásico no sabe tocar se
        conserva de ``base``: los plazos y los avisos nuevos (``opt_in``).
        """
        chosen = set(car_types)
        targets: dict[str, tuple[str, ...]] = {}
        for notice in NOTICES:
            if notice.opt_in:
                targets[notice.id] = base.targets.get(notice.id, ()) if base else ()
            elif notice.group == GROUP_CAR and notice.id not in chosen:
                targets[notice.id] = ()
            else:
                targets[notice.id] = _unique(groups.get(notice.group) or ())
        return cls(targets=targets, thresholds=dict(base.thresholds) if base else {})


#: Coche sin ningún aviso.
NO_ROUTE: Final = Route(targets={}, thresholds={})


def route_for(config: Mapping[str, Any] | None, vehicle_id: str) -> Route:
    """A quién avisa un coche, según las opciones de la cuenta.

    Lee los tres formatos que ha habido:

    - **2.5.0** (panel): destinos aviso a aviso y plazos, por coche.
    - **2.4.0**: destinos por grupo, por coche.
    - **Antes**: una sola lista para toda la cuenta. Todos los coches avisan
      a esa lista de los tipos que estuvieran activados.

    Al leer un formato anterior, los avisos de un grupo heredan sus destinos,
    de modo que nadie nota nada al actualizar.
    """
    if not config:
        return NO_ROUTE
    vehicles = config.get(OPT_ALERT_VEHICLES)
    if isinstance(vehicles, Mapping):
        stored = vehicles.get(vehicle_id)
        if not isinstance(stored, Mapping):
            return NO_ROUTE
        if isinstance(stored.get(KEY_NOTICES), Mapping):
            try:
                thresholds = clean_thresholds(stored.get(KEY_THRESHOLDS))
            except ThresholdError:
                thresholds = {}
            return Route(
                targets={
                    notice.id: _unique(stored[KEY_NOTICES].get(notice.id) or ()) for notice in NOTICES
                },
                thresholds=thresholds,
            )
        known = stored.get(OPT_ALERT_CAR_KNOWN)
        chosen = set(stored.get(OPT_ALERT_CAR_TYPES) or ())
        # Tipos que no existían al guardar nacen activados.
        new = set(CAR_ALERT_TYPES) - set(CAR_ALERT_TYPES if known is None else known)
        return Route.from_groups(stored, (chosen & set(CAR_ALERT_TYPES)) | new)

    targets = list(config.get(OPT_ALERT_TARGETS) or ())
    if config.get(OPT_ALERT_PERSISTENT):
        targets.append(TARGET_PANEL)
    types = enabled_types(config.get(OPT_ALERT_TYPES), config.get(OPT_ALERT_KNOWN))
    return Route.from_groups(
        {
            GROUP_CAR: targets,
            **{group: targets for group in (GROUP_MAINTENANCE, GROUP_ITV, GROUP_INSURANCE) if group in types},
        },
        types & set(CAR_ALERT_TYPES),
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


def pin_armed_text(seconds: int, language: str) -> str:
    """Aviso "Comandos con PIN permitidos durante N segundos" (Opción B)."""
    return _texts(language)["pin_armed"].format(seconds=seconds)


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


def texts(language: str) -> dict[str, str]:
    """Textos de los avisos en un idioma (con el de respaldo si falta alguno)."""
    return _texts(language)


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
    """Texto del aviso de seguro.

    ``kind``: ``"cancel"`` (quedan X días para desistir), ``"last_day"``,
    ``"renewal"`` (quedan X días para que se renueve; ``days_to_cancel`` son
    entonces los días hasta la renovación) o ``"renewed"``.
    """
    texts = _texts(language)
    if kind == "renewed":
        return texts["insurance_renewed"].format(renewal=renewal)
    if kind == "renewal":
        return texts["insurance_renewal"].format(
            days=_days(days_to_cancel, texts), renewal=renewal
        )
    if kind == "last_day":
        return texts["insurance_last_day"].format(company=company or texts["your_insurer"])
    return texts["insurance_cancel"].format(
        days=_days(days_to_cancel, texts), deadline=deadline, renewal=renewal
    )
