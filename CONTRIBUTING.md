# Cómo colaborar

¡Gracias! Hay muchas formas de ayudar, y la mayoría **no requieren programar**.

## Sin programar

- **Probar con tu coche** lo marcado como `No` en
  [docs/correlacion_endpoints_entidades.csv](docs/correlacion_endpoints_entidades.csv)
  y contar el resultado (Telegram o Issue).
- **Capturas** para descubrir datos nuevos: [docs/depuracion.md](docs/depuracion.md).
- **Iconos:** un `.svg` en `icons/svg/` ([docs/iconos.md](docs/iconos.md)).
- **Fotos y colores:** [docs/imagenes.md](docs/imagenes.md).
- **Traducciones:** [docs/anadir-pais-vehiculo-idioma.md](docs/anadir-pais-vehiculo-idioma.md).

## Programando

1. Lee [docs/arquitectura.md](docs/arquitectura.md).
2. Reglas del proyecto:
   - Comentarios y documentación **en español**; nombres de código en inglés.
   - Cada módulo empieza con un docstring que explica qué hace y por qué.
   - `api/`, `telemetry/`, `registries/` y `debug/` **no importan** Home Assistant.
   - Un dato nuevo = señal (`telemetry/signals.py`) + mapeo + entidad +
     bloque en `icons/icons.yaml` + textos en `translations/` + fila en el CSV
     de correlación.
   - Nunca inventar valores: si no se entiende, `None`.
   - Todo lo que salga hacia el usuario pasa por `debug/redact.py`.
3. Pruebas: `pip install -r requirements_test.txt` y `pytest` (con la versión
   mínima de Home Assistant, `requirements_test_min.txt`). Cobertura:
   `pytest --cov` (la CI falla si baja del 74 %).
4. Estilo: `ruff check .` (reglas en `pyproject.toml`: errores, imports
   ordenados, tipos, asyncio, logging...). Un `noqa` siempre con su motivo.
5. JavaScript: `npm install` y `npm run lint:js` (ESLint sobre la tarjeta, el
   panel y los iconos generados; ver `eslint.config.mjs`).

## Publicar una versión

1. Sube `version` en `custom_components/dec_deepal/manifest.json`.
2. Añade la entrada en `CHANGELOG.md`.
3. Crea en GitHub una *release* con etiqueta `v<versión>` (p. ej. `v2.0.0b1`),
   marcada como *pre-release* si es beta. El workflow comprueba que la
   etiqueta coincide con `manifest.json`.
