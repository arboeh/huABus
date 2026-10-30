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
from paho.mqtt.reasoncodes import ReasonCode

from .config.sensors_mqtt import NUMERIC_SENSORS, TEXT_SENSORS

logger = logging.getLogger("huawei.mqtt")

# Globale MQTT Client Instanz (Singleton-Pattern)
_mqtt_client: mqtt.Client | None = None

# Connection State Flag - verhindert Publishing wenn nicht verbunden
_is_connected = False

# Thread-safe event for connection establishment (paho callbacks run in their own thread)
_connected_event = threading.Event()

# Last refused CONNACK code of the current connect attempt (None = no CONNACK refusal seen).
# Separates "wrong credentials" from "broker unreachable" in the timeout message.
_last_connack_rc: ReasonCode | int | None = None

CONNECT_TIMEOUT = 10.0
DATA_PUBLISH_TIMEOUT = 2.0
STATUS_PUBLISH_TIMEOUT = 1.0


class MqttNotConnectedError(ConnectionError):
    """Raised when publishing is attempted without an active broker connection."""


class MqttPublishError(Exception):
    """Raised when the broker did not confirm a publish."""


def _on_connect(client, userdata, flags, rc, properties=None):
    """Callback when MQTT connection is established."""
    global _is_connected, _last_connack_rc
    if rc == 0:
        _is_connected = True
        _connected_event.set()
    else:
        _last_connack_rc = rc
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


async def _wait_for_publish(result, timeout: float) -> bool:
    """Offload blocking wait_for_publish to executor.

    Returns:
        True if the broker confirmed the publish, False on timeout.

    Raises:
        RuntimeError, ValueError: paho reports a failed publish (no connection, queue full).
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, result.wait_for_publish, timeout)
    return bool(result.is_published())


async def _discard_client() -> None:
    """Stop the network thread of the current client and drop it.

    A failed connect attempt must not leave a running loop thread behind;
    the next attempt then starts with a fresh client.
    """
    global _mqtt_client
    client, _mqtt_client = _mqtt_client, None
    if client is None:
        return

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, client.loop_stop)
        await loop.run_in_executor(None, client.disconnect)
    except Exception as e:
        logger.debug(f"MQTT cleanup after failed connect: {e}")


def _parse_port(raw: str) -> int:
    """Return the broker port or raise RuntimeError for an invalid value."""
    try:
        port = int(raw)
    except ValueError:
        port = 0
    if not 1 <= port <= 65535:
        logger.error(f"🚨 Invalid MQTT port: {raw!r}")
        raise RuntimeError(f"Invalid MQTT port: {raw!r} (expected 1-65535)")
    return port


async def connect_mqtt() -> None:
    """Connect to MQTT broker and wait for connection via thread-safe event.

    Raises:
        RuntimeError: Broker host is missing or the port is not a valid number.
        OSError: Broker is not reachable (DNS, refused, ...).
        ConnectionError: No CONNACK within CONNECT_TIMEOUT.
    """
    global _last_connack_rc
    broker = os.environ.get("HUAWEI_MQTT_HOST")
    if not broker:
        logger.error("🚨 MQTT broker not configured")
        raise RuntimeError("MQTT broker not configured")

    port = _parse_port(os.environ.get("HUAWEI_MQTT_PORT", "1883"))
    client = _get_mqtt_client()

    logger.debug(f"Connecting MQTT to {broker}:{port}")
    _connected_event.clear()
    _last_connack_rc = None

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, client.connect, broker, port, 60)
        client.loop_start()
        connected = await loop.run_in_executor(None, _connected_event.wait, CONNECT_TIMEOUT)
        if not connected:
            refused = f", last CONNACK: {_last_connack_rc}" if _last_connack_rc is not None else ""
            raise ConnectionError(f"MQTT connection timeout after {CONNECT_TIMEOUT:.0f}s{refused}")
    except (Exception, asyncio.CancelledError):
        await _discard_client()
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
            await _wait_for_publish(result, STATUS_PUBLISH_TIMEOUT)

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
        if not await _wait_for_publish(result, STATUS_PUBLISH_TIMEOUT):
            logger.warning(f"⚠️ Discovery not confirmed by broker: {topic}")
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
    if not await _wait_for_publish(result, STATUS_PUBLISH_TIMEOUT):
        logger.warning("⚠️ Status sensor discovery not confirmed by broker")


async def publish_data(data: dict[str, Any], topic: str) -> None:
    """Publish sensor data to MQTT.

    The passed dict is not modified; ``last_update`` is added to a copy.

    Raises:
        MqttNotConnectedError: No active broker connection.
        MqttPublishError: Publish failed or was not confirmed by the broker.
    """
    if not _is_connected:
        logger.warning("⚠️ MQTT not connected, cannot publish data")
        raise MqttNotConnectedError("🚨 MQTT not connected")

    client = _get_mqtt_client()
    payload = {**data, "last_update": int(time.time())}
    body = json.dumps(payload)

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Publishing: Solar={payload.get('power_active', 'N/A')}W, "
            f"Grid={payload.get('meter_power_active', 'N/A')}W, "
            f"Battery={payload.get('battery_power', 'N/A')}W"
        )

    try:
        result = client.publish(topic, body, qos=1, retain=True)
        confirmed = await _wait_for_publish(result, DATA_PUBLISH_TIMEOUT)
    except (RuntimeError, ValueError) as e:
        # paho signals a lost connection (rc > 0) or a full queue this way.
        logger.error(f"❌ MQTT publish failed: {e}")
        raise MqttPublishError(f"MQTT publish failed: {e}") from e
    except Exception as e:
        logger.error(f"❌ MQTT publish failed: {e}")
        raise

    if not confirmed:
        logger.warning(f"⚠️ MQTT publish not confirmed within {DATA_PUBLISH_TIMEOUT:.0f}s")
        raise MqttPublishError(f"MQTT publish not confirmed within {DATA_PUBLISH_TIMEOUT:.0f}s")

    logger.debug(f"Data published: {len(payload)} keys")


async def publish_status(status: str, topic: str) -> None:
    """Publish online/offline status to MQTT."""
    if not _is_connected:
        logger.debug(f"MQTT not connected, cannot publish status '{status}'")
        return

    client = _get_mqtt_client()
    status_topic = f"{topic}/status"

    try:
        result = client.publish(status_topic, status, qos=1, retain=True)
        if await _wait_for_publish(result, STATUS_PUBLISH_TIMEOUT):
            logger.debug(f"Status: '{status}' → {status_topic}")
        else:
            logger.warning(f"⚠️ Status '{status}' not confirmed by broker")
    except Exception as e:
        logger.error(f"❌ Status publish failed: {e}")
