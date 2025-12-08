# mqtt.py
import logging
import os
import json
import time
import paho.mqtt.client as mqtt

# Logger für dieses Modul
logger = logging.getLogger("huawei.mqtt")


def get_mqtt_client():
    """Create and configure MQTT client with LWT."""
    logger.debug("Creating MQTT client")
    client = mqtt.Client()

    mqtt_user = os.environ.get("HUAWEI_MODBUS_MQTT_USER")
    mqtt_password = os.environ.get("HUAWEI_MODBUS_MQTT_PASSWORD")

    if mqtt_user and mqtt_password:
        client.username_pw_set(mqtt_user, mqtt_password)
        logger.debug(f"MQTT authentication configured for user: {mqtt_user}")
    else:
        logger.debug("MQTT authentication not configured (no credentials)")

    # KORREKT: base_topic IMMER vor Verwendung abrufen!
    base_topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
    if base_topic:
        # LWT: Falls der Client unerwartet disconnected, setzt der Broker den Status auf offline
        client.will_set(f"{base_topic}/status", payload="offline", retain=True)
        logger.debug(f"MQTT Last Will Testament set for topic: {base_topic}/status")
    else:
        logger.warning("HUAWEI_MODBUS_MQTT_TOPIC not set - LWT disabled")

    return client

def publish_discovery_configs(base_topic):
    """Publish Home Assistant MQTT Discovery configs for all sensors"""

    logger.info("Starting MQTT Discovery config publication")

    client = get_mqtt_client()

    try:
        mqtt_broker = os.environ.get('HUAWEI_MODBUS_MQTT_BROKER')
        mqtt_port = int(os.environ.get('HUAWEI_MODBUS_MQTT_PORT', '1883'))

        logger.debug(f"Connecting to MQTT broker: {mqtt_broker}:{mqtt_port}")
        client.connect(mqtt_broker, mqtt_port, 60)

        device_config = {
            "identifiers": ["huawei_solar_modbus"],
            "name": "Huawei Solar Inverter",
            "model": "SUN2000",
            "manufacturer": "Huawei"
        }

        # === SENSOR DEFINITIONS ===
        # enabled_by_default: false = Disabled by default (expert sensors)
        # entity_category: "diagnostic" = Diagnostic sensor (less important)

        sensors = [
            # === POWER (Main - Always Enabled) ===
            {
                "name": "Solar Power",
                "key": "power_active",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:solar-power",
                "enabled": True
            },
            {
                "name": "Input Power",
                "key": "power_input",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:solar-panel",
                "enabled": True
            },
            {
                "name": "Grid Power",
                "key": "meter_power_active",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:transmission-tower",
                "enabled": True
            },
            {
                "name": "Battery Power",
                "key": "battery_power",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:battery-charging",
                "enabled": True
            },

            # === ENERGY (Main - Always Enabled) ===
            {
                "name": "Solar Daily Yield",
                "key": "energy_yield_day",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
                "icon": "mdi:solar-power",
                "enabled": True
            },
            {
                "name": "Solar Total Yield",
                "key": "energy_yield_accumulated",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
                "icon": "mdi:solar-power",
                "enabled": True
            },
            {
                "name": "Grid Energy Exported",
                "key": "energy_grid_exported",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
                "icon": "mdi:transmission-tower-export",
                "enabled": True
            },
            {
                "name": "Grid Energy Imported",
                "key": "energy_grid_accumulated",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
                "icon": "mdi:transmission-tower-import",
                "enabled": True
            },

            # === BATTERY (Main - Always Enabled) ===
            {
                "name": "Battery SOC",
                "key": "battery_soc",
                "unit": "%",
                "device_class": "battery",
                "state_class": "measurement",
                "icon": "mdi:battery",
                "enabled": True
            },
            {
                "name": "Battery Charge Today",
                "key": "battery_charge_day",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
                "icon": "mdi:battery-plus",
                "enabled": True
            },
            {
                "name": "Battery Discharge Today",
                "key": "battery_discharge_day",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
                "icon": "mdi:battery-minus",
                "enabled": True
            },

            # === PV STRINGS (Main) ===
            {
                "name": "PV1 Power",
                "key": "power_PV1",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:solar-panel",
                "enabled": True
            },
            {
                "name": "PV1 Voltage",
                "key": "voltage_PV1",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "enabled": True,
                "entity_category": "diagnostic"
            },
            {
                "name": "PV1 Current",
                "key": "current_PV1",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement",
                "enabled": True,
                "entity_category": "diagnostic"
            },

            # === PV STRINGS 2-4 (Optional, Disabled by default) ===
            {
                "name": "PV2 Power",
                "key": "power_PV2",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:solar-panel",
                "enabled": False
            },
            {
                "name": "PV3 Power",
                "key": "power_PV3",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:solar-panel",
                "enabled": False
            },
            {
                "name": "PV4 Power",
                "key": "power_PV4",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:solar-panel",
                "enabled": False
            },
            {
                "name": "PV2 Voltage",
                "key": "voltage_PV2",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "PV3 Voltage",
                "key": "voltage_PV3",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "PV4 Voltage",
                "key": "voltage_PV4",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "PV2 Current",
                "key": "current_PV2",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "PV3 Current",
                "key": "current_PV3",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "PV4 Current",
                "key": "current_PV4",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },

            # === INVERTER STATUS ===
            {
                "name": "Inverter Temperature",
                "key": "inverter_temperature",
                "unit": "°C",
                "device_class": "temperature",
                "state_class": "measurement",
                "enabled": True
            },
            {
                "name": "Inverter Efficiency",
                "key": "inverter_efficiency",
                "unit": "%",
                "state_class": "measurement",
                "icon": "mdi:gauge",
                "enabled": True,
                "entity_category": "diagnostic"
            },

            # === GRID (3-Phase - Main) ===
            {
                "name": "Grid Voltage Phase A",
                "key": "voltage_grid_A",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "enabled": True
            },
            {
                "name": "Grid Voltage Phase B",
                "key": "voltage_grid_B",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "enabled": True
            },
            {
                "name": "Grid Voltage Phase C",
                "key": "voltage_grid_C",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "enabled": True
            },
            {
                "name": "Grid Frequency",
                "key": "frequency_grid",
                "unit": "Hz",
                "device_class": "frequency",
                "state_class": "measurement",
                "enabled": True,
                "entity_category": "diagnostic"
            },

            # === GRID (3-Phase - Advanced, Disabled) ===
            {
                "name": "Grid Current Phase A",
                "key": "current_grid_A",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Grid Current Phase B",
                "key": "current_grid_B",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Grid Current Phase C",
                "key": "current_grid_C",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Grid Power Phase A",
                "key": "power_grid_A",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Grid Power Phase B",
                "key": "power_grid_B",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Grid Power Phase C",
                "key": "power_grid_C",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Line Voltage A-B",
                "key": "voltage_line_AB",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Line Voltage B-C",
                "key": "voltage_line_BC",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Line Voltage C-A",
                "key": "voltage_line_CA",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },

            # === POWER METER (Advanced) ===
            {
                "name": "Meter Voltage Phase A",
                "key": "meter_voltage_A",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Meter Voltage Phase B",
                "key": "meter_voltage_B",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Meter Voltage Phase C",
                "key": "meter_voltage_C",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Meter Current Phase A",
                "key": "meter_current_A",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Meter Current Phase B",
                "key": "meter_current_B",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Meter Current Phase C",
                "key": "meter_current_C",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },

            # === BATTERY (Advanced) ===
            {
                "name": "Battery Total Charge",
                "key": "battery_charge_total",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
                "enabled": True,
                "entity_category": "diagnostic"
            },
            {
                "name": "Battery Total Discharge",
                "key": "battery_discharge_total",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
                "enabled": True,
                "entity_category": "diagnostic"
            },
            {
                "name": "Battery Bus Voltage",
                "key": "battery_bus_voltage",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Battery Bus Current",
                "key": "battery_bus_current",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },

            # === POWER FACTOR & REACTIVE POWER (Expert) ===
            {
                "name": "Power Factor",
                "key": "power_factor",
                "state_class": "measurement",
                "icon": "mdi:sine-wave",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Reactive Power",
                "key": "power_reactive",
                "unit": "var",
                "device_class": "reactive_power",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Meter Reactive Power",
                "key": "meter_power_reactive",
                "unit": "var",
                "device_class": "reactive_power",
                "state_class": "measurement",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Grid Reactive Energy",
                "key": "energy_grid_accumulated_reactive",
                "unit": "kvarh",
                "state_class": "total_increasing",
                "enabled": False,
                "entity_category": "diagnostic"
            },

            # === OTHER METRICS ===
            {
                "name": "Day Peak Power",
                "key": "power_active_peak_day",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "enabled": True,
                "entity_category": "diagnostic"
            },
            {
                "name": "Insulation Resistance",
                "key": "inverter_insulation_resistance",
                "unit": "MΩ",
                "state_class": "measurement",
                "icon": "mdi:resistor",
                "enabled": False,
                "entity_category": "diagnostic"
            },
        ]

        logger.debug(
            f"Publishing discovery configs for {len(sensors)} sensors")

        # Publish sensor configs
        published_count = 0
        for sensor in sensors:
            config_topic = f"homeassistant/sensor/huawei_solar/{sensor['key']}/config"

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

            # Add optional fields
            if "unit" in sensor:
                config["unit_of_measurement"] = sensor["unit"]
            if "device_class" in sensor:
                config["device_class"] = sensor["device_class"]
            if "state_class" in sensor:
                config["state_class"] = sensor["state_class"]
            if "icon" in sensor:
                config["icon"] = sensor["icon"]
            if "entity_category" in sensor:
                config["entity_category"] = sensor["entity_category"]
            if "enabled" in sensor and not sensor["enabled"]:
                config["enabled_by_default"] = False

            client.publish(config_topic, json.dumps(config), retain=True)
            published_count += 1

        logger.debug(f"Published {published_count} sensor discovery configs")

        # === TEXT SENSORS (Status) ===
        text_sensors = [
            {
                "name": "Inverter Status",
                "key": "inverter_status",
                "icon": "mdi:information",
                "enabled": True
            },
            {
                "name": "Battery Status",
                "key": "battery_status",
                "icon": "mdi:battery-heart",
                "enabled": True
            },
            {
                "name": "Meter Status",
                "key": "meter_status",
                "icon": "mdi:meter-electric",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Inverter State 1",
                "key": "inverter_state_1",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Inverter State 2",
                "key": "inverter_state_2",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Inverter State 3",
                "key": "inverter_state_3",
                "enabled": False,
                "entity_category": "diagnostic"
            },
            {
                "name": "Inverter Startup Time",
                "key": "inverter_startup_time",
                "device_class": "timestamp",
                "enabled": False,
                "entity_category": "diagnostic"
            },
        ]

        logger.debug(
            f"Publishing discovery configs for {len(text_sensors)} text sensors")

        text_published_count = 0
        for sensor in text_sensors:
            config_topic = f"homeassistant/sensor/huawei_solar/{sensor['key']}/config"

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

            if "icon" in sensor:
                config["icon"] = sensor["icon"]
            if "device_class" in sensor:
                config["device_class"] = sensor["device_class"]
            if "entity_category" in sensor:
                config["entity_category"] = sensor["entity_category"]
            if "enabled" in sensor and not sensor["enabled"]:
                config["enabled_by_default"] = False

            client.publish(config_topic, json.dumps(config), retain=True)
            text_published_count += 1

        logger.debug(
            f"Published {text_published_count} text sensor discovery configs")

        # Binary sensor for connectivity
        status_config = {
            "name": "Huawei Solar Status",
            "unique_id": "huawei_solar_status",
            "state_topic": f"{base_topic}/status",
            "payload_on": "online",
            "payload_off": "offline",
            "device_class": "connectivity",
            "device": device_config
        }
        client.publish(
            "homeassistant/binary_sensor/huawei_solar/status/config",
            json.dumps(status_config),
            retain=True
        )

        logger.debug("Published binary sensor discovery config")

        client.disconnect()

        total_entities = published_count + text_published_count + 1
        logger.info(
            f"Successfully published {total_entities} MQTT Discovery configs")

    except Exception as e:
        logger.error(f"Error publishing discovery configs: {e}")
        logger.debug(f"Exception details: {type(e).__name__}", exc_info=True)
        raise


def publish_data(data, topic):
    """Publish sensor data to MQTT"""
    client = get_mqtt_client()

    try:
        mqtt_broker = os.environ.get("HUAWEI_MODBUS_MQTT_BROKER")
        mqtt_port = int(os.environ.get("HUAWEI_MODBUS_MQTT_PORT", "1883"))

        logger.debug(f"Connecting to MQTT broker: {mqtt_broker}:{mqtt_port}")

        connect_start = time.time()
        client.connect(mqtt_broker, mqtt_port, 60)
        connect_duration = time.time() - connect_start

        logger.debug(f"MQTT connection established in {connect_duration:.3f}s")

        # Add metadata
        data["last_update"] = int(time.time())

        # Log wichtige Datenpunkte bei DEBUG
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Publishing data: {len(data)} keys - "
                f"Solar: {data.get('power_active', 'N/A')}W, "
                f"Grid: {data.get('meter_power_active', 'N/A')}W, "
                f"Battery: {data.get('battery_power', 'N/A')}W"
            )

        # Publish data
        publish_start = time.time()
        client.publish(topic, json.dumps(data))
        publish_duration = time.time() - publish_start

        logger.debug(
            f"Data published in {publish_duration:.3f}s ({len(json.dumps(data))} bytes)")

        client.disconnect()

    except Exception as e:
        logger.error(f"Error publishing data to MQTT: {e}")
        logger.debug(f"Exception details: {type(e).__name__}", exc_info=True)
        raise


def publish_status(status, topic):
    """Publish status message (online/offline)"""

    logger.debug(f"Publishing status '{status}' to {topic}/status")

    client = get_mqtt_client()

    try:
        mqtt_broker = os.environ.get("HUAWEI_MODBUS_MQTT_BROKER")
        mqtt_port = int(os.environ.get("HUAWEI_MODBUS_MQTT_PORT", "1883"))

        client.connect(mqtt_broker, mqtt_port, 60)
        client.publish(f"{topic}/status", status, retain=True)
        client.disconnect()

        logger.debug(f"Status '{status}' published successfully")

    except Exception as e:
        logger.error(f"Error publishing status to MQTT: {e}")
        logger.debug(f"Exception details: {type(e).__name__}", exc_info=True)
