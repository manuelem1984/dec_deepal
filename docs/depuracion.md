# Depuración

Herramientas para saber qué manda el coche y por qué algo no funciona. **En
todas se ocultan los datos personales** (tokens, VIN, móvil, correo, PIN,
identificadores…), así que se pueden compartir en un Issue.

## 1. Modo depuración (interruptor)

Configurar → **Avanzado** → *Modo depuración*.

Con él activado:

- El registro interno guarda también el **cuerpo completo** de cada petición y
  respuesta (con datos ocultos). Sin él, solo guarda ruta, duración y error.
- Los mensajes de nivel **DEBUG** de la integración salen en el registro de
  Home Assistant, sin tocar `configuration.yaml`.

Desactívalo cuando termines: genera mucho registro.

> Alternativa manual, equivalente para el registro:
> ```yaml
> logger:
>   logs:
>     custom_components.dec_deepal: debug
> ```

## 2. Diagnósticos

Ficha de la integración → ⋮ → **Descargar diagnósticos**. Incluye:

| Sección | Qué es |
| --- | --- |
| `integracion` | Versión, país, opciones (sin PIN) |
| `catalogos` | Modelos cargados, iconos SVG y avisos de iconos |
| `vehiculos` | Por coche: modelo/versión/color, **señales** interpretadas y su **origen** (mqtt / rest / anterior / optimista / calculado), **MQTT en bruto**, claves **sin mapear**, **REST en bruto**, avisos |
| `registro_depuracion` | Últimos 300 eventos: peticiones HTTP, lecturas MQTT, comandos (enviado, aceptado, rechazado…), actualizaciones |
| `capturas` | Las capturas hechas con el servicio de abajo |

`mqtt_sin_mapear` es la lista de claves que el coche manda y ninguna entidad
usa todavía: **son las candidatas a nuevas entidades**.

## 3. Servicio de captura (`dec_deepal.capture_snapshot`)

Herramientas para desarrolladores → **Acciones** → *DEC Deepal: Captura de
depuración*.

| Campo | Qué es |
| --- | --- |
| Vehículo | El coche |
| Etiqueta | Nombre para reconocerla (p. ej. `A - reposo`) |
| Leer antes | Hacer una lectura justo antes (por defecto sí) |

Qué hace:

1. Guarda una foto completa del estado (señales, MQTT y REST en bruto).
2. La **compara con la captura anterior** del mismo coche y devuelve qué
   claves cambiaron y de qué valor a cuál.
3. La escribe en `/config/dec_deepal_capturas/<fecha>_<coche>.json`.

### Plan de prueba en dos capturas

Es la forma más rápida de descubrir qué significa un dato:

1. **Captura A** con el coche en reposo (cerrado con el mando, sin contacto,
   sin clima, sin cargar).
2. Haz **un solo cambio** y anótalo (bajar una ventanilla concreta, abrir con
   el mando, dar el contacto, enchufar el cable…).
3. **Captura B.**
4. Mira `diferencias_con_anterior.mqtt` y `.rest`: lo que cambió es ese dato.
5. Apunta el resultado en `docs/correlacion_endpoints_entidades.csv`.

Pendientes que se resuelven así: qué valor de `driverDoorLock` es
"bloqueado", qué significa cada valor de `powerStatusFeedBack`, si el REST
trae temperatura exterior…

## 4. Registro de Home Assistant

Mensajes útiles (con modo depuración):

| Texto | Significado |
| --- | --- |
| `POST <ruta> OK (N ms)` | Petición correcta |
| `POST <ruta> falló` | Petición con error (el motivo va detrás) |
| `lectura MQTT fallida ... se usa solo el REST` | MQTT no respondió; los datos vienen del REST |
| `Sesión renovada` | Se renovó el token |
| `Iconos: ...` | Problema con un SVG o con `icons.yaml` |
| `Catálogo con errores` | Un YAML de `countries/`, `vehicles/` o `icons/` está mal |
