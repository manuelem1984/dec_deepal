# Cambios

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versiones: [SemVer](https://semver.org/lang/es/) (`2.0.0b1` = beta).

## [2.6.0b10] — 2026-10-26

### Añadido

- **«Carga detenida» (`ChrgSts` 5):** con la manguera puesta y el cargador
  bloqueado o desactivado, el coche manda un estado nuevo. Antes se
  descartaba y la tarjeta podía decir «Desconectado» con el cable puesto;
  ahora el «Estado de carga» es «Carga detenida», «Cargando» está apagado y
  la manguera cuenta como enchufada (AC, salvo que el coche diga DC). Lo
  vio Deepal Alternative el 25-10-2026; es justo lo que pasa cuando DEC
  Deepal bloquea el cargador al llegar al límite o al terminar.

### Corregido

- **Corriente de carga negativa:** el coche puede mandarla con el signo de la
  batería (p. ej. −60,5 A cargando en DC). Antes salía «desconocida»; ahora se
  enseña en positivo. Los valores falsos (2538 A y −2538 A) siguen fuera.
- **El cuentakilómetros nunca baja:** una lectura menor que la anterior (un
  fallo de una fuente) ya no se enseña; se conserva la anterior.

## [2.6.0b9] — 2026-10-21

### Cambiado

- **Revisión de HACS:** el cargador temprano de iconos ya no se copia a la
  carpeta `www` del usuario (que se sirve sin autenticación) ni se registra
  como recurso `/local/`. Ahora se sirve desde la ruta propia de la
  integración (`/dec_deepal/frontend/dec-icons-loader.js`) y es esa la que se
  registra como recurso de los paneles. Al arrancar se borran la copia
  antigua de `<config>/www/dec_deepal/` (solo nuestro archivo; la carpeta,
  solo si queda vacía) y el recurso `/local/` antiguo.
- **Revisión de HACS:** la clave RSA del inicio de sesión se genera en un hilo
  aparte, sin frenar el bucle de eventos de Home Assistant.

## [2.6.0b8] — 2026-10-19

### Añadido

- **Dato principal en las tarjetas del coche y de vista planta:** en su editor
  se elige qué se ve en grande junto a la batería: **Autonomía** (de fábrica,
  como hasta ahora), **Batería** (el %) o **Las dos** («76 % · 312 km»). Cada
  tarjeta guarda el suyo. La barra sigue siendo el % de batería y, sin
  cobertura, manda el % estimado por el cargador.

## [2.6.0b7] — 2026-10-19

### Añadido

- **Límite de carga (70, 80, 90 o 100 %).** Se elige en la tarjeta de cada
  coche, debajo de la barra de batería (con una marca en la barra), o en
  Ajustes → Límite de carga. Al llegar al límite (el % real o, sin cobertura,
  el estimado), DEC Deepal **bloquea el cargador vinculado**: es lo único que
  para la carga del EV, que no aplica el límite del servidor. En el PHEV,
  además, se le manda su límite propio. Sin bloqueo en el cargador, solo se
  avisa. Cerca del límite (a menos de 5 puntos), el coche se lee cada 5 min si
  «Leer el coche mientras carga» está activado.
- **«Solo esta: 100 %»** en la tarjeta del coche: la siguiente carga llega al
  100 % sin cambiar el límite.
- **Avisos nuevos (apartado Cargador):** «Llegó al límite de carga», con el
  botón «Seguir hasta el 100 %» (desbloquea y esa carga ya no se para); y
  «Recordar cargar al 100 %».
- **Recordar cargar al 100 %** cada 3, 4, 5 o 6 cargas seguidas sin llegar,
  para que la batería se equilibre y el % sea exacto, con «La próxima al
  100 %» / «Ahora no»; o «Hacerla al 100 % sin preguntar». Desactivado de
  fábrica.
- **Tarjeta del cargador:** «Cargando · se para al 80 %», la marca en la barra,
  «Para en ≈ 25 min» y, parada por el límite, «Seguir al 100 %».

## [2.6.0b6] — 2026-10-18

### Añadido

- **S05 PHEV: combustible.** «Nivel de gasolina» (%), «Autonomía con
  gasolina» (km, preferiblemente el dato europeo WLTC) y «Gasolina en el
  depósito» (litros). Solo en los coches con depósito; con el coche dormido
  conservan el último valor. Sin verificar en un PHEV real.
- **S05 PHEV: límite de carga** en AC (60-100 %), como en la app oficial.
  Solo en el PHEV: el EV acepta la orden pero no cambia el límite. Sin
  verificar en un PHEV real.

### Cambiado

- **Testigos solo con el coche encendido.** Al despertar un S05 dormido (por
  ejemplo, con Actualizar o mientras carga), el coche manda testigos
  encendidos sin motivo (ABS, frenos...). Ahora, con el coche apagado, se
  conserva el último testigo que llegó con el coche encendido: sin falsos
  avisos.
- **Menos llamadas al servidor:** la configuración del broker y el token del
  MQTT se reutilizan 10 minutos entre lecturas (dos peticiones menos en cada
  una). Si fallan, se piden de nuevo.

### Corregido

- Si el servidor devolvía la lista de coches vacía (un fallo suyo), todos los
  coches salían como «retirados» en Reparaciones. Ahora no se toca nada.
- Un mensaje MQTT mal formado ya no corta la lectura entera: se salta.
- La foto oficial del coche solo se descarga por https y sin seguir
  redirecciones.

## [2.6.0b5] — 2026-10-18

### Añadido

- **Leer el coche mientras carga** (editor del cargador, con cobertura o «no
  lo sé»; cada 15 min de fábrica, o 10, 30 o nunca): mientras el cargador
  carga, se despierta el coche como con el botón Actualizar para tener el %
  real. Necesita «Despertar el coche» activado en Ajustes. Si no responde dos
  veces seguidas, se da por comprobado que no hay cobertura y se deja de
  intentar en esa carga.
- **kWh por la potencia:** si el cargador no tiene entidad de energía, o su
  contador no avanza mientras la potencia sí, los kWh (y con ellos el %
  estimado y el coste) salen de la potencia por el tiempo. La tarjeta lo dice
  («Energía (potencia)») y el panel avisa («kWh por potencia»).

### Cambiado

- **«Sin cobertura» solo cuando está comprobado.** Antes salía siempre que el
  coche no había informado desde que empezó a cargar, aunque tuviera
  cobertura. Ahora, mientras tanto, la tarjeta dice «último dato HH:MM».

## [2.6.0b4] — 2026-10-18

### Añadido

- **Bloquear al terminar la carga** (editor del cargador, de fábrica a los 30
  min; también 15 o 45): con la manguera puesta, al 100 % (real o estimado)
  y sin cargar ese tiempo, el cargador se bloquea y avisa. Si la compañía hace
  una pausa antes del 100 %, no se bloquea. La tarjeta enseña «Se bloquea en
  N min».
- **% estimado en la tarjeta del coche** (Ajustes → Cargadores → «Mostrar el
  % estimado en la tarjeta del coche», activado de fábrica): mientras el coche
  no tiene cobertura, la tarjeta enseña «≈ 100 %» con la etiqueta
  «estimado», el estado del cargador y de qué cargador sale. Cuando el coche
  vuelve a informar, el dato real.

### Cambiado

- **Tarjeta del cargador al terminar:** ✓ verde, «Carga terminada · hora»,
  de qué % a cuál y cuánto duró; «En la batería» en vez de la potencia a 0 y
  «Sin precio» en vez de un guion.
- **Barra de carga dinámica:** claro hasta el % con el que se enchufó (con su
  marca) y fuerte lo cargado; las rayas solo se mueven mientras carga.
- **Notificación de elegir el coche:** dice que hay que mantenerla pulsada
  (en el iPhone, los botones solo salen así) y, al tocarla, abre el panel en
  la ventana de elegir el coche.

## [2.6.0b3] — 2026-10-18

### Cambiado

- **Ajustes con un solo formato.** Los interruptores van a la derecha del
  texto; los selectores (intervalo de lectura, cuánto dura el desbloqueo,
  quién puede desbloquear...) y los campos (PIN, enlace del manual), debajo,
  alineados con el texto, a todo lo ancho, en una línea y con ✓ en la opción
  elegida. «Directo / Desbloquear antes» también lleva ✓.
- **Editor del cargador:** cabecera fija con ✕, el nombre y «Guardar», y
  «Cancelar · Guardar» fijos abajo; en medio se desplaza el contenido.

### Corregido

- En el iPhone, las ventanas del panel y de la tarjeta se metían bajo la hora
  y la batería (la parte de arriba quedaba tapada). Ahora respetan la zona
  segura de arriba y de abajo.

## [2.6.0b2] — 2026-10-18

### Cambiado

- **Cargadores en el móvil:** los selectores («Quién puede desbloquear», «El
  bloqueo, encendido es…», «Si nadie contesta…», «Pasados» y «Precio del
  kWh») van debajo de su texto, a todo lo ancho y en una sola línea; la opción
  elegida lleva ✓. Textos más cortos: «Personas y admins», «Solo admins»,
  «Solo leer», «Al confirmar el coche» y «Entidad».
- **Nombre del cargador:** ahora es un campo con su etiqueta y un lápiz, para
  que se vea que se puede cambiar.
- **Entidades del cargador:** en la lista sale el nombre y, debajo, el
  identificador en pequeño (antes se cortaba); su estado sale en palabras
  («Sí», «No», «Bloqueado», «3,9 kW») en vez de «on/off».

## [2.6.0b1] — 2026-10-18

### Añadido

- **Cargadores.** DEC Deepal puede unir la carga de tus coches con tus
  cargadores (cualquiera con entidades en Home Assistant: V2C Trydan,
  Wallbox, Easee, OCPP...). Se activa en Panel → Ajustes → Cargadores y,
  desactivado, no cambia nada. **Solo bloquea y desbloquea el cargador:**
  nunca inicia ni pausa la carga (con OCPP, la compañía carga en cuanto está
  desbloqueado).
  - **Desbloquear al confirmar el coche:** al enchufar, el cargador sigue
    bloqueado hasta saber qué coche es. Con cobertura, lo dice el coche y se
    desbloquea solo; sin cobertura (o con varios coches), llega una
    notificación con un botón por coche y, al elegirlo, se desbloquea. Si
    nadie contesta, se recuerda.
  - **Bloquear al desenchufar**, pasados 3, 5 o 10 minutos, con aviso.
  - **Sin cobertura**, el % y el tiempo se estiman con los kWh del cargador
    y las **pérdidas** (10 % de fábrica, ajustables con tus propias cargas).
  - Cada carga se apunta con su coche, kWh y **coste** (precio fijo o de una
    entidad, como el PVPC).
  - **Quién puede desbloquear:** las personas de los coches y los
    administradores, o solo los administradores.
  - Avisos nuevos en el apartado **Cargador** de la pestaña Avisos (si un
    coche no tiene destinos ahí, se usan los de sus avisos de carga).
- **Tarjeta «DEC Deepal · Cargador»** (`custom:dec-deepal-charger-card`):
  el cargador, el coche que carga, kW, kWh, €, el candado y el historial de
  cargas. Se añade desde el editor de paneles, sin YAML.
- **Ventana de carga:** si el coche carga en un cargador vinculado, lo
  enseña (potencia, kWh y coste) y, sin cobertura, el % estimado.
- Catálogo: capacidad de la batería de cada versión (`bateria_kwh`).

Ver `docs/cargadores.md`.

## [2.5.2b1] — 2026-10-17

### Añadido

- **Ventana de carga: tiempo con el equilibrado.** Al tiempo que queda según
  el coche se le suman 15 minutos al final, lo que tarda el equilibrado de la
  batería; la hora de fin («lleno a las…», «Termina hacia las…») también. Lo
  dice debajo: «Incluye 15 min de equilibrado». Se quita en Panel → Ajustes →
  Lectura de datos → «Sumar el equilibrado» (activado de fábrica). El sensor
  «Tiempo de carga restante» sigue siendo el dato del coche.
- **Ventana de carga: botón ⟳ arriba a la derecha** para actualizar los
  datos; gira mientras tanto. Sustituye al «Actualizar» de abajo, donde solo
  queda «Cerrar».

### Cambiado

- La ventana de carga enseña la autonomía sin decimales («318 km»), aunque
  la entidad tenga decimales configurados.

## [2.5.1] — 2026-10-16

Versión estable. Reúne las betas `2.5.0b1` a `2.5.0b12`, probadas en una
instalación real con dos S05 EV RWD Max, y la `2.5.1b1`. (No hubo 2.5.0
estable: se pasó directamente a esta.)

### Añadido

- **Panel DEC Deepal en la barra lateral**, que sustituye a los apartados de
  Configurar (el botón Configurar de la integración lo abre). Pestañas:
  - **Coches:** foto, versión, equipamiento y matrícula de cada coche; fichas
    de mantenimiento, ITV y seguro; **Apariencia** (modelo, versión, color y
    llanta) y **Personas** (a quién pertenece cada coche; los tuyos salen
    como «Tuyo»).
  - **Avisos:** a quién llega cada aviso, coche a coche, y los plazos de cada
    uno (días y kilómetros). Nuevos avisos de renovación del seguro.
  - **Datos:** copia de seguridad (descargar, enviar al móvil, cargar) y
    borrar los datos guardados de un coche.
  - **Diagnóstico:** lo que ha pasado desde el último reinicio y la ficha de
    cada coche.
  - **Ajustes:** control remoto con PIN, intervalo de lectura, despertar el
    coche, enlace del manual y modo depuración.
- **Panel para todos los usuarios:** quien no es administrador ve Coches y
  Avisos en solo lectura.
- **Matrícula como placa europea** en Coches y Avisos, con el formato del
  país de la cuenta.
- **Coches nuevos y retirados de la cuenta:** aviso en Reparaciones para
  añadirlos o quitarlos.
- **Ventana de carga** en la tarjeta (al pulsar la franja de la batería) con
  la **última carga**: de qué porcentaje a cuál y cuánto duró.
- **Tarjeta «DEC Deepal · Vista planta»** (`custom:dec-deepal-top-card`).
- **«Vista lateral» del Max sin tapacubos**, en los cinco colores.
- **Siete idiomas nuevos** (alemán, francés, neerlandés, noruego, danés,
  griego y esloveno): la integración está en 12 idiomas, panel incluido.
- **Portugal, Italia, Alemania y Francia** al añadir una cuenta (el país por
  defecto es el de Home Assistant). Aún sin probar con cuentas de esos
  países.

### Cambiado

- **Fotos del coche en tema oscuro:** una luz de estudio detrás del coche en
  la tarjeta y en el panel.
- **Nombres de las vistas:** «Vista lateral» (antes «Imagen DEC»), «Vista
  planta» y «Vista carga». Los identificadores (`image.…`) no cambian.
- **El alta es solo con correo electrónico.**
- **Climatización:** de 18 °C a 32 °C (antes desde 16 °C).
- **Despertar el coche** más fiable: el servidor guarda la orden hasta que el
  coche la recibe.
- **«Conector AC» y «Conector DC» salen del estado de carga del coche** y
  están activos: el AC con la manguera AC puesta (cargando o no), el DC con
  la de DC. Al actualizar se activan solos, salvo que los hubieras
  desactivado tú a mano.
- Si el servidor de Deepal pide esperar, la integración espera antes de
  volver a leer.
- Preparada para Home Assistant 2026.10 y posteriores (sigue funcionando
  desde la 2026.3).

### Corregido

- **Enchufar la manguera ya no cuenta como «cargando»**; «Estado de carga»,
  los conectores y la corriente de carga (también en DC) salen del dato de
  carga del coche, y un valor viejo ya no los deja encendidos.
- **La comprobación de coches de la cuenta cada 30 minutos no llegaba a
  hacerse** (solo funcionaba al arrancar Home Assistant). Ahora se hace.
- Panel → Datos: en «Datos guardados» salía «section_people» en vez de
  «Personas», en todos los idiomas.
- El aviso del PIN armado sale en el idioma de Home Assistant.
- Un valor puesto por una orden que el coche nunca confirmó ya no se queda
  fijo.

### Limitación conocida

- La carga (estados AC y DC, avisos de carga y última carga) no se ha podido
  probar todavía con esta versión.
- Si al terminar una carga con la manguera puesta el coche dice «sin
  manguera», se verá «Desconectado». Falta comprobar qué manda el S05.

## [2.5.1b1] — 2026-10-16

### Cambiado

- **«Conector AC» y «Conector DC» vuelven a estar activos** y ahora salen
  del estado de carga del coche: el AC está enchufado con la manguera AC
  puesta (cargando o no) y el DC, con la de DC. Antes salían de unos campos
  que el S05 manda mal (cargando decía que no había manguera, o se quedaban
  encendidos con el cable quitado) y por eso estaban desactivados. Al
  actualizar se activan solos, salvo que los hubieras desactivado tú a mano.
- Con el coche diciendo «sin manguera», un valor viejo de esos campos ya no
  puede dejar «Estado de carga» en «Conectado» ni pintar el cable en la vista
  de carga.

### Corregido

- **Coches nuevos y retirados de la cuenta:** la comprobación de cada 30
  minutos no llegaba a hacerse (solo funcionaba al arrancar Home Assistant).
  Ahora se hace.
- Panel → Datos: en «Datos guardados» salía «section_people» en vez de
  «Personas», en todos los idiomas.

## [2.5.0b12] — 2026-10-15

### Cambiado

- **Fotos del coche en tema oscuro:** en la tarjeta y en el panel, detrás de
  la foto del coche hay ahora una luz de estudio suave que se funde con la
  tarjeta. Así el techo, el alerón y la zaga ya no se pierden en el fondo
  oscuro (sobre todo en los colores oscuros). En tema claro no cambia nada,
  y las fotos son las mismas.

## [2.5.0b11] — 2026-10-15

### Añadido

- **«Vista lateral» del Max sin tapacubos.** Si en Apariencia tu Max lleva la
  llanta sin tapacubos, la vista lateral del coche la enseña, en los cinco
  colores, igual que ya hacía la vista isométrica. La ventana de Apariencia
  del panel también cambia la foto al elegir la llanta.

### Cambiado

- **Nombres de las vistas**, más cortos y todos iguales: «Imagen DEC» pasa a
  ser **«Vista lateral»** (en todos los idiomas), y en español «Vista de
  planta» y «Vista de carga» pasan a ser **«Vista planta»** y **«Vista
  carga»** (también la tarjeta «DEC Deepal · Vista planta»). Solo cambia el
  nombre que se ve: los identificadores (`image.…`) siguen igual, así que no
  se rompe ninguna tarjeta ni automatización.

## [2.5.0b10] — 2026-10-15

### Añadido

- **Matrícula en el panel**, como una pequeña placa europea (franja azul con
  la letra del país) junto al modelo y el color en Coches, y junto al nombre
  en Avisos. Lleva el formato del país de la cuenta: `6545 NPD` en España,
  `AA-00-AA` en Portugal, `AB 123 CD` en Italia, `AB-123-CD` en Francia y,
  en Alemania, los dos sellos entre la ciudad y el resto. Si una matrícula no
  encaja con ese formato, se enseña tal cual. Sin matrícula, no sale nada.

### Corregido

- Panel → Coches: la etiqueta «Personas» salía con una raya encima y
  desplazada; y «Ficha verificada» y «Tuyo» salían pegadas.

## [2.5.0b9] — 2026-10-15

### Añadido

- **Panel para todos los usuarios.** Quien no es administrador ve las
  pestañas Coches y Avisos en **solo lectura**: las fichas de cada coche y a
  quién avisa de cada cosa, sin poder cambiar nada. Datos, Diagnóstico y
  Ajustes siguen siendo solo para administradores.
- **A quién pertenece cada coche.** En Panel → Coches, la fila «Personas»
  enseña las personas de Home Assistant de cada coche y el administrador las
  elige con «Elegir». Los coches de quien mira el panel salen como «Tuyo».
  Se guardan con el coche y van en la copia de seguridad.
- **Coches nuevos y retirados de la cuenta.** Cada 30 minutos se mira la
  lista de coches de la cuenta. Si aparece uno nuevo (por ejemplo, otro
  compartido), sale un aviso en Ajustes → Reparaciones para añadirlo; al
  añadirlo, aparece «Configura tu vehículo» para elegir su modelo. Si uno ya
  no está, otro aviso permite quitarlo (sus fichas de mantenimiento, ITV y
  seguro se conservan por si vuelve).
- **Portugal, Italia, Alemania y Francia.** Al añadir una cuenta se elige el
  país (por defecto, el de Home Assistant). Usan el mismo servidor que
  España y la integración ya está traducida a sus idiomas. Aún sin probar con
  cuentas de esos países, y sin su inspección técnica (la ITV es solo de
  España).

### Corregido

- El aviso «Comandos con PIN permitidos durante N segundos» (Opción B) salía
  siempre en español: ahora sale en el idioma de Home Assistant.
- Un valor puesto por una orden que el coche nunca confirmó podía quedarse
  fijo si el coche dejaba de informar de ese dato. Ahora caduca.
- Si el servidor de Deepal pide esperar (demasiadas peticiones), la
  integración espera lo que pida antes de volver a leer, en vez de seguir
  insistiendo.

### Cambiado

- Se retiran los antiguos apartados de **Configurar** (apariencia, PIN,
  avisos, mantenimiento, ITV, seguro, datos y avanzado). Desde la 2.5.0b2 el
  botón Configurar abre el panel DEC Deepal, que hace todo eso.
- Preparada para las próximas versiones de Home Assistant (2026.10 y
  posteriores): se dejan de usar dos funciones que dejarán de existir.

## [2.5.0b8] — 2026-10-15

### Corregido

- **Enchufar la manguera ya no cuenta como «cargando».** El coche manda su
  estado de carga como un número del 0 al 4 (0 sin cargar, 1 manguera AC
  puesta, 2 manguera DC puesta, 3 cargando en AC, 4 cargando en DC), y se
  leía como sí/no. Con solo enchufar, «Cargando» se encendía, empezaba una
  carga en la ventana de carga y llegaba el aviso «carga iniciada»; al
  desenchufar sin haber cargado se apuntaba una «última carga» falsa. Ahora
  solo cuentan el 3 y el 4. ⚠️ Pendiente de comprobar en el S05 de España.
- **«Estado de carga» y la vista de carga**, a partir de ese mismo dato:
  enseñan «Conectado AC/DC» con la manguera puesta sin cargar aunque el coche
  no mande los conectores (la limitación conocida de la 2.5.0b7).
- **Corriente de carga:** es la del cargador en uso. Antes, en DC salía 0
  porque se cogía primero la de AC. Sin cargar marca 0, y los valores
  imposibles (fuera de 0-600 A, como los 2538 A que manda a veces el coche
  tras una carga en DC) se descartan.
- **Climatización:** el mínimo pasa de 16 °C a 18 °C y la temperatura se
  recorta a 18-32 °C antes de enviarla. El servidor rechaza cualquier otra
  (`COMMON_1_1_01_005`), y el coche puede informar de una fuera de rango que
  luego se reutilizaba al encender.

### Cambiado

- **Despertar el coche** con QoS 1: el servidor guarda la orden hasta que el
  coche, si está muy dormido, vuelva a conectarse. Antes se perdía.

## [2.5.0b7] — 2026-10-12

### Corregido

- **«Estado de carga» ya no depende de los conectores.** En el S05 los datos
  de «Conector AC» y «Conector DC» no son fiables: el coche llega a decir que
  carga y, a la vez, que no tiene la manguera puesta, y hay coches que no
  mandan el de AC. Antes, en esos casos el estado de carga se quedaba sin
  valor o salía «Desconectado» cargando. Ahora manda «cargando»: si carga, es
  «Cargando AC» (o «Cargando DC» si hay conector o corriente de continua).
- **Vista de carga:** el cable sale siempre que el coche carga, digan lo que
  digan los conectores.

### Cambiado

- **«Conector AC» y «Conector DC» pasan a estar desactivados** y a la
  categoría de diagnóstico. En las instalaciones que ya los tenían se
  desactivan solos al actualizar (una vez); quien los quiera puede volver a
  activarlos a mano.

### Limitación conocida

- «Enchufado sin cargar» solo se puede enseñar cuando el coche informa del
  conector. Si no lo hace, con la carga terminada se verá «Desconectado»
  aunque el cable siga puesto.

## [2.5.0b6] — 2026-10-12

### Añadido

- **Ventana de carga** en las dos tarjetas: se abre al pulsar la franja de la
  batería. Enseña la vista de carga, el porcentaje, el tiempo que queda y a
  qué hora termina, la corriente, el conector, lo que lleva la carga en curso
  y la última carga.
- **La integración apunta cada carga** (cuándo y con cuánto empezó y terminó)
  y lo conserva al reiniciar. Está en los atributos `carga_actual` y
  `ultima_carga` del sensor "Cargando".

## [2.5.0b5] — 2026-10-12

### Añadido

- **Tarjeta «DEC Deepal · Vista de planta»** (`custom:dec-deepal-top-card`):
  la misma tarjeta, con el coche visto desde arriba. Se puede poner tumbado
  (por defecto, morro a la izquierda) o de pie. La tarjeta de siempre no
  cambia y las dos pueden estar en el mismo panel.

## [2.5.0b4] — 2026-10-12

### Añadido

- **Siete idiomas nuevos:** alemán, francés, neerlandés, noruego, danés,
  griego y esloveno. Con los que ya había (español, inglés, portugués,
  italiano y polaco) quedan cubiertos los países donde Changan vende en
  Europa. Traducido todo lo que se ve: entidades, avisos al móvil, tarjeta,
  panel y operaciones de mantenimiento.
- **El panel, también en portugués, italiano y polaco** (hasta ahora se veía
  en inglés).
- El noruego nynorsk se ve en bokmål y el luxemburgués en francés, igual que
  catalán, gallego y euskera se ven en español.

### Cambiado

- **El alta es solo con correo electrónico.** Se quita el acceso con teléfono
  (SMS): Deepal dejó de entregar esos SMS en septiembre de 2026 y solo servía
  para confundir. El asistente pide directamente el correo; tras pedir el
  código se puede reenviar o corregir el correo. Las cuentas ya añadidas
  siguen funcionando igual; al volver a iniciar sesión se pide el correo.

### Corregido

- Mensajes que seguían mandando a «Configurar → Mantenimiento / ITV / Seguro»
  (pantallas sustituidas por el panel en la 2.5.0b2): ahora dicen dónde está
  en el panel DEC Deepal. Afectaba a la tarjeta, a los errores y a las
  acciones, en español, inglés, portugués, italiano y polaco.
- En portugués, italiano y polaco, el aviso de la tarjeta para activar el PIN
  nombraba la pestaña "Settings" en inglés.
- En español, la ayuda de «Desbloquear antes» citaba mal el nombre de la
  entidad; en inglés, «Terceros ampliado» se llamaba de dos formas.

### Quitado

- Del catálogo de países: `prefijo`, `digitos_movil` y `metodos_login`.

## [2.5.0b3] — 2026-10-11

### Añadido

- **Panel → Coches: fichas.** Pulsar el recuadro de Mantenimiento, ITV o
  Seguro abre una ventana con su información: qué toca en la revisión (y qué
  se añade en la siguiente), cuánto falta por tiempo y por kilómetros, el
  historial y el manual; las fechas y normas de la ITV; y del seguro, la
  póliza, el plazo para desistir sobre la línea del año y los teléfonos para
  llamar con un toque. El engranaje sigue abriendo la configuración.

### Cambiado

- **Formularios de mantenimiento, ITV y seguro rehechos:** por bloques, con
  una explicación en cada uno y un recuadro que adelanta el resultado según
  se escribe. El intervalo de mantenimiento se elige entre el del manual y
  otro; el preaviso del seguro, entre 15, 30, 60 días u otro; la ITV se
  calcula sola o se pone a mano.
- "Registrar revisión hecha" y "Registrar ITV pasada" pasan del formulario a
  la ficha.

## [2.5.0b2] — 2026-10-11

### Añadido

- **Panel → Coches → Apariencia:** una ventana para elegir modelo, versión,
  color y llanta, con la foto del catálogo delante, que cambia con lo que se
  va eligiendo.
- **Panel → Ajustes** (pestaña nueva), con lo que es de la cuenta: el control
  remoto con PIN (un PIN para todos los coches) y la lectura de datos
  (intervalo, despertar el coche, enlace del manual y modo depuración).

### Cambiado

- **El botón Configurar de la integración abre el panel**, como en Alarmo. El
  panel sustituye a los apartados de Configurar; lo único que queda fuera es
  añadir la cuenta y volver a iniciar sesión.
- Los dos modos del PIN se llaman ahora «Directo» y «Desbloquear antes».

## [2.5.0b1] — 2026-10-11

### Añadido

- **Panel DEC Deepal en la barra lateral.** Una página propia, solo para
  administradores, que convive con Configurar. Cuatro pestañas:
  - **Coches:** cada coche con su foto, versión, equipamiento de su ficha y
    tres recuadros —mantenimiento, ITV y seguro— con un engranaje para
    configurarlos y registrar revisiones o ITV.
  - **Avisos:** una tabla por coche, con un apartado por cada cosa (carga,
    testigos, mantenimiento, ITV, seguro), una fila por aviso y una casilla
    por destino.
  - **Datos:** descargar la copia, enviarla a un móvil, cargarla y borrar.
  - **Diagnóstico:** lo que ha pasado (cambios, órdenes, avisos) y la ficha
    de cada coche.
  Ver `docs/panel.md`.
- **Cada aviso tiene sus destinos**, no solo cada grupo: se puede mandar el
  aviso de los 15 días a un móvil y el de «cumplido» a dos.
- **Plazos editables por coche** (el lápiz de la pestaña Avisos): los días y
  los kilómetros de cada aviso de mantenimiento, ITV y seguro.
- **Avisos de renovación del seguro:** 30 y 15 días antes de renovarse.
  Nacen sin destinos; se activan en el panel.

### Cambiado

- **Avisos de mantenimiento por kilómetros:** de fábrica pasan a 5.000, 2.500
  y 1.000 km (antes 3.000, 2.000 y 1.000). Se pueden cambiar en el panel.
- Quien ya tenía avisos configurados no nota nada: cada aviso hereda los
  destinos de su grupo. Configurar → Avisos al móvil sigue funcionando, por
  grupos.
- El panel está en español e inglés; en portugués, italiano y polaco se ve en
  inglés por ahora.

## [2.4.0] — 2026-10-11

Versión estable. Reúne las betas `2.4.0b1` a `2.4.0b4`, probadas en una
instalación real, más la copia desde el móvil.

### Añadido

- **Los datos son del coche, no de la cuenta.** El mantenimiento, la ITV, el
  seguro y la apariencia se guardan por bastidor: si se quita la cuenta y se
  vuelve a añadir, cada coche recupera lo suyo. Lo que ya había se pasa solo
  al formato nuevo.
- **Configurar → Datos de los coches:** descargar una copia de seguridad,
  enviarla a un móvil, cargarla (en esta u otra instalación) y borrar los
  datos de los coches que se elijan.
- **Avisos por coche y por grupo.** Cada coche elige a quién avisa de cada
  cosa: los avisos del coche (carga, testigos, neumáticos, pila del mando),
  mantenimiento, ITV y seguro. Las notificaciones de Home Assistant (la
  campana) son un destino más. Quien ya tenía avisos no nota nada al
  actualizar.
- **Fichas de coche.** Las cinco variantes del S05 en España, con el
  equipamiento de los catálogos oficiales: EV RWD Pro, EV RWD Max, EV 4WD
  Max, PHEV Pro y PHEV Limited Edition. Un coche sin ficha propia usa la del
  Max. Verificada en un coche real solo está la del EV RWD Max.
- **S05 PHEV:** manual y plan de mantenimiento propios (manual oficial).
- **Diagnóstico ampliado:** bloque `historial` con los cambios de señales,
  las órdenes y su respuesta, los avisos enviados y los errores; y, por
  coche, la ficha que se le aplica y sus entidades.
- **Pruebas automáticas de la tarjeta en un navegador**, que GitHub ejecuta
  en cada subida.

### Corregido

- **Humedad interior mal escalada:** se mostraba 6,1 % en vez de 61 %.
- **La copia no se descargaba desde la app del móvil:** el enlace se abre
  ahora en el navegador del teléfono.

### Cambiado

- **Los Pro, como son de verdad:** sin asientos calefactados ni ventilados,
  sin volante calefactado y sin portón eléctrico. Dejan de crearse esas
  entidades (y se quitan si existían) y la tarjeta no enseña esos mandos.
- **Quitar la cuenta ya no borra los datos de los coches.**
- **Nombres:** «Deepal S05 EV RWD Max» en vez de «Deepal S05 Max (2024-25)»;
  «Max AWD» pasa a ser «4WD Max»; el color se llama «Ganymede Grey».
- **La tarjeta, por módulos:** su código está repartido en
  `frontend_card/src/` y se une con `tools/construir_tarjeta.py`.
- Qué testigos no avisan (hoy, el del airbag) lo dice la ficha del coche.

## [2.4.0b4] — 2026-10-11

### Añadido

- **S05 PHEV: manual y plan de mantenimiento propios**, del manual oficial
  (julio de 2026). Revisión cada 20.000 km o 12 meses, con lo del EV más el
  motor de gasolina: aceite y filtro de aceite e inspección del sistema de
  combustible en todas; bujías y filtro de aire del motor cada dos; aceite
  del reductor delantero cada tres. En Configurar → Avanzado, su enlace se
  llama «Manual PHEV».

### Cambiado

- Confirmado: el PHEV (Pro y Limited Edition) lleva la misma llanta de 18"
  que el EV Pro.

## [2.4.0b3] — 2026-10-11

### Añadido

- **Avisos por coche y por grupo.** En Configurar → Avisos al móvil, cada
  coche elige a quién avisa de cada cosa: los avisos del coche (carga,
  testigos, neumáticos, pila del mando), mantenimiento, ITV y seguro, cada
  grupo con sus destinos. Un grupo sin destinos no avisa. Las notificaciones
  de Home Assistant (la campana) son un destino más. Quien ya tenía avisos
  configurados no nota nada al actualizar.
- **Fichas de coche.** El catálogo describe las cinco variantes del S05 en
  España, con el equipamiento de los catálogos oficiales: EV RWD Pro, EV RWD
  Max, EV 4WD Max, PHEV Pro y PHEV Limited Edition. Cada versión solo escribe
  en qué se diferencia; un coche sin ficha propia usa la del Max. Verificada
  en un coche real solo está la del EV RWD Max. Ver
  `docs/anadir-pais-vehiculo-idioma.md`.
- **Los Pro, como son de verdad.** Sin asientos calefactados ni ventilados,
  sin volante calefactado y sin portón eléctrico: dejan de crearse esas
  entidades (y se quitan si existían), la ventana de Confort no enseña esos
  botones y el botón Maletero de la tarjeta solo indica el estado.
- **Diagnóstico ampliado.** Nuevo bloque `historial`, que la rutina no borra:
  qué señales cambiaron y cuándo, órdenes enviadas con la respuesta del
  servidor, avisos enviados y errores. Además, por coche, la ficha que se le
  aplica y sus entidades con su estado. Ver `docs/depuracion.md`.

### Corregido

- **Humedad interior mal escalada.** El coche la envía a veces en % (61) y a
  veces en décimas (453): se mostraba 6,1 % en vez de 61 %.

### Cambiado

- **Nombres de modelo y versión:** «Deepal S05 EV RWD Max» en vez de «Deepal
  S05 Max (2024-25)»; «Max AWD» pasa a ser «4WD Max». No hay que volver a
  elegir nada. El color se llama «Ganymede Grey» (estaba mal escrito).
- Qué testigos no avisan (hoy, el del airbag) lo dice ahora la ficha del
  coche, no el código. Para el usuario no cambia nada.

## [2.4.0b2] — 2026-10-11

Sin cambios para el usuario: la tarjeta hace lo mismo que en la 2.4.0b1.

### Cambiado

- **La tarjeta, por módulos.** Su código pasa de un fichero de 1.750 líneas a
  14 módulos en `frontend_card/src/` (uno por ventana), que se unen en el
  fichero de siempre con `tools/construir_tarjeta.py`. Sin Node ni
  dependencias. Ver `docs/tarjeta.md`.

### Añadido

- **Pruebas automáticas de la tarjeta en un navegador** (`tests_tarjeta/`):
  lo que pinta, los idiomas, cada ventana y lo que se le pide al coche. GitHub
  las ejecuta en cada subida. Incluyen los tres fallos de la 2.3.0 (botones
  de llamar, Confort en azul y texto de carga al cambiar de idioma).

## [2.4.0b1] — 2026-10-11

### Cambiado

- **Los datos son del coche, no de la cuenta.** El mantenimiento, la ITV, el
  seguro y la apariencia (modelo, versión, color y llanta) se guardan por
  bastidor. Si se quita la cuenta y se vuelve a añadir, cada coche recupera
  su historial y su apariencia. Los datos que ya había se pasan solos al
  formato nuevo al actualizar.
- **Quitar la cuenta ya no borra esos datos.** Se borran desde Configurar →
  Datos de los coches.

### Añadido

- **Configurar → Datos de los coches:** descargar una copia de seguridad,
  cargarla (en esta u otra instalación) y borrar los datos guardados de los
  coches que se elijan. La copia incluye la apariencia de cada coche.
- El almacén queda preparado para cambiar de formato en versiones futuras sin
  perder datos.

## [2.3.0] — 2026-10-10

Versión estable. Reúne las betas `2.3.0b1` a `2.3.0b11`, validadas en una
instalación real. Quedan por comprobar con el coche los avisos de carga
(iniciada, terminada e interrumpida).

### Añadido

- **Avisos al móvil** desde la integración, sin automatizaciones: carga
  iniciada, terminada e interrumpida, testigos, neumáticos y pila del mando.
  Se eligen en Configurar → Avisos al móvil.
- **Mantenimiento** por coche, con el plan del fabricante: entidades, testigo
  en la tarjeta, ventana con las operaciones de la revisión y avisos por
  fecha y por kilómetros.
- **ITV** (solo España) y **Seguro**: fechas, avisos y ventana en la tarjeta,
  con la póliza y botones para llamar a la asistencia y a la compañía.
- **Tarjeta: botón «Otros»**, con Manual, Mantenimiento, ITV y Seguro.
- **Vista isométrica en el color del coche**, con la llanta de cada versión
  (Pro de 18"; Max con o sin tapacubos) y la matrícula «DEC Deepal».
- **Idiomas:** inglés, portugués, italiano y polaco. Catalán, gallego y
  euskera se muestran en español. Todos los textos salen de una sola fuente
  (`docs/idiomas.md`).

### Corregido

- **Tarjeta: el botón Confort salía en azul con todo apagado.** Ahora solo se
  pone en azul si hay algo encendido (clima, asientos o volante).
- **Tarjeta: el estado de carga se quedaba en el idioma anterior** al cambiar
  de idioma, hasta recargar la página.

### Cambiado

- **El testigo del airbag ya no avisa ni sale en la tarjeta.** El coche lo
  enciende unos segundos cada vez que despierta y saltaba sin motivo. La
  entidad «Testigo airbag» sigue existiendo.

## [2.3.0b11] — 2026-10-10

### Corregido

- **Tarjeta → Seguro: los botones de llamar no hacían nada** en la app del
  móvil. Ahora abren el marcador del teléfono. Además, cada botón enseña el
  número y, al pulsarlo, lo copia.

## [2.3.0b10] — 2026-10-10

### Añadido

- **Idiomas: italiano y polaco.** Solo la traducción: integración, avisos al
  móvil, tarjeta y operaciones de mantenimiento. Pendientes de revisión por
  alguien nativo. (Las cuentas siguen siendo las de España.)
- Los avisos usan el formato de cada idioma para los números (`2.000`,
  `2 000`), los ordinales (`2ª`, `2º`, `2.`) y las fechas (`10/03/2027`,
  `10.03.2027`).

### Cambiado

- **El módulo de ITV es solo para España.** Depende del país de la cuenta, no
  del idioma: en un país sin ITV dada de alta no aparecen el apartado de
  Configurar, las entidades, los avisos ni la opción de la tarjeta. Hoy solo
  existe España, así que para los usuarios actuales no cambia nada.

## [2.3.0b9] — 2026-10-10

Reorganización interna de los idiomas. **Para quien usa la integración no
cambia ningún texto.**

### Cambiado

- **Una sola fuente por idioma.** Todos los textos están ahora en
  `idiomas/<idioma>.json` (integración, avisos, tarjeta y catálogo). Los
  ficheros de Home Assistant, los textos de los avisos y la tabla de la
  tarjeta se generan con `tools/generar_idiomas.py`. Guía:
  [docs/idiomas.md](docs/idiomas.md).
- **Añadir un idioma es añadir un fichero**, y puede estar a medias: lo que
  falte se rellena con el inglés.
- Los idiomas que usan los textos de otro (catalán, gallego y euskera → español)
  se declaran en `idiomas/idiomas.json`, en vez de mantener copias a mano.
- **Normas por país:** los plazos de la ITV y el preaviso del seguro salen de
  `countries/countries.yaml` (`normas`), no del código. Hoy solo España.
- Las operaciones del plan de mantenimiento se identifican por clave
  (`clave: brake_fluid`) y su nombre está en los ficheros de idioma.

### Añadido

- Glosario de términos por idioma y revisor de cada idioma, en `docs/idiomas.md`.
- `python tools/generar_idiomas.py --informe`: qué le falta a cada idioma.

## [2.3.0b8] — 2026-10-10

### Añadido

- **Idiomas: inglés y portugués (de Portugal)**, además del español. Se usa
  el idioma que cada usuario tenga en Home Assistant. Está traducido todo:
  los menús de Configurar, los nombres de las entidades, los errores, los
  avisos al móvil, la tarjeta y las operaciones del plan de mantenimiento.
- La tarjeta elige el idioma por usuario: dos personas con idiomas distintos
  ven cada una el suyo en el mismo panel.

### Cambiado

- Hasta ahora el "inglés" de la integración era el mismo texto en español.
  Con Home Assistant en **catalán, gallego o euskera** la integración se
  sigue viendo en español. En cualquier otro idioma sin traducción pasa a
  verse en inglés (antes, en español).
- Los avisos al móvil y las operaciones de mantenimiento salen en el idioma
  general de Home Assistant (*Ajustes → Sistema → General*), no en el de cada
  usuario.

### Pendiente de revisar

- El portugués y el inglés los ha traducido el proyecto; conviene que alguien
  nativo revise los términos del coche y del seguro.

## [2.3.0b7] — 2026-10-10

### Añadido

- **ITV** (*Configurar → ITV*, por coche): con la fecha de matriculación y la
  de la última ITV, la integración calcula la siguiente con la regla de los
  turismos en España (4 años; cada 2 hasta los 10; anual después). Se puede
  poner otra fecha a mano. Entidades: **Testigo ITV**, **Próxima ITV** y
  **Días hasta la ITV**. Avisos: quedan 2 meses, 1 mes, 15 días y vencida.
- **Seguro** (*Configurar → Seguro*, por coche): compañía, número de póliza,
  tipo, fecha de renovación, días de antelación para desistir y teléfonos
  opcionales. Entidades: **Testigo seguro**, **Renovación del seguro**,
  **Días hasta la renovación** y **Límite para desistir**. Avisos: 30 y 15
  días antes del límite, el último día y al renovarse (la fecha pasa sola al
  año siguiente).
- **El número de póliza y los teléfonos solo se ven en la tarjeta**: no hay
  ninguna entidad con ellos ni salen en los diagnósticos.
- **Tarjeta**: "Otros" tiene ahora cuatro opciones (Manual, Mantenimiento,
  ITV y Seguro). Testigos de ITV (portapapeles) y de seguro (escudo), ámbar o
  rojo, que abren su ventana; la de seguro tiene botones para llamar a la
  asistencia y a la compañía. Botón *Registrar ITV pasada*, con confirmación.
- Acción `dec_deepal.register_itv`.

### Cambiado

- Los avisos de ITV y de seguro nacen activados para quien ya tenía
  configurados los avisos (se pueden quitar en *Configurar → Avisos al móvil*).

## [2.3.0b6] — 2026-10-09

### Cambiado

- *Configurar → Avisos al móvil*: en "Avisar a" se ve el **nombre del
  dispositivo** ("iPhone de Manuel"), como en *Ajustes → Aplicación móvil*, en
  lugar del nombre interno (`notify.mobile_app_iphone_de_manuel`). Lo que ya
  estuviera elegido se conserva.

## [2.3.0b5] — 2026-10-09

### Añadido

- **Vista isométrica con el color de tu coche.** Se dibuja con el color
  elegido en *Configurar → Apariencia*: Andromeda Blue, Deep Space Black,
  Ganymade Grey, Mercury Silver o Moonlight White, también con puertas, capó
  y portón abiertos. Sin color elegido se ve la de siempre. Como la tarjeta
  usa esta vista, cambia sola.
- **Llantas en la vista isométrica.** El Pro lleva su llanta de 18" con
  tapacubos. En el Max se elige en *Configurar → Apariencia*: 20" con
  tapacubos (la de siempre) o 20" sin tapacubos.
- **Matrícula "DEC Deepal"** en la vista isométrica.

### Cambiado

- El plata de la vista isométrica es ahora el Mercury Silver oficial (más
  cálido y oscuro), para distinguirlo del blanco.

### Notas

- Las vistas de planta, interior y de carga no cambian.
- Los colores se han obtenido repintando las capas originales; las llantas
  salen de una foto oficial (Pro) y de una foto de un socio (Max).

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

Siempre centrado en el S05 de España.

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
  v1 (con la que funcionaba), así que el fallo es
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

- **Login por SMS:** las cabeceras ahora son las de la app actual: `appversion V1.12.0`
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

Reescritura completa desde cero.

### ⚠️ Cambio incompatible

- Dominio nuevo `dec_deepal` y repositorio nuevo. Los `entity_id` cambian.

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

### Cambiado

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
