# Cambios

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versiones: [SemVer](https://semver.org/lang/es/) (`2.0.0b1` = beta).

## [2.0.0rc9] — 2026-10-02

### Añadido

- **Vista interior** (entidad de imagen nueva): el habitáculo desde arriba con
  el aro del volante y las zonas acolchadas de los asientos delanteros
  "encendidas" cuando están calefactados (naranja) o ventilados (celeste).
  Tinte neón que respeta las costuras, con bordes difuminados y halo suave,
  20 % transparente. Capas en `vehicles/vista_interior/s05_2024/`. Cualquier
  nivel de asiento (1-3) enciende su capa.

## [2.0.0rc8] — 2026-10-02

### Corregido

- **Vista isométrica:** el espejo del conductor salía tapado y se veía la junta
  entre las puertas izquierdas. El cristal de cada ventanilla va ahora
  **debajo** de su puerta y la puerta trasera debajo de la delantera. Con todo
  cerrado la imagen es idéntica a la foto del coche cerrado (comprobado píxel
  a píxel).

## [2.0.0rc7] — 2026-10-02

### Añadido

- **Vista isométrica** (entidad de imagen nueva): el coche desde delante a la
  izquierda, realista, con capó, maletero, puertas, ventanillas (bajada = sin
  cristal) y luz de cruce según su estado. Capas en
  `vehicles/vista_isometrica/s05_2024/`; lo que queda detrás de la carrocería
  se pone debajo de ella, así "todo cerrado" es idéntico a la foto del coche
  cerrado.
- `capas.yaml`: nueva condición `solo_si` (poner la capa solo si otra señal
  está a "sí").

### Cambiado

- Las vistas por capas son ahora genéricas: `vistas:` en `vehicles.yaml`
  (`top_view`, `isometric_view`) en vez de `carpeta_vista_planta`, que se
  sigue aceptando. Un ángulo nuevo es una carpeta con capas más su nombre.
  Módulos renombrados: `registries/views.py` y `view_renderer.py`.

## [2.0.0rc6] — 2026-10-02

### Añadido

- **Vista de planta** (entidad de imagen nueva): el coche visto desde arriba
  con puertas, capó, maletero y ventanillas abiertos (en rojo) y la luz de
  cruce encendida, según su estado. Se monta con capas PNG de
  `vehicles/vista_planta/s05_2024/` descritas en `capas.yaml`: añadir o
  cambiar capas no requiere tocar código. Si un dato no llega se usa el
  último conocido (o cerrado). Atributos `activo` y `sin_dato`. Preparada
  para juegos de otros colores (hoy solo plata). Ver `docs/imagenes.md`.

## [2.0.0rc5] — 2026-10-01

### Corregido

- **Cuentas con dos o más coches no arrancaban** ("Error de configuración:
  0 bytes read..."). Cada coche abría su propia conexión MQTT a la vez, todas
  con el mismo identificador de cliente (el de la cuenta), y el servidor solo
  admite una: cerraba las demás. Ahora las conexiones MQTT de una cuenta
  (lecturas y despertares) van **en fila**, y la primera lectura de cada
  coche se hace uno detrás de otro.
- Si el servidor MQTT cierra la conexión, ahora se trata como un fallo de
  conexión normal y se usa el **REST de respaldo**, en vez de dejar la
  integración sin arrancar.

### Cambiado

- **Matrícula** habilitada por defecto: el servidor la envía (`plateNumber`)
  para el S05 de España. Si ya tenías la entidad creada deshabilitada (rc4),
  habilítala una vez en su ficha.

## [2.0.0rc4] — 2026-10-01

Incorpora lo útil de las últimas betas de Deepal Alternative (1.3.2-beta.1 a
1.4.0-beta.3), siempre centrado en el S05 de España.

### Añadido

- **Despertar el coche** por MQTT (`TxWakeup`/`Cnr_ReWakeup`, como la app):
  - "Actualizar datos del vehículo" lo despierta si su último informe tiene
    más de 2 minutos y espera hasta 60 s a que lleguen datos nuevos; si no
    llegan, avisa en vez de mostrar datos viejos sin decir nada.
  - Puertas, ventanillas y maletero (PIN) lo despiertan antes de enviar la
    orden (hasta ~30 s); si falla, la orden se envía igualmente.
  - Límites para cuidar la batería de 12 V: uno cada 5 minutos por coche y
    nunca en las lecturas automáticas. Se puede desactivar en Configurar →
    Avanzado ("Despertar el coche cuando haga falta"). ⚠️ Pendiente de probar.
- Mensaje claro para `APP_1_1_05_001` (orden rechazada con el coche dormido).
- Entidades **deshabilitadas por defecto**, por si el servidor llega a enviar
  esos datos (hoy el S05 de España no los envía): **Matrícula** y
  **Ubicación** (rastreador en el mapa).
- Al arrancar se actualizan los datos guardados de cada coche (matrícula,
  imagen, apodo...).

### Corregido

- Privacidad: la ocultación de datos ya no distingue mayúsculas (`Lat`,
  `Lng`...) y oculta cualquier clave con "plate" (matrícula).

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
