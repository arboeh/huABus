# modbus_energy_meter/mqtt_client.py
import logging
import os
import json
import time
import paho.mqtt.client as mqtt  # type: ignore
from typing import Dict, Any, List, Optional

from .config.sensors_mqtt import NUMERIC_SENSORS, TEXT_SENSORS

logger = logging.getLogger("huawei.mqtt")

_mqtt_client: Optional[mqtt.Client] = None


def _get_mqtt_client() -> mqtt.Client:
    """Create/reuse MQTT client with LWT (persistent)."""
    global _mqtt_client
    if _mqtt_client is not None:
        return _mqtt_client

    client = mqtt.Client()

    user = os.environ.get("HUAWEI_MODBUS_MQTT_USER")
    password = os.environ.get("HUAWEI_MODBUS_MQTT_PASSWORD")

    if user and password:
        client.username_pw_set(user, password)
        logger.debug(f"MQTT auth configured for {user}")

    topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
    if topic:
        # LWT nur EINMAL setzen, wenn Client erzeugt wird
        client.will_set(f"{topic}/status", "offline", qos=1, retain=True)
        logger.debug(f"LWT set: {topic}/status")

    _mqtt_client = client
    return client


def connect_mqtt() -> None:
    """Connect MQTT client once at startup."""
    client = _get_mqtt_client()

    broker = os.environ.get("HUAWEI_MODBUS_MQTT_BROKER")
    port = int(os.environ.get("HUAWEI_MODBUS_MQTT_PORT", "1883"))

    if not broker:
        logger.error("MQTT broker not configured")
        raise RuntimeError("MQTT broker not configured")

    logger.debug(f"Connecting MQTT to {broker}:{port}")
    client.connect(broker, port, 60)
    client.loop_start()
    logger.info("MQTT connected")


def disconnect_mqtt() -> None:
    """Disconnect MQTT client on shutdown."""
    global _mqtt_client
    if _mqtt_client is None:
        return

    try:
        topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
        if topic:
            # explizit offline setzen, bevor Verbindung beendet wird
            _mqtt_client.publish(
                f"{topic}/status", "offline", qos=1, retain=True)
            time.sleep(0.1)
        _mqtt_client.loop_stop()
        _mqtt_client.disconnect()
        logger.info("MQTT disconnected")
    except Exception as e:
        logger.error(f"MQTT disconnect error: {e}")
    finally:
        _mqtt_client = None


def _build_sensor_config(sensor: Dict[str, Any], base_topic: str,
                         device_config: Dict[str, Any]) -> Dict[str, Any]:
    """Build discovery config for single sensor."""
    config = {
        "name": sensor["name"],
        "unique_id": f"huawei_solar_{sensor['key']}",
        "state_topic": base_topic,
        "value_template": sensor.get(
            "value_template",
            f"{{{{ value_json.{sensor['key']} }}}}"  # ← Standard-Fallback
        ),
        "availability_topic": f"{base_topic}/status",
        "payload_available": "online",
        "payload_not_available": "offline",
        "device": device_config
    }

    # Optional fields
    for key in ["unit_of_measurement", "device_class", "state_class",
                "icon", "entity_category"]:
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


def _publish_sensor_configs(client: mqtt.Client, base_topic: str,
                            sensors: List[Dict[str, Any]],
                            device_config: Dict[str, Any]) -> int:
    """Publish sensor discovery configs."""
    count = 0
    for sensor in sensors:
        config = _build_sensor_config(sensor, base_topic, device_config)
        topic = f"homeassistant/sensor/huawei_solar/{sensor['key']}/config"
        client.publish(topic, json.dumps(config), qos=1, retain=True)
        count += 1
    return count


def publish_discovery_configs(base_topic: str) -> None:
    """Publish all HA MQTT Discovery configs."""
    logger.info("Publishing MQTT Discovery")
    client = _get_mqtt_client()

    device_config = {
        "identifiers": ["huawei_solar_modbus"],
        "name": "Huawei Solar Inverter",
        "model": "SUN2000",
        "manufacturer": "Huawei"
    }

    # Numeric sensors
    sensors = _load_numeric_sensors()
    count = _publish_sensor_configs(client, base_topic, sensors, device_config)
    logger.debug(f"Published {count} numeric sensors")

    # Text sensors
    text_sensors = _load_text_sensors()
    text_count = _publish_sensor_configs(
        client, base_topic, text_sensors, device_config)
    logger.debug(f"Published {text_count} text sensors")

    # Binary status sensor
    _publish_status_sensor(client, base_topic, device_config)

    logger.info(f"Discovery complete: {count + text_count + 1} entities")


def _publish_status_sensor(client: mqtt.Client, base_topic: str,
                           device_config: Dict[str, Any]) -> None:
    """Publish binary connectivity sensor."""
    config = {
        "name": "Huawei Solar Status",
        "unique_id": "huawei_solar_status",
        "state_topic": f"{base_topic}/status",
        "payload_on": "online",
        "payload_off": "offline",
        "device_class": "connectivity",
        "device": device_config
    }
    client.publish("homeassistant/binary_sensor/huawei_solar/status/config",
                   json.dumps(config), qos=1, retain=True)


def publish_data(data: Dict[str, Any], topic: str) -> None:
    """Publish sensor data."""
    client = _get_mqtt_client()

    data["last_update"] = int(time.time())

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Publishing: Solar={data.get('power_active', 'N/A')}W, "
                     f"Grid={data.get('meter_power_active', 'N/A')}W, "
                     f"Battery={data.get('battery_power', 'N/A')}W")

    try:
        result = client.publish(topic, json.dumps(data), qos=1, retain=True)
        result.wait_for_publish(timeout=1.0)
        logger.debug(f"Data published: {len(data)} keys")
    except Exception as e:
        logger.error(f"MQTT publish failed: {e}")
        raise


def publish_status(status: str, topic: str) -> None:
    """Publish online/offline status."""
    logger.debug(f"Status '{status}' → {topic}/status")
    client = _get_mqtt_client()

    try:
        status_topic = f"{topic}/status"
        result = client.publish(status_topic, status, qos=1, retain=True)
        result.wait_for_publish(timeout=1.0)
        logger.info(f"Status published: '{status}' → {status_topic}")
    except Exception as e:
        logger.error(f"MQTT status publish failed: {e}")
