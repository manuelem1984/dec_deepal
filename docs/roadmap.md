# Hoja de ruta

## v2.0.0 (esta reescritura) — pruebas con el coche real

Prioridad alta: todo lo que en
[correlacion_endpoints_entidades.csv](correlacion_endpoints_entidades.csv)
tiene `Verificado = No`.

- [x] Arranque limpio en HA 2026.3+ con una cuenta española por **correo**.
- [ ] Login por **SMS**: en la primera prueba el SMS no llegó (el servidor
      aceptó la petición). Reintentar con el nuevo "Reenviar el código" y
      mirar el registro (`Deepal aceptó la petición de código por sms…`).
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
