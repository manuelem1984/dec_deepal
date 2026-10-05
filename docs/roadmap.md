# Hoja de ruta

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
- [ ] Login por **SMS**: el servidor responde éxito completo
      (`success: true, code: 00000, data: "SUC"`) pero el SMS no llega. La
      petición es idéntica a la de v1 y a la de Deepal Alternative → el fallo
      parece estar en el envío de Deepal. Pendiente: probar SMS en la app
      oficial con el mismo número.
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
- [ ] Traducción al inglés (`en.json`) y portugués.
- [ ] Segundo país (Portugal) cuando alguien lo pruebe.
- [ ] Tarjeta Lovelace propia con foto + datos + comandos.
