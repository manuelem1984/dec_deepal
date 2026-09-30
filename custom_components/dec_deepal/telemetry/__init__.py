"""Telemetría: de datos en bruto (MQTT / REST) a "señales" limpias.

El coche informa por dos vías con formatos distintos:

- **MQTT** (``api/mqtt``): un diccionario *plano* con nombres propios del
  coche (``soc``, ``driverDoor``, ``lfTyrePressure``...). Es la fuente
  principal del S05: rápida y completa.
- **REST** (``condition``): un JSON *anidado* por categorías
  (``seat.leftFront.heatStatus``...). Es el mismo que usa la app para su
  pantalla y es más fiable para asientos, volante y desempañado.

Este paquete traduce ambos a un vocabulario común de **señales**
(``battery_level``, ``door_front_left``...), definido en ``signals.py``. Las
entidades de Home Assistant solo conocen señales: no saben de dónde vino cada
dato. Eso permite añadir otro modelo de coche (con otras claves) tocando solo
las tablas de mapeo.

=================  ============================================================
Módulo             Qué contiene
=================  ============================================================
``signals.py``     La lista de señales (nombre, significado, unidad).
``converters.py``  Conversores reutilizables (a entero, décimas, conector...).
``mqtt_map.py``    Tabla: clave MQTT → señal (+ conversor).
``rest_map.py``    Tabla: ruta REST → señal (+ conversor).
``derived.py``     Señales calculadas a partir de otras (estado de carga...).
``state.py``       Fusión de MQTT + REST + último valor conocido.
=================  ============================================================

Nada de este paquete importa Home Assistant.
"""
