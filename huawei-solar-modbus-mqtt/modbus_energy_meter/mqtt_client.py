# modbus_energy_meter/mqtt_client.py
import logging
import os
import json
import time
from typing import Dict, Any, List, Optional

import paho.mqtt.client as mqtt  # type: ignore

from .config.sensors_mqtt import NUMERIC_SENSORS, TEXT_SENSORS

logger = logging.getLogger("huawei.mqtt")

_mqtt_client: Optional[mqtt.Client] = None
_is_connected = False


def _on_connect(client, userdata, flags, rc, properties=None):
    """Callback when connected."""
    global _is_connected
    if rc == 0:
        _is_connected = True
        logger.info("MQTT connected")
    else:
        logger.error(f"MQTT connection failed: {rc}")


def _on_disconnect(client, userdata, flags, rc=0, properties=None):
    """Callback when disconnected."""
    global _is_connected
    _is_connected = False
    if rc != 0:
        logger.warning(f"MQTT unexpected disconnect: {rc}")


def _get_mqtt_client() -> mqtt.Client:
    """Create/reuse MQTT client with LWT (persistent)."""
    global _mqtt_client
    if _mqtt_client is not None:
        return _mqtt_client

    # paho-mqtt 2.x API
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)  # type: ignore[attr-defined]

    # Set callbacks
    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect

    user = os.environ.get("HUAWEI_MODBUS_MQTT_USER")
    password = os.environ.get("HUAWEI_MODBUS_MQTT_PASSWORD")

    if user and password:
        client.username_pw_set(user, password)
        logger.debug(f"MQTT auth configured for {user}")

    topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
    if topic:
        client.will_set(f"{topic}/status", "offline", qos=1, retain=True)
        logger.debug(f"LWT set: {topic}/status")

    _mqtt_client = client
    return client


def connect_mqtt() -> None:
    """Connect MQTT client once at startup."""
    global _is_connected

    client = _get_mqtt_client()

    broker = os.environ.get("HUAWEI_MODBUS_MQTT_BROKER")
    port = int(os.environ.get("HUAWEI_MODBUS_MQTT_PORT", "1883"))

    if not broker:
        logger.error("MQTT broker not configured")
        raise RuntimeError("MQTT broker not configured")

    logger.debug(f"Connecting MQTT to {broker}:{port}")
    client.connect(broker, port, 60)
    client.loop_start()

    # Warte bis connected
    timeout = 10
    waited = 0
    while not _is_connected and waited < timeout:
        time.sleep(0.1)
        waited += 0.1

    if not _is_connected:
        client.loop_stop()
        raise ConnectionError(f"MQTT connection timeout after {timeout}s")

    time.sleep(0.3)
    logger.debug("MQTT connection stable")


def disconnect_mqtt() -> None:
    """Disconnect MQTT client on shutdown."""
    global _mqtt_client, _is_connected
    if _mqtt_client is None:
        return

    try:
        topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
        if topic and _is_connected:
            result = _mqtt_client.publish(
                f"{topic}/status", "offline", qos=1, retain=True
            )
            result.wait_for_publish(timeout=1.0)
        _mqtt_client.loop_stop()
        _mqtt_client.disconnect()
        logger.info("MQTT disconnected")
    except Exception as e:
        logger.error(f"MQTT disconnect error: {e}")
    finally:
        _mqtt_client = None
        _is_connected = False


def _build_sensor_config(
    sensor: Dict[str, Any], base_topic: str, device_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Build discovery config for single sensor."""
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


def _load_numeric_sensors() -> List[Dict[str, Any]]:
    """Load numeric sensor definitions."""
    return NUMERIC_SENSORS


def _load_text_sensors() -> List[Dict[str, Any]]:
    """Load text sensor definitions."""
    return TEXT_SENSORS


def _publish_sensor_configs(
    client: mqtt.Client,
    base_topic: str,
    sensors: List[Dict[str, Any]],
    device_config: Dict[str, Any],
) -> int:
    """Publish sensor discovery configs."""
    count = 0
    for sensor in sensors:
        config = _build_sensor_config(sensor, base_topic, device_config)
        topic = f"homeassistant/sensor/huawei_solar/{sensor['key']}/config"
        result = client.publish(topic, json.dumps(config), qos=1, retain=True)
        result.wait_for_publish(timeout=1.0)
        count += 1
    return count


def publish_discovery_configs(base_topic: str) -> None:
    """Publish all HA MQTT Discovery configs."""
    if not _is_connected:
        logger.warning("MQTT not connected, skipping discovery")
        return

    logger.info("Publishing MQTT Discovery")
    client = _get_mqtt_client()

    device_config = {
        "identifiers": ["huawei_solar_modbus"],
        "name": "Huawei Solar Inverter",
        "model": "SUN2000",
        "manufacturer": "Huawei",
    }

    sensors = _load_numeric_sensors()
    count = _publish_sensor_configs(client, base_topic, sensors, device_config)
    logger.debug(f"Published {count} numeric sensors")

    text_sensors = _load_text_sensors()
    text_count = _publish_sensor_configs(
        client, base_topic, text_sensors, device_config
    )
    logger.debug(f"Published {text_count} text sensors")

    _publish_status_sensor(client, base_topic, device_config)

    logger.info(f"Discovery complete: {count + text_count + 1} entities")


def _publish_status_sensor(
    client: mqtt.Client, base_topic: str, device_config: Dict[str, Any]
) -> None:
    """Publish binary connectivity sensor."""
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
    result.wait_for_publish(timeout=1.0)


def publish_data(data: Dict[str, Any], topic: str) -> None:
    """Publish sensor data to MQTT."""
    if not _is_connected:
        logger.warning("MQTT not connected, cannot publish data")
        raise ConnectionError("MQTT not connected")

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
        result.wait_for_publish(timeout=2.0)
        logger.debug(f"Data published: {len(data)} keys")
    except Exception as e:
        logger.error(f"MQTT publish failed: {e}")
        raise


def publish_status(status: str, topic: str) -> None:
    """Publish online/offline status."""
    if not _is_connected:
        logger.debug(f"MQTT not connected, cannot publish status '{status}'")
        return

    client = _get_mqtt_client()
    status_topic = f"{topic}/status"

    try:
        result = client.publish(status_topic, status, qos=1, retain=True)
        result.wait_for_publish(timeout=1.0)
        logger.debug(f"Status: '{status}' → {status_topic}")
    except Exception as e:
        logger.error(f"Status publish failed: {e}")
