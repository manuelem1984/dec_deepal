"""Avisos al móvil y ficha de mantenimiento de cada coche.

Un :class:`AlertManager` por cuenta. Hace dos cosas:

1. **Avisos.** Escucha cada lectura de cada coche y, según lo que el usuario
   haya elegido en el panel DEC Deepal → Avisos, envía una notificación a las apps de
   Home Assistant (o al panel de notificaciones). Cada coche tiene sus
   destinos para cada grupo de avisos: los del coche, mantenimiento, ITV y
   seguro. Qué se avisa, a quién y con qué texto: ``alert_rules.py``. El
   título es siempre ``DEC Deepal <nombre del coche>``. Ningún aviso es crítico.
2. **Mantenimiento.** Guarda la ficha de cada coche (última revisión,
   intervalo, historial) y calcula cuánto falta (``maintenance.py``).
3. **ITV y seguro.** Lo mismo con sus fichas (``documents.py``).

Dónde se guarda
---------------
En el almacén de coches (``vehicle_store.py``), no en las opciones: registrar
una revisión o apuntar un aviso ya enviado no debe recargar la integración.
Los datos van por bastidor: son del coche, no de la cuenta, y sobreviven a
quitar la cuenta y volver a añadirla.

Estructura del paquete (2.6.0b15; antes, un solo ``alerts.py``)
---------------------------------------------------------------
==================  ==============================================================
Módulo              Qué tiene
==================  ==============================================================
``const``           Horas tranquilas y revisión diaria.
``manager``         :class:`AlertManager`: arranque, guardado, escuchas, destinos
                    y envío. Junta por herencia:
``coche``           avisos por cambios del coche y cargas apuntadas;
``mantenimiento``   ficha de mantenimiento y sus avisos;
``documentos``      fichas de ITV y seguro y sus avisos.
==================  ==============================================================
"""

from .const import DAILY_CHECK_HOURS, QUIET_BEFORE_HOUR, QUIET_FROM_HOUR
from .manager import AlertManager

__all__ = ["DAILY_CHECK_HOURS", "QUIET_BEFORE_HOUR", "QUIET_FROM_HOUR", "AlertManager"]
