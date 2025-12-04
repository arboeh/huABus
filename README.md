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
- Battery (SOC, charge/discharge power, daily energy)
- PV Strings (PV1/PV2, optional PV3/PV4)
- Grid (import/export, 3-phase voltage)
- Energy yield (daily/total)
- Inverter status, temperature, efficiency
- Online/offline status with heartbeat
- Automatic reconnection

## Installation
1. **[Add Repository](https://github.com/arboeh/homeassistant-huawei-solar-addon)**
2. Install "Huawei Solar Modbus to MQTT" from Add-on Store
3. Configure and start
4. Entities auto-appear in HA

## Configuration

    modbushost: 192.168.1.100
    modbusport: 502
    modbusdeviceid: 1
    mqtttopic: huawei-solar
    debug: false
    statustimeout: 180
    pollinterval: 60

    
## MQTT Topics
- `huawei-solar` (JSON data)
- `huawei-solar/status` (online/offline)

## Support
- [GitHub Issues](https://github.com/arboeh/homeassistant-huawei-solar-addon/issues)
- [HA Community](https://community.home-assistant.io)

**Based on [huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)**
