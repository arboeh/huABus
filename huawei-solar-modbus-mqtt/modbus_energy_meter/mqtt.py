import logging
import os
import json
import time
import paho.mqtt.client as mqtt


def logger():
    return logging.getLogger()


def get_mqtt_client():
    """Create and configure MQTT client"""
    client = mqtt.Client()

    mqtt_user = os.environ.get('HUAWEI_MODBUS_MQTT_USER')
    mqtt_password = os.environ.get('HUAWEI_MODBUS_MQTT_PASSWORD')

    if mqtt_user and mqtt_password:
        client.username_pw_set(mqtt_user, mqtt_password)

    return client


def publish_discovery_configs(base_topic):
    """Publish Home Assistant MQTT Discovery configs"""

    client = get_mqtt_client()

    try:
        mqtt_broker = os.environ.get('HUAWEI_MODBUS_MQTT_BROKER')
        mqtt_port = int(os.environ.get('HUAWEI_MODBUS_MQTT_PORT', '1883'))

        client.connect(mqtt_broker, mqtt_port, 60)

        device_config = {
            "identifiers": ["huawei_solar_modbus"],
            "name": "Huawei Solar Inverter",
            "model": "SUN2000",
            "manufacturer": "Huawei"
        }

        sensors = [
            # Power
            {
                "name": "Solar Power",
                "key": "power_active",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:solar-power"
            },
            {
                "name": "Grid Power",
                "key": "power_active_meter",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:transmission-tower"
            },
            {
                "name": "Battery Power",
                "key": "power_battery",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:battery-charging"
            },
            {
                "name": "PV1 Power",
                "key": "power_PV1",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:solar-panel"
            },
            {
                "name": "PV2 Power",
                "key": "power_PV2",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:solar-panel"
            },
            {
                "name": "Input Power",
                "key": "power_input",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement"
            },

            # Energy
            {
                "name": "Solar Daily Yield",
                "key": "enery_yield_day",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
                "icon": "mdi:solar-power"
            },
            {
                "name": "Solar Total Yield",
                "key": "energy_yield_accumulated",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing",
                "icon": "mdi:solar-power"
            },
            {
                "name": "Grid Energy Accumulated",
                "key": "energy_grid_accumulated",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing"
            },
            {
                "name": "Grid Energy Exported",
                "key": "energy_grid_exported",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing"
            },
            {
                "name": "Battery Charge Today",
                "key": "energy_battery_charge_day",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing"
            },
            {
                "name": "Battery Discharge Today",
                "key": "energy_battery_discharge_day",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing"
            },
            {
                "name": "Battery Total Charge",
                "key": "energy_battery_charge_total",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing"
            },
            {
                "name": "Battery Total Discharge",
                "key": "energy_battery_discharge_total",
                "unit": "kWh",
                "device_class": "energy",
                "state_class": "total_increasing"
            },

            # Battery
            {
                "name": "Battery SOC",
                "key": "soc_battery",
                "unit": "%",
                "device_class": "battery",
                "state_class": "measurement",
                "icon": "mdi:battery"
            },

            # Voltage
            {
                "name": "Grid Voltage Phase A",
                "key": "voltage_grid_A",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement"
            },
            {
                "name": "Grid Voltage Phase B",
                "key": "voltage_grid_B",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement"
            },
            {
                "name": "Grid Voltage Phase C",
                "key": "voltage_grid_C",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement"
            },
            {
                "name": "PV1 Voltage",
                "key": "voltage_PV1",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement"
            },
            {
                "name": "PV2 Voltage",
                "key": "voltage_PV2",
                "unit": "V",
                "device_class": "voltage",
                "state_class": "measurement"
            },

            # Current
            {
                "name": "PV1 Current",
                "key": "current_PV1",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement"
            },
            {
                "name": "PV2 Current",
                "key": "current_PV2",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement"
            },
            {
                "name": "Grid Current Phase A",
                "key": "current_active_grid_A",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement"
            },
            {
                "name": "Grid Current Phase B",
                "key": "current_active_grid_B",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement"
            },
            {
                "name": "Grid Current Phase C",
                "key": "current_active_grid_C",
                "unit": "A",
                "device_class": "current",
                "state_class": "measurement"
            },

            # Other
            {
                "name": "Inverter Temperature",
                "key": "temperature_internal",
                "unit": "°C",
                "device_class": "temperature",
                "state_class": "measurement"
            },
            {
                "name": "Grid Frequency",
                "key": "frequency_grid",
                "unit": "Hz",
                "device_class": "frequency",
                "state_class": "measurement"
            },
            {
                "name": "Active Grid Frequency",
                "key": "freq_active_grid",
                "unit": "Hz",
                "device_class": "frequency",
                "state_class": "measurement"
            },
            {
                "name": "Efficiency",
                "key": "efficiency",
                "unit": "%",
                "state_class": "measurement",
                "icon": "mdi:gauge"
            },
            {
                "name": "Power Factor",
                "key": "power_factor_meter",
                "state_class": "measurement",
                "icon": "mdi:sine-wave"
            },
            {
                "name": "Day Peak Power",
                "key": "power_active_peak_day",
                "unit": "W",
                "device_class": "power",
                "state_class": "measurement"
            },
        ]

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

            client.publish(config_topic, json.dumps(config), retain=True)
            logger().debug(f"Published discovery config for {sensor['name']}")

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

        client.disconnect()
        logger().info("Successfully published all MQTT Discovery configs")

    except Exception as e:
        logger().error(f"Error publishing discovery configs: {e}")
        raise


def publish_data(data, topic):
    """Publish sensor data to MQTT"""
    client = get_mqtt_client()

    try:
        mqtt_broker = os.environ.get('HUAWEI_MODBUS_MQTT_BROKER')
        mqtt_port = int(os.environ.get('HUAWEI_MODBUS_MQTT_PORT', '1883'))

        client.connect(mqtt_broker, mqtt_port, 60)

        # Add metadata
        data['last_update'] = int(time.time())
        data['status'] = 'online'

        # Publish data
        client.publish(topic, json.dumps(data))

        client.disconnect()
        logger().debug(f"Published data to MQTT topic {topic}")

    except Exception as e:
        logger().error(f"Error publishing data to MQTT: {e}")
        raise


def publish_status(status, topic):
    """Publish status message (online/offline)"""
    client = get_mqtt_client()

    try:
        mqtt_broker = os.environ.get('HUAWEI_MODBUS_MQTT_BROKER')
        mqtt_port = int(os.environ.get('HUAWEI_MODBUS_MQTT_PORT', '1883'))

        client.connect(mqtt_broker, mqtt_port, 60)
        client.publish(f"{topic}/status", status, retain=True)
        client.disconnect()

        logger().debug(f"Published status '{status}' to MQTT")

    except Exception as e:
        logger().error(f"Error publishing status to MQTT: {e}")
