# Cambios

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versiones: [SemVer](https://semver.org/lang/es/) (`2.0.0b1` = beta).

## [2.3.0b4] — 2026-10-09

### Cambiado

- **Otros → Manual abre el PDF en el navegador** (pestaña nueva), en vez de
  enseñarlo dentro de una ventana de la tarjeta: incrustado no se podían
  pasar las páginas. Se abre directamente el enlace del fabricante; Home
  Assistant ya no hace de intermediario.
- En *Configurar → Avanzado*, el campo del enlace se llama **Manual BEV**
  (el del PHEV llegará con ese modelo).

## [2.3.0b3] — 2026-10-09

### Añadido

- **Tarjeta: sexto botón "Otros"**, con un menú como el de "Localizar
  vehículo". Los seis botones quedan en dos filas de tres.
- **Otros → Manual**: enseña el manual de usuario del coche (PDF) en una
  ventana, con un enlace para abrirlo a pantalla completa. Home Assistant lo
  lee del enlace del fabricante en ese momento (su web no deja mostrarlo
  incrustado directamente); no se guarda ninguna copia.
- **Otros → Mantenimiento**: la ventana de mantenimiento, ahora accesible
  siempre (antes, solo con el testigo encendido). Si el coche no lo tiene
  activado, explica cómo activarlo.
- **Enlace del manual configurable** en *Configurar → Avanzado*. Viene con el
  del S05 eléctrico para España (está en el catálogo, `manual:` en
  `vehicles.yaml`); si se deja vacío, se vuelve a usar ese.
- Cuando la revisión está próxima o vencida, el botón "Otros" lo indica
  ("Revisión en 47 días").

### Sin verificar

- Cómo se ve el PDF incrustado en cada dispositivo, sobre todo en la app del
  móvil. Si no se ve bien, usar el enlace de pantalla completa.

## [2.3.0b2] — 2026-10-09

### Corregido

- *Configurar → Mantenimiento* daba "Unknown error occurred" al abrir la
  ficha del coche: una casilla numérica sin unidad ("Revisiones ya pasadas"
  y "Revisión cada (meses)") hacía fallar el formulario.

## [2.3.0b1] — 2026-10-09

Beta. Avisos al móvil y mantenimiento, sin crear automatizaciones: todo se
configura desde *Configurar*. Guía: [docs/avisos-y-mantenimiento.md](docs/avisos-y-mantenimiento.md).

### Añadido

- **Avisos al móvil** (*Configurar → Avisos al móvil*): se eligen los móviles
  con la app de Home Assistant y qué avisos se quieren. Carga iniciada,
  interrumpida y terminada; testigos del cuadro; neumáticos (cuando el coche
  enciende el aviso); pila del mando baja (CR2032) y mantenimiento. Ninguno
  es crítico y todos llevan el nombre del coche en el título
  ("DEC Deepal Changote"). Un testigo no se repite hasta que se apague y
  vuelva a encenderse.
- **Mantenimiento por coche** (*Configurar → Mantenimiento*): se indica la
  última revisión (o la matriculación) y la integración cuenta desde ahí
  20.000 km o 12 meses, el intervalo del manual del S05 (se puede cambiar).
  Entidades nuevas: **Testigo mantenimiento**, **Días hasta el
  mantenimiento**, **Kilómetros hasta el mantenimiento** y **Próximo
  mantenimiento**. Solo se crean en los coches que lo activan.
- **Avisos de mantenimiento**: quedan 2 meses, 1 mes, 15 días, 3.000 km,
  2.000 km, 1.000 km y vencido. Cada uno, una vez por revisión y entre las
  8:00 y las 22:00.
- **Plan de mantenimiento del S05** (del manual de usuario) en
  `vehicles/vehicles.yaml`: qué operaciones lleva cada revisión, con el
  aceite del reductor delantero solo en el Max AWD.
- **Tarjeta**: testigo de mantenimiento (llave inglesa, ámbar o rojo si está
  vencido). Al pulsarlo se ven los días y kilómetros que quedan, lo que
  incluye la revisión, el historial y el botón *Registrar mantenimiento*,
  con confirmación.
- Acción `dec_deepal.register_maintenance` y registro de revisiones también
  desde *Configurar → Mantenimiento* (con otra fecha u otros kilómetros).

### Sin verificar

- Distinguir carga "terminada" de "interrumpida": el coche no dice por qué
  dejó de cargar y se deduce. Falta probarlo cargando.
- Avisos de testigos y de pila del mando: no se pueden provocar.

## [2.2.1] — 2026-10-09

### Cambiado

- **Logo de la integración redibujado sin fondo**, con el mismo diseño: azul
  marino para el tema claro (`icon.png`) y plata para el tema oscuro
  (`dark_icon.png`), como recomiendan las normas de Home Assistant. Antes era
  un cuadrado oscuro con mucho margen.
- Los archivos del logo pesan ahora 110 KB en total (antes, más de 1 MB), así
  que la integración se descarga más rápido.

## [2.2.0] — 2026-10-09

Versión estable. Reúne las betas `2.1.3b1`, `2.2.0b1` y `2.2.0b2`, validadas
en una instalación real.

### Añadido

- **Tarjeta DEC Deepal** para los paneles (`custom:dec-deepal-card`). Se
  instala sola y encuentra las entidades del coche sin configurarlas:
  cabecera con "Actualizado", vista isométrica, línea de estado (tic verde o
  testigos encendidos), batería con icono por nivel y color, autonomía,
  estado de carga y cinco botones (Confort, Bloqueo, Maletero, Ventilar y
  Localizar vehículo). Ventana de Confort con la vista interior y los
  controles de volante, asientos, temperatura y climatizador. Ver
  `docs/tarjeta.md`.
- **Icono propio de la llave del Deepal S05** para "Pila del mando baja".

### Corregido

- **Iconos propios que no aparecían tras reiniciar** Home Assistant hasta
  recargar la app: cargador temprano automático (copia en `www/dec_deepal/`
  y recurso de paneles) y repintado de los iconos dibujados antes de tiempo.

## [2.2.0b2] — 2026-10-09

Beta. Ajustes de la tarjeta tras la primera prueba.

### Añadido

- **Línea de estado** en la tarjeta, encima de la batería: un tic verde si no
  hay avisos; si los hay, el icono de cada testigo encendido (rojo los
  graves, ámbar el resto), incluida la pila del mando.
- **Icono propio de la llave del Deepal S05** para "Pila del mando baja":
  la llave cuando está bien y la llave con una exclamación cuando está baja.

### Cambiado

- La tarjeta pasa a **cinco botones**: Luces y Claxon se unen en **Localizar
  vehículo**, que abre un menú con Luces, Claxon y Luces y claxon.
- Tocar la foto del coche ya no abre nada.

## [2.2.0b1] — 2026-10-09

Beta. Incluye la 2.1.3b1 (iconos tras reiniciar), ya validada.

### Añadido

- **Tarjeta DEC Deepal** para los paneles (`custom:dec-deepal-card`). Se
  instala sola con la integración y encuentra las entidades del coche sin
  configurarlas.
  - Cabecera con "Actualizado: ...", vista isométrica, batería (icono por
    nivel y color), autonomía y estado de carga.
  - Seis botones: Confort, Bloqueo, Maletero, Ventilar, Luces y Claxon.
  - **Ventana de Confort:** vista interior con los botones de volante y
    asientos sobre la foto, temperatura y climatizador.
  - Bloqueo, Maletero y Ventilar piden confirmación y, con el modo de
    desbloqueo previo, la tarjeta lo hace sola.
- Documentación: `docs/tarjeta.md`.

## [2.1.3b1] — 2026-10-08

Beta. Segundo intento con los iconos propios que no aparecían tras reiniciar
Home Assistant hasta recargar la app. La 2.1.2 no bastó: la página se cargaba
sin nuestro script y, además, los iconos pintados antes de tiempo quedaban
marcados como desconocidos y la interfaz no los reintentaba.

### Corregido

- **Cargador temprano de iconos**, automático: la integración copia un
  pequeño script a `www/dec_deepal/` y lo registra como recurso de los
  paneles, que Home Assistant sirve desde el primer instante. Reintenta
  cargar los iconos hasta que la integración termina de arrancar.
- **Repintado:** cuando el script de iconos llega tarde, arregla los iconos
  que la página ya había dibujado en blanco.
- Al desinstalar la integración se quitan el recurso y la copia de `www`.

### Límites conocidos

- Home Assistant solo carga los recursos al abrir un panel: si la app recarga
  estando en Ajustes, los iconos aparecen al abrir un panel o recargar.
- No se registra si los recursos de los paneles están en modo YAML.
- Si la carpeta `www` no existía, funciona desde el siguiente reinicio.

## [2.1.2] — 2026-10-08

### Corregido

- **Iconos propios que no aparecían tras reiniciar** hasta recargar la app.
  El navegador pedía cada icono por separado y, si la petición caía antes de
  que la integración terminara de arrancar, recordaba el fallo para siempre.
  Ahora pide **un solo paquete** con todos los iconos y lo **reintenta**
  durante un minuto: los iconos aparecen solos, sin recargar.
- Limitación que queda: si la página se cargó antes de que Home Assistant
  conociera el script de iconos, sigue haciendo falta recargar una vez (no
  depende de la integración). Ver `docs/iconos.md`.

## [2.1.1] — 2026-10-08

### Cambiado

- Los 4 **avisos de neumático** pasan al apartado **Diagnóstico** del
  dispositivo (antes estaban en Sensores).
- Nombres: **Luces de Carretera** (antes "Luz de carretera"), **Luces de
  Cruce** (antes "Luz de cruce") y **Luces Antiniebla** (antes "Antiniebla
  trasera"). Son las mismas entidades: no cambian sus identificadores.

## [2.1.0] — 2026-10-05

Versión estable. Reúne las betas `2.1.0b1` y `2.1.0b2`, ajustadas con las
pruebas en el coche del 05-10-2026.

### Añadido

- **Antiniebla trasera** ✅ y **Recirculación de aire** ✅ (probadas).
- **Testigos del cuadro** (11) como avisos de problema, en "Diagnóstico":
  batería de 12 V, presión de neumáticos, ABS, airbag, líquido de frenos,
  frenos, dirección asistida, potencia limitada, sistema de propulsión,
  batería baja y temperatura del refrigerante. Sin falsas alarmas en las
  pruebas; el encendido real no se puede provocar.
- **Pila del mando baja** (misma situación que los testigos).
- **Apertura de cada ventanilla** (4 sensores), **desactivados por defecto**:
  la escala no está clara (ventilación 19-20, a la mitad 92, del todo 97).
- **12 iconos propios** al estilo de Home Assistant, distintos para abierto y
  cerrado: las 4 puertas, capó y maletero.

### Cambiado

- **"Luces encendidas (testigo)" pasa a llamarse "Luces de posición":**
  comprobado con el coche que es eso lo que indica. La entidad es la misma
  (no cambia su identificador).

### Corregido

- **Renovación de sesión repetida:** cerca de la caducidad se pedía una
  renovación en cada lectura (7 en 2 minutos) porque el servidor devolvía el
  mismo token. Ahora se espera 1 minuto antes de volver a intentarlo.

### Eliminado (respecto a las betas 2.1.0)

- **Tapa de carga:** el S05 no informa de ella (el dato vale siempre 0). Los
  dos iconos se conservan en `icons/reserva/` por si en el futuro hay datos.
- **Antiniebla delantera:** el S05 no tiene.
- Quien instaló una beta: las dos entidades se borran solas al actualizar.

### Verificado con el coche (05-10-2026)

Bloquear / desbloquear, maletero y cerrar ventanillas desde Home Assistant;
luz de cruce en las vistas; botón de luces y claxon a la vez; "Encendido" en
marcha. Detalle en `docs/roadmap.md`.

### Sigue sin verificar

Despertar el coche dormido, vista de carga y corrientes de carga.

## [2.1.0b2] — 2026-10-05

Beta. Solo iconos: 14 iconos propios nuevos, con el estilo de los de Home
Assistant (Material Design Icons) y distintos para abierto y cerrado.

### Añadido

- **Puertas (4):** delantera y trasera, izquierda y derecha. Cerrada de
  frente; abierta en perspectiva, girada sobre su bisagra. Las traseras
  tienen forma de puerta trasera (caída del techo y paso de rueda).
- **Capó** y **Maletero:** el coche de lado con la tapa o el portón
  levantados; cerrados, con su junta marcada.
- **Tapa de carga:** cerrada (con el rayo) y abierta hacia la derecha, con
  el puerto CCS2 a la vista.

Los iconos están en `icons/svg/` y se pueden sustituir por otros con el
mismo nombre. Derivados de Material Design Icons: ver `NOTICE.md`.

## [2.1.0b1] — 2026-10-05

Beta. Entidades nuevas a partir de datos que el coche ya enviaba y nadie
usaba (aparecían en los diagnósticos como "MQTT sin mapear"). Todas están
**sin verificar**: llegan en cada lectura, pero solo se han visto a 0 (coche
cerrado y sin averías). Hace falta ver qué valor toman al activarse.

### Añadido

- **Tapa de carga** (abierta / cerrada).
- **Antiniebla delantera** y **Antiniebla trasera**.
- **Pila del mando baja**.
- **Recirculación de aire** del climatizador.
- **Apertura de cada ventanilla** (4 sensores, en %): para distinguir
  "entreabierta para ventilar" de "abierta del todo". Se supone escala 0-100.
- **Testigos del cuadro** como avisos de problema (en "Diagnóstico"): batería
  de 12 V, presión de neumáticos, ABS, airbag, líquido de frenos, frenos,
  dirección asistida, potencia limitada, sistema de propulsión, batería baja
  y temperatura del refrigerante.

### No añadido (a propósito)

- Los testigos `acc`, `aeb`, `lwd`, `oilFuel` y `esp`: valen 1 con el coche
  sano o cambian sin avería, así que darían falsas alarmas.

## [2.0.1] — 2026-10-05

### Eliminado

- **Desempañado delantero** en el S05: el coche no es compatible (el
  interruptor no hacía nada). Ya no se crea, y la entidad que dejaron las
  versiones anteriores se borra sola al actualizar. Si la usabas en una
  tarjeta o automatización, quítala de ahí.

## [2.0.0] — 2026-10-03

Primera versión estable de la reescritura. Mismo código que la 2.0.0rc10;
reúne todo lo de las betas `2.0.0b1`–`2.0.0rc10` (detalle más abajo).

### Verificado con coches reales (S05 Max, España)

- Cuenta con dos coches, reautenticación, asistente "Configura tu vehículo".
- Batería, autonomía, kilometraje, neumáticos, temperaturas, humedad.
- Climatización, ventilador, luces y claxon, volante y asientos.
- Puertas, capó, maletero, ventanillas (sensores y modo ventilación), luces.
- Imágenes: oficial, Imagen DEC, vista de planta, isométrica e interior.

### Publicado sin verificar con el coche (ver `docs/roadmap.md`)

- Despertar el coche dormido (botón *Actualizar* y órdenes con PIN). Si
  fallara, se comporta como antes de la rc4 y se puede desactivar en
  Configurar → Avanzado.
- Bloquear / desbloquear, cerrar ventanillas y maletero desde HA.
- Vista de carga y corrientes de carga.
- Botón *Luces y claxon* a la vez.

### Problemas conocidos

- **Desempañado delantero:** el S05 probado lo da como no compatible.
- **Login por SMS:** el servidor acepta la petición pero el SMS no llega
  (lado de Deepal). Usar correo.
- Velocidad, km del trayecto, temperatura exterior y ubicación: el S05 no las
  envía (entidades desactivadas).

## [2.0.0rc10] — 2026-10-02

### Añadido

- **Vista de carga** (entidad de imagen nueva): el coche de lado,
  semitransparente, con el cable de carga gris si está enchufado sin cargar y
  verde si está cargando. Capas en `vehicles/vista_carga/s05_2024/`.
- Señal calculada `charger_plugged` (manguera AC o DC enchufada).

## [2.0.0rc9] — 2026-10-02

### Añadido

- **Vista interior** (entidad de imagen nueva): el habitáculo desde arriba con
  el aro del volante y las zonas acolchadas de los asientos delanteros
  "encendidas" cuando están calefactados (naranja) o ventilados (celeste).
  Tinte neón que respeta las costuras, con bordes difuminados y halo suave,
  20 % transparente. Capas en `vehicles/vista_interior/s05_2024/`. Cualquier
  nivel de asiento (1-3) enciende su capa.

### Corregido

- **Inicio de sesión que fallaba muy de vez en cuando:** al preparar la clave
  pública que se registra en el servidor se descartaba cualquier línea que
  contuviera "BEGIN" o "END", y el cuerpo base64 (aleatorio) a veces contiene
  "END" por casualidad: esa línea se perdía y la clave quedaba rota. Ahora
  solo se quitan las líneas `-----BEGIN/END-----`. Lo destapó una prueba.

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
