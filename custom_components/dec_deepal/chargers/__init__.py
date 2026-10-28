"""Cargadores: une la carga de los coches con los cargadores de casa o del trabajo.

Sirve para **cualquier cargador** que tenga sus entidades en Home Assistant
(V2C, Wallbox, Easee, Zaptec, OCPP...): en el panel DEC Deepal → Ajustes →
Cargadores se elige qué entidad hace cada papel:

==============  ==========================================  =============
Papel           Entidad                                      ¿Obligatoria?
==============  ==========================================  =============
``plugged``     Manguera enchufada (``binary_sensor``)       Sí
``charging``    Cargando (``binary_sensor``)                 No
``power``       Potencia de carga (W o kW)                   No
``energy``      Energía de la carga (kWh)                    No
``lock``        Bloqueo (``switch`` o ``lock``)              No
==============  ==========================================  =============

Qué hace
--------
- **Solo bloquea y desbloquea.** Nunca inicia, pausa ni cambia la intensidad
  de la carga: con OCPP, la compañía empieza a cargar en cuanto el cargador
  queda desbloqueado.
- **Desbloquear al confirmar el coche** (``unlock = "confirm"``): al
  enchufar, el cargador sigue bloqueado hasta saber qué coche es:

  * Con cobertura (o "no lo sé"), se espera a que un coche diga que tiene la
    manguera puesta (``CHARGE_WAIT``): ese es, y se desbloquea solo.
  * Si no lo dice ninguno (o no hay cobertura), se pregunta por
    notificación, con un botón por coche (``mobile_app``). Al elegirlo, se
    desbloquea. Si nadie contesta, se recuerda pasados ``remind_minutes``.
- **Bloquear al desenchufar** (``relock``): desbloqueado y con la manguera
  quitada, se bloquea pasados ``relock_minutes`` (si no se vuelve a enchufar).
- **Cada carga** se apunta (coche, kWh, €, de qué % a cuál) y, sin cobertura,
  se **estima** el % y el tiempo con los kWh del cargador menos las
  **pérdidas** (10 % de fábrica). Cuando el coche vuelve a informar, se mide
  la pérdida real de esa carga (``learn``) y el panel la ofrece.
- **Límite de carga** (70, 80, 90 o 100 %, por coche; se elige en la tarjeta
  del coche): al llegarle (real o estimado), se **bloquea el cargador**. Es lo
  único que puede parar la carga: el EV no aplica el límite del servidor y el
  PHEV no deja leerlo (2.6.0b11). Sin bloqueo, solo se avisa. «Solo esta: 100 %» hace la siguiente carga completa.
- **Recordar cargar al 100 %** cada 3-6 cargas seguidas sin llegar (para que
  la batería se equilibre y el % sea exacto), o hacerla al 100 % sin preguntar.

Avisos
------
Los del apartado "Cargador" de la pestaña Avisos, de cada coche. Si un coche
no tiene destinos ahí, se usan los de sus avisos de carga. Ninguno es
crítico. El título es ``DEC Deepal <coche>``; mientras no se sabe el coche,
``DEC Deepal · <cargador>``.

Todo se guarda en su almacén (``dec_deepal.chargers``): es de la casa, no de
una cuenta, y un cargador puede servir a coches de cuentas distintas.

Estructura del paquete (2.6.0b13; antes, un solo ``chargers.py``)
-----------------------------------------------------------------
==================  ==============================================================
Módulo              Qué tiene
==================  ==============================================================
``const``           Papeles, opciones, tiempos, avisos y botones.
``models``          Formas de lo guardado (``TypedDict``): cargador, carga, historial,
                    límite de un coche y opciones del límite.
``config``          Validar lo que manda el panel (:func:`clean_charger`...).
``estimate``        Cuentas: % estimado, minutos que faltan, pérdida medida.
``util``            Leer estados de Home Assistant y fechas.
``manager``         :class:`ChargerManager`: arranque, guardado, escuchas,
                    configuración y temporizadores. Junta por herencia:
``session``         cada carga (enchufar, asignar, terminar, bloquear, leer el coche);
``energy``          kWh, % estimado y pérdidas;
``limit``           límite de carga y recordatorio del 100 %;
``notify``          preguntar, desbloquear y avisar;
``status``          lo que ven las tarjetas y el panel (solo lee);
``cars``            los coches y los permisos;
``entities``        las entidades del cargador.
==================  ==============================================================
"""

from .config import ChargerError, clean_charger, clean_limit
from .const import (
    ACTION_AGAIN,
    ACTION_FULL,
    ACTION_NEXT_FULL,
    ACTION_NO,
    ACTION_PREFIX,
    BY_CAR,
    BY_SINGLE,
    BY_USER,
    CHARGE_WAIT,
    CHARGE_WAIT_STEP,
    CONTROLS,
    CONTROL_ADMINS,
    CONTROL_PEOPLE,
    COVERAGES,
    COVERAGE_NO,
    COVERAGE_UNKNOWN,
    COVERAGE_YES,
    DEFAULT_LIMIT,
    DEFAULT_LOSS,
    EVENT_ACTION,
    FULL_EVERY_CHOICES,
    FULL_LEVEL,
    HISTORY_SIZE,
    LEARN_INTERVAL,
    LIMIT_CHOICES,
    LIMIT_NEAR,
    LIMIT_READ_MINUTES,
    LOCK_FULL_CHOICES,
    LOSS_SAMPLES,
    MAX_LOSS,
    NOTICE_CONFIRM,
    NOTICE_FINISHED,
    NOTICE_FULL,
    NOTICE_LIMIT,
    NOTICE_LOCKED,
    NOTICE_NOT_CHARGING,
    NOTICE_UNLOCKED,
    NOT_CHARGING_AFTER,
    READ_CHOICES,
    READ_FAILURES,
    RELOCK_CHOICES,
    REMIND_CHOICES,
    ROLES,
    ROLE_CHARGING,
    ROLE_DOMAINS,
    ROLE_ENERGY,
    ROLE_LOCK,
    ROLE_PLUGGED,
    ROLE_POWER,
    STORAGE_KEY,
    STORAGE_VERSION,
    UNLOCK_CONFIRM,
    UNLOCK_MODES,
    UNLOCK_NONE,
)
from .estimate import estimate_level, estimate_minutes, measured_loss
from .manager import ChargerManager, async_get_manager

__all__ = [
    "ACTION_AGAIN",
    "ACTION_FULL",
    "ACTION_NEXT_FULL",
    "ACTION_NO",
    "ACTION_PREFIX",
    "BY_CAR",
    "BY_SINGLE",
    "BY_USER",
    "CHARGE_WAIT",
    "CHARGE_WAIT_STEP",
    "CONTROLS",
    "CONTROL_ADMINS",
    "CONTROL_PEOPLE",
    "COVERAGES",
    "COVERAGE_NO",
    "COVERAGE_UNKNOWN",
    "COVERAGE_YES",
    "ChargerError",
    "ChargerManager",
    "DEFAULT_LIMIT",
    "DEFAULT_LOSS",
    "EVENT_ACTION",
    "FULL_EVERY_CHOICES",
    "FULL_LEVEL",
    "HISTORY_SIZE",
    "LEARN_INTERVAL",
    "LIMIT_CHOICES",
    "LIMIT_NEAR",
    "LIMIT_READ_MINUTES",
    "LOCK_FULL_CHOICES",
    "LOSS_SAMPLES",
    "MAX_LOSS",
    "NOTICE_CONFIRM",
    "NOTICE_FINISHED",
    "NOTICE_FULL",
    "NOTICE_LIMIT",
    "NOTICE_LOCKED",
    "NOTICE_NOT_CHARGING",
    "NOTICE_UNLOCKED",
    "NOT_CHARGING_AFTER",
    "READ_CHOICES",
    "READ_FAILURES",
    "RELOCK_CHOICES",
    "REMIND_CHOICES",
    "ROLES",
    "ROLE_CHARGING",
    "ROLE_DOMAINS",
    "ROLE_ENERGY",
    "ROLE_LOCK",
    "ROLE_PLUGGED",
    "ROLE_POWER",
    "STORAGE_KEY",
    "STORAGE_VERSION",
    "UNLOCK_CONFIRM",
    "UNLOCK_MODES",
    "UNLOCK_NONE",
    "async_get_manager",
    "clean_charger",
    "clean_limit",
    "estimate_level",
    "estimate_minutes",
    "measured_loss",
]
