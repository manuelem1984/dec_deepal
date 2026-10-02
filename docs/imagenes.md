# Imágenes del vehículo, modelos y colores

Cada coche tiene **cuatro entidades de imagen, independientes**:

| Entidad | De dónde sale | Si no hay imagen |
| --- | --- | --- |
| **Imagen oficial** (`official_image`) | URL que envía el servidor de Deepal en la lista de vehículos | No disponible |
| **Imagen DEC** (`dec_photo`) | Catálogo local `vehicles/photos/`, según modelo + versión + color | Foto por defecto del modelo; si tampoco hay (p. ej. modelo genérico), **la imagen oficial** |
| **Vista de planta** (`top_view`) | Capas de `vehicles/vista_planta/`, montadas según el estado del coche | No se crea si el modelo no tiene esa vista |
| **Vista isométrica** (`isometric_view`) | Capas de `vehicles/vista_isometrica/`, montadas según el estado del coche | No se crea si el modelo no tiene esa vista |

La imagen oficial se descarga una sola vez y la comparten las dos entidades.

## El catálogo: `vehicles/vehicles.yaml`

Mismo concepto que los iconos: **datos, no código**. Ahí se definen:

- **Modelos** (`s05_2024`...): nombre, descripción, países, cómo reconocerlo,
  qué funciones tiene y en qué carpeta están sus fotos.
- **Versiones** (`pro`, `max`, `max_awd`): nombre, descripción, grupo de foto
  y funciones que cambian respecto al modelo.
- **Colores** (`andromeda_blue`...): nombre comercial y descripción.

Todos los campos están explicados en la cabecera del propio YAML.

## Fotos

```
vehicles/photos/<carpeta_fotos>/<grupo_foto>_<color>.<ext>
vehicles/photos/<carpeta_fotos>/<foto_defecto>
```

Ejemplo S05:

```
vehicles/photos/s05_2024/
├── default.png
├── pro_andromeda_blue.png   … pro_moonlight_white.png   (5)
└── max_andromeda_blue.png   … max_moonlight_white.png   (5)
```

- `grupo_foto` permite que versiones iguales por fuera compartan fotos: el
  **Max AWD** usa las del **Max**.
- Extensiones: `.png`, `.jpg`, `.jpeg`, `.webp` (se prueban en ese orden).
- Si falta una foto concreta, se usa `foto_defecto`. No falla nada.

### Añadir un color nuevo

1. Añadir el color en `colores:` del modelo.
2. Copiar `pro_<color>.png` y `max_<color>.png` en la carpeta del modelo.
3. Reiniciar. Aparece en Configurar → Apariencia.

### Añadir un modelo nuevo

Ver [anadir-pais-vehiculo-idioma.md](anadir-pais-vehiculo-idioma.md).

## Vistas por capas (planta, isométrica…)

Cada vista es el coche desde un ángulo, montado en el momento con capas PNG
transparentes que se ponen una encima de otra según su estado. Qué vistas
tiene cada modelo lo dice `vistas:` en `vehicles.yaml`:

```yaml
vistas:
  top_view: vista_planta/s05_2024            # "Vista de planta"
  isometric_view: vista_isometrica/s05_2024  # "Vista isométrica"
```

Cada vista es una entidad de imagen y todas funcionan igual (mismo código);
solo cambian sus capas. Para un ángulo nuevo: carpeta con sus capas y su
`capas.yaml`, una clave nueva en `KNOWN_VIEWS` (`registries/vehicles.py`) y
su nombre en `translations/`.

### Vista de planta (`top_view`)

El coche **visto desde arriba** (750×750). Las piezas abiertas están
dibujadas en rojo para que se vean de un vistazo:

| Pieza | Señal | Capas |
| --- | --- | --- |
| Carrocería | (siempre) | `base.png` (con el hueco del capó y del maletero) |
| Capó | `hood_open` | `hood_open.png` / `hood_closed.png` |
| Maletero | `trunk_open` | `trunk_open.png` / `trunk_closed.png` |
| Puertas (4) | `door_<pos>` | `door_<pos>_open.png` / `door_<pos>_closed.png` |
| Ventanillas (4) | `window_<pos>` | `window_<pos>_open.png`, solo con la puerta cerrada |
| Luz de cruce | `low_beam` | `low_beam_on.png` |

`<pos>` = `front_left`, `front_right`, `rear_left`, `rear_right` (izquierda /
derecha vistas desde el asiento del conductor).

### Vista isométrica (`isometric_view`)

El coche **desde delante a la izquierda** (lado del conductor), 750×500,
realista (sin rojo):

| Pieza | Señal | Capas |
| --- | --- | --- |
| Carrocería | (siempre) | `base.png` (sin puertas, capó ni portón: se ve el interior) |
| Capó | `hood_open` | `hood_open.png` / `hood_closed.png` |
| Maletero | `trunk_open` | `trunk_open.png` (encima) / `trunk_closed.png` (debajo) |
| Puertas (4) | `door_<pos>` | `door_<pos>_open.png` / `door_<pos>_closed.png` |
| Ventanillas (4) | `window_<pos>` | **cristal** subido: `window_<pos>_closed.png`, o `window_<pos>_closed_door_open.png` con la puerta abierta; bajada = sin cristal |
| Luz de cruce | `low_beam` | `low_beam_on.png` |

- **El orden importa:** lo que en la realidad queda detrás de la carrocería
  (puertas del lado derecho con sus cristales y el portón cerrado) va
  **antes** de `base.png` para que la base lo tape. Dentro de cada lado, el
  **cristal antes que su puerta** (el espejo queda delante) y la **puerta
  trasera antes que la delantera** (el canto de la delantera tapa el de la
  trasera). Con ese orden, "todo cerrado" es idéntico a la foto del coche
  cerrado (comprobado píxel a píxel).
- Desde este ángulo las puertas del lado derecho casi no se ven abiertas; para
  las puertas es mejor la vista de planta. La isométrica luce con capó,
  maletero y luces.

### Común a todas las vistas

```
vehicles/<vista>/<modelo>/
├── capas.yaml        orden de las capas y qué señal decide cada una
├── base.png
├── hood_closed.png   hood_open.png
├── …
└── <color>/          (opcional, futuro) capas de otro color
```

- **Orden:** la lista de `capas.yaml`, de abajo arriba. Campos: `imagen`
  (fija), `senal` + `si_activo` / `si_inactivo`, y las condiciones `salvo_si`
  (no poner si otra señal está a "sí") y `solo_si` (poner solo si está a
  "sí"). Todos explicados en la cabecera de cada `capas.yaml`.
- **Cuándo cambia:** cada vez que llegan datos se decide qué capas tocan; solo
  si cambian, la imagen se marca como nueva y Home Assistant la vuelve a pedir.
  Las últimas combinaciones se guardan en memoria.
- **Dato desconocido** (coche dormido, señal que no llega): se usa el último
  valor conocido; si nunca se ha conocido, se dibuja cerrado / apagado.
- **Atributos:** `activo` (señales abiertas / encendidas) y `sin_dato`
  (señales sin dato en la última lectura). Sirven para automatizaciones.
- **Colores:** hoy solo hay el juego plata (en la raíz de la carpeta). Para
  otro color basta con una subcarpeta con el id del color (p. ej.
  `deep_space_black/`) con las capas que cambien, con el mismo nombre; las que
  falten se toman de la raíz.
- **Modelo sin configurar:** mientras el coche es "genérico" se usan las capas
  del modelo reconocido por el nombre (p. ej. el S05).
- El montaje usa Pillow, que ya viene con Home Assistant.

## Elegir modelo, versión y color

**Todo coche arranca como "Deepal (sin configurar)"** (modelo `generico`):
solo datos básicos, sin asientos, volante ni control con PIN. Así nunca se
crean entidades de funciones que el coche no tiene.

Mientras tanto aparece un aviso en **Ajustes → Reparaciones** ("Configura tu
vehículo"). Al pulsar *Enviar* pide modelo (se propone el reconocido por el
nombre que da el servidor), versión y color. Al terminar, la integración se
recarga con las entidades correctas y el aviso desaparece.

Se puede cambiar en cualquier momento en Configurar → **Apariencia del
vehículo**.

En la ficha del dispositivo el modelo aparece como
`nombre_con_version` del catálogo, p. ej. **Deepal S05 Max (2024-25)**.

> La versión **nunca se aplica sola**: en el asistente se **propone** la que
> se deduce de las capacidades del servidor (`function-config`) y el usuario
> la confirma o la cambia. La b1 la aplicaba sola y clasificó un Max como Pro,
> porque en España los códigos de ventilación son otros
> (`FronSeatVentilationSW`, `#vent3`…). Las capacidades se ven en los
> diagnósticos (`vehiculos → capacidades`). Falta el diagnóstico de un **Pro**
> para confirmar que no manda esos códigos.

## Funciones (qué entidades se crean)

La versión no solo cambia la foto: también decide qué entidades existen.

| Función (`funciones:`) | Entidades que dependen de ella |
| --- | --- |
| `telemetria_mqtt` | Lectura por MQTT (sin ella, solo REST) |
| `climatizacion` | Climatización, sensor "Climatizador" |
| `luces_claxon` | Botones de luces y claxon |
| `asientos_calefaccion` | Calefacción de asientos (conductor, acompañante) |
| `asientos_ventilacion` | Ventilación de asientos (en el S05, solo Max) |
| `volante_calefactado` | Volante calefactado |
| `desempanado` | Desempañado delantero |
| `comandos_pin` | Puertas, ventanillas, maletero (si además el PIN está activo) |
| `combustible` | Reservado para híbridos (aún sin entidades) |
