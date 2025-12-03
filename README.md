# Home Assistant Add-on: Huawei Solar Modbus to MQTT

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]
![Supports armhf Architecture][armhf-shield]
![Supports armv7 Architecture][armv7-shield]
![Supports i386 Architecture][i386-shield]

Query Huawei Solar Inverter Sun2000 via Modbus TCP and publish to MQTT with automatic Home Assistant discovery.

## About

This add-on connects to your Huawei Solar inverter via Modbus TCP and publishes all relevant data to MQTT. All entities are automatically discovered in Home Assistant.

### Features

- 🔌 Direct Modbus TCP connection to Huawei inverter
- 📡 Automatic MQTT discovery for Home Assistant
- 🔋 Battery monitoring (SOC, charge/discharge power)
- ☀️ PV string monitoring (voltage, current, power)
- 📊 Grid monitoring (import/export, voltage, frequency)
- 🌡️ Temperature monitoring
- 📈 Energy statistics (daily yield, total yield)
- 🔄 Automatic reconnection on errors
- 📝 Configurable via Home Assistant UI

## Installation

1. Add this repository to your Home Assistant instance:
   
   [![Add Repository][repository-badge]][repository-url]

2. Click on "Huawei Solar Modbus to MQTT" in the add-on store
3. Click "Install"
4. Configure the add-on (see Configuration section)
5. Start the add-on
6. Check the logs for any errors
7. Entities will appear automatically in Home Assistant

## Configuration

modbus_host: "192.168.1.100"  
modbus_port: 502  
modbus_device_id: 1  
mqtt_topic: "huawei-solar"  
debug: false  

### Option: `modbus_host`

The IP address of your Huawei Solar inverter.

### Option: `modbus_port`

Modbus TCP port (default: 502).

### Option: `modbus_device_id`

Modbus Slave ID of your inverter (typically 1, sometimes 16 or 0).

### Option: `mqtt_topic`

MQTT topic prefix for publishing data (default: "huawei-solar").

### Option: `debug`

Enable debug logging (default: false).

## MQTT Configuration

The add-on automatically uses the MQTT broker configured in Home Assistant. No additional MQTT configuration needed!
## License

MIT License

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg
[issues]: https://github.com/arboeh/homeassistant-huawei-solar-addon/issues
[forum]: https://community.home-assistant.io
[repository-badge]: https://img.shields.io/badge/Add%20repository%20to%20Home%20Assistant-41BDF5?logo=home-assistant&style=for-the-badge
[repository-url]: https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Farboeh%2Fhomeassistant-huawei-solar-addon
