# Huawei Solar Modbus → Home Assistant via MQTT

🌐 **English** | 🇩🇪 [Deutsch](README_de.md)

[![aarch64](https://img.shields.io/badge/aarch64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![amd64](https://img.shields.io/badge/amd64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armhf](https://img.shields.io/badge/armhf-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armv7](https://img.shields.io/badge/armv7-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![i386](https://img.shields.io/badge/i386-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![release](https://img.shields.io/github/v/release/arboeh/homeassistant-huawei-solar-addon?display_name=tag)](https://github.com/arboeh/homeassistant-huawei-solar-addon/releases/latest)

Home Assistant Add-on for Huawei SUN2000 inverters via Modbus TCP → MQTT with Auto-Discovery.

**Version 1.3.0** - 47 Registers, 59 Entities, ~5s Cycle-Time

## Features

- **Modbus TCP → MQTT:** 59 entities with Auto-Discovery
- **Complete Monitoring:** Battery, PV (1-4), Grid (3-phase), Yield, Grid Power
- **EVCC-compatible:** Grid Power for smart EV charging ⚡
- **Performance:** ~5s cycle, configurable (30-60s recommended)

## Installation

1. [![Add Repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Farboeh%2Fhomeassistant-huawei-solar-addon)
2. Install "Huawei Solar Modbus to MQTT" → Start
3. **Settings → Devices & Services → MQTT → "Huawei Solar Inverter"**

## Configuration

    modbus_host: "192.168.1.100" # Inverter IP
    modbus_device_id: 1 # Slave ID (1 or 16)
    mqtt_topic: "huawei-solar"
    poll_interval: 30 # Seconds
    log_level: "INFO"

**Auto-MQTT:** Leave `mqtt_host` empty → uses HA MQTT Service automatically

## Important Entities

| Category | Sensors |
|----------|---------|
| **Power** | `solar_power`, `grid_power` ⚡, `battery_power`, `pv1-4_power` |
| **Energy** | `daily_yield`, `total_yield`, `grid_exported/imported` |
| **Battery** | `battery_soc`, `charge/discharge_today`, `bus_voltage/current` |
| **Grid** | `voltage_phase_a/b/c`, `line_voltage_ab/bc/ca`, `frequency` |
| **Device** | `model_name`, `serial_number`, `efficiency`, `temperature` |

## Troubleshooting

**No Connection:** Enable Modbus TCP, verify IP/Slave-ID (try 1/16/0), set `log_level: DEBUG`  
**MQTT Errors:** Use `mqtt_host: "core-mosquitto"`, leave credentials empty  
**Performance:** Increase `poll_interval: 60` if cycle warnings appear

**Logs:** Add-ons → Huawei Solar → Log Tab

## Credits

**Forked from:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)  
**Developed by:** [arboeh](https://github.com/arboeh) | **License:** MIT
