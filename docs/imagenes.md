# Imágenes del vehículo, modelos y colores

Cada coche tiene **dos entidades de imagen, independientes**:

| Entidad | De dónde sale | Si no hay imagen |
| --- | --- | --- |
| **Imagen oficial** (`official_image`) | URL que envía el servidor de Deepal en la lista de vehículos | No disponible |
| **Foto DEC** (`dec_photo`) | Catálogo local `vehicles/photos/`, según modelo + versión + color | Foto por defecto del modelo; si tampoco hay, no disponible |

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

## Elegir versión y color

Configurar → **Apariencia del vehículo** → modelo → versión y color.

Si no se elige versión, la integración intenta adivinarla (⚠️) con las
capacidades que informa el servidor: con ventilación de asientos → Max; sin
ella → Pro. El color no se puede adivinar.

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
