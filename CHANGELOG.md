# Cambios

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versiones: [SemVer](https://semver.org/lang/es/) (`2.0.0b1` = beta).

## [2.0.0rc3] — 2026-09-30

### Cambiado

- **"Ventanillas" pasa a "Ventanillas - Modo Ventilación".** El comando que
  usamos entreabre las ventanillas para ventilar (no las baja del todo).
- **Flechas al revés, a propósito:** Home Assistant pinta "abrir" con ↑, al
  contrario que el cristal. Ahora, con las ventanillas cerradas el botón activo
  es **↓ (entreabrir)** y ventilando es **↑ (cerrar)**. El estado se muestra
  como "Cerradas" / "Ventilando". En automatizaciones, el estado `open` de esta
  entidad significa ventanillas **cerradas**. Sigue necesitando el PIN y el
  armado (Opción B).
- Iconos propios de ventanillas: `windows_closed.svg` y `windows_vent.svg`.

## [2.0.0rc2] — 2026-09-30

Ajustes tras una prueba real en marcha y parado con el coche arrancado.

### Cambiado

- **"Motor" pasa a llamarse "Encendido"** y se calcula con el estado de
  alimentación (`powerStatusFeedBack`: 0 = apagado, 2 = en marcha).
  `engineStatus` no sirve en un eléctrico: vale 0 también circulando. El
  `entity_id` no cambia.
- **"Luz de posición" pasa a llamarse "Luces encendidas (testigo)"**: el dato
  del coche es un testigo de "hay luces encendidas" (posición forzada o
  cruce/carretera en automático), no la luz de posición.
- Rechazo `1032` ("Power is not off") con mensaje claro: el coche tiene que
  estar apagado para esa orden (visto al subir las ventanillas).

### Verificado con el coche real

- Climatización (encender/apagar), parpadear luces y claxon, nivel del
  ventilador.
- Lectura y control de calefacción y ventilación de asientos (escala 1:1 y
  `6` = módulo dormido confirmados), volante calefactado, climatizador.
- Alguna puerta abierta, cierre centralizado y cerraduras, puertas, humedad,
  kilometraje, luces de carretera y cruce, intermitentes, avisos de
  neumáticos, Imagen DEC e imagen oficial.
- Desbloqueo de puertas y bajada de ventanillas con PIN: aceptados por el
  coche (código 0).

## [2.0.0rc1] — 2026-09-30

Candidata a primera versión estable. Si la prueba mínima de comandos con el
coche (ver `docs/roadmap.md`) sale bien, se publica como **2.0.0** sin cambios
de código.

### Cambiado

- **Acceso por SMS desaconsejado:** ahora mismo Deepal responde que ha enviado
  el código (`SUC`) pero el SMS no llega. La petición es idéntica a la de la
  v1 (con la que funcionaba) y a la de Deepal Alternative, así que el fallo es
  del lado de Deepal. El asistente lo avisa, propone el **correo** por defecto
  y marca el SMS como "ahora mismo no llega". Documentado en README y en
  `docs/protocolo.md`.

## [2.0.0b5] — 2026-09-30

### Corregido

- **Reparaciones "Configura tu vehículo" daba error 500.** Home Assistant
  arranca el asistente llamando al primer paso con `{"issue_id": ...}`, y el
  asistente lo tomaba por el formulario enviado (buscaba el campo `model`).
  Ahora el primer paso solo redirige al formulario. La prueba automática
  reproduce la llamada real.

### Añadido

- Durante el asistente de login se registra (aviso "DEC Deepal login
  (informativo)") la **respuesta completa** del servidor a cada paso, con los
  datos personales ocultos, para investigar por qué no llega el SMS.

## [2.0.0b4] — 2026-09-30

### Cambiado

- "Foto DEC" pasa a llamarse **"Imagen DEC"**. Si el catálogo no tiene foto
  para el coche (p. ej. modelo genérico), muestra la **imagen oficial** en vez
  de quedar no disponible. La imagen oficial se descarga una sola vez para las
  dos entidades. (El `entity_id` no cambia: la clave interna sigue siendo
  `dec_photo`.)
- Nuevos iconos de luces de carretera, cruce y posición (Material Design
  Icons), un solo icono para encendida y apagada. Se retiran los `_on`/`_off`
  anteriores.

### Corregido

- **Login por SMS:** las cabeceras ahora son las de la app actual, iguales a
  las de Deepal Alternative (a quien le llegan los SMS): `appversion V1.12.0`
  (antes `V1.11.0`) y sin cabecera `authorization` vacía antes de iniciar
  sesión. El servidor aceptaba la petición pero el SMS no llegaba.
  ⚠️ Pendiente de confirmar.

### Pruebas

- Nueva prueba del asistente de Reparaciones "Configura tu vehículo".

## [2.0.0b3] — 2026-09-30

Ajustes tras el primer diagnóstico real de un S05 Max (b2).

### Cambiado

- Capacidades: se reconocen los códigos de ventilación del servidor europeo
  (`FronSeatVentilationSW`, `DriverSeatVentilatorSW`, `#vent3`…). La versión
  deducida ahora se **propone por defecto** en el asistente de Configurar /
  Reparaciones (el usuario la confirma).
- `function-config` se pide primero con `vehicleId` (el formato que funciona
  en España), ahorrando una petición fallida en cada arranque.

### Corregido

- Diagnósticos: la clave `unlockKeyDrivingStatus` (y cualquiera con
  "driving") se ocultaba por contener "vin".

### Verificado con el coche real

- Imagen oficial; temperaturas y presiones REST (décimas de grado, kPa);
  endpoint de capacidades.

## [2.0.0b2] — 2026-09-30

Primeras correcciones tras probar la b1 con un S05 Max real.

### Cambiado

- **Todo coche arranca como genérico** ("Deepal (sin configurar)") hasta que
  se elige su modelo. Ya no se adivina la versión (la b1 clasificó un Max como
  Pro). Nuevo aviso en **Ajustes → Reparaciones**, "Configura tu vehículo",
  con asistente de modelo, versión y color.
- La ficha del dispositivo muestra el modelo con la versión en un solo texto:
  **Deepal S05 Max (2024-25)** (campo `nombre_con_version` del catálogo).
- Iconos de avisos de neumáticos: `mdi:tire` (OK y desconocido) y
  `mdi:car-tire-alert` (aviso). `mdi:car-tire` no existe en MDI.

### Añadido

- Tras pedir el código de acceso, menú con **Ya tengo el código / Reenviar el
  código / Usar otro método o corregir el dato** (antes no había forma de
  volver atrás si el SMS no llegaba).
- Registro (INFO) de cada petición de código aceptada por Deepal.
- Diagnósticos: modelo sugerido, si está configurado, capacidades del servidor
  (para estudiar Pro/Max) y resultado de la descarga de la imagen oficial.

### Corregido

- **Imagen oficial:** se descarga con un método propio que no depende de que el
  servidor indique bien el tipo de imagen; si falla, se registra el motivo.

### Verificado con el coche real

- Batería, autonomía, presión de los 4 neumáticos, temperatura interior y
  temperatura del climatizador.

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
- **Dos imágenes separadas:** "Imagen oficial" (servidor) y "Imagen DEC" (catálogo).
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
