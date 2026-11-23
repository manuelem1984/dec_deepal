# Carga programada, climatización programada, diario y conexión permanente

Novedades de la **2.6.0b18**. Todo se configura con entidades del coche o
desde el panel DEC Deepal: nada necesita YAML ni automatizaciones.

> ⚠️ **Sin probar con nuestros coches.** El plan de carga y la conexión
> permanente siguen lo que comprobó Deepal Alternative 1.9 (MIT) con S05 EV
> y PHEV reales. El resto es lógica de la integración y está cubierto por
> las pruebas, pero falta verlo en un coche.

## Humedad interior

El coche no manda la humedad en %: `innerHumidity` es la **humedad
absoluta** en décimas de g/m³. Lo comprobamos con nueve lecturas reales
(30-09 a 11-10-2026): con 26-28,5 °C dentro, los valores de 34 a 157 dan
entre un 14 % y un 62 % de humedad relativa, todo creíble. Leídos como %
salían saltos imposibles, como un 97 % y, un rato después, un 11,8 %.

- **Humedad interior** (%): se calcula con la humedad absoluta y la
  temperatura interior, con la fórmula de Magnus (coeficientes de Sonntag).
- **Humedad absoluta interior** (g/m³): la que manda el coche. Viene
  desactivada; se activa en la entidad.
- `0` es "sin lectura" (módulo dormido): sale como desconocido.

## Carga programada (plan de carga)

Entidades del coche (S05 EV y PHEV):

| Entidad | Qué hace |
| --- | --- |
| **Carga programada** (interruptor) | Enciende o apaga el plan de carga del coche |
| **Inicio de la carga programada** (hora) | A qué hora empieza a cargar |
| **Fin de la carga programada** (hora) | A qué hora deja de cargar |
| **Hasta llenar** (interruptor) | Sin hora de fin: carga hasta el límite |

Y la acción **`dec_deepal.set_charge_plan`** para automatizaciones
(vehículo, activa, inicio, fin, hasta llenar; lo que no se indica no cambia).

Cómo lo hace (`charge_plan_control.py` y `telemetry/charge_plan.py`):

- El S05 no deja **modificar** un plan: para cambiarlo se borran los
  activos y se añade otro. Para apagarlo, se borra.
- Con el plan **apagado**, cambiar una hora no manda nada al coche: se
  apunta para cuando se encienda. Las horas del último plan se conservan.
- Tiene que durar al menos **30 minutos** (como en la app).
- **PHEV:** el plan que guarda la app oficial o el coche (id `1`) no se
  puede apagar ni sustituir desde fuera. Si está activo, el error lo dice:
  hay que quitarlo antes en la app o en el coche.
- La hora es la local: la zona del plan que ya tiene el coche o, si no
  tiene, la de Home Assistant.

## Climatización programada

| Entidad | Qué hace |
| --- | --- |
| **Climatización programada** (interruptor) | Activa o no |
| **Hora de la climatización** | A qué hora se enciende |
| **Días de la climatización** | Todos los días, lunes a viernes o fin de semana |
| **Temperatura programada** | 18-32 °C |
| **Batería mínima para climatizar** | Por debajo, no se enciende salvo con el coche enchufado (0 = siempre) |

Tampoco se enciende con el coche **encendido** (el servidor lo rechaza). Una
programación salta una vez al día, a su hora (la de Home Assistant). El
resultado se avisa con «Climatización programada» (apartado Testigos de la
pestaña Avisos; nace sin destinos). Se guarda en
`.storage/dec_deepal.climate_schedule`.

## Avisos nuevos (panel → Avisos)

Los tres nacen **sin destinos**: se eligen en el panel.

| Aviso | Qué hace |
| --- | --- |
| **Carga en vivo** (apartado Carga) | Mientras carga, una notificación en el móvil que se actualiza con el % y la hora a la que termina. En Android es un *Live Update* (barra y cuenta atrás); en iPhone, una notificación que se reemplaza. Al acabar, se quita. Solo va a los móviles (`notify.mobile_app_*`) |
| **Coche abierto o sin bloquear** (apartado Testigos) | Con el coche apagado, tras N minutos (10 de fábrica, se cambia con el lápiz) sin bloquear o con una puerta, ventanilla, el maletero o el capó abiertos. Avisa una vez hasta que se cierre todo. Con el control con PIN activo trae el botón **Bloquear** (solo bloquea, nunca abre) |
| **Climatización programada** (apartado Testigos) | Si se encendió, o por qué no (batería baja, coche encendido, orden rechazada) |

Ninguno es crítico.

## Diario del coche y estadísticas

La integración apunta cada **viaje** (del encendido al apagado) y cada
**carga** (con o sin cargador vinculado):

- **Viaje:** km del cuentakilómetros y % de batería gastado; con la
  capacidad de la batería del catálogo, los kWh. Un viaje de menos de 0,5 km
  no cuenta.
- **Carga:** AC (casa) o DC (rápida), % al empezar y al acabar, kWh que
  entraron en la batería y coste. La energía no incluye las pérdidas de la
  carga, así que el coste real es algo mayor.
- **Precios:** «Precio de la electricidad en casa» y «Precio de la carga
  rápida» (por kWh, en la moneda de Home Assistant). Sin precio, la carga se
  apunta sin coste.

Dónde se ve:

| Dónde | Qué |
| --- | --- |
| **Registro** de Home Assistant (y la página del coche) | Cada viaje y cada carga, con su texto («Carga en casa del 40 % al 80 % · 27,5 kWh · 4,13 EUR.») |
| **Energía cargada** (kWh, total creciente) | Sirve para las estadísticas de Home Assistant (día, semana, mes) y el panel de Energía |
| **Coste de las cargas** | Ídem, en dinero |
| **Consumo medio** (kWh/100 km) | De los últimos 10 viajes de 20 km o más |
| **Último viaje** (km) | Con sus datos y el resumen del mes como atributos |
| Acción **`dec_deepal.export_car_log`** | Devuelve el diario entero (para guardarlo o pasarlo a una hoja de cálculo) |
| Evento **`dec_deepal_car_log`** | Para automatizaciones: cada viaje o carga terminados |

Se guarda en `.storage/dec_deepal.car_log` (las últimas 300 entradas por
coche; los totales no se borran).

## Conexión permanente (experimental)

**Panel → Ajustes → Lectura de datos → Conexión permanente.** Desactivada
de fábrica.

- Mantiene abierta la conexión MQTT con el coche: sus informes llegan al
  momento, sin esperar a la siguiente lectura (cada 5 minutos). Se juntan en
  2 segundos antes de publicarse.
- **Solo con un coche MQTT en la cuenta:** el broker admite una sola
  conexión por cuenta. Con dos coches, el ajuste no hace nada.
- Despertar el coche y la lectura de siempre la **pausan** un momento.
- Si se cae, se reabre sola (esperas de 5 s a 5 min). Si la echan varias
  veces seguidas, por ejemplo otra instalación con la misma cuenta, espera 5
  minutos.
- Si da problemas, se desactiva y todo vuelve a ser como antes. El
  diagnóstico la enseña en `mqtt_permanente` (conexiones, mensajes, último
  error).
