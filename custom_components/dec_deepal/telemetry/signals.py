"""Vocabulario común de señales del vehículo.

Cada constante es el nombre de una señal. El valor ya viene **limpio**: en su
unidad final y con ``None`` cuando el coche no la informa (nunca un valor
inventado).

Convenciones:
- Booleanos de apertura: ``True`` = abierto / encendido.
- Cerraduras: ``True`` = **bloqueado** (ojo: la entidad de HA de tipo "lock"
  muestra "encendido" cuando está *desbloqueado*; la conversión se hace en la
  entidad, no aquí).
- Posiciones: ``front_left`` = conductor (volante a la izquierda),
  ``front_right`` = acompañante, ``rear_left`` / ``rear_right`` = traseras.

Para saber qué endpoint y qué clave alimenta cada señal, ver
``mqtt_map.py``, ``rest_map.py`` y ``docs/correlacion_endpoints_entidades.csv``.
"""

from __future__ import annotations

from typing import Final

# --- Batería y carga --------------------------------------------------------
BATTERY_LEVEL: Final = "battery_level"  # % (0-100)
RANGE_KM: Final = "range_km"  # km de autonomía eléctrica estimada
CHARGING: Final = "charging"  # bool: está cargando
AC_CONNECTOR: Final = "ac_connector"  # bool: manguera AC (Tipo 2) enchufada
DC_CONNECTOR: Final = "dc_connector"  # bool: manguera DC (CCS2) enchufada
CHARGE_CURRENT: Final = "charge_current"  # A (AC o DC, la que haya)
AC_CHARGE_CURRENT: Final = "ac_charge_current"  # A
DC_CHARGE_CURRENT: Final = "dc_charge_current"  # A
REMAINING_CHARGE_MIN: Final = "remaining_charge_min"  # minutos

# --- Estado general ---------------------------------------------------------
REPORT_TIME: Final = "report_time"  # datetime UTC del último informe del coche
CLOUD_CONNECTED: Final = "cloud_connected"  # bool: el coche respondió en la nube
ENGINE_ON: Final = "engine_on"  # bool
POWER_STATUS: Final = "power_status"  # entero en bruto (significado sin mapear)
ODOMETER_KM: Final = "odometer_km"  # km totales
MILEAGE_YESTERDAY_KM: Final = "mileage_yesterday_km"  # km (no llega en el S05)
TRIP_KM: Final = "trip_km"  # km desde el último arranque (no llega en el S05)
SPEED_KMH: Final = "speed_kmh"  # km/h (no llega en el S05 por MQTT)
PARKING_BRAKE: Final = "parking_brake"  # entero en bruto del freno de mano eléctrico

# --- Clima ------------------------------------------------------------------
INSIDE_TEMP_C: Final = "inside_temp_c"  # °C
OUTSIDE_TEMP_C: Final = "outside_temp_c"  # °C (solo REST, sin verificar)
CABIN_HUMIDITY: Final = "cabin_humidity"  # %
CLIMATE_ON: Final = "climate_on"  # bool
FAN_LEVEL: Final = "fan_level"  # entero
CLIMATE_TARGET_C: Final = "climate_target_c"  # °C

# --- Confort ----------------------------------------------------------------
SEAT_HEAT_DRIVER: Final = "seat_heat_driver"  # 0-3
SEAT_HEAT_PASSENGER: Final = "seat_heat_passenger"  # 0-3
SEAT_VENT_DRIVER: Final = "seat_vent_driver"  # 0-3
SEAT_VENT_PASSENGER: Final = "seat_vent_passenger"  # 0-3
STEERING_WHEEL_HEAT: Final = "steering_wheel_heat"  # bool
FRONT_DEFROST: Final = "front_defrost"  # bool

# --- Carrocería -------------------------------------------------------------
DOOR_FRONT_LEFT: Final = "door_front_left"  # bool abierta
DOOR_FRONT_RIGHT: Final = "door_front_right"
DOOR_REAR_LEFT: Final = "door_rear_left"
DOOR_REAR_RIGHT: Final = "door_rear_right"
TRUNK_OPEN: Final = "trunk_open"
HOOD_OPEN: Final = "hood_open"
WINDOW_FRONT_LEFT: Final = "window_front_left"  # bool abierta
WINDOW_FRONT_RIGHT: Final = "window_front_right"
WINDOW_REAR_LEFT: Final = "window_rear_left"
WINDOW_REAR_RIGHT: Final = "window_rear_right"
LOCKED_DRIVER: Final = "locked_driver"  # bool: True = bloqueada
LOCKED_PASSENGER: Final = "locked_passenger"

# --- Neumáticos -------------------------------------------------------------
TIRE_PRESSURE_FRONT_LEFT: Final = "tire_pressure_front_left"  # kPa
TIRE_PRESSURE_FRONT_RIGHT: Final = "tire_pressure_front_right"
TIRE_PRESSURE_REAR_LEFT: Final = "tire_pressure_rear_left"
TIRE_PRESSURE_REAR_RIGHT: Final = "tire_pressure_rear_right"
TIRE_ALARM_FRONT_LEFT: Final = "tire_alarm_front_left"  # bool: aviso
TIRE_ALARM_FRONT_RIGHT: Final = "tire_alarm_front_right"
TIRE_ALARM_REAR_LEFT: Final = "tire_alarm_rear_left"
TIRE_ALARM_REAR_RIGHT: Final = "tire_alarm_rear_right"

# --- Luces ------------------------------------------------------------------
HIGH_BEAM: Final = "high_beam"
LOW_BEAM: Final = "low_beam"
POSITION_LAMP: Final = "position_lamp"
INDICATOR_LEFT: Final = "indicator_left"
INDICATOR_RIGHT: Final = "indicator_right"
REAR_FOG_LAMP: Final = "rear_fog_lamp"  # bool

# --- Extras del informe MQTT (2.1.0) -----------------------------------------
KEY_BATTERY_LOW: Final = "key_battery_low"  # bool: pila del mando baja
AIR_RECIRCULATION: Final = "air_recirculation"  # bool: recirculación de aire
# Apertura de cada ventanilla. ⚠️ Escala dudosa (ver sensor.py): desactivadas.
WINDOW_OPENING_FRONT_LEFT: Final = "window_opening_front_left"
WINDOW_OPENING_FRONT_RIGHT: Final = "window_opening_front_right"
WINDOW_OPENING_REAR_LEFT: Final = "window_opening_rear_left"
WINDOW_OPENING_REAR_RIGHT: Final = "window_opening_rear_right"
# Testigos del cuadro: True = encendido. Solo los que valen 0 con el coche
# sano (ver mqtt_map.py para los descartados).
WARNING_12V_BATTERY: Final = "warning_12v_battery"
WARNING_TPMS: Final = "warning_tpms"
WARNING_ABS: Final = "warning_abs"
WARNING_AIRBAG: Final = "warning_airbag"
WARNING_BRAKE_FLUID: Final = "warning_brake_fluid"
WARNING_BRAKE: Final = "warning_brake"
WARNING_EPS: Final = "warning_eps"
WARNING_POWER_LIMIT: Final = "warning_power_limit"
WARNING_POWER_SYSTEM: Final = "warning_power_system"
WARNING_TRACTION_BATTERY_LOW: Final = "warning_traction_battery_low"
WARNING_COOLANT_TEMPERATURE: Final = "warning_coolant_temperature"

# --- Ubicación (hoy el S05 no la envía; ver location.py) --------------------
LATITUDE: Final = "latitude"  # grados
LONGITUDE: Final = "longitude"  # grados

# --- Señales calculadas (ver derived.py) ------------------------------------
CHARGE_STATUS: Final = "charge_status"  # enum: disconnected / connected_ac / ...
REMAINING_CHARGE_HHMM: Final = "remaining_charge_hhmm"  # "H:MM"
ANY_DOOR_OPEN: Final = "any_door_open"  # bool
CENTRAL_LOCKED: Final = "central_locked"  # bool: True = bloqueado
POWER_ON: Final = "power_on"  # bool: coche encendido (alimentación distinta de 0)
CHARGER_PLUGGED: Final = "charger_plugged"  # bool: manguera AC o DC enchufada
