# tests\fixtures\mock_mqtt_broker.py

"""Mock MQTT-Broker für End-to-End-Tests"""

import json
from typing import Any


class MockMQTTMessage:
    """Simuliert eine MQTT-Message"""

    def __init__(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        self.topic = topic
        self.payload = payload
        self.qos = qos
        self.retain = retain

    def as_dict(self) -> dict[str, Any]:
        try:
            return {
                "topic": self.topic,
                "payload": json.loads(self.payload),
                "qos": self.qos,
                "retain": self.retain,
            }
        except json.JSONDecodeError:
            return {
                "topic": self.topic,
                "payload": self.payload,  # Raw string
                "qos": self.qos,
                "retain": self.retain,
            }


class MockMQTTBroker:
    """Mock für MQTT-Broker - speichert alle Messages"""

    def __init__(self):
        self.messages: list[MockMQTTMessage] = []
        self.connected = False
        self.subscriptions = {}

    def connect(self, host: str, port: int, keepalive: int = 60):
        """Simuliert Verbindung"""
        self.connected = True
        return 0  # Success

    def is_connected(self):
        return self.connected

    def disconnect(self):
        """Simuliert Trennung"""
        self.connected = False

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        """Speichert Message statt zu senden"""
        if not self.connected:
            raise RuntimeError("Not connected to MQTT broker")

        msg = MockMQTTMessage(topic, payload, qos, retain)
        self.messages.append(msg)
        return 0  # Success

    def get_messages(self, topic: str | None = None) -> list[MockMQTTMessage]:
        """Hole alle Messages (optional gefiltert nach Topic)"""
        if topic:
            return [m for m in self.messages if m.topic == topic]
        return self.messages

    def get_latest(self, topic: str) -> dict[str, Any] | None:
        """Hole letzte Message für Topic als Dict"""
        messages = self.get_messages(topic)
        if messages:
            return messages[-1].as_dict()
        return None

    def clear(self):
        """Lösche alle gespeicherten Messages"""
        self.messages.clear()
