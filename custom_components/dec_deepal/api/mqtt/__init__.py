"""Cliente MQTT mínimo para leer la telemetría de los coches "MQTT" (S05).

No se usa ninguna librería MQTT externa: el intercambio es corto y siempre el
mismo, así que basta con construir a mano los pocos paquetes necesarios.

Cómo funciona una lectura (verificado ✅ con un S05 de España):

1. Por REST (pasarela CA) se piden la configuración del broker
   (``getConnConf``) y un token de acceso (``getAuthTokenByUserId``).
2. Se abre una conexión TLS al broker y se envía CONNECT (usuario = id de
   dispositivo, contraseña = token).
3. Se suscribe a los topics de respuesta.
4. Se publica un "login" MQTT; el broker responde con una ``secretKey``.
5. Con esa clave se cifra y publica la petición ``car_condition``.
6. El coche responde (cifrado) con un diccionario plano de parámetros
   (``soc``, ``driverDoor``, ``lfTyrePressure``...). Eso es lo que se devuelve.

Módulos:

- ``protocol.py`` — construir y leer paquetes MQTT 3.1.1.
- ``topics.py``   — sacar broker y topics de la respuesta de ``getConnConf``.
- ``client.py``   — la lectura completa descrita arriba.
"""
