"""Cliente de la nube de Deepal / Changan (sin dependencias de Home Assistant).

Este paquete habla con los servidores oficiales exactamente igual que la app
"My Changan / Deepal". Está separado del resto de la integración a propósito:

- No importa nada de ``homeassistant``: se puede probar con pytest sin Home
  Assistant y, si algún día interesa, publicar como librería independiente.
- Todo lo que depende del país (URLs, prefijo telefónico...) le llega desde
  fuera, a través de :class:`~.transport.CountryProfile`. Así, añadir un país
  no obliga a tocar este código.

Mapa del paquete:

=====================  ======================================================
Módulo                 Responsabilidad
=====================  ======================================================
``errors.py``          Excepciones y traducción de códigos de error del servidor.
``endpoints.py``       Rutas de todos los endpoints conocidos.
``crypto.py``          RSA del login, AES de MQTT, firma de comandos.
``session.py``         Tokens de la sesión y su caducidad.
``transport.py``       Petición HTTP genérica: cabeceras, errores, registro.
``auth.py``            Pedir código, iniciar sesión, renovar sesión.
``account.py``         La cuenta: sesión compartida, renovación única a la vez.
``models.py``          Datos simples: vehículo, resultado de comando, capacidades.
``client.py``          Lecturas: vehículos, estado REST, arranque de MQTT.
``commands.py``        Comandos firmados (clima, luces, PIN, etc.).
``mqtt/``              Cliente MQTT mínimo para leer la telemetría del S05.
=====================  ======================================================
"""
