# Idiomas

Todos los textos de la integración se escriben **una sola vez**, en
`custom_components/dec_deepal/idiomas/`. Lo que usa cada parte (Home
Assistant, los avisos, la tarjeta) se **genera** a partir de ahí.

```
idiomas/
├── idiomas.json   Qué idiomas hay, cuál es el base y cuáles usan los de otro
├── es.json        Español
├── en.json        Inglés (idioma base)
├── pt.json        Portugués de Portugal
├── it.json        Italiano
└── pl.json        Polaco
```

## Qué hay en cada fichero

Cuatro secciones:

| Sección | Qué contiene | Dónde se ve |
|---|---|---|
| `integracion` | Configurar, nombres de entidades, errores, acciones | Home Assistant (idioma de cada usuario) |
| `avisos` | Mensajes al móvil | Notificaciones (idioma general de Home Assistant) |
| `tarjeta` | Botones, ventanas y mensajes de la tarjeta | Paneles (idioma de cada usuario) |
| `catalogo` | Nombres del catálogo, p. ej. `operacion_brake_fluid` | Ventana de mantenimiento (idioma general) |

Lo que va entre llaves (`{vehicle}`, `{days}`, `{name}`...) es un dato que se
rellena al mostrar el texto: se deja tal cual, en el sitio que pida la frase.

## Cambiar un texto

1. Editar el texto en `idiomas/<idioma>.json`.
2. Generar: `python tools/generar_idiomas.py` (desde la raíz del repositorio;
   no hace falta instalar nada).
3. Subir **tanto** el fichero editado **como** los generados.

Si se olvida el paso 2, la prueba `tests/test_translations.py` falla y dice
qué ficheros faltan por regenerar.

## Añadir un idioma

1. Copiar `en.json` con el código del idioma (p. ej. `it.json`) y traducir.
   **No hace falta traducirlo todo:** se pueden borrar las claves que aún no
   estén traducidas; se rellenan solas con el inglés.
2. Apuntarlo en `idiomas.json` → `idiomas`, con su nombre y quién lo revisa.
3. Generar (`python tools/generar_idiomas.py`).

Para ver qué le falta a cada idioma: `python tools/generar_idiomas.py --informe`.

## Idiomas que usan los textos de otro

En `idiomas.json` → `prestados`. Hoy: catalán (`ca`), gallego (`gl`) y euskera
(`eu`) usan el español. No tienen fichero propio. El día que alguien los
traduzca, se quita la línea de `prestados` y se añade su fichero.

Cualquier otro idioma sin traducción ve los textos en el idioma **base**
(inglés), igual que hace Home Assistant con los suyos.

## Qué se genera (no editar a mano)

| Fichero | Para qué |
|---|---|
| `translations/<idioma>.json` y `strings.json` | Home Assistant |
| `textos_generados.py` | Avisos y catálogo (código Python) |
| Bloque `TEXTOS GENERADOS` de `frontend_card/dec-deepal-card.js` | Tarjeta |

El generador avisa, con un mensaje claro, si un idioma tiene una clave que no
existe en el idioma base o si los datos entre llaves no coinciden.

## Idioma y país no son lo mismo

Los plazos de la ITV o el preaviso del seguro no son textos: son **normas de
un país**. Están en `countries/countries.yaml` → `normas`, y se aplican según
el país de la cuenta, no según el idioma. Lo mismo el **módulo de ITV**: solo
existe en los países con `itv: true` (hoy, España); un usuario con Home
Assistant en italiano y cuenta española la tiene, en italiano. Ver
[anadir-pais-vehiculo-idioma.md](anadir-pais-vehiculo-idioma.md).

## Glosario

Para que varias personas traduzcan igual, cada idioma usa siempre la misma
palabra para estas piezas. Ampliar la tabla al añadir un idioma.

| Español | English | Português | Italiano | Polski |
|---|---|---|---|---|
| maletero | boot | mala | bagagliaio | bagażnik |
| capó | bonnet | capô | cofano | maska |
| llanta | wheel | jante | cerchio | felga |
| tapacubos | aero cover | tampão | copricerchio | kołpak |
| neumático | tyre | pneu | pneumatico | opona |
| ventanilla | window | janela | finestrino | szyba |
| testigo (del cuadro) | warning (light) | aviso (luz de aviso) | spia | kontrolka |
| luces de cruce / carretera / posición | dipped beam / main beam / side lights | médios / máximos / mínimos | anabbaglianti / abbaglianti / luci di posizione | światła mijania / drogowe / pozycyjne |
| mantenimiento / revisión | servicing / service | manutenção / revisão | manutenzione / tagliando | serwis / przegląd |
| ITV | ITV (roadworthiness test) | ITV (inspeção periódica) | ITV (revisione spagnola) | ITV (hiszpański przegląd techniczny) |
| desistir (del seguro) | cancel | cancelar | disdire | wypowiedzieć |
| todo riesgo con franquicia | comprehensive with excess | danos próprios com franquia | kasko con franchigia | AC z udziałem własnym |
| mando / pila del mando | key fob / key fob battery | chave / pilha da chave | chiave / batteria della chiave | kluczyk / bateria kluczyka |
| tarjeta (de los paneles) | card | cartão | scheda | karta |

## Revisores

Cada idioma tiene un revisor en `idiomas.json`. Las traducciones al inglés,
portugués, italiano y polaco las hizo el proyecto y están pendientes de
revisión por alguien nativo.

## Formato de números, ordinales y fechas

En la sección `avisos` de cada idioma hay tres claves que no son frases:
`thousands` (separador de miles), `ordinal` (cómo se escribe "2.º") y
`date_format` (formato de fecha corta). El inglés resuelve sus ordinales
(1st, 2nd, 3rd) en el código.
