# Añadir un país, un vehículo o un idioma

La integración está preparada para crecer en tres ejes. Hoy: **España**,
**Deepal S05** (EV y, de forma provisional, PHEV) y **español**.

---

## Añadir un país

Todo en `custom_components/dec_deepal/countries/countries.yaml`.

1. Si el país usa servidores que aún no están en `entornos:`, añade el
   entorno con sus tres URLs (`url_intl`, `url_ca`, `url_sda`). Los países
   europeos usan `eu`.
2. Añade el país en `paises:` con su código ISO en minúsculas:

   ```yaml
   pt:
     nombre: Portugal
     activo: false          # poner true cuando se haya probado
     entorno: eu
     pais_venta: PT
     idioma_api: en_US
     verificado: false
   ```
3. Añade el país a `paises:` de los modelos que se vendan allí
   (`vehicles/vehicles.yaml`).
4. Añade el país a `country` de `hacs.json` (opcional, para HACS).
5. Reinicia, prueba con una cuenta real y pon `activo: true` y
   `verificado: true`.

Mientras solo haya un país activo, el asistente se salta el paso de elegir
país.

---

## La ficha de cada coche

Todo lo que la integración sabe de un coche sale de `vehicles/vehicles.yaml`:
es su **ficha**. Se compone por capas:

1. El **modelo** dice lo común. Sus valores son los de la versión más
   equipada (en el S05, el Max).
2. Cada **versión** solo escribe en qué se diferencia.
3. Un coche **sin versión elegida**, o con una que no está en el catálogo,
   usa la ficha del modelo tal cual (la del Max).
4. Un modelo puede **copiar a otro** con `como:` y cambiar solo lo distinto.
5. Un coche **sin modelo elegido** usa `generico`: lo mínimo.

Fichas de hoy:

| Coche | Modelo / versión | Asientos calefactados y ventilados, volante calefactado, portón eléctrico | Llanta | Estado |
|---|---|---|---|---|
| Deepal S05 EV RWD Pro | `s05_2024` / `pro` | No | 18" | Catálogo oficial |
| Deepal S05 EV RWD Max | `s05_2024` / `max` | Sí | 20" | **Verificada** (dos coches reales) |
| Deepal S05 EV 4WD Max | `s05_2024` / `max_awd` | Sí | 20" | Catálogo oficial |
| Deepal S05 PHEV Pro | `s05_phev` / `pro` | No | 18" | Catálogo oficial |
| Deepal S05 PHEV Limited Edition | `s05_phev` / `limited_edition` | Sí | 18" | Catálogo oficial |

El equipamiento sale de los catálogos oficiales de España (S05 EV,
septiembre de 2026; S05 PHEV, 2026). El PHEV es de tracción delantera, no
tiene 4WD y su versión alta se llama Limited Edition. "Catálogo oficial"
quiere decir que el equipamiento es el publicado, pero nadie ha comprobado
todavía qué envía de verdad ese coche.

Para verificar una ficha hace falta el **diagnóstico** de un coche de esa
versión: dice qué ficha se le aplica (`vehiculos → <coche> → ficha`), qué
funciones declara el servidor (`capacidades`) y qué datos envía de verdad.
Con eso se corrige la ficha y se marca `verificada: true`.

El PHEV lleva su propio manual y su plan de mantenimiento (manual oficial,
julio de 2026): el del EV más el motor de gasolina (aceite y filtro en cada
revisión; bujías y filtro de aire cada dos), con el reductor delante y sin
reductor trasero. Sus datos de combustible aún no tienen entidades: hace
falta el diagnóstico de un PHEV para saber cómo los envía.

## Añadir un vehículo

### Caso A — manda los mismos datos que el S05

1. En `vehicles/vehicles.yaml`, copia el bloque `s05_2024` con otra clave
   (p. ej. `s07_2025`) y ajusta:
   - `nombre`, `descripcion`, `paises`;
   - `reconocer.nombre_contiene` (texto que aparece en `modelName`; míralo en
     los diagnósticos, `vehiculos → info → model_name`);
   - `funciones` (qué tiene y qué no);
   - `versiones` y `colores`;
   - `carpeta_fotos`.
2. Crea `vehicles/photos/<carpeta_fotos>/` con `default.png` y las fotos
   `<grupo_foto>_<color>.png`.
3. Reinicia. El coche se reconoce solo; si no, elígelo en el panel DEC Deepal →
   Coches → Apariencia.

### Caso B — manda datos con otros nombres

Además de lo anterior:

1. Haz capturas (ver [depuracion.md](depuracion.md)) y mira `mqtt_sin_mapear`.
2. Añade los nombres nuevos como **alternativas** en
   `telemetry/mqtt_map.py` (la tupla `keys` de cada fila) o en
   `telemetry/rest_map.py` (la tupla de rutas). Por ejemplo:
   `MqttField(s.BATTERY_LEVEL, ("soc", "socDsp", "remainPower", "nuevoNombre"), c.to_int)`.
3. Si hay un dato totalmente nuevo: nueva señal en `telemetry/signals.py`,
   fila en el mapeo, entidad en la plataforma que toque, bloque en
   `icons/icons.yaml`, textos en `translations/` y fila en
   `docs/correlacion_endpoints_entidades.csv`.

### Caso C — no es "MQTT" (telemetría solo por REST)

Pon `telemetria_mqtt: false` en sus funciones. La integración leerá solo el
REST `condition`.

---

## Añadir un idioma

1. Copia `translations/es.json` como `translations/<código>.json`
   (`pt.json`, `fr.json`...).
2. Traduce **solo los valores** (el texto a la derecha de los dos puntos). No
   cambies las claves ni los `{marcadores}` como `{error}` o `{seconds}`.
3. Reinicia. Home Assistant usa el idioma del perfil del usuario.

Notas:

- `en.json` es el idioma de **respaldo**: Home Assistant lo usa si no existe
  el del usuario. Hoy contiene el texto en español; cuando se traduzca al
  inglés, los usuarios con otros idiomas verán inglés.
- `strings.json` y `translations/*.json` son ficheros **generados**: no se
  editan a mano (ver [idiomas.md](idiomas.md)).
- Los nombres de modelos, versiones y colores vienen de `vehicles.yaml` (son
  nombres comerciales, no se traducen). Sus descripciones sí se podrían
  traducir en el futuro añadiendo campos por idioma.
- Los catálogos YAML y la documentación están en español por decisión del
  proyecto (comunidad española).

## Idiomas

Los textos están en `custom_components/dec_deepal/idiomas/`, un fichero por
idioma, y todo lo demás se genera. Cómo cambiar un texto, añadir un idioma o
usar los textos de otro: [idiomas.md](idiomas.md).

## Normas del país (ITV, seguro)

Los plazos no dependen del idioma sino del país de la cuenta. En
`countries/countries.yaml`, cada país puede llevar un bloque `normas`:

| Campo | Qué es | España |
|---|---|---|
| `itv_primera_meses` | Meses hasta la primera inspección | 48 |
| `itv_cada_meses` | Meses entre inspecciones | 24 |
| `itv_reducida_desde_meses` | Edad del coche desde la que el intervalo se reduce | 120 |
| `itv_reducida_cada_meses` | Intervalo reducido | 12 |
| `seguro_preaviso_dias` | Días de preaviso para no renovar el seguro | 30 |

Lo que no se ponga vale lo mismo que en España.

Además, `itv: true` activa el **módulo de ITV** en ese país (apartado de
Configurar, entidades, avisos y opción de la tarjeta). Sin esa línea, el país
no tiene ITV. Hoy solo la lleva España. Ojo: los textos que explican
la regla al usuario ("Primera ITV a los 4 años...") describen la española; al
añadir un país con otra norma habrá que adaptarlos.
