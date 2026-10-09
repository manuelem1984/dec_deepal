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
  ventanillas y luces. Al tocarla se abre la imagen.
- **Batería:** icono según el nivel (verde con el 50 % o más, amarillo por
  debajo del 50 %, rojo por debajo del 15 %; con un rayo si está cargando),
  autonomía, estado de carga y la barra.
- **Seis botones:**

| Botón | Qué hace | PIN |
| --- | --- | --- |
| **Confort** | Abre la ventana de confort | No |
| **Bloqueo** | Bloquea o desbloquea las puertas | Sí |
| **Maletero** | Abre o cierra el maletero | Sí |
| **Ventilar** | Entreabre las ventanillas, o las cierra | Sí |
| **Luces** | Parpadea las luces | No |
| **Claxon** | Toca el claxon | No |

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
