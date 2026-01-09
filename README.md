# Huawei Solar Modbus → Home Assistant via MQTT

🌐 **English** | 🇩🇪 [Deutsch](README_de.md)

[![aarch64](https://img.shields.io/badge/aarch64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![amd64](https://img.shields.io/badge/amd64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armhf](https://img.shields.io/badge/armhf-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armv7](https://img.shields.io/badge/armv7-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![i386](https://img.shields.io/badge/i386-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![release](https://img.shields.io/github/v/release/arboeh/homeassistant-huawei-solar-addon?display_name=tag)](https://github.com/arboeh/homeassistant-huawei-solar-addon/releases/latest)

> **⚠️ IMPORTANT: Single Modbus Connection Limit**  
> Huawei inverters allow **only ONE active Modbus TCP connection**. This is a common beginner mistake when integrating Huawei solar systems into smart home environments.
>
> **Before installing this add-on:**
> - ✅ Disable or remove any other Huawei Solar integrations (official wlcrs/huawei_solar, HACS integrations, etc.)
> - ✅ Ensure no other software is accessing Modbus TCP (monitoring tools, apps, other Home Assistant instances)
> - ✅ Note: FusionSolar Cloud may show "Abnormal communication" when Modbus is active - this is expected
>
> Running multiple Modbus connections simultaneously will cause **connection timeouts and data loss** for all clients!

Home Assistant Add-on for Huawei SUN2000 inverters via Modbus TCP → MQTT with Auto-Discovery.

**Version 1.4.2** – 58 Essential Registers, 69+ entities, ~2–5 s cycle time  
**Changelog** - [CHANGELOG.md](huawei-solar-modbus-mqtt/CHANGELOG.md)

## Features

- **Modbus TCP → MQTT:** 69+ entities with Auto-Discovery
- **Complete Monitoring:** Battery, PV (1-4), Grid (3-phase), Yield, Grid Power
- **Performance:** ~2-5s cycle, configurable (30-60s recommended)
- **Error Tracking:** Intelligent error aggregation with downtime tracking
- **Optimized Logging:** Bashio log level synchronization
- **Cross-Platform:** Supports all major architectures (aarch64, amd64, armhf, armv7, i386)

## Installation

1. [![Add Repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Farboeh%2Fhomeassistant-huawei-solar-addon)
2. Install "Huawei Solar Modbus to MQTT" → Start
3. **Settings → Devices & Services → MQTT → "Huawei Solar Inverter"**

## Configuration

Add-on configuration via Home Assistant UI with translated field names:

- **Modbus Host:** IP address of the Huawei Solar inverter (e.g. `192.168.1.100`)
- **Modbus Port:** Port for Modbus connection (default: `502`)
- **Slave ID:** Modbus Slave ID of the inverter (typically `1`, sometimes `16` or `0`)
- **MQTT Broker:** Hostname or IP address of the MQTT broker (e.g. `core-mosquitto`)
- **MQTT Port:** Port of the MQTT broker (default: `1883`)
- **MQTT Username:** Username for MQTT authentication (optional)
- **MQTT Password:** Password for MQTT authentication (optional)
- **MQTT Topic:** Base topic for MQTT messages (default: `huawei-solar`)
- **Log Level:** Verbosity level of logging (`DEBUG` | `INFO` | `WARNING` | `ERROR`)
- **Status Timeout:** Timeout in seconds for status checks (30-600, default: `180`)
- **Poll Interval:** Interval in seconds between Modbus polls (10-300, default: `30`)

**Auto-MQTT:** Leave MQTT Broker, Username and Password empty → uses HA MQTT Service automatically

## Important Entities

| Category    | Sensors                                                                                  |
| ----------- | ---------------------------------------------------------------------------------------- |
| **Power**   | `solar_power`, `input_power`, `grid_power`, `battery_power`, `pv1-4_power`               |
| **Energy**  | `daily_yield`, `total_yield`, `grid_exported/imported`                                   |
| **Battery** | `battery_soc`, `charge/discharge_today`, `total_charge/discharge`, `bus_voltage/current` |
| **Grid**    | `voltage_phase_a/b/c`, `line_voltage_ab/bc/ca`, `frequency`                              |
| **Meter**   | `meter_power_phase_a/b/c`, `meter_current_a/b/c`, `meter_reactive_power`                 |
| **Device**  | `model_name`, `serial_number`, `efficiency`, `temperature`, `rated_power`                |
| **Status**  | `inverter_status`, `battery_status`, `meter_status`                                      |

## What's new in 1.4.2?

**Repository Maintenance:** Added `.gitattributes`, `.editorconfig`, and `.gitignore` for better development workflow; normalized all files to LF line endings (prevents Linux/Docker compatibility issues)

**Fixed:** Corrected `pymodbus` dependency version requirement; enhanced `.dockerignore` to include required Home Assistant documentation files

**Documentation:** Added GitHub Issue Templates for structured bug reports and feature requests; troubleshooting guide for connection timeout issues

**Previous (1.4.1):** Enhanced startup logging with emoji icons, visual separators, dynamic log level synchronization

**Previous (1.4.0):** Error tracker with downtime tracking, improved logging architecture, poll interval default optimized to 30s

## Troubleshooting

### ⚠️ Multiple Modbus Connections (Most Common Issue!)

**Symptom:** Connection timeouts, "No response received", intermittent data loss

**Cause:** Huawei inverters support **only ONE Modbus TCP connection** at a time

**Solution:**
1. Check **Settings → Devices & Services** for other Huawei integrations
2. Remove or disable:
   - Official `wlcrs/huawei_solar` integration
   - Any HACS-based Huawei integrations
   - Third-party monitoring software
3. If using **FusionSolar Cloud**: Note that active Modbus may show "Abnormal communication" in the app - this is normal and expected
4. Only **ONE** system can connect to Modbus at any time

### Other Common Issues

**No Connection:** Enable Modbus TCP, verify IP/Slave-ID (try 1/16/0), set Log Level to `DEBUG`  
**Connection Timeouts:** Try different Slave IDs (`0`, `1`, `16`); increase Poll Interval to 60s; check if FusionSolar Cloud is blocking Modbus access  
**MQTT Errors:** Set MQTT Broker to `core-mosquitto`, leave credentials empty  
**Performance:** Increase Poll Interval to 60 if cycle warnings appear

**Logs:** Add-ons → Huawei Solar Modbus to MQTT → Log Tab

## Support & Issues

Found a bug or have a feature request? Please use our [GitHub Issue Templates](https://github.com/arboeh/homeassistant-huawei-solar-addon/issues/new/choose) for structured reporting.

## Documentation

- **[DOCS.md](huawei-solar-modbus-mqtt/DOCS.md)** - Complete documentation (German)
- **[CHANGELOG.md](huawei-solar-modbus-mqtt/CHANGELOG.md)** - Version history

## Credits

**Based on the idea of:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)  
**Uses Huawei modbus library:** [wlcrs/huawei-solar-lib](https://github.com/wlcrs/huawei-solar-lib)  
**Developed by:** [arboeh](https://github.com/arboeh) | **License:** MIT