# Cargadores

Desde la 2.6.0b1, DEC Deepal puede unir la carga de los coches con los
cargadores de casa o del trabajo. Sirve para **cualquier cargador** que tenga
sus entidades en Home Assistant (V2C Trydan, Wallbox, Easee, Zaptec, OCPP...).
El código está en `custom_components/dec_deepal/chargers.py`.

**DEC Deepal solo bloquea y desbloquea el cargador.** Nunca inicia, pausa ni
cambia la intensidad de la carga. Con OCPP, la compañía empieza a cargar en
cuanto el cargador queda desbloqueado.

## Dónde se configura

Panel DEC Deepal → **Ajustes → Cargadores**:

- **Usar cargadores**: lo activa todo. Desactivado, nada cambia y no se toca
  ningún cargador.
- **Quién puede desbloquear** (tarjeta y notificaciones): las personas de los
  coches y los administradores, o solo los administradores.
- **Añadir cargador** abre su ventana, por bloques:
  1. **Entidades** de cada papel. Solo «Enchufado» es obligatoria.

     | Papel      | Entidad                              | En el V2C Trydan        |
     |------------|--------------------------------------|-------------------------|
     | Enchufado  | `binary_sensor` (u otro sí/no)       | Conectado               |
     | Cargando   | `binary_sensor` (u otro sí/no)       | Cargando                |
     | Potencia   | `sensor` en W o kW                   | Potencia de carga       |
     | Energía    | `sensor` en kWh o Wh                 | Energía de carga        |
     | Bloqueo    | `switch`, `lock` o `input_boolean`   | Bloquear EVSE           |

     En un interruptor se elige si «encendido» es bloqueado (el Trydan) o
     desbloqueado.
  2. **Coches que cargan aquí**: uno o varios.
  3. **Cobertura del coche aquí**: con cobertura, sin cobertura o «no lo sé».
  4. **Desbloqueo**: «sin bloqueo (solo leer)» o «desbloquear al confirmar el
     coche», con la notificación de confirmación y el recordatorio a los 5,
     15 o 60 minutos.
  5. **Bloquear solo**: al desenchufar, pasados 3, 5 o 10 minutos (si no se
     vuelve a enchufar antes), y **al terminar la carga**: con la manguera
     puesta, al 100 % (real o estimado) y sin cargar 15, 30 o 45 minutos. Una
     pausa antes del 100 % (la compañía) no bloquea. Aviso opcional.
  6. **Pérdidas** (10 % de fábrica), «ajustar con mis cargas» (enseña la
     pérdida medida y un botón para usarla) y el **precio del kWh** (fijo o
     de una entidad, como el PVPC).

La **capacidad de la batería** de cada versión está en el catálogo
(`bateria_kwh` en `vehicles/vehicles.yaml`).

## Qué pasa al enchufar

- **Con cobertura** (o «no lo sé»): se esperan hasta 5 minutos a que un coche
  diga que tiene la manguera puesta. Si lo dice, se desbloquea solo y avisa.
- **Sin cobertura**, o si ningún coche lo dice: notificación con un botón por
  coche y «No desbloquear». Al elegir el coche, se desbloquea y la carga queda
  apuntada a ese coche. Si nadie contesta, sigue bloqueado y se recuerda.
- Desbloqueado y sin cargar a los **10 minutos**: aviso «no carga».
- Al **terminar**: aviso con el % (estimado si no hay cobertura), los kWh y el
  coste.
- Al **desenchufar**: se apunta la carga y, con «Bloquear al desenchufar», se
  bloquea pasado el tiempo elegido.

Sin cobertura, el % se **estima**: % al enchufar + kWh del cargador × (1 −
pérdidas) ÷ capacidad. Cuando el coche vuelve a informar sin haberse movido,
se guarda el % real y la pérdida medida de esa carga.

## Avisos

Apartado **Cargador** de la pestaña Avisos (sale con los cargadores
activados): elegir el coche, desbloqueado por el coche, desbloqueado y no
carga, carga terminada y bloqueado al desenchufar. Si un coche no tiene
destinos ahí, se usan los de sus avisos de carga. Ninguno es crítico. Título:
`DEC Deepal <coche>` o, mientras no se sabe el coche, `DEC Deepal · <cargador>`.

Los botones de las notificaciones son de la app de Home Assistant
(`mobile_app`); el panel de notificaciones no los tiene.

## Tarjeta «DEC Deepal · Cargador»

```yaml
type: custom:dec-deepal-charger-card
charger: <id>      # opcional: si falta, el primero
```

Se añade desde el editor de paneles (el cargador se elige en una lista). Pinta
el cargador con un anillo de color: naranja esperando confirmación (los
coches son botones), verde cargando (con kW, kWh, € y, sin cobertura, % y
tiempo estimados), gris libre (resumen del mes). El candado bloquea o
desbloquea a mano (con confirmación) y «Cargas» abre el historial.

La **ventana de carga** de la tarjeta del coche enseña también el cargador en
el que carga y, sin cobertura, el % estimado. Con «Mostrar el % estimado en la
tarjeta del coche» (Ajustes → Cargadores), la **tarjeta del coche** enseña
«≈ %» con la etiqueta «estimado» mientras el coche no informa.

Tocar la notificación de elegir el coche abre el panel en la ventana de
elegir (`/dec-deepal-panel?elegir=<cargador>`); en el iPhone, los botones
salen al mantenerla pulsada.

## Órdenes (WebSocket)

- Panel (administradores): `dec_deepal/panel/set_chargers`, `save_charger`,
  `delete_charger`.
- Tarjeta: `dec_deepal/chargers/subscribe` (estado y cambios),
  `dec_deepal/chargers/state`, `dec_deepal/chargers/confirm` y
  `dec_deepal/chargers/lock` (estas dos comprueban el permiso).

Todo se guarda en `.storage/dec_deepal.chargers`.
