"""Pruebas de rc4: despertar por MQTT, ubicación, matrícula y ocultación."""

from __future__ import annotations

from custom_components.dec_deepal.api.crypto import mqtt_encrypt
from custom_components.dec_deepal.api.models import VehicleInfo
from custom_components.dec_deepal.api.mqtt.client import (
    WAKE_COMMAND_CODE,
    WAKE_SERVICE_CODE,
    _service_result,
    _wake_payload,
)
from custom_components.dec_deepal.api.mqtt.topics import parse_connection_config
from custom_components.dec_deepal.debug.redact import REDACTED, redact
from custom_components.dec_deepal.telemetry import signals as s
from custom_components.dec_deepal.telemetry.location import find_location
from custom_components.dec_deepal.telemetry.state import build_state

SECRET = "0123456789abcdef"


def _config(extra_pub: list[str] | None = None) -> dict:
    return {
        "mqttConnectionInfos": [
            {
                "clusterInfos": [{"brokerUrl": "ssl://b", "brokerPort": 8883}],
                "topicInfos": [
                    {"msgType": "loginout", "pubTopics": ["$vdp/P/client/loginout/req"], "subTopics": ["$vdp/P/server/loginout/res"]},
                    {
                        "msgType": "properties",
                        "pubTopics": ["$vdp/C/properties/get/req", *(extra_pub or [])],
                        "subTopics": ["$vdp/C/properties/get/res", "$vdp/C/properties/set/res"],
                    },
                ],
            }
        ]
    }


def test_set_topic_from_config_or_derived() -> None:
    explicit = parse_connection_config(_config(["$vdp/C/properties/set/req"]))
    assert explicit.properties_set_topic == "$vdp/C/properties/set/req"
    derived = parse_connection_config(_config())
    assert derived.properties_set_topic == "$vdp/C/properties/set/req"
    # Los topics /set/ siguen sin suscribirse.
    assert all("/set/" not in topic for topic in derived.subscribe_topics)


def test_wake_payload_and_result() -> None:
    payload = _wake_payload("C", "P", SECRET, "C_1")
    assert payload["did"] == "C" and payload["b"] == {"ruid": "P"}
    from custom_components.dec_deepal.api.crypto import mqtt_decrypt

    service = mqtt_decrypt(payload["sers"], SECRET, "C_1")[0]
    assert service["service_code"] == WAKE_SERVICE_CODE
    assert service["command_code"] == WAKE_COMMAND_CODE

    answer = {"r": "C_1", "rs": mqtt_encrypt([{"code": "000000", "success": True}], SECRET, "C_1")}
    assert _service_result(answer, SECRET) == ("000000", True)
    assert _service_result({"r": "C_1"}, SECRET) is None


def test_location_search_case_insensitive() -> None:
    assert find_location({"gps": {"Lat": "40.4", "Lng": "-3.7"}}) == (40.4, -3.7)
    assert find_location({"latitude": 0, "longitude": 0}) is None  # 0,0 = sin posición
    assert find_location({"lat": 200, "lng": 1}) is None  # imposible
    assert find_location(None, {"vehicleStatus": {"lat": 41.0, "lon": 2.1}}) == (41.0, 2.1)
    state = build_state(mqtt_params={"soc": 50}, rest_raw={"x": {"Lat": 40.0, "Lng": -3.0}}, previous=None)
    assert state.get(s.LATITUDE) == 40.0 and state.get(s.LONGITUDE) == -3.0
    assert build_state(mqtt_params={"soc": 50}, rest_raw=None, previous=None).get(s.LATITUDE) is None


def test_license_plate_and_redaction() -> None:
    assert VehicleInfo.from_api({"carId": 1, "plateNumber": "1234ABC"}).license_plate == "1234ABC"
    hidden = redact({"Lat": 40.0, "LNG": -3.0, "licensePlate": "1234ABC", "plateNumber": "x", "soc": 80})
    assert hidden == {"Lat": REDACTED, "LNG": REDACTED, "licensePlate": REDACTED, "plateNumber": REDACTED, "soc": 80}
    # Las señales de ubicación también salen ocultas en diagnósticos.
    assert redact({"latitude": 1.0, "longitude": 2.0}) == {"latitude": REDACTED, "longitude": REDACTED}
