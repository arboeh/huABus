# mqtt.py
import logging
import os
import json
import time
import paho.mqtt.client as mqtt
from typing import Dict, Any, List

logger = logging.getLogger("huawei.mqtt")


def get_mqtt_client() -> mqtt.Client:
    """Create MQTT client with LWT."""
    client = mqtt.Client()

    user = os.environ.get("HUAWEI_MODBUS_MQTT_USER")
    password = os.environ.get("HUAWEI_MODBUS_MQTT_PASSWORD")

    if user and password:
        client.username_pw_set(user, password)
        logger.debug(f"MQTT auth configured for {user}")

    topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
    if topic:
        client.will_set(f"{topic}/status", "offline", retain=True)
        logger.debug(f"LWT set: {topic}/status")

    return client


def _build_sensor_config(sensor: Dict[str, Any], base_topic: str,
                         device_config: Dict[str, Any]) -> Dict[str, Any]:
    """Build discovery config for single sensor."""
    config = {
        "name": sensor["name"],
        "unique_id": f"huawei_solar_{sensor['key']}",
        "state_topic": base_topic,
        "value_template": f"{{{{ value_json.{sensor['key']} }}}}",
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


def _publish_sensor_configs(client: mqtt.Client, base_topic: str,
                            sensors: List[Dict[str, Any]],
                            device_config: Dict[str, Any]) -> int:
    """Publish sensor discovery configs."""
    count = 0
    for sensor in sensors:
        config = _build_sensor_config(sensor, base_topic, device_config)
        topic = f"homeassistant/sensor/huawei_solar/{sensor['key']}/config"
        client.publish(topic, json.dumps(config), retain=True)
        count += 1
    return count


def _load_numeric_sensors() -> List[Dict[str, Any]]:
    """Load numeric sensor definitions."""
    return [
        # ==========================================
        # POWER (Main - Always Enabled)
        # ==========================================
        {
            "name": "Solar Power",
            "key": "power_active",
            "unit": "W",
            "device_class": "power",
            "state_class": "measurement",
            "icon": "mdi:solar-power",
            "enabled": True,
        },
        {
            "name": "Input Power",
            "key": "power_input",
            "unit": "W",
            "device_class": "power",
            "state_class": "measurement",
            "icon": "mdi:solar-panel",
            "enabled": True,
        },
        {
            "name": "Grid Power",
            "key": "meter_power_active",
            "unit": "W",
            "device_class": "power",
            "state_class": "measurement",
            "icon": "mdi:transmission-tower",
            "enabled": True,
        },
        {
            "name": "Battery Power",
            "key": "battery_power",
            "unit": "W",
            "device_class": "power",
            "state_class": "measurement",
            "icon": "mdi:battery-charging",
            "enabled": True,
        },

        # ==========================================
        # ENERGY (Main - Always Enabled)
        # ==========================================
        {
            "name": "Solar Daily Yield",
            "key": "energy_yield_day",
            "unit": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
            "icon": "mdi:solar-power",
            "enabled": True,
        },
        {
            "name": "Solar Total Yield",
            "key": "energy_yield_accumulated",
            "unit": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
            "icon": "mdi:solar-power",
            "enabled": True,
        },
        {
            "name": "Grid Energy Exported",
            "key": "energy_grid_exported",
            "unit": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
            "icon": "mdi:transmission-tower-export",
            "enabled": True,
        },
        {
            "name": "Grid Energy Imported",
            "key": "energy_grid_accumulated",
            "unit": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
            "icon": "mdi:transmission-tower-import",
            "enabled": True,
        },

        # ==========================================
        # BATTERY (Main - Always Enabled)
        # ==========================================
        {
            "name": "Battery SOC",
            "key": "battery_soc",
            "unit": "%",
            "device_class": "battery",
            "state_class": "measurement",
            "icon": "mdi:battery",
            "enabled": True,
        },
        {
            "name": "Battery Charge Today",
            "key": "battery_charge_day",
            "unit": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
            "icon": "mdi:battery-plus",
            "enabled": True,
        },
        {
            "name": "Battery Discharge Today",
            "key": "battery_discharge_day",
            "unit": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
            "icon": "mdi:battery-minus",
            "enabled": True,
        },
        {
            "name": "Battery Total Charge",
            "key": "battery_charge_total",
            "unit": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
            "enabled": True,
            "entity_category": "diagnostic",
        },
        {
            "name": "Battery Total Discharge",
            "key": "battery_discharge_total",
            "unit": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
            "enabled": True,
            "entity_category": "diagnostic",
        },

        # ==========================================
        # PV STRINGS - String 1 (Main, Enabled)
        # ==========================================
        {
            "name": "PV1 Power",
            "key": "power_PV1",
            "unit": "W",
            "device_class": "power",
            "state_class": "measurement",
            "icon": "mdi:solar-panel",
            "enabled": True,
        },
        {
            "name": "PV1 Voltage",
            "key": "voltage_PV1",
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "enabled": True,
            "entity_category": "diagnostic",
        },
        {
            "name": "PV1 Current",
            "key": "current_PV1",
            "unit": "A",
            "device_class": "current",
            "state_class": "measurement",
            "enabled": True,
            "entity_category": "diagnostic",
        },

        # ==========================================
        # PV STRINGS 2-4 (Optional, Disabled)
        # ==========================================
        {
            "name": "PV2 Power",
            "key": "power_PV2",
            "unit": "W",
            "device_class": "power",
            "state_class": "measurement",
            "icon": "mdi:solar-panel",
            "enabled": False,
        },
        {
            "name": "PV2 Voltage",
            "key": "voltage_PV2",
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "enabled": False,
            "entity_category": "diagnostic",
        },
        {
            "name": "PV2 Current",
            "key": "current_PV2",
            "unit": "A",
            "device_class": "current",
            "state_class": "measurement",
            "enabled": False,
            "entity_category": "diagnostic",
        },
        {
            "name": "PV3 Power",
            "key": "power_PV3",
            "unit": "W",
            "device_class": "power",
            "state_class": "measurement",
            "icon": "mdi:solar-panel",
            "enabled": False,
        },
        {
            "name": "PV3 Voltage",
            "key": "voltage_PV3",
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "enabled": False,
            "entity_category": "diagnostic",
        },
        {
            "name": "PV3 Current",
            "key": "current_PV3",
            "unit": "A",
            "device_class": "current",
            "state_class": "measurement",
            "enabled": False,
            "entity_category": "diagnostic",
        },
        {
            "name": "PV4 Power",
            "key": "power_PV4",
            "unit": "W",
            "device_class": "power",
            "state_class": "measurement",
            "icon": "mdi:solar-panel",
            "enabled": False,
        },
        {
            "name": "PV4 Voltage",
            "key": "voltage_PV4",
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "enabled": False,
            "entity_category": "diagnostic",
        },
        {
            "name": "PV4 Current",
            "key": "current_PV4",
            "unit": "A",
            "device_class": "current",
            "state_class": "measurement",
            "enabled": False,
            "entity_category": "diagnostic",
        },

        # ==========================================
        # INVERTER
        # ==========================================
        {
            "name": "Inverter Temperature",
            "key": "inverter_temperature",
            "unit": "°C",
            "device_class": "temperature",
            "state_class": "measurement",
            "enabled": True,
        },
        {
            "name": "Inverter Efficiency",
            "key": "inverter_efficiency",
            "unit": "%",
            "state_class": "measurement",
            "icon": "mdi:gauge",
            "enabled": True,
            "entity_category": "diagnostic",
        },
        {
            "name": "Day Peak Power",
            "key": "power_active_peak_day",
            "unit": "W",
            "device_class": "power",
            "state_class": "measurement",
            "enabled": True,
            "entity_category": "diagnostic",
        },

        # ==========================================
        # GRID - 3-Phase (Voltage, Current, Power, Frequency)
        # ==========================================

        # Voltage Phase A/B/C (Main, Enabled)
        {
            "name": "Grid Voltage Phase A",
            "key": "voltage_grid_A",
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "enabled": True,
        },
        {
            "name": "Grid Voltage Phase B",
            "key": "voltage_grid_B",
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "enabled": True,
        },
        {
            "name": "Grid Voltage Phase C",
            "key": "voltage_grid_C",
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "enabled": True,
        },

        # Current Phase A/B/C (Enabled, Diagnostic)
        {
            "name": "Grid Current Phase A",
            "key": "current_grid_A",
            "unit": "A",
            "device_class": "current",
            "state_class": "measurement",
            "enabled": True,
            "entity_category": "diagnostic",
        },
        {
            "name": "Grid Current Phase B",
            "key": "current_grid_B",
            "unit": "A",
            "device_class": "current",
            "state_class": "measurement",
            "enabled": True,
            "entity_category": "diagnostic",
        },
        {
            "name": "Grid Current Phase C",
            "key": "current_grid_C",
            "unit": "A",
            "device_class": "current",
            "state_class": "measurement",
            "enabled": True,
            "entity_category": "diagnostic",
        },

        # Power Phase A/B/C (Enabled, Diagnostic)
        {
            "name": "Grid Power Phase A",
            "key": "power_grid_A",
            "unit": "W",
            "device_class": "power",
            "state_class": "measurement",
            "enabled": True,
            "entity_category": "diagnostic",
        },
        {
            "name": "Grid Power Phase B",
            "key": "power_grid_B",
            "unit": "W",
            "device_class": "power",
            "state_class": "measurement",
            "enabled": True,
            "entity_category": "diagnostic",
        },
        {
            "name": "Grid Power Phase C",
            "key": "power_grid_C",
            "unit": "W",
            "device_class": "power",
            "state_class": "measurement",
            "enabled": True,
            "entity_category": "diagnostic",
        },

        # Frequency (Enabled, Diagnostic)
        {
            "name": "Grid Frequency",
            "key": "frequency_grid",
            "unit": "Hz",
            "device_class": "frequency",
            "state_class": "measurement",
            "enabled": True,
            "entity_category": "diagnostic",
        },
    ]


def _load_text_sensors() -> List[Dict[str, Any]]:
    """Load text sensor definitions."""
    return [
        {
            "name": "Inverter Status",
            "key": "inverter_status",
            "icon": "mdi:information",
            "enabled": True,
        },
        {
            "name": "Battery Status",
            "key": "battery_status",
            "icon": "mdi:battery-heart",
            "enabled": True,
        },
        {
            "name": "Meter Status",
            "key": "meter_status",
            "icon": "mdi:meter-electric",
            "enabled": False,
            "entity_category": "diagnostic",
        },
        {
            "name": "Inverter State 1",
            "key": "inverter_state_1",
            "enabled": False,
            "entity_category": "diagnostic",
        },
        {
            "name": "Inverter State 2",
            "key": "inverter_state_2",
            "enabled": False,
            "entity_category": "diagnostic",
        },
        {
            "name": "Inverter State 3",
            "key": "inverter_state_3",
            "enabled": False,
            "entity_category": "diagnostic",
        },
        {
            "name": "Inverter Startup Time",
            "key": "inverter_startup_time",
            "device_class": "timestamp",
            "enabled": False,
            "entity_category": "diagnostic",
        },
    ]


def publish_discovery_configs(base_topic: str) -> None:
    """Publish all HA MQTT Discovery configs."""
    logger.info("Publishing MQTT Discovery")
    client = get_mqtt_client()

    try:
        broker = os.environ.get('HUAWEI_MODBUS_MQTT_BROKER')
        port = int(os.environ.get('HUAWEI_MODBUS_MQTT_PORT', '1883'))

        client.connect(broker, port, 60)

        device_config = {
            "identifiers": ["huawei_solar_modbus"],
            "name": "Huawei Solar Inverter",
            "model": "SUN2000",
            "manufacturer": "Huawei"
        }

        # Numeric sensors
        sensors = _load_numeric_sensors()
        count = _publish_sensor_configs(
            client, base_topic, sensors, device_config)
        logger.debug(f"Published {count} numeric sensors")

        # Text sensors
        text_sensors = _load_text_sensors()
        text_count = _publish_sensor_configs(
            client, base_topic, text_sensors, device_config)
        logger.debug(f"Published {text_count} text sensors")

        # Binary status sensor
        _publish_status_sensor(client, base_topic, device_config)

        logger.info(f"Discovery complete: {count + text_count + 1} entities")

    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        raise
    finally:
        client.disconnect()


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
                   json.dumps(config), retain=True)


def publish_data(data: Dict[str, Any], topic: str) -> None:
    """Publish sensor data."""
    client = get_mqtt_client()

    try:
        broker = os.environ.get("HUAWEI_MODBUS_MQTT_BROKER")
        port = int(os.environ.get("HUAWEI_MODBUS_MQTT_PORT", "1883"))

        client.connect(broker, port, 60)

        data["last_update"] = int(time.time())

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Publishing: Solar={data.get('power_active', 'N/A')}W, "
                         f"Grid={data.get('meter_power_active', 'N/A')}W, "
                         f"Battery={data.get('battery_power', 'N/A')}W")

        client.publish(topic, json.dumps(data))
        logger.debug(f"Data published: {len(data)} keys")

    except Exception as e:
        logger.error(f"MQTT publish failed: {e}")
        raise
    finally:
        client.disconnect()


def publish_status(status: str, topic: str) -> None:
    """Publish online/offline status."""
    logger.debug(f"Status '{status}' → {topic}/status")

    client = get_mqtt_client()
    try:
        broker = os.environ.get("HUAWEI_MODBUS_MQTT_BROKER")
        port = int(os.environ.get("HUAWEI_MODBUS_MQTT_PORT", "1883"))

        client.connect(broker, port, 60)
        client.publish(f"{topic}/status", status, retain=True)
    finally:
        client.disconnect()
