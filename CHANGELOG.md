# Cambios

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versiones: [SemVer](https://semver.org/lang/es/) (`2.0.0b1` = beta).

## [2.0.0b1] — 2026-09-30

Reescritura completa desde cero de
[ha-deepal-spain-dec](https://github.com/manuelem1984/ha-deepal-spain-dec) 1.3.1b18.

### ⚠️ Cambio incompatible

- Dominio nuevo `dec_deepal` y repositorio nuevo. **No se migra** desde
  `deepal_spain_dec`: hay que quitar la integración antigua y añadir la nueva.
  Los `entity_id` cambian.

### Añadido

- Estructura por capas: `api/` (cliente), `telemetry/` (señales),
  `registries/` (catálogos), `debug/` (depuración), sin dependencias de HA
  en las capas de datos.
- **Multi-país:** `countries/countries.yaml` (hoy solo España).
- **Multi-vehículo:** una entrada por cuenta con todos sus coches;
  `vehicles/vehicles.yaml` con modelos, versiones, colores, funciones y fotos.
  Las entidades se crean según las funciones del modelo y la versión.
- **Multi-idioma:** todos los textos en `translations/`, incluidos los errores.
- **Iconos sin código:** `icons/icons.yaml` + `icons/svg/<entidad>_<estado>.svg`,
  con respaldo `mdi:` y avisos al arrancar.
- **Dos imágenes separadas:** "Imagen oficial" (servidor) y "Foto DEC" (catálogo).
- **Correlación endpoints ↔ entidades:** `docs/correlacion_endpoints_entidades.csv`.
- **Depuración:** modo depuración en opciones, registro de eventos en
  diagnósticos y servicio `dec_deepal.capture_snapshot` con comparación entre
  capturas.
- Sensor "Tiempo de carga restante (H:MM)".
- Sensores (desactivados por defecto) de velocidad, km del trayecto, km de ayer
  y temperatura exterior, por si llegan por REST.
- Pista automática de versión Pro/Max por capacidades (⚠️).

### Cambiado (tomado de Deepal Alternative, ver NOTICE.md)

- Comando de **puertas**: `{"command": "lock", "open": …}`.
- Comando de **ventanillas**: una sola entidad para todas
  (`{"command": "window", "open": …, "openType": 10}`); se eliminan las
  cuatro persianas individuales, basadas en un formato no verificado.
- `rcToken` solo en comandos con PIN.
- Asientos por MQTT en escala 1:1 (`6` = desconocido) en vez de ÷2.
- Renovación de sesión por caducidad del JWT, una a la vez, con ventana de 30 min.
- Respaldo por REST si falla MQTT; reintento de MQTT si caduca el token CA.
- Espera física de luces (30 s) y claxon (6 s) con mensaje claro.
- Valor optimista mantenido 120 s y deshecho si el coche rechaza el comando.
- Se conserva el último valor de asientos/volante/desempañado/clima.
- El REST no sustituye datos del MQTT si su informe es más antiguo.

### Corregido

- Guardar tokens renovados ya no recarga la integración.
- Un corte de red al renovar la sesión ya no obliga a volver a iniciar sesión.
