# Avisos al móvil y mantenimiento

Dos funciones que se configuran desde **Ajustes → Dispositivos y servicios →
DEC Deepal → Configurar**. No hay que crear automatizaciones ni tocar nada más
en Home Assistant.

## Avisos al móvil

Desde la 2.5.0, los avisos se eligen **uno a uno** y con sus plazos en el
**panel DEC Deepal** de la barra lateral (pestaña Avisos; ver
[panel.md](panel.md)). Lo que sigue describe el apartado clásico, que sigue
funcionando y es una versión resumida de lo mismo.

**Panel DEC Deepal → Avisos** (uno por coche). Cada coche reparte sus
avisos en cuatro grupos, y cada grupo tiene su lista de destinos:

| Grupo | Qué avisos lleva |
|---|---|
| Avisos del coche | Carga iniciada, interrumpida y terminada, testigos, neumáticos y pila del mando. Se activan uno a uno |
| Mantenimiento | Los de la revisión |
| ITV | Los de la ITV |
| Seguro | Los del seguro |

Así, en una casa con dos coches, cada conductor recibe los avisos de su
coche, y quien lleva los papeles, los de mantenimiento, ITV y seguro de los
dos.

- **Destinos:** los móviles y tabletas con la app de Home Assistant, con el
  nombre que tienen en *Ajustes → Aplicación móvil*; cualquier otro servicio
  `notify` (aparece como `notify.nombre`), y las **notificaciones de Home
  Assistant** (la campana).
- **Un grupo sin destinos no avisa.**
- **Usar lo mismo en los demás coches:** copia lo elegido a todos.
- Quien configuró los avisos antes de la 2.4.0 (una sola lista para toda la
  cuenta) no nota nada al actualizar: todos los coches siguen avisando a esa
  lista hasta que se guarde este apartado.
- Un coche que se añada después a la cuenta empieza sin avisos.

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
- **Testigos que no avisan.** El S05 enciende el del airbag unos segundos
  cada vez que despierta: su ficha (`testigos_sin_aviso` en `vehicles.yaml`)
  lo silencia, y no avisa ni sale en la tarjeta. La entidad sigue existiendo.
- ⚠️ **Sin verificar con el coche:** distinguir "terminada" de
  "interrumpida". El coche no dice por qué dejó de cargar; se deduce (ver
  `alert_rules.py`). Los testigos y la pila del mando tampoco se han podido
  provocar.

## Mantenimiento

**Panel DEC Deepal → Coches → Mantenimiento** (uno por coche). Se indica:

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
- **En el panel DEC Deepal → Coches → Mantenimiento → Registrar:** permite
  poner otra fecha y otros kilómetros.
- **Acción** `dec_deepal.register_maintenance` (para automatizaciones).

La revisión queda en el historial y se empieza a contar para la siguiente.
Para corregir un error: *Panel DEC Deepal → Coches → Mantenimiento*, con el
lápiz de la ficha (o desactivarla).

### Qué incluye cada revisión

Sale del plan del modelo en `vehicles/vehicles.yaml` (`mantenimiento:`),
tomado del manual de usuario del S05 para España:

| Revisión | Operaciones |
|---|---|
| Todas | Inspección general, neumáticos, filtro del aire acondicionado, limpieza del condensador y del evaporador |
| 2.ª, 4.ª, 6.ª... | Además: inspección de electricidad, aire acondicionado y mangueras; líquido de frenos (cada 2 años o 40.000 km) |
| 3.ª, 6.ª, 9.ª... | Además: líquido refrigerante (cada 3 años u 80.000 km). En el 4WD Max, aceite del reductor delantero (cada 3 años o 60.000 km) |
| 5.ª, 10.ª... | Además: aceite del reductor trasero (cada 5 años o 100.000 km) |

Las operaciones con intervalo propio se colocan en la revisión en la que se
cumple su plazo **en años**. Quien haga muchos kilómetros al año puede
necesitarlas antes: manda lo que diga el taller.

## ITV

**Panel DEC Deepal → Coches → ITV** (uno por coche): fecha de matriculación y, si ya ha
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

**Panel DEC Deepal → Coches → Seguro** (uno por coche): compañía, número de póliza, tipo
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

El mantenimiento, la ITV, el seguro y los avisos ya enviados se guardan en
`.storage/dec_deepal.vehicles`, **por coche** (por su bastidor), no por
cuenta. Entra en las copias de seguridad de Home Assistant.

Con ellos se guarda una copia de la **apariencia** (modelo, versión, color y
llanta). La que manda es la del panel DEC Deepal → Coches → Apariencia; la copia sirve para
devolvérsela al coche si la cuenta se quita y se vuelve a añadir, y viaja en
las copias de seguridad. El PIN y los avisos al móvil son de la cuenta: no
se guardan con el coche.

- **Quitar la cuenta no borra los datos.** Al volver a añadirla, cada coche
  recupera su historial, aunque el servidor le dé otro identificador.
- **Copia de seguridad propia:** el panel DEC Deepal → Datos →
  *Descargar una copia* genera un fichero con las fichas de todos los coches
  (el enlace caduca a los 10 minutos y se abre en el navegador, también
  desde la app del móvil). *Enviar la copia a un móvil* manda una
  notificación al móvil elegido: al tocarla se abre el navegador y se
  descarga. *Cargar una copia* lo restaura en esta
  u otra instalación: deja los coches que trae como estaban en el fichero
  (fichas y apariencia) y no toca los demás. El fichero lleva la póliza y los teléfonos del seguro.
- **Borrar:** el panel DEC Deepal → Datos → *Borrar datos guardados*,
  eligiendo los coches (también los que ya no están en ninguna cuenta). Para
  no dejar nada al desinstalar, hay que borrarlos **antes** de quitar la
  cuenta.

Hasta la 2.3.0 había un almacén por cuenta (`.storage/dec_deepal.<id de la
cuenta>`): se pasa al nuevo solo, la primera vez que arranca la 2.4.0.

## Para quien toque el código

| Archivo | Qué hace |
|---|---|
| `maintenance.py` | Cálculo de días y kilómetros, escalones de aviso, registro (sin Home Assistant) |
| `documents.py` | ITV y seguro: fechas, niveles y avisos (sin Home Assistant) |
| `alert_rules.py` | Qué cambios del coche avisan y los textos (sin Home Assistant) |
| `alerts/` | `AlertManager` (`manager.py`): vigilancia de cada lectura y envío; avisos del coche (`coche.py`), de mantenimiento (`mantenimiento.py`) y de ITV y seguro (`documentos.py`) |
| `vehicle_data.py` | Formato de los datos por coche, migración y copias (sin Home Assistant) |
| `vehicle_store.py` | Almacén por bastidor, adopción del antiguo y descarga de la copia |
| `panel/` | Órdenes del panel: avisos, fichas y datos |
| `services.py` | Acción `register_maintenance` |

Pruebas: `tests/test_maintenance.py` y `tests/test_alert_manager.py`.
