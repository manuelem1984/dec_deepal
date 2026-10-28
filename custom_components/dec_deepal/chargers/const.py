"""Constantes de los cargadores: papeles, opciones, tiempos, avisos y botones."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from ..const import DOMAIN



STORAGE_KEY: Final = f"{DOMAIN}.chargers"
STORAGE_VERSION: Final = 1
_MANAGER_KEY: Final = "chargers"

# --- Papeles de las entidades -------------------------------------------------------
ROLE_PLUGGED: Final = "plugged"
ROLE_CHARGING: Final = "charging"
ROLE_POWER: Final = "power"
ROLE_ENERGY: Final = "energy"
ROLE_LOCK: Final = "lock"
ROLES: Final = (ROLE_PLUGGED, ROLE_CHARGING, ROLE_POWER, ROLE_ENERGY, ROLE_LOCK)
#: Dominios que admite cada papel.
ROLE_DOMAINS: Final = {
    ROLE_PLUGGED: ("binary_sensor", "sensor", "switch", "input_boolean"),
    ROLE_CHARGING: ("binary_sensor", "sensor", "switch", "input_boolean"),
    ROLE_POWER: ("sensor",),
    ROLE_ENERGY: ("sensor",),
    ROLE_LOCK: ("switch", "lock", "input_boolean"),
}

# --- Opciones de cada cargador ------------------------------------------------------
COVERAGE_YES: Final = "yes"
COVERAGE_NO: Final = "no"
COVERAGE_UNKNOWN: Final = "unknown"
COVERAGES: Final = (COVERAGE_YES, COVERAGE_NO, COVERAGE_UNKNOWN)
UNLOCK_NONE: Final = "none"
UNLOCK_CONFIRM: Final = "confirm"
UNLOCK_MODES: Final = (UNLOCK_NONE, UNLOCK_CONFIRM)
REMIND_CHOICES: Final = (5, 15, 60)
RELOCK_CHOICES: Final = (3, 5, 10)
#: Bloquear al terminar la carga: minutos sin cargar (con el coche al 100 %).
LOCK_FULL_CHOICES: Final = (15, 30, 45)
#: Desde qué % se da la carga por completa (real o estimado).
FULL_LEVEL: Final = 99.0
#: Leer el coche mientras carga: cada cuántos minutos (0 = no).
READ_CHOICES: Final = (0, 10, 15, 30)
#: Despertares fallidos seguidos que confirman que no hay cobertura.
READ_FAILURES: Final = 2
DEFAULT_LOSS: Final = 10.0
MAX_LOSS: Final = 40.0
#: Quién puede desbloquear desde la tarjeta o las notificaciones.
CONTROL_PEOPLE: Final = "people"  # las personas de los coches y los administradores
CONTROL_ADMINS: Final = "admins"
CONTROLS: Final = (CONTROL_PEOPLE, CONTROL_ADMINS)

# --- Tiempos ------------------------------------------------------------------------
#: Cuánto se espera a que el coche confirme la manguera antes de preguntar.
CHARGE_WAIT: Final = timedelta(minutes=5)
#: Cada cuánto se mira si algún coche lo ha confirmado.
CHARGE_WAIT_STEP: Final = 30
#: Desbloqueado y sin cargar pasado este tiempo: aviso "no carga".
NOT_CHARGING_AFTER: Final = timedelta(minutes=10)
#: Cada cuánto se intenta medir la pérdida de las cargas ya terminadas.
LEARN_INTERVAL: Final = timedelta(minutes=10)
#: Cargas que se guardan por cargador, y pérdidas medidas que se promedian.
HISTORY_SIZE: Final = 60
LOSS_SAMPLES: Final = 10

# --- Límite de carga ----------------------------------------------------------------
#: % a los que se puede limitar la carga de un coche (100 = sin límite).
LIMIT_CHOICES: Final = (70, 80, 90, 100)
DEFAULT_LIMIT: Final = 100
#: Recordar cargar al 100 % cada N cargas seguidas sin llegar.
FULL_EVERY_CHOICES: Final = (3, 4, 5, 6)
#: A menos de estos puntos del límite, el coche se lee más a menudo...
LIMIT_NEAR: Final = 5.0
#: ...cada estos minutos (si "Leer el coche mientras carga" está activado).
LIMIT_READ_MINUTES: Final = 5

# --- Notificaciones -----------------------------------------------------------------
EVENT_ACTION: Final = "mobile_app_notification_action"
ACTION_PREFIX: Final = "DEC_DEEPAL_CHARGER"
ACTION_NO: Final = "-"
ACTION_AGAIN: Final = "again"
NOTICE_CONFIRM: Final = "charger_confirm"
NOTICE_UNLOCKED: Final = "charger_unlocked"
NOTICE_NOT_CHARGING: Final = "charger_not_charging"
NOTICE_FINISHED: Final = "charger_finished"
NOTICE_LOCKED: Final = "charger_locked"
NOTICE_LIMIT: Final = "charger_limit"
NOTICE_FULL: Final = "charger_full"
#: Botones del límite: seguir hasta el 100 % (esta carga) y la próxima al 100 %.
ACTION_FULL: Final = "full"
ACTION_NEXT_FULL: Final = "nextfull:"

#: Cómo asignó la carga a un coche.
BY_CAR: Final = "car"  # el coche dijo que tenía la manguera
BY_USER: Final = "user"  # alguien lo eligió (notificación, tarjeta)
BY_SINGLE: Final = "single"  # el cargador solo tiene un coche
