# Huawei Solar Modbus → Home Assistant via MQTT

🌐 **English** | 🇩🇪 [Deutsch](README.de.md)

[![aarch64](https://img.shields.io/badge/aarch64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![amd64](https://img.shields.io/badge/amd64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armhf](https://img.shields.io/badge/armhf-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armv7](https://img.shields.io/badge/armv7-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![i386](https://img.shields.io/badge/i386-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![release](https://img.shields.io/github/v/release/arboeh/homeassistant-huawei-solar-addon?display_name=tag)](https://github.com/arboeh/homeassistant-huawei-solar-addon/releases/latest)

Home Assistant Add-on for Huawei SUN2000 inverters via Modbus TCP → MQTT with automatic discovery.

**Version 1.1.2** - Performance optimized (Cycle-Time < 3s, only 21 Essential Registers)

## Features

- **Modbus TCP** connection to Huawei SUN2000 inverter
- **MQTT Auto-Discovery** for Home Assistant
- **Monitoring:** Battery (SOC, Power, Energy), PV strings, Grid (Import/Export), Yield, Status
- **Online/Offline Status** with Heartbeat & MQTT LWT
- **Performance:** Optimized register reads, typical 1-3s cycle time
- **Configurable:** Log levels (DEBUG/INFO/WARNING/ERROR), poll interval, timeouts

## Installation

1. [![Add Repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Farboeh%2Fhomeassistant-huawei-solar-addon)

2. Add-on Store → Install "Huawei Solar Modbus to MQTT"
3. Configure (see below)
4. Start
5. Entities appear automatically at: **Settings → Devices & Services → MQTT → "Huawei Solar Inverter"**

## Configuration

### Minimal (recommended)

    modbus_host: "192.168.1.100"
    modbus_device_id: 1
    poll_interval: 30

### Complete

    Modbus
    modbus_host: "192.168.1.100" # Inverter IP address
    modbus_port: 502
    modbus_device_id: 1 # Slave ID (usually 1, sometimes 16)

    MQTT (Auto-Discovery from HA)
    mqtt_host: "core-mosquitto" # Leave empty for auto
    mqtt_port: 1883
    mqtt_user: "" # Empty = Auto from HA
    mqtt_password: ""
    mqtt_topic: "huawei-solar"

    Performance & Logging
    poll_interval: 30 # Recommendation: 30-60s
    status_timeout: 180
    log_level: "INFO" # DEBUG/INFO/WARNING/ERROR


## MQTT Topics

- `huawei-solar` - JSON data with all values
- `huawei-solar/status` - Status (online/offline)

## Main Entities

**Power:** `solar_power`, `grid_power`, `battery_power`, `pv1_power`  
**Energy:** `solar_daily_yield`, `solar_total_yield`, `grid_energy_exported/imported`  
**Battery:** `battery_soc`, `battery_status`  
**Grid:** `grid_voltage_phase_a/b/c`, `grid_frequency`  
**Status:** `huawei_solar_status` (binary_sensor), `inverter_status`

**Many additional diagnostic entities** are disabled by default and can be enabled in HA.

## Troubleshooting

### Modbus Errors
- Enable Modbus TCP on inverter (web interface)
- Check IP address
- Test Slave IDs: `1`, `16`, `0`
- Use `log_level: DEBUG` for details

### MQTT Errors
- Check MQTT broker status (Add-ons → Mosquitto)
- Use `mqtt_host: "core-mosquitto"`
- Leave credentials empty for auto-discovery

### Performance
- Increase `poll_interval` if warnings appear
- Recommended values: 30-60s (default), 120s (slow network)

**View logs:** Settings → Add-ons → Huawei Solar → Log

## Changelog Highlights

### 1.1.2 (2025-12-08)
Code refactoring, dynamic Python version, health check, improved MQTT fallbacks

### 1.1.1 (2025-12-08)
Essential Registers (only 21 instead of 500+), 94% reduction, cycle < 3s

### 1.1.0 (2025-12-08)
Parallel batch reads, 8x performance boost (240s → 30s)

[Full Changelog](CHANGELOG.md)

## Documentation & Support

- **[Full Documentation (English)](DOCS.md)** - Detailed guide, troubleshooting, performance tuning
- **[Home Assistant Community](https://community.home-assistant.io)** - Discussions & help

## Credits

**Based on:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)  
**Developed by:** [arboeh](https://github.com/arboeh)  
**License:** MIT
