# Huawei Solar Modbus → Home Assistant via MQTT

🌐 **English** | 🇩🇪 [Deutsch](README_de.md)

[![aarch64](https://img.shields.io/badge/aarch64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![amd64](https://img.shields.io/badge/amd64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armhf](https://img.shields.io/badge/armhf-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armv7](https://img.shields.io/badge/armv7-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![i386](https://img.shields.io/badge/i386-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![Repository](https://img.shields.io/badge/Add%20to%20Home%20Assistant-Repository-blue)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![release](https://img.shields.io/github/v/release/arboeh/homeassistant-huawei-solar-addon?display_name=tag)](https://github.com/arboeh/homeassistant-huawei-solar-addon/releases/latest)

Home Assistant Add-on: Huawei SUN2000 Inverter via Modbus TCP → MQTT with Auto-Discovery.

## Features
- Direct Modbus TCP connection to Huawei Inverter
- Automatic Home Assistant MQTT Discovery
- Battery monitoring (SOC, charge/discharge power, daily energy)
- PV String monitoring (PV1/PV2, optional PV3/PV4)
- Grid monitoring (import/export, 3-phase voltage)
- Energy yield tracking (daily/total)
- Inverter status, temperature, efficiency
- Online/offline status with heartbeat monitoring
- Automatic reconnection on communication errors
- Robust error handling for unknown register values

## Installation
1. [![Add Repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Farboeh%2Fhomeassistant-huawei-solar-addon)

2. Install "Huawei Solar Modbus to MQTT" from Add-on Store
3. Configure the add-on (see below)
4. Start the add-on
5. Entities auto-appear in Home Assistant via MQTT Discovery

## Configuration

### Modbus Settings
- **modbus_host**: IP address of your Huawei inverter (e.g., `192.168.1.100`)
- **modbus_port**: Modbus TCP port (default: `502`)
- **modbus_device_id**: Modbus slave ID (default: `1`)

### MQTT Settings
- **mqtt_host**: MQTT broker address (default: `core-mosquitto` for HA built-in broker)
- **mqtt_port**: MQTT broker port (default: `1883`)
- **mqtt_user**: MQTT username (leave empty if authentication is disabled)
- **mqtt_password**: MQTT password (leave empty if authentication is disabled)
- **mqtt_topic**: Base topic for MQTT messages (default: `huawei-solar`)

### Advanced Settings
- **debug**: Enable debug logging (default: `false`)
- **status_timeout**: Seconds after which the status is set to offline if no successful read (default: `180`)
- **poll_interval**: Interval in seconds between data reads (default: `60`)

### Example Configuration

    modbus_host: 192.168.1.100
    modbus_port: 502
    modbus_device_id: 1
    mqtt_host: core-mosquitto
    mqtt_port: 1883
    mqtt_user: ""
    mqtt_password: ""
    mqtt_topic: huawei-solar
    debug: false
    status_timeout: 180
    poll_interval: 60

## MQTT Topics
- `<mqtt_topic>` - JSON data with all inverter values
- `<mqtt_topic>/status` - Status (online/offline)
- `homeassistant/sensor/<mqtt_topic>/*` - Auto-discovery topics

## Monitored Data
- Battery state of charge (SOC)
- Battery charge/discharge power
- PV string voltages and currents (PV1-PV4)
- Grid power (import/export)
- Grid voltage (3-phase)
- Daily and total energy yield
- Inverter temperature
- Inverter efficiency
- Device status

## Troubleshooting
- Ensure Modbus TCP is enabled on your Huawei inverter
- Check network connectivity between Home Assistant and inverter
- Verify MQTT broker is running and accessible
- Enable debug mode for detailed logging
- Check the add-on logs for error messages

## Support
- [Home Assistant Community](https://community.home-assistant.io)
- [GitHub Issues](https://github.com/arboeh/homeassistant-huawei-solar-addon/issues)

**Based on [huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)**
