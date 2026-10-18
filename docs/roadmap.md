# Hoja de ruta

## Beta 2.6.0b5 (18-10-2026) — pendiente de probar

- [ ] **Con cobertura (caso del usuario):** cargando, cada 15 min el coche se
      despierta y la tarjeta pasa a enseñar el % real (sin «estimado»).
- [ ] **Sin cobertura (Garaje):** tras dos despertares fallidos, «sin
      cobertura» y no lo vuelve a intentar en esa carga.
- [ ] **Energía parada** (el usuario veía +0,0 kWh a 1,8 kW): los kWh avanzan
      con la potencia y el panel enseña «kWh por potencia».

## Beta 2.6.0b4 (18-10-2026) — pendiente de probar

- [ ] **Notificación en el iPhone:** mantenerla pulsada enseña los coches y
      elegir uno desbloquea; tocarla abre el panel en la ventana de elegir.
      (En la carga del 18-10, la pulsación no llegó a Home Assistant.)
- [ ] **Bloquear al terminar:** tras llegar al 100 %, a los 30 min se bloquea
      y avisa; la tarjeta cuenta los minutos que faltan.
- [ ] **Tarjeta del coche sin cobertura:** «≈ %» y «estimado» mientras el
      coche no informa; vuelve al dato real cuando informa.
- [ ] **Tarjeta del cargador:** ✓ al terminar, barra en dos tramos y rayas
      solo cargando.

## Beta 2.6.0b3 (18-10-2026) — pendiente de probar

- [ ] **iPhone:** el editor del cargador (y las demás ventanas) ya no se mete
      bajo la hora; la cabecera y «Cancelar · Guardar» no se pierden.
- [ ] **Ajustes:** todos los selectores y campos debajo del texto, en una
      línea y con ✓; los interruptores a la derecha. En móvil y ordenador.

## Beta 2.6.0b2 (18-10-2026) — pendiente de probar

- [ ] **Editor del cargador en el móvil:** todos los selectores en una línea;
      el nombre se cambia en su campo; las entidades con su estado en palabras.

## Beta 2.6.0b1 (18-10-2026) — pendiente de probar

Cargadores (ver `docs/cargadores.md`). Antes de activarlo, desactivar las
automatizaciones propias del cargador (en el V2C, «V2C Trydan - Inicio de
Carga») para que no se pisen con el bloqueo.

- [ ] **Configurar el Garaje** (V2C Trydan): Conectado, Cargando, Potencia de
      carga, Energía de carga y Bloquear EVSE (encendido = bloqueado), los dos
      coches, sin cobertura, desbloquear al confirmar, bloquear a los 5 min.
- [ ] **Enchufar sin cobertura:** llega «¿Cuál es?» con Changote, Changuito y
      «No desbloquear»; al elegir, se desbloquea y la compañía empieza a
      cargar. Comprobar que el botón funciona desde el iPhone y desde Android.
- [ ] **Nadie contesta:** recordatorio a los 15 min y el cargador sigue
      bloqueado.
- [ ] **Con cobertura** (un coche): se desbloquea solo y llega «Changote
      confirmó la manguera».
- [ ] **Tarjeta del cargador:** esperando (elegir el coche desde la tarjeta),
      cargando (kW, kWh, €, % estimado), libre (resumen del mes), candado y
      «Cargas». Con un usuario que no es de esos coches: sin botones.
- [ ] **Fin de carga:** aviso con % estimado, kWh y €; «Última» en la tarjeta.
- [ ] **Desenchufar:** a los 5 min se bloquea y avisa con «Desbloquear otra vez».
- [ ] **Pérdidas medidas:** tras una carga sin cobertura, cuando el coche
      vuelve a informar, sale «Medido: X %» en el editor del cargador.
- [ ] **Ventana de carga del coche:** con el coche cargando sin cobertura,
      sale «Cargador · Garaje · 3,9 kW» y el % estimado.
- [ ] Pendiente: que el estado del cargador salga también como entidades
      (para automatizaciones).

## Beta 2.5.2b1 (17-10-2026) — pendiente de probar

- [ ] **Ventana de carga, cargando:** el tiempo restante y la hora de fin
      llevan 15 min más que el coche, con «Incluye 15 min de equilibrado».
      Comparar con la hora real a la que termina la carga.
- [ ] **Ajustes → Sumar el equilibrado:** quitarlo y ver que la ventana
      enseña el tiempo del coche, sin la nota.
- [ ] **Botón ⟳** de la cabecera: actualiza y gira mientras tanto; abajo solo
      «Cerrar».
- [ ] La autonomía de la ventana sale sin decimales (Changuito tiene 2 en su
      entidad).

## 2.5.1 (16-10-2026) — publicada

Panel DEC Deepal (también en solo lectura para quien no es administrador),
matrícula, personas, coches nuevos y retirados, ventana de carga, vista
planta, vista lateral del Max sin tapacubos, tema oscuro, conectores desde
`ChrgSts`, 12 idiomas y cuatro países nuevos. Reúne las betas 2.5.0b1 a b12 y
la 2.5.1b1 (no hubo 2.5.0 estable). Probado en una instalación real con dos
S05 EV RWD Max, todo menos la carga.

Pendiente de comprobar:

- [ ] **Conectores:** tras actualizar, «Conector AC» y «Conector DC» están
      activos. Sin manguera, los dos apagados; con la AC (enchufada o
      cargando), solo el AC; con la DC, solo el DC.
- [ ] **Estado de carga (`ChrgSts`):** sin manguera (0 → Desconectado), AC
      enchufado sin cargar (1 → Conectado AC, sin aviso de "carga
      iniciada"), AC cargando (3 → Cargando AC, cable verde en la vista de
      carga) y, si se puede, DC (2 → Conectado DC, 4 → Cargando DC, con la
      corriente de DC). El valor en bruto sale en el diagnóstico.
- [ ] **Última carga:** tras una carga completa, de qué porcentaje a cuál y
      cuánto duró; enchufar y desenchufar sin cargar no apunta nada. (La de
      Changote del 12-10, «del 100 % al 100 % en 14 h 28 min», es de antes
      de la 2.5.0b8.)
- [ ] **Carga terminada con la manguera puesta:** ¿qué `ChrgSts` manda?
- [ ] **Coche nuevo o retirado de la cuenta:** el aviso sale en menos de 30
      minutos sin reiniciar (corregido en la 2.5.0).
- [ ] **Países nuevos:** que alguien de Portugal, Italia, Alemania o Francia
      lo pruebe con su cuenta.
- [ ] Revisión de cada idioma por alguien nativo.
- [ ] Pendiente: potencia (kW) en la ventana de carga, si el coche da el
      voltaje.
- [ ] Pendiente: la vista de planta solo está dibujada en plata.
- [ ] Pendiente: una foto de la llanta sin tapacubos más de frente y con luz
      uniforme mejoraría la vista lateral.
- [ ] Pendiente: saber si está enchufado sin cargar cuando el coche no manda
      el conector (candidato: `charge.chargeConStatus` del REST).

## 2.4.0 (11-10-2026) — publicada

Datos por coche, copia de seguridad, avisos por coche y grupo, fichas de las
cinco versiones del S05, diagnóstico ampliado y tarjeta por módulos.

Pendiente de comprobar:

- [ ] **Copia desde el móvil:** que "Descargar una copia" abra el navegador
      del teléfono y que "Enviar la copia a un móvil" llegue y se descargue
      (iPhone y Android).
- [ ] **Avisos por coche:** repartirlos y ver que cada uno llega a su destino.
- [ ] Con el `historial` de varios días, medir cuánto dura encendido el
      testigo del airbag al despertar y cambiar "no avisa" por "avisa solo si
      sigue encendido X minutos".
- [ ] Verificar con el diagnóstico de un coche real las fichas del EV RWD
      Pro, EV 4WD Max y PHEV (hoy salen del catálogo oficial). Del PHEV
      faltan además las entidades de combustible (depósito de 51 L) y los
      raíles de techo en las vistas.

## 2.3.0 (10-10-2026) — publicada

Probado en una instalación real: mantenimiento, ITV, seguro, botón «Otros»,
manual, colores y llantas de la vista isométrica, idiomas, mandos de la
tarjeta, clima con el coche apagado y despertar del coche.

Pendiente de comprobar:

- [ ] **Avisos de carga**: iniciada, terminada e interrumpida. Sobre todo,
      que al terminar con un límite de carga (p. ej. 80 %) diga "terminada" y
      no "interrumpida", y que desenchufar a media carga diga "interrumpida".
- [ ] **Avisos de testigos, neumáticos y pila del mando**: no se pueden
      provocar; falta ver uno real.
- [ ] **Testigo del airbag**: se quitó de los avisos y de la tarjeta porque
      se enciende unos segundos al despertar el coche. Estudiar si se puede
      recuperar ignorando los encendidos breves.
- [ ] **Clima con el coche encendido**: el servidor lo rechaza; falta un
      mensaje claro en la tarjeta.
- [ ] Revisión de todos los idiomas (menos el español) por alguien nativo.
- [ ] Los mismos colores en la **vista de planta** (las vistas interior y de
      carga no se tocan).
- [ ] Manual del PHEV: cuando se añada ese modelo al catálogo, con su enlace.

## Pendiente de diseño

- [ ] **Volante a la derecha** (Reino Unido, Irlanda, Malta, Australia):
      hoy se da por hecho que el delantero izquierdo es el del conductor
      (puertas, ventanillas, asientos, vistas). Hace falta una opción por
      coche (o por país) que lo intercambie antes de añadir esos países.
- [ ] **Permisos por persona:** los coches ya tienen personas asignadas
      (2.5.0b9). Falta decidir qué puede hacer cada una con su coche
      (órdenes, ver otros coches, avisos propios...) y cómo se hace cumplir
      también en las entidades y la tarjeta, no solo en el panel.
- [ ] **Normas de cada país nuevo:** Portugal, Italia, Alemania y Francia
      entran sin su inspección (IPO, revisione, HU/TÜV, contrôle technique)
      y con los plazos del seguro de España. Revisar con usuarios de allí
      (en Italia el seguro no se renueva solo; en Alemania se cancela con un
      mes de antelación) y el manual del coche en su idioma.

- [x] **Italiano y polaco**, solo la traducción (2.3.0b10). Pendiente:
      revisor nativo de cada idioma. Las cuentas de Italia y Polonia (países
      nuevos, con sus normas de inspección) no están previstas por ahora.
- [ ] **Aceptar solo el S05** al añadir la cuenta (los demás modelos, "no
      compatible todavía"). Decidir qué pasa con el S05 PHEV.
- [ ] **No enviar el clima con el coche encendido** (el servidor lo rechaza:
      1032 "Power is not off") y decirlo claro en la tarjeta.
- [x] **Fichas ligadas al coche** (2.4.0b1): mantenimiento, ITV, seguro y
      apariencia van por bastidor.
- [x] **Humedad interior** (2.4.0b3). Sigue pendiente el **despertar**
      (falló dos veces el 10-10-2026).
- [x] **Cargando con "conector AC: no"** (visto el 11-10-2026): resuelto en
      la 2.5.0b7, el estado de carga ya no depende de los conectores.
- [ ] El **tiempo de carga restante** (1.353 min con 16 A al 56 %) no cuadra.
- [ ] **Aviso "cargado sin cobertura":** si el coche vuelve a tener cobertura
      con más batería y no se vio la carga, avisar "Cargado: del 40 % al 80 %".
- [ ] Guardar la configuración y el permiso de conexión entre lecturas para
      hacer menos llamadas al servidor.

- [ ] **Adaptación de funciones para modelo Pro.** Hoy la única diferencia
      con el Max es la ventilación de asientos, y es una suposición: no hay
      diagnóstico de ningún Pro. Idea: crear las entidades según las
      capacidades que declara cada coche (`function-config`), con la versión
      elegida a mano como respaldo. Hace falta el diagnóstico de un Pro real.
      En la tarjeta: centrar el botón de calefacción cuando no hay
      ventilación, y ocultar los botones de órdenes que el coche no admita.
- [ ] **Entidades cuyo dato el coche nunca envía** (el segundo coche de
      pruebas no manda testigos ni conector AC): decidir si se crean
      desactivadas, no se crean o se dejan. En la tarjeta, no mostrar el tic
      verde si el coche no informa de los testigos.
- [ ] **Control con PIN por coche.** El PIN es de la cuenta de Deepal (la
      comprobación no lleva el identificador del coche), pero activarlo y
      elegir el modo sí podría ser por coche.

## Publicada la 2.1.0 (05-10-2026) — pendiente de probar con el coche

Lo que la 2.1.0 lleva **sin verificar**. Quien lo pruebe, que lo cuente en
Telegram o en un *issue* y se marca en
[correlacion_endpoints_entidades.csv](correlacion_endpoints_entidades.csv).

### Coche dormido (lo más importante)

- [ ] Botón *Actualizar datos del vehículo* con el coche **dormido** (varias
      horas parado): debe despertarlo y traer datos nuevos en menos de 1 min.
      Pulsarlo otra vez antes de 5 min NO debe volver a despertarlo.
- [ ] Orden con PIN (p. ej. desbloquear) con el coche dormido: debe
      despertarlo antes (hasta ~30 s) y ejecutarse.
- [ ] Con el coche dormido: un comando rechazado muestra un mensaje claro y
      la entidad vuelve a su estado anterior.

Si el despertar no funcionara, la integración se comporta como antes de la
rc4 (datos sin refrescar hasta que el coche se despierte solo) y se puede
desactivar en Configurar → Avanzado.

### Carga

- [ ] Vista de carga: enchufado sin cargar (cable gris) y cargando (cable
      verde), en AC y, si se puede, en DC.
- [ ] Corriente de carga AC / DC y conector DC.
- [ ] **Segundo coche de la cuenta de pruebas ("Changuito"):** su informe MQTT
      trae menos datos que el otro S05 Max (05-10-2026): no manda
      `acChargeGunConnectionState`, ni los testigos del cuadro. Sin conector
      AC, su "Estado de carga" queda en desconocido. Comprobar enchufándolo;
      el REST trae `charge.chargeConStatus`, candidato a respaldo.

### Entidades sin poder provocar

- [ ] **Pila del mando baja** y **testigos del cuadro** (11): sin falsas
      alarmas parado ni en marcha (05-10-2026); falta ver uno encendido de
      verdad.
- [ ] **Apertura de ventanillas** (desactivadas por defecto): entender la
      escala. Lecturas del 05-10-2026: ventilación 19-20; a la mitad 92; del
      todo 97; cerrada 0 en los diagnósticos, pero en pantalla se vio 100.

### Otros

- [ ] Velocidad, km del trayecto, km de ayer y temperatura exterior:
      activadas a mano el 05-10-2026, **no traen ningún dato** en el S05.
      Siguen desactivadas por defecto.
- [x] Login por **SMS**: quitado en la 2.5.0b4 (el servidor respondía éxito
      pero el SMS no llegaba). Solo se entra con correo.
- [ ] Capacidades de un **Pro**: confirmar que no manda `FronSeatVentilationSW`
      ni `#vent3` (pedir diagnóstico a alguien con un Pro).
- [ ] Dejar un SVG nuevo (`outside_temperature.svg`) y comprobar que aparece
      tras reiniciar sin tocar código.
- [ ] `powerStatusFeedBack`: nombres legibles por valor.
- [ ] Servicio de captura y comparación.

## Verificado con el coche el 05-10-2026 (2.1.0b2)

- [x] Bloquear y desbloquear desde HA, y lectura de las cerraduras y del
      cierre centralizado.
- [x] Maletero desde HA (abrir y cerrar) y su lectura.
- [x] Ventanillas: entreabrir (modo ventilación) y **cerrar** desde HA con el
      coche apagado; los 4 sensores de abierta.
- [x] Luz de cruce en las vistas de planta e isométrica.
- [x] Botón *Luces y claxon* a la vez.
- [x] **Luces de posición:** `positionLamp` son las luces de posición
      (entidad renombrada; antes "Luces encendidas (testigo)").
- [x] Antiniebla trasera.
- [x] Recirculación de aire.
- [x] "Encendido" con el coche arrancado, parado y en marcha.
- [x] Iconos propios de puertas, capó y maletero (abierto / cerrado).
- [x] Testigos del cuadro y pila del mando: ninguna falsa alarma.
- [x] **Desempañado delantero:** el S05 no es compatible. Retirado en la 2.0.1.
- [x] **Tapa de carga:** el S05 no informa (`chargeCoverStatus` siempre 0).
      Entidad retirada en la 2.1.0; iconos guardados en `icons/reserva/`.
- [x] **Antiniebla delantera:** el S05 no tiene. Entidad retirada en la 2.1.0.

## Verificado con coches reales antes de la 2.0.0

- [x] Arranque limpio con una cuenta española por **correo**.
- [x] Cuenta con **dos coches**: arranca y los dos muestran datos (rc5, rc10).
- [x] Reautenticación: al entrar en la app oficial con la misma cuenta, HA
      pide volver a entrar y el nuevo acceso funciona (rc10).
- [x] Asistente de Reparaciones "Configura tu vehículo" (b5).
- [x] Batería, autonomía, kilometraje, 4 presiones y avisos de neumáticos,
      temperatura y humedad interior, temperatura del climatizador.
- [x] Climatización: encender a 21 °C y apagar; ventilador.
- [x] Parpadear luces y tocar el claxon; repetir enseguida → "Espera N s".
- [x] Volante calefactado y asientos (calefacción y ventilación), lectura y
      control; encender el clima NO apaga el volante en pantalla (rc10).
- [x] Puertas (4), capó, maletero, "Alguna puerta abierta", cierre
      centralizado con el coche cerrado.
- [x] Ventanillas: los 4 sensores de abierta y el modo ventilación (rc10).
- [x] Luces de cruce y carretera, testigo de luces, intermitentes.
- [x] Matrícula (dos coches, rc10).
- [x] Imagen oficial e Imagen DEC (cambia al elegir versión / color, rc10).
- [x] Iconos `dec:` visibles (luces, intermitentes, volante) (rc10).
- [x] Vista de planta y vista isométrica: puertas, capó, maletero y
      ventanillas (rc10).
- [x] Vista interior: volante y los dos asientos, calor y ventilación (rc10).
- [x] Capacidades de un **Max** (responde con `vehicleId`).

## Después

- [ ] Horario de carga (sin verificar en el S05).
- [x] Testigos del cuadro como sensores de problema (2.1.0b1, sin verificar).
- [x] Traducción al inglés y al portugués (2.3.0b8).
- [ ] Segundo país (Portugal) cuando alguien lo pruebe.
- [x] Tarjeta propia para los paneles (2.2.0, validada en una instalación
      real). Pendiente: opciones (qué botones mostrar), elegir vista, otros
      idiomas y comprobar el tema oscuro.
- [x] Avisos al móvil desde la integración: carga, testigos, neumáticos,
      pila del mando y mantenimiento (2.3.0b1). Pendiente: descuidos (coche
      sin bloquear, ventanillas o maletero abiertos) y coche sin informar.
- [x] Mantenimiento periódico por coche, con testigo en la tarjeta (2.3.0b1).
- [ ] Plan de mantenimiento: confirmar con la comunidad las operaciones de
      cada revisión (el manual y la tabla de la comunidad difieren en algún
      detalle; se ha seguido el manual).
- [ ] Carga inteligente: iniciar / parar y horario (hace falta capturar lo
      que envía la app oficial).
