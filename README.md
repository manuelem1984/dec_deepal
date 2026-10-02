# DEC Deepal — Comunidad Deepal España

Integración **no oficial** de Home Assistant para coches Deepal. Lee el estado
del coche desde la nube oficial y permite comandos remotos (climatización,
luces, claxon, asientos, volante, y —con PIN— puertas, ventanillas y maletero).

- **Hoy:** España 🇪🇸 · Deepal S05 (2024-2025) · español.
- **Preparada para más:** países, modelos e idiomas se añaden editando
  ficheros de datos, sin programar (ver [docs/anadir-pais-vehiculo-idioma.md](docs/anadir-pais-vehiculo-idioma.md)).
- Requiere **Home Assistant 2026.3.0** o superior.
- Comunidad y soporte: [Telegram Deepal España](https://t.me/deepalespana_general).

> **Versión 2 (reescritura).** Sustituye a
> [ha-deepal-spain-dec](https://github.com/manuelem1984/ha-deepal-spain-dec).
> Es una integración nueva (dominio `dec_deepal`): se instala aparte y hay que
> configurarla de nuevo. Ver [CHANGELOG.md](CHANGELOG.md).

## ⚠️ Antes de instalar

- Uso bajo tu responsabilidad. No está afiliada a Deepal ni a Changan.
- **Una sola sesión por cuenta:** si inicias sesión en la app oficial con la
  misma cuenta, Home Assistant pierde la suya (y al revés). Usa una **cuenta
  secundaria** con el coche compartido:
  1. En la app, crea otra cuenta con otro correo.
  2. Con tu cuenta principal, comparte el coche con la nueva.
  3. Entra con la nueva y acepta el coche compartido.
  4. Si quieres puertas/ventanillas/maletero: con la cuenta nueva, intenta
     bajar una ventanilla en la app; te pedirá crear el **PIN**. Créalo.
  5. Cierra sesión en la app y usa la cuenta nueva en Home Assistant.
- Los comandos actúan sobre el coche de verdad. Úsalos solo cuando sea seguro.

## 📥 Instalación

**HACS:** ⋮ → Repositorios personalizados → `https://github.com/manuelem1984/dec_deepal`
(tipo *Integración*) → instalar **DEC Deepal** → reiniciar.

**Manual:** copia `custom_components/dec_deepal` en `config/custom_components/`
y reinicia.

## ⚙️ Configuración

Ajustes → Dispositivos y servicios → Añadir integración → **DEC Deepal** →
**correo** → código → (si hay varios) elegir coches.

> ⚠️ **Entra con el correo.** El acceso por SMS no funciona ahora mismo: Deepal
> responde que ha enviado el código, pero el SMS no llega (no es un fallo de
> la integración; ver [docs/protocolo.md](docs/protocolo.md), apartado "Login por SMS").

El coche arranca en **modo genérico** (solo datos básicos). Ve a **Ajustes →
Reparaciones → "Configura tu vehículo"** y elige modelo, versión y color: se
crearán las entidades de tu versión (asientos, volante, PIN...) y su foto.

En **Configurar**:

| Apartado | Qué permite |
| --- | --- |
| Apariencia | Modelo, versión y color → foto exacta y entidades según versión |
| Control con PIN | Activar puertas/ventanillas/maletero. El PIN se comprueba al guardar. **Opción A**: directo. **Opción B**: hay que desbloquear antes "Desbloqueo acciones con PIN" durante 10-60 s |
| Avanzado | Intervalo de lectura (5 min por defecto) y modo depuración |

## 🚗 Qué incluye

Un dispositivo por coche con: batería, autonomía, estado de carga, corrientes,
tiempo restante, kilometraje, puertas, ventanillas, cerraduras, capó,
maletero, presión y avisos de neumáticos, luces, temperatura y humedad
interior, climatización, asientos, volante, desempañado, botones de luces y
claxon, y cuatro imágenes (oficial, imagen DEC, y vista de planta y vista
isométrica con puertas, capó, maletero, ventanillas y luces según su estado).

Qué está comprobado con el coche real y qué no:
[docs/correlacion_endpoints_entidades.csv](docs/correlacion_endpoints_entidades.csv)
(columna *Verificado*).

## 🎨 Personalizar sin programar

| Qué | Dónde | Guía |
| --- | --- | --- |
| Iconos de las entidades | `icons/svg/<entidad>_<estado>.svg` | [docs/iconos.md](docs/iconos.md) |
| Modelos, versiones, colores y fotos | `vehicles/vehicles.yaml` + `vehicles/photos/` | [docs/imagenes.md](docs/imagenes.md) |
| Capas de las vistas (planta, isométrica) | `vehicles/vista_*/<modelo>/capas.yaml` | ídem |
| Países | `countries/countries.yaml` | [docs/anadir-pais-vehiculo-idioma.md](docs/anadir-pais-vehiculo-idioma.md) |
| Idiomas | `translations/<idioma>.json` | ídem |

## 🛟 Problemas frecuentes

- **No llega el SMS con el código:** ahora mismo Deepal no entrega los SMS de
  acceso. Tras pedir el código, elige *Usar otro método* y entra con el correo.
- **Pide volver a iniciar sesión:** se entró en la app con la misma cuenta.
  Usa una cuenta secundaria.
- **Un comando falla con el coche parado mucho tiempo:** el coche a veces
  rechaza comandos hasta que se usa un poco. El mensaje lo indica.
- **"Espera N s":** luces (30 s) y claxon (6 s) necesitan terminar su ciclo.
- **"PIN incorrecto o creado con otra cuenta":** crea el PIN con la cuenta que
  usa Home Assistant.
- **Para reportar un fallo:** ⋮ → *Descargar diagnósticos* (datos personales
  ocultos) y abre un Issue. Más herramientas en [docs/depuracion.md](docs/depuracion.md).

## 📚 Documentación

| Documento | Contenido |
| --- | --- |
| [docs/arquitectura.md](docs/arquitectura.md) | Cómo está organizado el código |
| [docs/protocolo.md](docs/protocolo.md) | Endpoints, cifrado, comandos, códigos de error |
| [docs/correlacion_endpoints_entidades.csv](docs/correlacion_endpoints_entidades.csv) | Qué endpoint alimenta cada entidad y si está verificado |
| [docs/iconos.md](docs/iconos.md) | Sistema de iconos |
| [docs/imagenes.md](docs/imagenes.md) | Imágenes, modelos, versiones y colores |
| [docs/depuracion.md](docs/depuracion.md) | Modo depuración, diagnósticos y capturas |
| [docs/anadir-pais-vehiculo-idioma.md](docs/anadir-pais-vehiculo-idioma.md) | Ampliar países, coches e idiomas |
| [docs/comparativa-alternativo.md](docs/comparativa-alternativo.md) | Qué se tomó de Deepal Alternative |
| [docs/roadmap.md](docs/roadmap.md) | Pendientes |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Cómo colaborar |
| [NOTICE.md](NOTICE.md) | Créditos y licencias de terceros |

## Licencia

MIT. Incluye trabajo adaptado de Deepal Alternative (MIT), ver [NOTICE.md](NOTICE.md).
