# Hoja de ruta

## De 2.0.0rc5 a 2.0.0 — prueba mínima con el coche

La rc5 pasa a 2.0.0 (sin cambiar código) si esto funciona:

- [x] Climatización: encender a 21 °C y apagar (cambio inmediato en HA y
      confirmado en la app oficial).
- [x] Parpadear luces y tocar el claxon; repetir enseguida → mensaje
      "Espera N s".
- [ ] Botón *Actualizar datos del vehículo* con el coche **dormido** (varias
      horas parado): debe despertarlo y traer datos nuevos en menos de 1 min.
      Pulsarlo otra vez antes de 5 min NO debe volver a despertarlo.
- [ ] Orden con PIN (p. ej. desbloquear) con el coche dormido: debe
      despertarlo antes (hasta ~30 s) y ejecutarse.
- [x] Volante calefactado y asientos (calefacción y ventilación).
- [ ] Con el coche dormido: un comando rechazado muestra un mensaje claro y
      la entidad vuelve a su estado anterior.

- [ ] Cuenta con **dos coches**: arranca y los dos muestran datos (rc5).

Lo demás (PIN, ventanillas, cerraduras abiertas, desempañado...) puede
seguir como ⚠️ en la 2.0.0: está señalado en el CSV de correlación.

## v2.0.0 (esta reescritura) — pruebas con el coche real

Prioridad alta: todo lo que en
[correlacion_endpoints_entidades.csv](correlacion_endpoints_entidades.csv)
tiene `Verificado = No`.

- [x] Arranque limpio en HA 2026.3+ con una cuenta española por **correo**.
- [ ] Login por **SMS**: el servidor responde éxito completo
      (`success: true, code: 00000, data: "SUC"`, b5) pero el SMS no llega.
      La petición es idéntica a la de v1 (verificada en su día) y a la de
      Deepal Alternative → el fallo parece estar en el envío de Deepal o en
      que el número no pertenece a la cuenta. Pendiente: probar SMS en la app
      oficial con el mismo número.
- [x] Asistente de Reparaciones "Configura tu vehículo" (b5).
- [x] Batería, autonomía, 4 presiones, temperatura interior y del climatizador.
- [x] Imagen oficial (b2): PNG de `ca-m.iov.changanauto.com.de`.
- [x] Capacidades de un **Max** (responde con `vehicleId`).
- [ ] Capacidades de un **Pro**: confirmar que no manda `FronSeatVentilationSW`
      ni `#vent3` (pedir diagnóstico a alguien con un Pro).
- [ ] Cerraduras con el coche **abierto** (con el coche cerrado vale 0: ✅).
- [ ] Reautenticación: entrar en la app oficial con la misma cuenta y
      comprobar que HA pide volver a entrar y que funciona.
- [ ] Iconos `dec:` visibles (luces, intermitentes, volante) y selector de
      iconos mostrando los `dec:`.
- [ ] Dejar un SVG nuevo (`outside_temperature.svg`) y comprobar que aparece
      tras reiniciar sin tocar código.
- [ ] Imagen DEC cambia al elegir versión/color; imagen oficial aparece si el
      servidor manda URL.
- [ ] Vista de planta (rc6): abrir una puerta, el capó, el maletero y una
      ventanilla y comprobar que la imagen cambia; luz de cruce encendida.
- [ ] Vista isométrica (rc7): lo mismo; el capó, el maletero y las luces son
      lo que más se nota desde ese ángulo.
- [ ] Vista interior (rc9): encender volante, calefacción y ventilación de
      cada asiento y comprobar que se ilumina la zona correcta.
- [ ] Asientos (escala 1:1), volante y desempañado: lectura y control.
- [ ] Encender el clima NO apaga el volante en pantalla.
- [ ] Puertas / ventanillas / maletero con el payload nuevo (Opción A y B).
- [ ] Cerraduras: qué valor es "bloqueado" (dos capturas con el mando).
- [ ] `powerStatusFeedBack`: nombres legibles por valor.
- [ ] REST: ¿trae temperatura exterior, velocidad, km del trayecto?
- [ ] Capacidades (`function-config`): ¿responde en España? ¿acierta Pro/Max?
- [ ] Servicio de captura y comparación.

## Después

- [ ] Horario de carga (sin verificar en el S05).
- [ ] Testigos del cuadro como sensores de problema (tras capturas).
- [ ] Traducción al inglés (`en.json`) y portugués.
- [ ] Segundo país (Portugal) cuando alguien lo pruebe.
- [ ] Tarjeta Lovelace propia con foto + datos + comandos.
