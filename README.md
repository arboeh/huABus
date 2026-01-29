<img src="logo.svg" alt="jaABlu" height="40"/>

### Huawei Solar Modbus → Home Assistant via MQTT + Auto-Discovery

🇬🇧 **English** | [🇩🇪 Deutsch](README.de.md)

[![release](https://img.shields.io/github/v/release/arboeh/huABus?display_name=tag)](https://github.com/arboeh/huABus/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/arboeh/huABus/blob/main/LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-41BDF5?logo=home-assistant)](https://www.home-assistant.io/)  
[![aarch64](https://img.shields.io/badge/aarch64-yes-green.svg)](https://github.com/arboeh/huABus)
[![amd64](https://img.shields.io/badge/amd64-yes-green.svg)](https://github.com/arboeh/huABus)
[![armhf](https://img.shields.io/badge/armhf-yes-green.svg)](https://github.com/arboeh/huABus)
[![armv7](https://img.shields.io/badge/armv7-yes-green.svg)](https://github.com/arboeh/huABus)
[![i386](https://img.shields.io/badge/i386-yes-green.svg)](https://github.com/arboeh/huABus)

> **⚠️ IMPORTANT: Single Modbus Connection Limit**  
> Huawei inverters allow **only ONE active Modbus TCP connection**. This is a common beginner mistake when integrating Huawei solar systems into smart home environments.
>
> **Before installing this add-on:**
>
> - ✅ Disable or remove any other Huawei Solar integrations (official wlcrs/huawei_solar, HACS integrations, etc.)
> - ✅ Ensure no other software is accessing Modbus TCP (monitoring tools, apps, other Home Assistant instances)
> - ✅ Note: FusionSolar Cloud may show "Abnormal communication" when Modbus is active - this is expected
>
> Running multiple Modbus connections simultaneously will cause **connection timeouts and data loss** for all clients!

**Version 1.6.2** – 58 Essential Registers, 69+ entities, ~2–5 s cycle time  
**Changelog** - [CHANGELOG.md](huawei-solar-modbus-mqtt/CHANGELOG.md)

## Features

- **Modbus TCP → MQTT:** 69+ entities with Auto-Discovery
- **Complete Monitoring:** Battery, PV (1-4), Grid (3-phase), Yield, Grid Power
- **total_increasing Filter:** Prevents false counter resets in Home Assistant energy statistics
  - Warmup period (60s) for stable filter initialization
  - Automatic protection against Modbus read errors
- **TRACE Log Level (NEW):** Ultra-detailed logging for deep debugging with Modbus byte arrays
- **Comprehensive Test Suite (NEW):** 43 tests covering all critical functionality
  - Unit tests for filter logic
  - Integration tests for component interaction
  - E2E tests for complete workflows
  - Regression tests for bug fixes
- **Performance:** ~2-5s cycle, configurable (30-60s recommended)
- **Error Tracking:** Intelligent error aggregation with downtime tracking
- **MQTT Stability:** Connection wait loop and retry logic for reliable publishing
- **Optimized Logging:** Bashio log level synchronization with filter status indicators
- **Cross-Platform:** Supports all major architectures (aarch64, amd64, armhf, armv7, i386)

## 🚀 Quick Start

**New to huABus?** Check out our [5-minute Quick Start Guide](huawei-solar-modbus-mqtt/DOCS.md#-quick-start-5-minutes) for:

- ✅ Step-by-step installation with expected outputs
- ✅ Connection troubleshooting (Slave ID issues, timeouts)
- ✅ Clear success indicators
- ✅ Common first-time problems solved

Perfect for first-time users! Experienced users can jump directly to [Configuration](#configuration).

## Comparison: wlcrs/huawei_solar vs. This Add-on

Both solutions use the same `huawei-solar` library but target different use cases:

**wlcrs/huawei_solar** (Native HA Integration):

- ✅ Battery control (charge/discharge commands)
- ✅ GUI configuration
- ✅ Optimizer monitoring
- ✅ RS485 serial support

**This Add-on** (MQTT Bridge):

- ✅ MQTT-native (data accessible to [EVCC](https://evcc.io/), Node-RED, Grafana, etc.)
- ✅ total_increasing filter (protects energy statistics from false resets)
- ✅ Advanced error tracking & performance monitoring
- ✅ Fast 2-5s cycle times
- ✅ Read-only monitoring

**Important:** Both share the same limitation - Huawei inverters allow **only ONE Modbus connection**. To use both simultaneously, you need a Modbus Proxy.

**When to use which?**

- **wlcrs:** Battery control + native HA integration
- **This add-on:** MQTT monitoring + external system integration

## Screenshots

### Home Assistant Integration

![Diagnostic Entities](screenshots/diagnostics.png)

_Diagnostic entities showing inverter status, temperature, and battery information_

![Sensor Overview](screenshots/sensors.png)

_Complete sensor overview with real-time power, energy, and grid data_

![MQTT Device Info](screenshots/mqtt-info.png)

_MQTT device integration details_

## Installation

1. [![Add Repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Farboeh%2FhuABus)
2. Install "huABus | Huawei Solar Modbus to MQTT" → Start
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

### MQTT Topics

- **Sensor Data (JSON)**: `huawei-solar` (or your configured topic)  
  All sensor data as JSON object with `last_update` timestamp.
- **Status (online/offline)**: `huawei-solar/status`  
  Used for binary sensor, `availability_topic`, and last will testament.

### Example MQTT Payload

Published to topic `huawei-solar`:

```json
{
  "power_active": 1609,
  "power_input": 2620,
  "battery_soc": 32,
  "battery_power": 1020,
  "meter_power_active": 50,
  "voltage_grid_A": 239.3,
  "inverter_temperature": 32.4,
  "inverter_status": "On-grid",
  "model_name": "SUN2000-6KTL-M1",
  "last_update": 1768649491
   ...
   ..
   .
}
```

_Complete example with all 58+ data points: [examples/mqtt_payload.json](examples/mqtt_payload.json)_

## Important Entities

| Category    | Sensors                                                                                    |
| ----------- | ------------------------------------------------------------------------------------------ |
| **Power**   | `solar_power`, `input_power`, `grid_power`, `battery_power`, `pv1-4_power`                 |
| **Energy**  | `daily_yield`, `total_yield`_, `grid_exported/imported`_                                   |
| **Battery** | `battery_soc`, `charge/discharge_today`, `total_charge/discharge`\*, `bus_voltage/current` |
| **Grid**    | `voltage_phase_a/b/c`, `line_voltage_ab/bc/ca`, `frequency`                                |
| **Meter**   | `meter_power_phase_a/b/c`, `meter_current_a/b/c`, `meter_reactive_power`                   |
| **Device**  | `model_name`, `serial_number`, `efficiency`, `temperature`, `rated_power`                  |
| **Status**  | `inverter_status`, `battery_status`, `meter_status`                                        |

_\* Sensors marked with asterisk are protected by total_increasing filter against false counter resets_

## What's new in 1.6.2?

**TRACE Log Level, Tests & Filter Improvements**

- **New**: Ultra-detailed TRACE logging for maximum debugging
  - Shows all Modbus bytes, register mappings, library internals
  - Perfect for protocol-level debugging and connection analysis
  - pymodbus and huawei_solar libraries set to DEBUG when TRACE is active

- **New**: Comprehensive test suite with 43 tests
  - Unit tests for filter logic (17 tests)
  - Integration tests for components (10 tests)
  - E2E tests for complete workflows (7 tests)
  - Warmup tests for startup scenarios (6 tests)
  - Regression tests for Issue #7 (3 tests)
  - Automated CI/CD pipeline with GitHub Actions
- **Improved**: Filter with warmup period (60s)
  - Filter learns valid baseline values after restart
  - Prevents false filtering with unknown state
  - Visual indicator: `🔥 Warmup active (42/60s)`
  - Better stability after inverter restart

- **Improved**: German and English UI translations
  - Concrete examples (IP addresses, hostnames)
  - Helpful hints ("Use core-mosquitto for Mosquitto add-on")
  - All log levels explained with use cases
  - Better beginner support

- **Fixed**: Documentation localization
  - `DOCS_de.md` → `DOCS.de.md` (correct Home Assistant format)
  - German users now automatically see German documentation

**Previous (1.6.1):** Critical filter timing bug fix  
**Previous (1.6.0):** `total_increasing` filter for energy statistics

## Troubleshooting

### ⚠️ Multiple Modbus Connections (Most Common Issue!)

**Symptom:** Connection timeouts, "No response received", intermittent data loss

**Cause:** Huawei inverters support **only ONE active Modbus TCP connection**

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
**Performance:** Increase Poll Interval to 60s if cycle warnings appear  
**Filter Activity:** Occasional filtering (1-2 per hour) is normal; frequent filtering indicates connection issues - enable DEBUG mode

**Logs:** Add-ons → Huawei Solar Modbus to MQTT → Log Tab

## Support & Issues

Found a bug or have a feature request? Please use our [GitHub Issue Templates](https://github.com/arboeh/huABus/issues/new/choose) for structured reporting.

## Documentation

- 🇬🇧 **[DOCS.md](huawei-solar-modbus-mqtt/DOCS.md)** - Complete Documentation
- 🇩🇪 **[DOCS.de.md](huawei-solar-modbus-mqtt/DOCS.de.md)** - Vollständige Dokumentation

## Credits

**Based on the idea of:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)  
**Uses Huawei modbus library:** [wlcrs/huawei-solar-lib](https://github.com/wlcrs/huawei-solar-lib)  
**Developed by:** [arboeh](https://github.com/arboeh) | **License:** MIT
