"""Pruebas de api/mqtt (protocolo y topics)."""

from __future__ import annotations

import json

import pytest

from custom_components.dec_deepal.api.mqtt import protocol
from custom_components.dec_deepal.api.mqtt.topics import parse_connection_config


@pytest.mark.parametrize(
    ("length", "expected"),
    [(0, b"\x00"), (127, b"\x7f"), (128, b"\x80\x01"), (16383, b"\xff\x7f")],
)
def test_remaining_length(length: int, expected: bytes) -> None:
    assert protocol.encode_remaining_length(length) == expected


def test_parse_publish_qos1() -> None:
    topic = "$vdp/abc/properties/get/res"
    payload = json.dumps({"r": "x"}).encode()
    body = protocol.encode_string(topic) + b"\x00\x07" + payload
    parsed_topic, parsed_payload, packet_id = protocol.parse_publish(0x32, body)
    assert (parsed_topic, parsed_payload, packet_id) == (topic, {"r": "x"}, 7)


def test_parse_connack() -> None:
    assert protocol.parse_connack(0x20, b"\x00\x00") == 0
    assert protocol.parse_connack(0x30, b"\x00\x00") is None


CONFIG = {
    "mqttConnectionInfos": [
        {
            "clusterInfos": [{"brokerUrl": "ssl://broker.example", "brokerPort": 8883}],
            "topicInfos": [
                {
                    "msgType": "loginout",
                    "pubTopics": ["$vdp/PHONE/client/loginout/req"],
                    "subTopics": ["$vdp/PHONE/server/loginout/res"],
                },
                {
                    "msgType": "properties",
                    "pubTopics": ["$vdp/CAR/properties/get/req"],
                    "subTopics": ["$vdp/CAR/properties/get/res", "$vdp/CAR/commands/x"],
                },
            ],
        }
    ]
}


def test_parse_connection_config() -> None:
    connection = parse_connection_config(CONFIG)
    assert connection.host == "broker.example"
    assert connection.login_device_id == "PHONE"
    assert connection.vehicle_device_id == "CAR"
    assert "$vdp/CAR/commands/x" not in connection.subscribe_topics


def test_parse_connection_config_reports_missing() -> None:
    with pytest.raises(ValueError, match="falta"):
        parse_connection_config({"mqttConnectionInfos": [{"clusterInfos": [{}]}]})
