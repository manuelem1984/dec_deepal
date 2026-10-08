# Sistema de iconos

**Objetivo:** cambiar el icono de cualquier entidad **sin tocar código**:
se copia un `.svg` con el nombre correcto y se reinicia Home Assistant.

## Dónde

```
custom_components/dec_deepal/icons/
├── icons.yaml      Registro: cada entidad, sus estados e iconos de respaldo
├── svg/            Tus iconos (.svg)
├── reserva/        Iconos guardados que hoy no usa ninguna entidad
├── dec-icons.js    Script del navegador (no hace falta tocarlo)
└── dec-icons-loader.js  Cargador temprano (se copia solo a www/)
```

## Cómo se elige el icono

Para cada entidad, en este orden (gana el primero que exista):

| # | Qué se busca | Ejemplo (entidad `trunk_control`, estado `open`) |
| --- | --- | --- |
| 1 | `svg/<entidad>_<sufijo>.svg` | `svg/trunk_control_open.svg` |
| 2 | `svg/<entidad>.svg` | `svg/trunk_control.svg` |
| 3 | `mdi` del estado en `icons.yaml` | `mdi:window-open-variant` |
| 4 | `defecto` en `icons.yaml` | `mdi:window-closed-variant` |
| 5 | nada | Icono estándar de Home Assistant para ese tipo |

- **`<entidad>`** es la clave de la entidad: la del bloque en `icons.yaml`.
- **`<sufijo>`** es el campo `archivo` del estado en `icons.yaml`; si no se
  indica, es el propio estado.

### Estados de cada tipo de entidad

| Tipo | Estados | Ejemplo de archivo |
| --- | --- | --- |
| Sensor binario | `on` / `off` (o el `archivo` que diga icons.yaml) | `door_front_left_open.svg` |
| Interruptor | `on` / `off` | `steering_wheel_heat_on.svg` |
| Persiana (ventanillas, maletero) | `open` / `closed` | `windows_closed.svg` |
| Cerradura | `locked` / `unlocked` | `doors_unlocked.svg` |
| Climatización | `off` / `heat_cool` | `cabin_climate_heat_cool.svg` |
| Número (asientos) | `0`, `1`, `2`, `3` | `seat_heat_driver_3.svg` |
| Sensor de lista | cada opción | `charge_status_charging_ac.svg` |
| Sensor normal, botón, imagen | — | `outside_temperature.svg` |

> Nota: en Home Assistant el estado de "cerrado" es `closed` (no `close`). Por
> eso el archivo es `windows_closed.svg`.

## Ejemplos

**Un solo icono para la temperatura exterior:** copia
`outside_temperature.svg` en `icons/svg/`.

**Iconos distintos para las ventanillas cerradas y ventilando:** copia
`windows_closed.svg` (cerradas) y `windows_vent.svg` (entreabiertas).

> Ojo: la entidad de ventanillas presenta su estado **invertido** a Home
> Assistant para que las flechas coincidan con el cristal (↓ entreabre,
> ↑ cierra). Por eso en `icons.yaml` el estado `open` usa el archivo
> `closed` y el estado `closed` usa `vent`: los nombres de archivo dicen lo
> que pasa de verdad.

**Puertas con nombres semánticos:** en `icons.yaml`, `door_front_left` tiene
`"on": {archivo: open}` y `"off": {archivo: closed}`; por eso sus archivos son
`door_front_left_open.svg` y `door_front_left_closed.svg` (y no `_on`/`_off`).

## Requisitos del SVG

El sistema de iconos de Home Assistant solo dibuja **trazados rellenos de un
color** (como los de Material Design Icons). Por tanto:

- ✅ Solo elementos `<path d="...">` con relleno. Se unen todos los `<path>`
  (menos los que tengan `fill="none"`).
- ✅ Un `viewBox` en la etiqueta `<svg>` (lo normal es `0 0 24 24`).
- ❌ Sin trazos (`stroke`): conviértelos a relleno (Inkscape: *Trayecto →
  Trazo a trayecto*).
- ❌ Sin `<circle>`, `<rect>`… sueltos: conviértelos a trayecto (Inkscape:
  *Trayecto → Objeto a trayecto*).
- ❌ Sin máscaras, degradados, textos, imágenes ni animaciones.
- Nombre del archivo: minúsculas, números y `_`. Nada de espacios.

Buen sitio para buscar iconos: <https://icon-sets.iconify.design/> (botón
"SVG"). Revisa la licencia de la colección y anótala en `icons/README.md`.

## Al arrancar

En el registro de Home Assistant aparece un aviso (`Iconos: ...`) si:

- un `.svg` no corresponde a ninguna entidad/estado de `icons.yaml` (¿errata?);
- un `.svg` usa trazos, máscaras, animaciones…;
- el nombre del archivo no es válido.

## Añadir una entidad nueva

Al programar una entidad nueva, añade su bloque en `icons.yaml` (plataforma,
descripción, estados y respaldo `mdi`). Así queda documentado qué nombres de
archivo acepta, y cualquiera puede ponerle icono sin programar.

## Por dentro

- `registries/icons.py` lee `icons.yaml`, descubre los `.svg` y resuelve el
  icono (`IconRegistry.resolve`).
- `entity.py` pregunta a ese registro en la propiedad `icon`.
- `frontend.py` publica `icons/svg/` en `/dec_deepal/icons/`, un paquete con
  todos los SVG en `/api/dec_deepal/icons_bundle` y carga `dec-icons.js`.
- `dec-icons.js` pide ese paquete **una sola vez** y, si falla, lo
  **reintenta** durante un minuto; el icono queda pendiente y aparece solo
  cuando llega. Un icono que no esté en el paquete se pide suelto.
- El selector de iconos de HA muestra también los `dec:`.

### Iconos que no salían tras reiniciar (2.1.2 y 2.1.3)

Tras reiniciar Home Assistant, la app recarga la página antes de que la
integración termine de arrancar. Pasaban tres cosas, analizadas sobre el
código de Home Assistant 2026.9.4 (frontend 20260826.7):

1. **La página salía sin nuestro script.** Home Assistant decide qué
   scripts incluye al servir la página y una integración de HACS se
   registra unos segundos más tarde.
2. **Los iconos se pintaban antes de tiempo.** Durante el arranque las
   entidades conservan su icono (`dec:...`) y la página lo dibuja; como
   nadie conoce aún el prefijo `dec`, `<ha-icon>` lo marca como
   desconocido (`_legacy`) y **no lo reintenta**, aunque el script llegue
   después.
3. **Las descargas que fallaban se recordaban** (corregido en la 2.1.2).

Solución, sin que el usuario toque nada:

- **Cargador temprano** (`icons/dec-icons-loader.js`). Al arrancar, la
  integración lo copia a `<config>/www/dec_deepal/` y lo registra como
  **recurso de los paneles** (`/local/dec_deepal/dec-icons-loader.js`):
  esas dos cosas existen desde el primer instante. El cargador reintenta
  cargar `dec-icons.js` (unos 2 minutos) hasta que la integración lo
  publica. Su contenido no cambia entre versiones: se registra una vez.
- **Repintado.** Al llegar, `dec-icons.js` busca los `<ha-icon>` con icono
  `dec:` que quedaron marcados, les quita la marca y les hace recargar.
- Al desinstalar la integración se quitan el recurso y la copia de `www`.

Límites conocidos:

- Home Assistant solo carga los recursos **al abrir un panel**. Si la app
  recarga estando en Ajustes (p. ej. la ficha del dispositivo) sin haber
  pasado por un panel, los iconos siguen sin verse hasta abrir un panel o
  recargar.
- Si los recursos de los paneles están en **modo YAML**, no se pueden
  registrar desde una integración: queda como antes.
- `/local/` solo existe si la carpeta `www` ya estaba al arrancar Home
  Assistant. Si la crea la integración, funciona desde el siguiente
  reinicio.
- El resultado se ve en los diagnósticos: `catalogos → cargador_iconos`.

## Iconos propios incluidos

| Entidad | Archivos | Origen |
| --- | --- | --- |
| Luces de cruce, carretera y posición | `low_beam.svg`, `high_beam.svg`, `position_lamp.svg` | Propios |
| Intermitentes | `indicator_left_on/off.svg`, `indicator_right_on/off.svg` | Propios |
| Volante calefactado | `steering_wheel_heat.svg` | Propio |
| Puertas (4) | `door_<pos>_closed.svg`, `door_<pos>_open.svg` | Derivados de `mdi:car-door` (2.1.0b2) |
| Capó | `hood_closed.svg`, `hood_open.svg` | Derivados de `mdi:car-hatchback` (2.1.0b2) |
| Maletero | `trunk_closed.svg`, `trunk_open.svg` | Derivados de `mdi:car-hatchback` (2.1.0b2) |

`<pos>` = `front_left`, `front_right`, `rear_left`, `rear_right`.

### Iconos en reserva

`icons/reserva/` guarda iconos ya dibujados que hoy no usa ninguna entidad.
No se cargan ni se publican en el navegador. Para usar uno, moverlo a
`icons/svg/` con el nombre de la entidad.

| Archivos | Para qué eran |
| --- | --- |
| `charge_cover_closed.svg`, `charge_cover_open.svg` | Tapa de carga (con el puerto CCS2). La entidad se retiró en la 2.1.0 porque el S05 no informa de la tapa |

**Para dibujar uno nuevo con el mismo estilo:** lienzo `viewBox="0 0 24 24"`,
un único `<path fill="currentColor">`, formas rellenas con "trazo" de unas 2
unidades. Home Assistant rellena con la regla *nonzero*: los huecos
(ventanillas, juntas) deben ir en sentido contrario al de la forma que los
contiene.

