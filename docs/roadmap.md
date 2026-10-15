# Hoja de ruta

## Beta 2.5.0b10 (15-10-2026) — pendiente de probar

- [ ] **Placa de matrícula** en Coches y Avisos, con la matrícula del coche
      en el formato de España (`6545 NPD`), en tema claro y oscuro y en el
      móvil (si no cabe, baja entera a la línea siguiente).
- [ ] La fila «Personas» ya no lleva la raya encima.

## Beta 2.5.0b9 (15-10-2026) — pendiente de probar

- [ ] **Usuario que no es administrador:** ve el panel con Coches y Avisos en
      solo lectura (aviso arriba), sin engranajes, Apariencia, Personas,
      casillas ni Guardar; no ve Datos, Diagnóstico ni Ajustes.
- [ ] **Personas:** elegir a quién pertenece cada coche; sale "Tuyo" en los
      coches del usuario que mira; viaja en la copia de seguridad.
- [ ] **Coche nuevo en la cuenta** (compartir otro coche con la cuenta de
      Home Assistant): en menos de 30 min aparece en Reparaciones; al
      añadirlo, sale "Configura tu vehículo". **Coche retirado** (dejar de
      compartirlo): aviso para quitarlo; sus fichas se conservan.
- [ ] **Aviso del PIN armado** (Opción B, con el aviso activado): sale en el
      idioma de Home Assistant.
- [ ] **Configurar** (Ajustes → Dispositivos y servicios) sigue abriendo el
      panel tras quitar los apartados antiguos.
- [ ] **Países nuevos:** al añadir una cuenta se elige el país (por defecto,
      el de Home Assistant). Falta que alguien de Portugal, Italia, Alemania
      o Francia lo pruebe con su cuenta.

## Beta 2.5.0b8 (15-10-2026) — pendiente de probar

- [ ] **Estado de carga (`ChrgSts`) en el S05 de España:** recorrer los
      estados y comprobar "Estado de carga" y "Cargando" en cada uno:
      sin manguera (0 → Desconectado, no carga), AC enchufado sin cargar
      (1 → Conectado AC, no carga), AC cargando (3 → Cargando AC) y, si se
      puede, DC (2 → Conectado DC, 4 → Cargando DC). El valor en bruto sale
      en el diagnóstico (`charge_state`).
- [ ] **Enchufar sin cargar no abre una carga** ni manda el aviso "carga
      iniciada"; desenchufar después no apunta una "última carga".
- [ ] **Carga terminada con la manguera puesta:** ¿qué `ChrgSts` manda?
- [ ] **Corriente de carga:** en DC enseña la de DC (antes, 0); sin cargar, 0.
- [ ] **Climatización:** no deja bajar de 18 °C; encender con el coche
      informando una temperatura fuera de rango funciona.
- [ ] **Despertar con QoS 1:** "Actualizar datos" con el coche muy dormido
      (horas parado) trae datos nuevos.

## Beta 2.5.0b7 (12-10-2026) — pendiente de probar

- [ ] **Estado de carga sin conectores:** cargando, la tarjeta y el sensor
      dicen "Cargando AC" y la vista de carga pinta el cable verde.
- [ ] Tras actualizar, "Conector AC" y "Conector DC" aparecen desactivados.
- [ ] Pendiente: saber si está enchufado sin cargar cuando el coche no manda
      el conector. Candidato: `charge.chargeConStatus` del REST (sin
      verificar qué significa cada valor).

## Beta 2.5.0b6 (12-10-2026) — pendiente de probar

- [ ] **Ventana de carga:** pulsar la franja de la batería sin enchufar,
      enchufado y cargando; en tema claro y en oscuro.
- [ ] **Cargas apuntadas:** tras una carga completa, "Última carga" enseña
      de qué porcentaje a cuál y cuánto duró; sigue ahí tras reiniciar.
- [ ] Pendiente: potencia (kW) en la ventana, si el coche da el voltaje.
- [ ] Pendiente: imágenes de la vista de carga para fondo claro (hoy se
      oscurecen con un filtro).

## Beta 2.5.0b5 (12-10-2026) — pendiente de probar

- [ ] **Tarjeta de planta:** añadir "DEC Deepal · Vista de planta" a un
      panel, en horizontal y en vertical; abrir una puerta y ver que cambia.
- [ ] Pendiente: la vista de planta solo está dibujada en plata; faltan los
      demás colores.

## Beta 2.5.0b4 (12-10-2026) — pendiente de probar

- [ ] **Idiomas nuevos:** alemán, francés, neerlandés, noruego, danés,
      griego y esloveno; y el panel, ya también en portugués, italiano y
      polaco. Cambiar el idioma del usuario y ver panel, tarjeta y entidades.
- [ ] Pendiente: revisión de cada idioma por alguien nativo.
- [ ] **Alta solo con correo:** añadir la cuenta (o volver a iniciar sesión)
      y ver que pide directamente el correo, sin elegir método.

## Beta 2.5.0b3 (11-10-2026) — pendiente de probar

- [ ] **Fichas:** pulsar Mantenimiento, ITV y Seguro abre su ventana con los
      datos del coche; registrar una revisión desde la ficha.
- [ ] **Formularios nuevos:** el recuadro verde cambia según se escribe y
      guardar deja el recuadro del coche con lo puesto.
- [ ] En el móvil: los teléfonos del seguro abren el marcador.

## Beta 2.5.0b2 (11-10-2026) — pendiente de probar

- [ ] **Configurar** (en la integración) abre el panel.
- [ ] **Apariencia:** cambiar el color o la llanta de un coche y ver que
      cambian la foto, la vista y, con otra versión, las entidades.
- [ ] **Ajustes:** cambiar el modo del PIN y el intervalo; un PIN equivocado
      se rechaza sin perder lo cambiado.
- [ ] Pendiente: quitar del código los apartados de Configurar cuando el
      panel esté rodado.

## Beta 2.5.0b1 (11-10-2026) — pendiente de probar

- [ ] **Panel:** aparece "DEC Deepal" en la barra lateral y las cuatro
      pestañas cargan con los dos coches (ordenador y app del móvil).
- [ ] **Coches:** los engranajes abren mantenimiento, ITV y seguro y guardan.
- [ ] **Avisos:** marcar destinos aviso a aviso, cambiar un plazo con el
      lápiz y guardar; comprobar que Configurar → Avisos al móvil enseña lo
      mismo por grupos.
- [ ] **Datos:** el botón Descargar baja la copia también desde el móvil.
- [ ] **Diagnóstico:** el historial enseña lo que va pasando.
- [x] Traducir el panel a portugués, italiano y polaco (2.5.0b4).

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
