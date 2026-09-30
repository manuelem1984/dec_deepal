"""Módulo de depuración de DEC Deepal.

Herramientas para entender qué manda el coche y por qué algo no funciona,
sin exponer nunca datos personales. Guía de uso: ``docs/depuracion.md``.

==================  ==========================================================
Módulo              Qué hace
==================  ==========================================================
``redact.py``       Oculta tokens, VIN, móvil, PIN... en cualquier estructura.
``recorder.py``     Registro en memoria de los últimos intercambios con la
                    nube (HTTP, MQTT, comandos). Se ve en "Descargar
                    diagnósticos".
``capture.py``      Capturas de estado (fotos del coche en un momento) y
                    comparación entre dos capturas: qué claves cambiaron.
==================  ==========================================================

Cómo se activa: Configurar → Opciones avanzadas → **Modo depuración**. Con él
activo:

- el registro guarda también los cuerpos completos (ocultando datos
  sensibles) de peticiones y respuestas;
- los mensajes de nivel DEBUG de la integración aparecen en el registro de
  Home Assistant sin tener que tocar ``configuration.yaml``.

El servicio ``dec_deepal.capture_snapshot`` funciona siempre, con o sin modo
depuración.
"""
