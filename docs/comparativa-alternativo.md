# Qué se tomó de Deepal Alternative (y qué no)

Análisis del proyecto [Sunek0/ha-deepal-alternative](https://github.com/Sunek0/ha-deepal-alternative)
(v1.3.1, septiembre 2026, licencia MIT) hecho antes de reescribir DEC Deepal.
Atribución: [NOTICE.md](../NOTICE.md).

## Adoptado

| Qué | Por qué | Dónde |
| --- | --- | --- |
| Payload de **puertas** `{"command":"lock","open":…}` | El nuestro (`"doors"`/`"lock"`) nunca se verificó; el suyo lo usan en producción | `api/commands.py` |
| Payload de **ventanillas** `{"command":"window","open":…,"openType":10}` (todas) | El nuestro por ventanilla era una suposición | `api/commands.py`, `cover.py` |
| `rcToken` **solo** en comandos con PIN | Evita `COMMON_1_1_01_008` tras usar puertas/ventanillas | `api/commands.py` |
| Escala de asientos MQTT **1:1**, `6` = dormido | Verificado por ellos en un S05; el ÷2 anterior venía de otro material | `telemetry/converters.py` |
| **Conservar el último valor** de confort/clima si no llega | Evita que encender el clima "apague" el volante en pantalla | `telemetry/state.py` |
| REST no pisa MQTT si su informe es **más antiguo** | No sustituir un dato nuevo por uno viejo | `telemetry/state.py` |
| Petición REST con **todas** las categorías | Permite descubrir datos (temperatura exterior…) sin coste | `api/client.py` |
| Renovación con **JWT**, ventana de 30 min, **una a la vez** | Evita tormentas de renovaciones con varios coches | `api/account.py` |
| Reintento de MQTT si la pasarela CA rechaza el token | Menos lecturas fallidas | `api/client.py` |
| **Respaldo REST** si MQTT falla | Datos aunque el broker no responda | `coordinator.py` |
| **Espera física** luces 30 s / claxon 6 s con mensaje | Mejor que el rechazo críptico del coche | `command_runner.py` |
| Mantener el valor optimista **120 s** y **deshacerlo** si el coche rechaza | Evita rebotes y estados falsos | `coordinator.py`, `command_runner.py` |
| Códigos de error de PIN y firma | Mensajes claros | `api/errors.py` |
| Pista de versión Pro/Max por capacidades | Foto y entidades correctas sin configurar | `api/models.py`, `__init__.py` |
| Sensor "Tiempo de carga (H:MM)" | Útil en paneles | `telemetry/derived.py` |

## No adoptado (por ahora)

| Qué | Motivo |
| --- | --- |
| MQTT 5.0 | Nuestro MQTT 3.1.1 está verificado en España; el broker acepta ambos |
| SDK aparte con `httpx` y `pydantic` | Usamos el `aiohttp` de HA y `dataclasses`: sin dependencias extra |
| Límite de carga y horario de carga | El S05 no admite límite; el horario está sin verificar. Candidato para más adelante |
| Plataforma SDA / E07 / cuentas chinas | Fuera del alcance (España + S05) |
| Firma con `encodebytes` (con saltos de línea) | Nuestra firma con `b64encode` está verificada ✅ |

## Lo propio de DEC Deepal

- Catálogos editables sin código: países, vehículos/colores/fotos, iconos.
- Dos imágenes separadas (oficial y foto DEC).
- Opción A / Opción B (armado) para comandos con PIN.
- Módulo de depuración con capturas y comparación.
- Archivo de correlación endpoints ↔ entidades.
