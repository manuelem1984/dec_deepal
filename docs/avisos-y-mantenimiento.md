# Avisos al móvil y mantenimiento

Dos funciones que se configuran desde **Ajustes → Dispositivos y servicios →
DEC Deepal → Configurar**. No hay que crear automatizaciones ni tocar nada más
en Home Assistant.

## Avisos al móvil

**Configurar → Avisos al móvil.** Se elige:

- **Avisar a:** los móviles y tabletas con la app de Home Assistant, con el
  nombre que tienen en *Ajustes → Aplicación móvil*. También vale cualquier
  otro servicio `notify` (aparece como `notify.nombre`).
- **Avisos activados:** los que se quieran de la lista.
- **Mostrar también en las notificaciones de Home Assistant** (la campana).

Todos los avisos son notificaciones normales (ninguno es crítico) y llevan el
nombre del coche en el título: **DEC Deepal Changote**.

| Aviso | Cuándo salta | Ejemplo de mensaje |
|---|---|---|
| Carga iniciada | El coche empieza a cargar | Carga iniciada (batería al 46 %). |
| Carga terminada | Deja de cargar con la batería llena o cuando quedaban pocos minutos | Carga terminada (batería al 80 %). |
| Carga interrumpida | Deja de cargar a media carga (corte, o cable desenchufado) | Carga interrumpida (batería al 63 %). |
| Testigos del cuadro | El coche enciende un testigo | Testigo encendido: Testigo ABS. |
| Neumáticos | El coche enciende el aviso de presión | Aviso de neumáticos: Aviso neumático delantero izquierdo. |
| Pila del mando baja | El coche lo indica | Pila del mando baja. Cámbiala por una CR2032. |
| Mantenimiento | Ver más abajo | Quedan 2.000 km o 47 días para la 2ª revisión. |

Detalles:

- **Sin repeticiones.** Un testigo se avisa cuando se enciende y no vuelve a
  avisarse hasta que se apague y se encienda otra vez (aunque se reinicie Home
  Assistant).
- **Depende de lo que envíe el coche.** Si un coche no manda testigos, no
  habrá avisos de testigos.
- ⚠️ **Sin verificar con el coche:** distinguir "terminada" de
  "interrumpida". El coche no dice por qué dejó de cargar; se deduce (ver
  `alert_rules.py`). Los testigos y la pila del mando tampoco se han podido
  provocar.

## Mantenimiento

**Configurar → Mantenimiento** (uno por coche). Se indica:

- **Revisiones ya pasadas.** 0 si el coche aún no ha pasado ninguna.
- **Fecha y kilómetros de la última revisión.** Con 0 revisiones: la fecha de
  matriculación y 0 km.
- **Intervalo.** Por defecto, el del manual del S05: 20.000 km o 12 meses, lo
  que llegue antes. El manual pide acortarlo con trayectos cortos repetidos,
  polvo, barro, frío extremo o sal.

La próxima revisión se cuenta **desde la última hecha** (no desde un
calendario fijo).

### Entidades

Solo en los coches con el mantenimiento activado:

| Entidad | Qué muestra |
|---|---|
| Testigo mantenimiento | Encendido cuando quedan 2 meses o 3.000 km, y mientras esté vencido |
| Días hasta el mantenimiento | Negativo si está vencido |
| Kilómetros hasta el mantenimiento | Negativo si está vencido |
| Próximo mantenimiento | Fecha prevista |

Se calculan con el último kilometraje conocido, así que siguen disponibles
aunque el coche esté dormido.

### Avisos de mantenimiento

Si el aviso "Mantenimiento" está activado, hay uno por escalón, una sola vez
por revisión: quedan **2 meses**, **1 mes**, **15 días**, **3.000 km**,
**2.000 km**, **1.000 km** y **vencido**. Solo se envían entre las 8:00 y las
22:00. Si al configurarlo ya se cumplen varios escalones, llega un único aviso
con la situación actual.

### Registrar una revisión

- **En la tarjeta:** pulsar la llave inglesa → *Registrar mantenimiento* →
  confirmar. Anota la fecha de hoy y los kilómetros actuales.
- **En Configurar → Mantenimiento → Registrar un mantenimiento hecho:** permite
  poner otra fecha y otros kilómetros.
- **Acción** `dec_deepal.register_maintenance` (para automatizaciones).

La revisión queda en el historial y se empieza a contar para la siguiente.
Para corregir un error: *Configurar → Mantenimiento → Corregir los datos o
desactivar*.

### Qué incluye cada revisión

Sale del plan del modelo en `vehicles/vehicles.yaml` (`mantenimiento:`),
tomado del manual de usuario del S05 para España:

| Revisión | Operaciones |
|---|---|
| Todas | Inspección general, neumáticos, filtro del aire acondicionado, limpieza del condensador y del evaporador |
| 2.ª, 4.ª, 6.ª... | Además: inspección de electricidad, aire acondicionado y mangueras; líquido de frenos (cada 2 años o 40.000 km) |
| 3.ª, 6.ª, 9.ª... | Además: líquido refrigerante (cada 3 años u 80.000 km). En el Max AWD, aceite del reductor delantero (cada 3 años o 60.000 km) |
| 5.ª, 10.ª... | Además: aceite del reductor trasero (cada 5 años o 100.000 km) |

Las operaciones con intervalo propio se colocan en la revisión en la que se
cumple su plazo **en años**. Quien haga muchos kilómetros al año puede
necesitarlas antes: manda lo que diga el taller.

## ITV

**Configurar → ITV** (uno por coche): fecha de matriculación y, si ya ha
pasado alguna, fecha de la última ITV. La próxima se calcula con la regla de
los turismos en España: la primera a los 4 años; después, cada 2 años mientras
el coche tenga menos de 10, y cada año a partir de entonces. Se puede poner
otra fecha a mano, que vale hasta registrar la siguiente ITV.

| Entidad | Qué muestra |
|---|---|
| Testigo ITV | Encendido desde 2 meses antes de la fecha límite, y mientras esté vencida |
| Próxima ITV | Fecha límite |
| Días hasta la ITV | Negativo si está vencida |

Avisos (tipo "ITV"): quedan 2 meses, 1 mes, 15 días y vencida. Registrar una
ITV pasada: en la tarjeta (*Registrar ITV pasada*, con confirmación), con la
acción `dec_deepal.register_itv` o poniendo la fecha en Configurar.

## Seguro

**Configurar → Seguro** (uno por coche): compañía, número de póliza, tipo
(terceros, terceros ampliado, todo riesgo con o sin franquicia), fecha de
renovación, días de antelación para desistir (30 por defecto) y dos teléfonos
opcionales (asistencia en carretera y compañía).

| Entidad | Qué muestra |
|---|---|
| Testigo seguro | Ámbar los 30 días antes del límite para desistir; rojo el último día |
| Renovación del seguro | Fecha |
| Días hasta la renovación del seguro | |
| Límite para desistir del seguro | Renovación menos los días de antelación |

Avisos (tipo "Seguro"): 30 y 15 días antes del límite para desistir, el
último día y el día de la renovación. Ese día la ficha pasa sola al año
siguiente.

**Privacidad:** el número de póliza y los teléfonos no están en ninguna
entidad (quedarían en el historial) ni en los diagnósticos. Solo los pide la
tarjeta, con la sesión del usuario, al abrir la ventana del seguro.

## Dónde se guarda

Las fichas de mantenimiento y los avisos ya enviados se guardan en
`.storage/dec_deepal.<id de la cuenta>` (entra en las copias de seguridad).
Se borran al quitar la cuenta de la integración.

## Para quien toque el código

| Archivo | Qué hace |
|---|---|
| `maintenance.py` | Cálculo de días y kilómetros, escalones de aviso, registro (sin Home Assistant) |
| `documents.py` | ITV y seguro: fechas, niveles y avisos (sin Home Assistant) |
| `alert_rules.py` | Qué cambios del coche avisan y los textos (sin Home Assistant) |
| `alerts.py` | `AlertManager`: almacén, vigilancia de cada lectura y envío |
| `options_flow.py` | Pasos `alerts` y `maintenance*` |
| `services.py` | Acción `register_maintenance` |

Pruebas: `tests/test_maintenance.py` y `tests/test_alert_manager.py`.
