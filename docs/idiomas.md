# Idiomas

Todos los textos de la integración se escriben **una sola vez**, en
`custom_components/dec_deepal/idiomas/`. Lo que usa cada parte (Home
Assistant, los avisos, la tarjeta) se **genera** a partir de ahí.

```
idiomas/
├── idiomas.json   Qué idiomas hay, cuál es el base y cuáles usan los de otro
├── es.json        Español
├── en.json        Inglés (idioma base)
└── pt.json        Portugués de Portugal
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
el país de la cuenta, no según el idioma. Ver
[anadir-pais-vehiculo-idioma.md](anadir-pais-vehiculo-idioma.md).

## Glosario

Para que varias personas traduzcan igual, cada idioma usa siempre la misma
palabra para estas piezas. Ampliar la tabla al añadir un idioma.

| Español | English | Português |
|---|---|---|
| maletero | boot | mala |
| capó | bonnet | capô |
| llanta | wheel | jante |
| tapacubos | aero cover | tampão |
| neumático | tyre | pneu |
| ventanilla | window | janela |
| testigo (del cuadro) | warning (light) | aviso (luz de aviso) |
| luces de cruce / carretera / posición | dipped beam / main beam / side lights | médios / máximos / mínimos |
| mantenimiento / revisión | servicing / service | manutenção / revisão |
| ITV | ITV (roadworthiness test) | ITV (inspeção periódica) |
| desistir (del seguro) | cancel | cancelar |
| todo riesgo con franquicia | comprehensive with excess | danos próprios com franquia |
| mando / pila del mando | key fob / key fob battery | chave / pilha da chave |
| tarjeta (de los paneles) | card | cartão |

## Revisores

Cada idioma tiene un revisor en `idiomas.json`. Las traducciones al inglés y
al portugués las hizo el proyecto y están pendientes de revisión por alguien
nativo.
