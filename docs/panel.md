# Panel DEC Deepal

Una página propia en la barra lateral de Home Assistant, donde se ve y se
configura todo lo de los coches de un vistazo.

Aparece sola al instalar la integración (**DEC Deepal** en la barra lateral)
y solo la ven los administradores. El botón **Configurar** de la integración
(Ajustes → Dispositivos y servicios → DEC Deepal) lleva también aquí, como en
Alarmo: desde la 2.5.0b2 el panel sustituye a los apartados de Configurar.
Lo único que queda fuera es añadir la cuenta y volver a iniciar sesión.

## Pestañas

### Coches

Una tarjeta por coche: foto, versión, batería, autonomía y kilómetros; el
equipamiento de su ficha del catálogo (y si la ficha está verificada), y
tres recuadros con su **engranaje**:

| Recuadro | Qué enseña | Engranaje |
|---|---|---|
| Mantenimiento | Próxima revisión y cuánto falta | Datos de la última revisión e intervalo; registrar una revisión hecha |
| ITV | Fecha límite y días que quedan | Matriculación, última ITV, fecha a mano; registrar una ITV pasada |
| Seguro | Renovación y límite para desistir | Compañía, póliza, tipo, fechas y teléfonos |

Desmarcar "Activado" en la ventana del engranaje desactiva ese apartado (y
quita sus entidades y avisos).

El botón **Apariencia** abre una ventana para elegir modelo, versión, color
y llanta, con la foto del catálogo delante: cambia con lo que se va
eligiendo y nada se guarda hasta pulsar "Guardar". Cada versión dice qué
trae, y la llanta solo se pregunta cuando la versión deja elegirla. Guardar
recarga la integración: se crean las entidades de esa versión y se quitan
las que no le tocan.

### Avisos

Una tabla por coche, con los destinos en columnas (cada móvil con la app y
la campana de Home Assistant) y un apartado plegable por cada cosa:

| Apartado | Avisos |
|---|---|
| Carga | Iniciada, interrumpida, terminada |
| Testigos | Testigos del cuadro, neumáticos, pila del mando |
| Mantenimiento | Tiempo 1, 2 y 3 (60, 30 y 15 días); kilometraje 1, 2 y 3 (5.000, 2.500 y 1.000 km); cumplido |
| ITV | Avisos 1, 2 y 3 (60, 30 y 15 días); cumplida |
| Seguro | Desistimiento 1 y 2 (30 y 15 días antes del límite) y cumplido; renovación 1 y 2 (30 y 15 días); renovado |

- **Cada aviso tiene sus destinos.** La casilla del apartado marca todos sus
  avisos de golpe; con solo algunos marcados sale una raya.
- **Lápiz:** en los avisos con plazo, cambia los días o los kilómetros. Los
  plazos son de cada coche. El aviso 1 tiene que saltar antes que el 2, y el
  2 antes que el 3; si no, no deja guardar y lo explica. "Plazos de fábrica"
  los devuelve a su valor.
- **Guardar:** los cambios de un coche se quedan en borrador hasta pulsar
  "Guardar" (guardar recarga la integración).
- **Copiar de otro coche** trae sus avisos y plazos al borrador.
- Los avisos de **renovación del seguro** son nuevos en la 2.5.0 y nacen sin
  destinos.

El apartado clásico (Configurar → Avisos al móvil) sigue funcionando: elige
los destinos por grupo y, al guardar, se los pone a todos los avisos del
grupo. Los plazos solo se cambian en el panel.

### Datos

Descargar la copia (un enlace que se abre en el navegador, también desde la
app del móvil), enviarla a un móvil, cargarla y borrar los datos guardados
de un coche, estén o no en una cuenta.

### Diagnóstico

Lo que ha pasado desde el último reinicio —cambios de señales, órdenes con
la respuesta del servidor y avisos enviados—, con filtros por coche y por
tipo; la ficha que se le aplica a cada coche, y el fichero de diagnóstico de
la cuenta.

### Ajustes

Son de la cuenta, no de un coche (con varias cuentas, una tarjeta por cuenta).

- **Control remoto con PIN:** activarlo, el PIN (el de la app oficial de
  Deepal; se comprueba al guardar) y cómo se usan las órdenes: **Directo** o
  **Desbloquear antes**, con cuánto dura el desbloqueo y si avisa. Un solo
  PIN para todos los coches de la cuenta. El panel nunca recibe el PIN
  guardado: el campo sale vacío, y vacío significa "no cambiarlo".
- **Lectura de datos:** intervalo, despertar el coche cuando haga falta, el
  enlace del manual (BEV o PHEV, según el coche) y el modo depuración.

## Tocar el panel

Como la tarjeta: JavaScript plano, sin dependencias y sin Node. El código
está en `custom_components/dec_deepal/frontend_panel/src/`, un fichero por
parte, y se une en `frontend_panel/dec-deepal-panel.js` con
`python tools/construir_tarjeta.py`.

| Fichero | Qué contiene |
|---|---|
| `00_cabecera.js` | Comentario de cabecera: qué hace el panel |
| `10_constantes.js` | Pestañas, apartados, iconos |
| `20_textos.js` | Textos por idioma. **Generado** desde `idiomas/` (sección `panel`) |
| `21_idioma.js` | Qué idioma toca y cómo se rellenan los textos |
| `30_estilos.js` | Estilos del panel y de las ventanas |
| `40_dialogo.js` | La ventana emergente de formularios y confirmaciones |
| `50_panel.js` | El panel: carga de datos, pestañas y pulsaciones |
| `60_coches.js` … `66_ajustes.js` | Una pestaña (o una ventana) por fichero |
| `90_registro.js` | Alta del panel en Home Assistant |

Cada pulsación lleva `data-action="algo"` y la atiende el método `_do_algo`.
El lado de la integración está en `panel.py`: registra la página y las
órdenes `dec_deepal/panel/...`, que llaman a lo mismo que usa Configurar.

**Idiomas:** el panel está en español e inglés. En portugués, italiano y
polaco se ve en inglés hasta que se traduzca su sección `panel` (ver
[idiomas.md](idiomas.md)).

### Pruebas

- En un navegador: `tests_tarjeta/test_panel.py`, con `banco_panel.js`
  haciendo de Home Assistant y de la integración (ver
  [tarjeta.md](tarjeta.md), "Pruebas en un navegador").
- Del lado de la integración: `tests/test_panel.py`.

Para mirarlo a mano sin Home Assistant: abrir
`tests_tarjeta/pagina_panel.html?iconos=1` y escribir en la consola
`banco.montar()`.

## Límites conocidos

- Los apartados de Configurar siguen en el código pero ya no se llega a
  ellos: se quitarán cuando el panel esté rodado.
- El historial se pierde al reiniciar Home Assistant.
- No se puede ocultar el panel de la barra lateral desde la integración (sí
  desde el perfil de cada usuario, como cualquier otro panel).
