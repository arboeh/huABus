# huawei_solar_modbus_mqtt/bridge/mqtt_client.py

"""
MQTT Client Manager für Home Assistant Integration.

Verwaltet die persistente MQTT-Verbindung zum Broker und implementiert:
- Home Assistant MQTT Discovery (automatische Entity-Erstellung)
- Sensor-Daten Publishing (JSON-Payload mit allen Messwerten)
- Status Publishing (online/offline für Binary Sensor)
- Last Will Testament (LWT) für automatisches offline bei Verbindungsabbruch
- Connection State Tracking zur Vermeidung von "not connected" Errors

Die Verbindung wird einmalig beim Start erstellt und bleibt für die gesamte
Laufzeit bestehen (persistent), nur Modbus reconnected bei Fehlern.
"""

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from .config.sensors_mqtt import NUMERIC_SENSORS, TEXT_SENSORS

logger = logging.getLogger("huawei.mqtt")

# Globale MQTT Client Instanz (Singleton-Pattern)
_mqtt_client: mqtt.Client | None = None

# Connection State Flag - verhindert Publishing wenn nicht verbunden
_is_connected = False

# Thread-safe event for connection establishment (paho callbacks run in their own thread)
_connected_event = threading.Event()


def _on_connect(client, userdata, flags, rc, properties=None):
    """Callback when MQTT connection is established."""
    global _is_connected
    if rc == 0:
        _is_connected = True
        _connected_event.set()
    else:
        logger.error(f"❌ MQTT connection failed: {rc}")


def _on_disconnect(client, userdata, flags, rc=0, properties=None):
    """Callback when MQTT connection is lost."""
    global _is_connected
    _is_connected = False
    _connected_event.clear()
    if rc != 0:
        logger.warning(f"⚠️ MQTT unexpected disconnect: {rc}")


def _get_mqtt_client() -> mqtt.Client:
    """Create or return existing MQTT client (Singleton)."""
    global _mqtt_client
    if _mqtt_client is not None:
        return _mqtt_client

    client = mqtt.Client(CallbackAPIVersion.VERSION2)

    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect

    user = os.environ.get("HUAWEI_MQTT_USER")
    password = os.environ.get("HUAWEI_MQTT_PASSWORD")

    if user and password:
        client.username_pw_set(user, password)
        logger.debug(f"MQTT auth configured for {user}")

    topic = os.environ.get("HUAWEI_MQTT_TOPIC")
    if topic:
        client.will_set(f"{topic}/status", "offline", qos=1, retain=True)
        logger.debug(f"LWT set: {topic}/status")

    _mqtt_client = client
    return client


async def _wait_for_publish(result, timeout: float) -> None:
    """Offload blocking wait_for_publish to executor."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, result.wait_for_publish, timeout)


async def connect_mqtt() -> None:
    """Connect to MQTT broker and wait for connection via thread-safe event."""
    client = _get_mqtt_client()
    broker = os.environ.get("HUAWEI_MQTT_HOST")
    port = int(os.environ.get("HUAWEI_MQTT_PORT", "1883"))

    if not broker:
        logger.error("🚨 MQTT broker not configured")
        raise RuntimeError("MQTT broker not configured")

    logger.debug(f"Connecting MQTT to {broker}:{port}")
    _connected_event.clear()
    client.connect(broker, port, 60)
    client.loop_start()

    try:
        loop = asyncio.get_event_loop()
        connected = await loop.run_in_executor(None, _connected_event.wait, 10.0)
        if not connected:
            raise ConnectionError("MQTT connection timeout after 10s")
    except asyncio.CancelledError:
        client.loop_stop()
        raise

    logger.debug("MQTT connection stable")


async def disconnect_mqtt() -> None:
    """Disconnect MQTT client cleanly, offloading blocking calls to executor."""
    global _mqtt_client, _is_connected
    if _mqtt_client is None:
        return

    try:
        topic = os.environ.get("HUAWEI_MQTT_TOPIC")
        if topic and _is_connected:
            result = _mqtt_client.publish(f"{topic}/status", "offline", qos=1, retain=True)
            await _wait_for_publish(result, 1.0)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _mqtt_client.loop_stop)
        await loop.run_in_executor(None, _mqtt_client.disconnect)
        logger.info("🔌 MQTT disconnected")
    except Exception as e:
        logger.error(f"❌ MQTT disconnect error: {e}")
    finally:
        _mqtt_client = None
        _is_connected = False


def _build_sensor_config(sensor: dict[str, Any], base_topic: str, device_config: dict[str, Any]) -> dict[str, Any]:
    """Create MQTT Discovery config for a single sensor."""
    config = {
        "name": sensor["name"],
        "unique_id": f"huawei_solar_{sensor['key']}",
        "state_topic": base_topic,
        "value_template": sensor.get(
            "value_template",
            f"{{{{ value_json.{sensor['key']} }}}}",
        ),
        "availability_topic": f"{base_topic}/status",
        "payload_available": "online",
        "payload_not_available": "offline",
        "device": device_config,
    }

    for key in [
        "unit_of_measurement",
        "device_class",
        "state_class",
        "icon",
        "entity_category",
    ]:
        if key in sensor:
            config[key] = sensor[key]

    if sensor.get("enabled", True) is False:
        config["enabled_by_default"] = False

    return config


def _load_numeric_sensors() -> list[dict[str, Any]]:
    return NUMERIC_SENSORS


def _load_text_sensors() -> list[dict[str, Any]]:
    return TEXT_SENSORS


async def _publish_sensor_configs(
    client: mqtt.Client,
    base_topic: str,
    sensors: list[dict[str, Any]],
    device_config: dict[str, Any],
) -> int:
    """Publish MQTT Discovery configs for a list of sensors."""
    count = 0
    for sensor in sensors:
        config = _build_sensor_config(sensor, base_topic, device_config)
        topic = f"homeassistant/sensor/huawei_solar/{sensor['key']}/config"
        result = client.publish(topic, json.dumps(config), qos=1, retain=True)
        await _wait_for_publish(result, 1.0)
        count += 1
    return count


async def publish_discovery_configs(base_topic: str) -> None:
    """Publish all MQTT Discovery configs (once at startup)."""
    if not _is_connected:
        logger.warning("⚠️ MQTT not connected, skipping discovery")
        return

    logger.info("📊 Publishing MQTT Discovery")
    client = _get_mqtt_client()

    device_config = {
        "identifiers": ["huawei_solar_modbus"],
        "name": "Huawei Solar Inverter",
        "model": "SUN2000",
        "manufacturer": "Huawei",
    }

    sensors = _load_numeric_sensors()
    count = await _publish_sensor_configs(client, base_topic, sensors, device_config)

    text_sensors = _load_text_sensors()
    text_count = await _publish_sensor_configs(client, base_topic, text_sensors, device_config)

    await _publish_status_sensor(client, base_topic, device_config)
    logger.info(f"✅ Discovery complete: {count + text_count + 1} entities")


async def _publish_status_sensor(client: mqtt.Client, base_topic: str, device_config: dict[str, Any]) -> None:
    """Publish Binary Sensor for connectivity status."""
    config = {
        "name": "Huawei Solar Status",
        "unique_id": "huawei_solar_status",
        "state_topic": f"{base_topic}/status",
        "payload_on": "online",
        "payload_off": "offline",
        "device_class": "connectivity",
        "device": device_config,
    }
    result = client.publish(
        "homeassistant/binary_sensor/huawei_solar/status/config",
        json.dumps(config),
        qos=1,
        retain=True,
    )
    await _wait_for_publish(result, 1.0)


async def publish_data(data: dict[str, Any], topic: str) -> None:
    """Publish sensor data to MQTT."""
    if not _is_connected:
        logger.warning("⚠️ MQTT not connected, cannot publish data")
        raise ConnectionError("🚨 MQTT not connected")

    client = _get_mqtt_client()
    data["last_update"] = int(time.time())

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Publishing: Solar={data.get('power_active', 'N/A')}W, "
            f"Grid={data.get('meter_power_active', 'N/A')}W, "
            f"Battery={data.get('battery_power', 'N/A')}W"
        )

    try:
        result = client.publish(topic, json.dumps(data), qos=1, retain=True)
        await _wait_for_publish(result, 2.0)
        logger.debug(f"Data published: {len(data)} keys")
    except Exception as e:
        logger.error(f"❌ MQTT publish failed: {e}")
        raise


async def publish_status(status: str, topic: str) -> None:
    """Publish online/offline status to MQTT."""
    if not _is_connected:
        logger.debug(f"MQTT not connected, cannot publish status '{status}'")
        return

    client = _get_mqtt_client()
    status_topic = f"{topic}/status"

    try:
        result = client.publish(status_topic, status, qos=1, retain=True)
        await _wait_for_publish(result, 1.0)
        logger.debug(f"Status: '{status}' → {status_topic}")
    except Exception as e:
        logger.error(f"❌ Status publish failed: {e}")
