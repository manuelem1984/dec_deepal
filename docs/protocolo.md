# Protocolo de la nube de Deepal

Cómo habla la integración con los servidores oficiales. Reconstruido por
ingeniería inversa de la app "My Changan / Deepal" y contrastado con el
proyecto anterior y con Deepal Alternative. Qué endpoint alimenta cada
entidad: [correlacion_endpoints_entidades.csv](correlacion_endpoints_entidades.csv).

Leyenda: ✅ verificado con el coche real · ⚠️ implementado sin verificar.

## Servidores (entorno `eu`)

| Pasarela | URL | Uso |
| --- | --- | --- |
| intl | `https://m.iov.changanauto.com.de` | Login, vehículos, estado REST, comandos |
| ca | `https://ca-m.iov.changanauto.com.de` | Configuración y token MQTT |
| sda | `https://sda-m.iov.changanauto.com.de` | Llave digital (no se usa) |

Cabeceras: las de la app Android (`appid: ca`, `apptype: Android`,
`selectcountry: ES`...), ver `api/transport.py`. Autorización:
`authorization: <access>|<cac>`. En la pasarela CA además
`X-Tsp-User-Token: <access>` (✅ con el `cacToken` no funciona).

Los errores llegan con HTTP 200 y `{"success": false, "code", "msg"}`.

## Login por SMS ⚠️ no llega el código

Desde septiembre de 2026 (probado con la b1-b5), `send-auth-code` responde
éxito completo pero el SMS no llega al móvil (con el teléfono bien asociado a
la cuenta):

```json
{"success": true, "code": "00000", "msg": "success", "data": "SUC"}
```

Descartado en la integración:

- La petición es **idéntica** a la de la v1 (con la que el SMS estaba
  verificado) y a la de Deepal Alternative (endpoint, cuerpo y cabeceras,
  incluidas `appversion V1.12.0` y la ausencia de `authorization`).
- Deepal Alternative solo prueba su SMS contra un servidor simulado: no hay
  constancia de que les llegue.
- Un número, prefijo o cifrado incorrecto produce `success: false`, no `SUC`.

Conclusión: fallo de entrega del lado de Deepal. El asistente recomienda el
correo y lo propone por defecto. Pendiente: comprobar si en la app oficial
llega el SMS (si llegara, capturar su tráfico para comparar).

## Login ✅

| Paso | Endpoint | Cuerpo |
| --- | --- | --- |
| Código SMS | `/intl-app-gw/intl-app-auth/api/login/send-auth-code` | `countryCode`, `mobile` (RSA) |
| Código correo | `…/login/email-send-auth-code` | `type: "0"`, `email` (RSA) |
| Entrar SMS | `…/login/login-by-mobile-code` | `authCode`, `countryCode`, `mobile` (RSA), `salesCountry`, `pubKey` |
| Entrar correo | `…/login/email-code-in` | `authCode`, `salesCountry`, `email` (RSA), `pubKey` |
| Renovar | `/intl-app-gw/intl-app-auth/api/auth/refresh-token` | `refreshToken` |

Respuesta: `token`, `refreshToken`, `cacToken`, `userId`, `caUserId`,
`cacUserId`. `pubKey` es la mitad pública de un par RSA-1024 que generamos:
la privada firma los comandos.

## Lectura

### Vehículos ✅

`POST /intl-app-gw/intl-app-user/api/car/vehicles` → lista con `carId`, `vin`,
`modelName`, `protocolType` (`MQTT` en el S05), URL de imagen…

### REST condition

`POST /intl-app-gw/intl-app-car-condition/api/vehicle/condition`

```json
{"vechileCriteria": {"seat":"1","door":"1","hvac":"1","charge":"1","lamp":"1",
 "window":"1","tire":"1","vehicleStatus":"1","fuel":"1"}, "vehicleId": "<carId>"}
```

(`vechileCriteria` es una errata del servidor.) Respuesta anidada por
categorías. Temperaturas en **décimas**; presión en kPa; `door.doors` y
`window.windows` son listas de 4.

### Capacidades (`function-config`) ✅

`POST /intl-app-gw/intl-app-user/api/vehicle/function-config` con
`{"vehicleId": "<carId>"}` (con `carId` responde `COMMON_1_1_01_005`) →
`{"confList": [...]}`. Códigos vistos en un S05 **Max** de España, entre otros:
`#heat3`, `#vent3`, `FronSeatHeaterSW`, `FronSeatVentilationSW`,
`FronSeatVentilationLevel`, `DriverSeatVentilatorSW`, `SteeringWheelSW`,
`DoorLock`, `WindowSW`, `WindowSlightlyDown`, `TrunkUnlock`, `TrunkAutoSW`,
`FlashHonk`, `ACSW`, `ACTemperature`, `BatteryChargingPlan`,
`#batteryHeatingSchedule`, `#lockControl`, `#windowControl`, `#trunkControl`.
Se usan solo para **proponer** la versión (ventilación → Max).

### MQTT ✅

1. `getConnConf` (pasarela CA) → broker, puerto, topics.
2. `getAuthTokenByUserId` (pasarela CA) → `authToken`.
3. TLS al broker: CONNECT (usuario = id de dispositivo del login), SUBSCRIBE.
4. PUBLISH `loginout` → respuesta con `secretKey`.
5. PUBLISH `properties/get/req` con `car_condition` cifrado
   (AES-CBC, IV = MD5(requestId), base64(gzip(JSON))).
6. Respuesta cifrada con un diccionario plano de ~110 claves.

Servicios aceptados: `car_condition`, `BDC_Service`, `BMS_Service`,
`OBC_Service`, `THU_Service`. Otros se guardan como "desconocidos".

## Comandos

Todos bajo `/intl-app-gw/intl-app-car-control/api/`:

1. `serial-no/get` (`type: "1"`) → nº de serie cifrado con nuestra `pubKey`.
2. Descifrar con la clave privada.
3. Payload + `seriralNo` (sic) + `vehicleId` (+ `rcToken` si lleva PIN).
4. Firma: claves ordenadas sin `sign`/`class`/`command`, `k=v&k=v`,
   booleanos en minúscula, RSA-SHA256 PKCS#1 v1.5, base64 → campo `sign`.
5. POST → `commandId`.
6. `control/control-result` (sin firma) → `resultCode`:

| `resultCode` | Significado |
| --- | --- |
| `0`, `1201` | Éxito |
| `1015` | Ya estaba así |
| `-1`, `-2` | Rechazado |
| `-100` / ausente | Pendiente |
| otro | Rechazado (por prudencia) |

Un error con `TBOX_` suele indicar coche dormido u ocupado.

| Comando | Endpoint | Payload | Estado |
| --- | --- | --- | --- |
| Clima | `control/air-conditioner` | `command: air, enabled, targetTemp (décimas), runTime: 30, windMode: 1` | ✅ |
| Datos frescos | `control/condition-inquiry` | `command: COMMAND_GET_NEW_CONDITION` | ✅ |
| Luces / claxon / ambos | `control/flashing-honking` | `command: flash_bee, type: 1/2/3` | ✅ / ✅ / ⚠️ |
| Asientos calefacción | `control/seats/heat` | `command: seats_heat, masterSwitch/masterLevel` o `copilotSwitch/copilotLevel` | ⚠️ |
| Asientos ventilación | `control/seats/wind` | `command: seats_wind, …` | ⚠️ |
| Volante | `control/steering-wheel/heat` | `command: steering_wheel_heating, open` | ⚠️ |
| Desempañado | `control/defrost` | `command: defrost, enabled` | ⚠️ |
| Puertas (PIN) | `control/doors` | `command: lock, open` (`open: true` = desbloquear) | ⚠️ |
| Ventanillas (PIN) | `control/windows` | `command: window, open, openType: 10` (todas) | ⚠️ |
| Maletero (PIN) | `control/trunk` | `command: trunk, open` | ⚠️ |

Asientos: para **apagar**, `switch: 0` **sin** nivel (un nivel 0 lo rechaza el
servidor con `COMMON_1_1_01_005`).

### PIN de control remoto

1. `security-code/get-status` → `retryQuantity` (si es 0, no se intenta).
2. `security-code/check-code` con `safeCode` (PIN cifrado RSA) → `rcToken`.
3. El `rcToken` se reutiliza; si el servidor lo rechaza, se pide otro una vez.
4. **Solo** puertas, ventanillas y maletero llevan `rcToken`. Ponerlo en los
   demás provoca `COMMON_1_1_01_008`.

## Códigos de error conocidos

| Código | Significado | Qué hace la integración |
| --- | --- | --- |
| `APP_1_1_02_003…006`, `CAC_1_1_01_045`, `46000` | Sesión expulsada | Renovar; si falla, pedir volver a entrar |
| `APIGW_-1_7_01_004`, `APIGW_1_7_02_001` | Token de la pasarela CA caducado | Renovar y reintentar MQTT |
| `CAC_1_1_01_033` | Demasiados códigos pedidos | Avisar y esperar |
| `HW_1_1_01_047` | Demasiados intentos de PIN | Avisar |
| `HW_1_1_01_073` / `074` | PIN caducado / no creado | Avisar: revisar en la app |
| `COMMON_1_1_01_001` en `serial-no/get` | Clave de firma no registrada | Pedir volver a iniciar sesión |

## Claves MQTT sin interpretar (candidatas)

Llegan del S05 pero aún no se sabe qué significan. Usa las capturas
([depuracion.md](depuracion.md)) para descubrirlas.

- **Carga:** `chargeCoverStatus`, `chargeSystemStatus`, `powerBatteryStatus`, `powerBatteryBreakStatus`.
- **Clima:** `airRecycleStatus`, `airPurifierStatus`.
- **Carrocería:** `skyWindowDegree`, `spoilerPosition`, `spoilerMovement`.
- **Llave y accesos:** `keyLowPower`, `keylessEntryStartSystemStatus`, `unlockKeyDrivingStatus`, `reverseRadarStatus`.
- **Luces:** `frontFoglamp`, `rearFoglamp`, `brakeLightStatus`.
- **Testigos del cuadro:** `absLightStatus`, `airBagLightStatus`, `batt12VLightStatus`, `brakeFluidLightStatus`, `epbLightStatus`, `epsLightStatus`, `espLightStatus`, `tpmsLightStatus`, `powerLimitLightStatus`… (con el coche recién circulando, `aebLightStatus`, `accStatus`, `ldwStatus` aparecieron a 1: probablemente "sistema activo", no avería).
- **No sirven:** `…WindowDegree` (movimiento del cristal, vuelve a 0 al parar).
- **No llegan nunca en el S05 por MQTT:** temperatura exterior, velocidad, km de ayer, km del trayecto, temperatura de neumáticos.
