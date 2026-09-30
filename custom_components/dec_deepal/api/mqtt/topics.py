"""Interpretar la respuesta de ``getConnConf``: broker, puerto y topics.

Forma relevante de la respuesta (simplificada)::

    {
      "mqttConnectionInfos": [{
        "clusterInfos": [{"brokerUrl": "ssl://host", "brokerPort": 8883}],
        "topicInfos": [
          {"msgType": "loginout",
           "pubTopics": ["$vdp/<login_did>/client/loginout/req"],
           "subTopics": ["$vdp/<login_did>/server/loginout/res"]},
          {"msgType": "properties",
           "pubTopics": ["$vdp/<vehicle_did>/properties/get/req"],
           "subTopics": ["$vdp/<vehicle_did>/properties/get/res", ...]}
        ]
      }]
    }

``<login_did>`` identifica a "este teléfono" y ``<vehicle_did>`` al coche.
Verificado ✅ con el S05 en España.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MqttConnection:
    """Datos normalizados para conectarse y pedir el estado."""

    host: str
    port: int
    subscribe_topics: tuple[str, ...]
    login_topic: str  # donde se publica el "login" MQTT
    properties_topic: str  # donde se publica la petición de estado
    login_device_id: str  # did del teléfono (usuario del CONNECT)
    vehicle_device_id: str  # did del coche


def topic_device_id(topic: str) -> str | None:
    """Extrae ``<did>`` de un topic ``$vdp/<did>/...``."""
    parts = topic.split("/")
    if len(parts) > 2 and parts[0] == "$vdp":
        return parts[1]
    return None


def _first_dict(value: Any) -> dict[str, Any]:
    """Primer elemento de una lista si es un dict; si no, dict vacío."""
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def parse_connection_config(config: dict[str, Any]) -> MqttConnection:
    """Convierte la respuesta de ``getConnConf`` en :class:`MqttConnection`.

    Los topics de comandos (``/commands/``, ``/set/``) se descartan: la
    integración solo lee, nunca manda comandos por MQTT.

    Raises:
        ValueError: si falta cualquier dato imprescindible. El mensaje dice cuál.
    """
    info = _first_dict(config.get("mqttConnectionInfos"))
    if not info:
        raise ValueError("getConnConf sin 'mqttConnectionInfos'")
    cluster = _first_dict(info.get("clusterInfos"))
    if not cluster:
        raise ValueError("getConnConf sin 'clusterInfos'")

    host = str(cluster.get("brokerUrl") or "").replace("ssl://", "").strip()
    try:
        port = int(cluster.get("brokerPort") or 8883)
    except (TypeError, ValueError) as err:
        raise ValueError("Puerto del broker no válido") from err

    subscribe: list[str] = []
    login_topic = properties_topic = None
    login_did = vehicle_did = None

    for topic_info in info.get("topicInfos") or []:
        if not isinstance(topic_info, dict):
            continue
        message_type = topic_info.get("msgType")
        for topic in topic_info.get("pubTopics") or []:
            if not isinstance(topic, str):
                continue
            if message_type == "loginout" and "/loginout/req" in topic:
                login_topic = topic
                login_did = topic_device_id(topic)
            if message_type == "properties" and "/properties/get/req" in topic:
                properties_topic = topic
                vehicle_did = topic_device_id(topic)
        for topic in topic_info.get("subTopics") or []:
            if not isinstance(topic, str):
                continue
            if "/commands/" not in topic and "/set/" not in topic:
                subscribe.append(topic)
            if vehicle_did is None and "/properties/" in topic:
                vehicle_did = topic_device_id(topic)

    missing = [
        name
        for name, value in (
            ("broker", host),
            ("topics de suscripción", subscribe),
            ("topic de login", login_topic),
            ("topic de estado", properties_topic),
            ("id de dispositivo del login", login_did),
            ("id de dispositivo del coche", vehicle_did),
        )
        if not value
    ]
    if missing:
        raise ValueError("getConnConf incompleto: falta " + ", ".join(missing))

    return MqttConnection(
        host=host,
        port=port,
        subscribe_topics=tuple(sorted(set(subscribe))),
        login_topic=login_topic,  # type: ignore[arg-type]
        properties_topic=properties_topic,  # type: ignore[arg-type]
        login_device_id=login_did,  # type: ignore[arg-type]
        vehicle_device_id=vehicle_did,  # type: ignore[arg-type]
    )
