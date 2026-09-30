"""Rutas de los endpoints de la nube de Deepal / Changan.

Solo las *rutas*: la parte de la URL que va después del servidor. El servidor
(``https://m.iov.changanauto.com.de`` en Europa, por ejemplo) depende del país
y se define en ``countries/countries.yaml``, no aquí.

Hay tres "pasarelas" (servidores) distintas. Cada constante indica cuál usa:

- **intl** — la principal: login, vehículos, estado y comandos.
- **ca**   — la de conexión MQTT (configuración y token del broker).
- **sda**  — la de funciones SDA (llave digital...). No se usa todavía.

La tabla completa de qué endpoint alimenta qué entidad está en
``docs/correlacion_endpoints_entidades.csv``.
"""

from __future__ import annotations

from typing import Final

# Identificadores de pasarela, usados por transport.DeepalTransport.post().
GATEWAY_INTL: Final = "intl"
GATEWAY_CA: Final = "ca"
GATEWAY_SDA: Final = "sda"

# ---------------------------------------------------------------------------
# Login y sesión (pasarela intl) — verificado ✅ en España
# ---------------------------------------------------------------------------
SEND_SMS_CODE: Final = "/intl-app-gw/intl-app-auth/api/login/send-auth-code"
SEND_EMAIL_CODE: Final = "/intl-app-gw/intl-app-auth/api/login/email-send-auth-code"
LOGIN_BY_SMS_CODE: Final = "/intl-app-gw/intl-app-auth/api/login/login-by-mobile-code"
LOGIN_BY_EMAIL_CODE: Final = "/intl-app-gw/intl-app-auth/api/login/email-code-in"
REFRESH_TOKEN: Final = "/intl-app-gw/intl-app-auth/api/auth/refresh-token"

# ---------------------------------------------------------------------------
# Vehículos y estado (pasarela intl)
# ---------------------------------------------------------------------------
#: Lista de vehículos de la cuenta — verificado ✅.
VEHICLES: Final = "/intl-app-gw/intl-app-user/api/car/vehicles"
#: Estado completo bajo demanda (REST). Mismo que usa la app para pintar su
#: pantalla. Verificado ✅ para asientos/volante/desempañado.
VEHICLE_CONDITION: Final = "/intl-app-gw/intl-app-car-condition/api/vehicle/condition"
#: Capacidades del vehículo (lista de funciones "#driverSeatVent"...). ⚠️ Opcional.
FUNCTION_CONFIG: Final = "/intl-app-gw/intl-app-user/api/vehicle/function-config"

# ---------------------------------------------------------------------------
# MQTT (pasarela ca) — verificado ✅
# ---------------------------------------------------------------------------
#: Configuración de conexión (broker, topics). Cabecera X-Tsp-User-Token.
MQTT_CONN_CONF: Final = "/user-apigw/vot-connect-conf-center/api/device/getConnConf"
#: Alternativa que usa la app si la anterior falla. ⚠️ Sin probar en España.
MQTT_CONN_CONF_FALLBACK: Final = "/user-apigw/vot-connect-conf-center/api/device/appGetCarConfFunc"
#: Token para conectarse al broker.
MQTT_AUTH_TOKEN: Final = "/user-apigw/vot-connect-auth-center/api/auth/getAuthTokenByUserId"
#: Alternativa que usa la app si la anterior falla. ⚠️ Sin probar en España.
MQTT_AUTH_TOKEN_FALLBACK: Final = "/app-apigw/vot-auth/api/token/getAuthTokenByUserId"

# ---------------------------------------------------------------------------
# Control remoto (pasarela intl). Todos firmados salvo control-result.
# ---------------------------------------------------------------------------
_CONTROL: Final = "/intl-app-gw/intl-app-car-control/api"

SERIAL_NO: Final = f"{_CONTROL}/serial-no/get"
SECURITY_CODE_STATUS: Final = f"{_CONTROL}/security-code/get-status"
CHECK_CONTROL_CODE: Final = f"{_CONTROL}/security-code/check-code"
CONTROL_RESULT: Final = f"{_CONTROL}/control/control-result"

AIR_CONDITIONER: Final = f"{_CONTROL}/control/air-conditioner"
CONDITION_INQUIRY: Final = f"{_CONTROL}/control/condition-inquiry"
FLASHING_HONKING: Final = f"{_CONTROL}/control/flashing-honking"
SEATS_HEAT: Final = f"{_CONTROL}/control/seats/heat"
SEATS_WIND: Final = f"{_CONTROL}/control/seats/wind"
STEERING_WHEEL_HEAT: Final = f"{_CONTROL}/control/steering-wheel/heat"
DEFROST: Final = f"{_CONTROL}/control/defrost"

# Con PIN (rcToken):
DOORS: Final = f"{_CONTROL}/control/doors"
WINDOWS: Final = f"{_CONTROL}/control/windows"
TRUNK: Final = f"{_CONTROL}/control/trunk"
