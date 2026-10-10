# Tarjeta DEC Deepal

Una tarjeta para los paneles de Home Assistant con tu coche de un vistazo. Se
instala sola con la integración: no hay que añadir recursos ni copiar archivos.

## Añadirla

Panel → **Editar** → **Añadir tarjeta** → buscar **DEC Deepal** → elegir el
coche. En YAML:

```yaml
type: custom:dec-deepal-card
device_id: <dispositivo del coche>   # opcional: si falta, el primero
```

Con dos coches, una tarjeta por coche.

## Qué muestra

- **Cabecera:** nombre del coche, "Actualizado: hoy, 14:11" (el último informe
  del coche) y el botón de actualizar.
- **Vista isométrica**, que cambia sola con puertas, capó, maletero,
  ventanillas y luces. Tocarla no hace nada.
- **Línea de estado** (encima de la batería, a la derecha): un tic verde si
  no hay avisos. Si los hay, el icono de cada testigo encendido: en rojo
  los graves (frenos, líquido de frenos, airbag, batería de 12 V,
  refrigerante y sistema de propulsión) y en ámbar el resto (ABS,
  dirección asistida, neumáticos, potencia limitada, batería baja y pila
  del mando).
- **Batería:** icono según el nivel (verde con el 50 % o más, amarillo por
  debajo del 50 %, rojo por debajo del 15 %; con un rayo si está cargando),
  autonomía, estado de carga y la barra.
- **Seis botones** (dos filas de tres):

| Botón | Qué hace | PIN |
| --- | --- | --- |
| **Confort** | Abre la ventana de confort | No |
| **Bloqueo** | Bloquea o desbloquea las puertas | Sí |
| **Maletero** | Abre o cierra el maletero | Sí |
| **Ventilar** | Entreabre las ventanillas, o las cierra | Sí |
| **Localizar vehículo** | Abre un menú: Luces, Claxon, o Luces y claxon | No |
| **Otros** | Abre un menú: Manual y Mantenimiento | No |

### Botón "Otros"

Abre un menú con dos opciones:

- **Manual** (libro abierto): abre el manual de usuario (PDF) en el
  navegador, en una pestaña nueva. El manual no viene dentro de la
  integración: es un enlace a la web del fabricante. Sale del catálogo según
  el modelo y se puede cambiar en *Configurar → Avanzado → Manual BEV*. Si el
  modelo no tiene manual, la opción no aparece.
- **Mantenimiento** (llave inglesa): la ventana de mantenimiento, disponible
  siempre. Si el coche no lo tiene activado, explica cómo hacerlo.
- **ITV** (portapapeles): días que quedan, fecha límite, matriculación, última
  ITV, historial y el botón *Registrar ITV pasada*.
- **Seguro** (escudo): días para la renovación y para desistir, compañía, tipo,
  número de póliza y botones para llamar a la asistencia y a la compañía (si
  se pusieron los teléfonos).

Las cuatro opciones salen de dos en dos. ITV y Seguro tienen también su
testigo en la línea de estado, como el de mantenimiento.

Cuando la revisión está próxima o vencida, el texto del botón cambia a
"Revisión en 47 días" o "Revisión vencida".

### Testigo de mantenimiento

Si el coche tiene el mantenimiento activado (*Configurar → Mantenimiento*), en
la línea de estado aparece una **llave inglesa** cuando quedan 2 meses o
3.000 km para la revisión: ámbar, o roja si está vencida. Es el único testigo
que se puede pulsar. Abre una ventana con los días y kilómetros que quedan, la
fecha prevista, lo que incluye la revisión, el historial y el botón
**Registrar mantenimiento**, que pide confirmación y anota la revisión con la
fecha de hoy y los kilómetros actuales. Ver
[avisos-y-mantenimiento.md](avisos-y-mantenimiento.md).

### Ventana de Confort

La vista interior con los botones encima de la foto:

- **Volante** calefactado (encendido / apagado).
- En cada asiento delantero, **ventilación** (izquierda) y **calefacción**
  (derecha). Cada toque sube un nivel: 1, 2, 3 y apagado.
- Los iconos no llevan color para no chocar con la vista: **blanco =
  encendido** (con su nivel), **atenuado = apagado**. Lo encendido se ve
  además iluminado en la propia foto (naranja = calor, azul = ventilación).
- **Temperatura** (− / +, de medio en medio grado) y **climatizador**
  encendido / apagado.
- Debajo: temperatura interior, humedad, ventilador y aire exterior o
  recirculación.

### Órdenes con PIN

Bloqueo, Maletero y Ventilar piden **confirmación**. Si en la integración
tienes el modo "con desbloqueo previo", la tarjeta hace sola el desbloqueo y
después la orden. Si el control con PIN no está activado, esos tres botones
solo muestran el estado y avisan de cómo activarlo.

## Cómo funciona por dentro

- `frontend_card/dec-deepal-card.js`: JavaScript plano, un solo archivo, sin
  dependencias ni compilación.
- **Encuentra las entidades sola:** cada entidad de la integración tiene una
  clave interna (`translation_key`) que no cambia aunque se renombre. La
  tarjeta busca, entre las entidades del dispositivo elegido, la de cada
  clave. Una prueba comprueba que todas las claves que usa existen.
- **Carga:** la trae `dec-icons.js`, así llega por los mismos caminos que los
  iconos (ver [iconos.md](iconos.md)). Tras un reinicio, si llega tarde, Home
  Assistant la vuelve a pintar sola.
- Solo repinta cuando cambia alguna de sus entidades, y la imagen solo se
  vuelve a pedir cuando cambia.
- La posición de los botones sobre la foto interior y los recortes de las
  imágenes están al principio del archivo (`HOTSPOTS`, `INTERIOR`,
  `ISOMETRIC`), hoy para el Deepal S05.

## Límites conocidos

- Hoy solo en español y con las vistas del Deepal S05.
- Sin opciones todavía: no se puede elegir qué botones mostrar.
- Los niveles de los asientos se envían al coche con cada toque; el coche
  tarda unos segundos en confirmar.
