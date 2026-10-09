# Arquitectura de DEC Deepal

Este documento explica **cómo está organizado el código y por qué**. Si vas a
tocar algo, empieza por aquí.

## Principios

1. **Separar lo que cambia por país, por coche o por idioma del código.**
   Países, modelos, colores, fotos e iconos viven en ficheros de datos (YAML +
   imágenes). Añadir cualquiera de ellos no requiere programar.
2. **El cliente de la API no sabe nada de Home Assistant.** `api/`,
   `telemetry/`, `registries/` y `debug/` son Python puro: se prueban con
   `pytest` y se podrían reutilizar fuera de HA.
3. **Las entidades solo conocen "señales".** No saben si un dato vino por MQTT
   o por REST, ni con qué nombre lo manda el coche.
4. **Un único punto de paso para cada cosa:** todas las peticiones HTTP pasan
   por `api/transport.py`; todos los comandos por `command_runner.py`; todos
   los iconos por `registries/icons.py`.
5. **Nunca inventar un valor.** Si un dato no llega o no se entiende, la
   entidad muestra *Desconocido*.

## Mapa de carpetas

```
custom_components/dec_deepal/
├── __init__.py            Arranque: monta todas las piezas por cuenta
├── manifest.json          Metadatos para Home Assistant / HACS
├── const.py               Constantes (claves de opciones, URLs de iconos...)
├── runtime.py             Objetos vivos de una cuenta (entry.runtime_data)
├── config_flow.py         Asistente de alta (país → método → código → coches)
├── options_flow.py        "Configurar": apariencia, PIN, avanzado
├── coordinator.py         Lecturas periódicas de UN coche
├── command_runner.py      Aduana de comandos de UN coche
├── entity.py              Entidad base (dispositivo, nombre, icono)
├── sensor.py … image.py   Una plataforma de HA por fichero
├── view_renderer.py       Monta las vistas por capas (planta, isométrica, interior, carga; Pillow)
├── frontend.py            Publica los iconos "dec:" y la tarjeta en el navegador
├── frontend_card/         Tarjeta para los paneles (custom:dec-deepal-card)
├── services.py/.yaml      Servicio de captura de depuración
├── diagnostics.py         "Descargar diagnósticos"
├── strings.json           Textos (idioma base)
├── translations/          Un JSON por idioma
│
├── api/                   Cliente de la nube (sin Home Assistant)
│   ├── transport.py       Petición HTTP genérica + errores + registro
│   ├── session.py         Tokens y caducidad (JWT)
│   ├── auth.py            Código SMS/correo, login, renovación
│   ├── account.py         Sesión compartida, renovación única y con ventana
│   ├── client.py          Lecturas: vehículos, REST condition, MQTT
│   ├── commands.py        Comandos firmados y PIN
│   ├── crypto.py          RSA, AES y firma
│   ├── endpoints.py       Rutas de los endpoints
│   ├── errors.py          Excepciones y códigos de error del servidor
│   ├── models.py          VehicleInfo, CommandResult, Capabilities
│   └── mqtt/              Cliente MQTT mínimo (protocolo, topics, lectura)
│
├── telemetry/             De datos en bruto a señales (sin Home Assistant)
│   ├── signals.py         Vocabulario de señales
│   ├── converters.py      Conversores (décimas, conector, nivel de asiento…)
│   ├── mqtt_map.py        Tabla clave MQTT → señal
│   ├── rest_map.py        Tabla ruta REST → señal
│   ├── derived.py         Señales calculadas
│   └── state.py           Fusión MQTT + REST + último valor + optimista
│
├── registries/            Cargadores de catálogos (sin Home Assistant)
│   ├── countries.py       countries/countries.yaml
│   ├── vehicles.py        vehicles/vehicles.yaml + fotos
│   ├── views.py           vista_*/<modelo>/capas.yaml (qué capas tocan)
│   └── icons.py           icons/icons.yaml + icons/svg
│
├── debug/                 Depuración (sin Home Assistant)
│   ├── redact.py          Ocultar datos personales
│   ├── recorder.py        Registro circular de eventos
│   └── capture.py         Capturas y comparación
│
├── countries/countries.yaml     ← DATOS: países y servidores
├── vehicles/vehicles.yaml       ← DATOS: modelos, versiones, colores
├── vehicles/photos/<modelo>/    ← DATOS: fotos
├── vehicles/vista_*/<modelo>/   ← DATOS: capas de cada vista (planta, isométrica, interior, carga)
├── icons/icons.yaml             ← DATOS: iconos por entidad
├── icons/svg/                   ← DATOS: iconos propios
├── icons/dec-icons.js           Script del navegador (no se toca)
└── brand/                       Logo de la integración: icon*.png (tema claro) y
                                 dark_icon*.png (tema oscuro), sin fondo
```

## Flujo de una lectura

```
Coordinador (cada N min)
   │
   ├─ account.ensure_fresh()            ¿token a punto de caducar? → renovar
   ├─ client.read_mqtt()                getConnConf → token → broker → params
   │     └─ si falla: aviso y se sigue solo con REST
   ├─ client.get_condition()            REST condition (todas las categorías)
   │
   └─ telemetry.state.build_state()
         ├─ map_mqtt(params)            claves del coche → señales
         ├─ map_rest(json)              rutas REST → señales
         ├─ fusión (MQTT base, REST rellena, REST manda en confort)
         ├─ conservar último valor (confort, clima)
         └─ apply_holds()               valores optimistas de comandos
               │
               ▼
        VehicleState  →  entidades (signal("battery_level")...)
```

## Flujo de un comando

```
Entidad (p. ej. switch volante)
   └─ runner.run("steering_wheel_heat", send, optimistic={...})
        ├─ ¿Opción B y no armado?          → error "desbloquea antes"
        ├─ ¿en espera física?              → error "espera N s"
        ├─ cola del coche (máx. 30 s)
        ├─ send()  → commands.send()
        │     ├─ serial-no/get → descifrar
        │     ├─ firmar (RSA-SHA256)  (+ rcToken si lleva PIN)
        │     └─ POST → commandId
        ├─ valor optimista en pantalla
        ├─ control-result (hasta 15 s)
        │     └─ rechazado → deshacer optimista + error claro
        └─ en segundo plano: condition-inquiry + releer a los 5 s y 25 s
```

## Varios coches en una cuenta

- Un coordinador por coche, pero **una sola conexión MQTT a la vez por
  cuenta** (candado en `api/client.py`): todas las conexiones de la cuenta usan
  el mismo identificador de cliente y el broker solo admite una; si se abren
  dos a la vez, cierra la anterior (visto con dos S05, 01-10-2026).
- La primera lectura de cada coche se hace uno detrás de otro.
- Si el broker cierra la conexión, se usa el REST de respaldo.

## Sesión y renovación

- Una **cuenta** = una entrada de configuración = una sesión, compartida por
  todos sus coches (`api/account.py`).
- Renovación **preventiva** si el JWT caduca en < 5 min; **reactiva** si el
  servidor rechaza el token (una vez, y se reintenta la petición).
- Nunca hay dos renovaciones a la vez; entre renovaciones rutinarias pasan al
  menos 30 min (como la app).
- Los tokens nuevos se guardan en `entry.data` **sin recargar** la
  integración (el listener solo recarga si cambian las opciones).
- Sin red al renovar → se reintenta más tarde; **no** se pide volver a entrar.

## Multi-país, multi-coche, multi-idioma

| Eje | Dónde se amplía | Guía |
| --- | --- | --- |
| País | `countries/countries.yaml` | [anadir-pais-vehiculo-idioma.md](anadir-pais-vehiculo-idioma.md) |
| Coche | `vehicles/vehicles.yaml` (+ mapeos si manda claves nuevas) | ídem |
| Idioma | `translations/<idioma>.json` | ídem |

## Pruebas

`tests/` cubre las partes puras (cripto, MQTT, mapeos, fusión, catálogos,
iconos, ocultación de datos). Se ejecutan en GitHub Actions (`tests.yaml`).
