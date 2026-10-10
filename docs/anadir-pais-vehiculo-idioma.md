# Añadir un país, un vehículo o un idioma

La integración está preparada para crecer en tres ejes. Hoy: **España**,
**Deepal S05 (2024-2025)** y **español**.

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
     prefijo: "351"
     digitos_movil: 9
     idioma_api: en_US
     metodos_login: [sms, email]
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
3. Reinicia. El coche se reconoce solo; si no, elígelo en Configurar →
   Apariencia.

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

Lo que no se ponga vale lo mismo que en España. Ojo: los textos que explican
la regla al usuario ("Primera ITV a los 4 años...") describen la española; al
añadir un país con otra norma habrá que adaptarlos.
