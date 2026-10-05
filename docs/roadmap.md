# Hoja de ruta

## Publicada la 2.0.0 (03-10-2026) — pendiente de probar con el coche

La 2.0.0 salió con esto **sin verificar** (no rompe nada si falla; ver el
motivo en cada punto). Quien lo pruebe, que lo cuente en Telegram o en un
*issue* y se marca en
[correlacion_endpoints_entidades.csv](correlacion_endpoints_entidades.csv).

### Entidades nuevas de la 2.1.0b1 (todas sin verificar)

Solo se han visto a 0. Para cada una: provocar el estado, pulsar *Actualizar*
y mirar si la entidad cambia (si no, mandar el diagnóstico).

- [ ] **Tapa de carga:** abrir la tapa → "Abierta".
- [ ] **Antinieblas:** encender la delantera y la trasera.
- [ ] **Recirculación de aire:** activarla en el climatizador.
- [ ] **Apertura de ventanillas:** bajar una a la mitad y otra del todo y
      apuntar qué número sale (¿0-100?). Mirar también el modo ventilación.
- [ ] **Pila del mando baja** y **testigos del cuadro:** no se pueden provocar;
      se verificarán cuando a alguien se le encienda uno de verdad. Vigilar
      que ninguno aparezca en "Problema" con el coche sano.

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

### Órdenes con PIN

- [ ] Bloquear / desbloquear desde HA y lectura de cerraduras con el coche
      **abierto** (con el coche cerrado vale 0: ✅).
- [ ] Cerrar las ventanillas desde HA con el coche apagado (entreabrir para
      ventilar: ✅ aceptado por el coche en la rc3).
- [ ] Maletero desde HA: abrir y, si el coche lo permite, cerrar.

### Luces

- [ ] Luz de cruce encendida en las vistas de planta e isométrica (el sensor
      de cruce ya está ✅).
- [ ] Botón *Luces y claxon* a la vez (los otros dos botones: ✅).

### Carga

- [ ] Vista de carga: enchufado sin cargar (cable gris) y cargando (cable
      verde), en AC y, si se puede, en DC.
- [ ] Corriente de carga AC / DC y conector DC.

### Otros

- [x] **Desempañado delantero:** el S05 no es compatible (02-10-2026).
      Retirado del modelo en la 2.0.1 (`desempanado: false`).
- [ ] "Encendido" con el coche en marcha (verificado en la rc2; repetir).
- [ ] Velocidad, km del trayecto, km de ayer y temperatura exterior (entidades
      desactivadas: el S05 no parece enviarlas).
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
