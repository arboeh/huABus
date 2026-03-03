<img src="images/logo.svg" alt="huABus" height="40"/>

### Huawei Solar Modbus to Home Assistant via MQTT + Auto-Discovery

🇬🇧 **English** | [🇩🇪 Deutsch](README.de.md)

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-41BDF5?logo=home-assistant)](https://www.home-assistant.io/)
[![release](https://img.shields.io/github/v/release/arboeh/huABus?display_name=tag)](https://github.com/arboeh/huABus/releases/latest)
[![Tests](https://github.com/arboeh/huABus/workflows/Tests/badge.svg)](https://github.com/arboeh/huABus/actions)
[![codecov](https://codecov.io/gh/arboeh/huABus/branch/main/graph/badge.svg)](https://codecov.io/gh/arboeh/huABus)
[![Security](https://img.shields.io/badge/Security-Policy-blue?logo=github)](https://github.com/arboeh/huABus/blob/main/SECURITY.md)  
[![maintained](https://img.shields.io/maintenance/yes/2026)](https://github.com/arboeh/huABus/graphs/commit-activity)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/arboeh/huABus/blob/main/LICENSE)  
[![aarch64](https://img.shields.io/badge/aarch64-yes-green.svg)](https://github.com/arboeh/huABus)
[![amd64](https://img.shields.io/badge/amd64-yes-green.svg)](https://github.com/arboeh/huABus)
[![armhf](https://img.shields.io/badge/armhf-yes-green.svg)](https://github.com/arboeh/huABus)
[![armv7](https://img.shields.io/badge/armv7-yes-green.svg)](https://github.com/arboeh/huABus)
[![i386](https://img.shields.io/badge/i386-yes-green.svg)](https://github.com/arboeh/huABus)

> **⚠️ IMPORTANT: Single Modbus Connection Limit**
> Huawei inverters allow **only ONE active Modbus TCP connection**. This is a common beginner mistake.
>
> **Before installing:**
>
> - ✅ Remove any other Huawei Solar integrations (wlcrs/huawei_solar, HACS, etc.)
> - ✅ Disable monitoring tools and apps with Modbus access
> - ✅ Note: FusionSolar Cloud may show "Abnormal communication" - this is expected
>
> Multiple connections cause **timeouts and data loss**!

**67 Essential Registers, 69+ entities, ~3-8s cycle time**
**Changelog:** [CHANGELOG.md](huawei_solar_modbus_mqtt/CHANGELOG.md)

## 🔌 Compatible Inverters

### ✅ Fully Supported

| Series            | Models                            | Status                    |
| ----------------- | --------------------------------- | ------------------------- |
| **SUN2000**       | 2KTL - 100KTL (all power classes) | ✅ **Tested & Confirmed** |
| **SUN2000-L0/L1** | Hybrid series (2-10kW)            | ✅ Confirmed              |
| **SUN3000**       | All models                        | ⚠️ Compatible (untested)  |
| **SUN5000**       | Commercial series                 | ⚠️ Compatible (untested)  |

### 📋 Requirements

- **Firmware:** V100R001C00SPC200+ (≈2023 or later)
- **Interface:** Modbus TCP enabled (Port 502 or 6607)
- **Dongle:** Smart Dongle-WLAN-FE or SDongle A-05

### 🧪 Compatibility Status

Have a **SUN3000** or **SUN5000** inverter? [Help us test!](https://github.com/arboeh/huABus/issues/new?assignees=&labels=compatibility%2Cenhancement&template=compatibility_report.yaml&title=%5BCompatibility%5D+)

**Community reports:**

| Model            | Firmware          | Status           | Reporter |
| ---------------- | ----------------- | ---------------- | -------- |
| SUN2000-10KTL-M2 | V100R001C00SPC124 | ✅ Working       | @arboeh  |
| SUN2000-5KTL-L1  | V100R001C00SPC200 | ⚠️ Needs testing | -        |
| SUN3000-20KTL    | -                 | ❓ Untested      | -        |

_Missing registers (battery/meter) are handled gracefully - your inverter will work even without all sensors._

## Features

- **Automatic Slave ID Detection:** No more guessing! Tries common values (1, 2, 100) automatically
- **Modbus TCP → MQTT:** 69+ entities with Auto-Discovery
- **Complete Monitoring:** Battery, PV (1-4), Grid (3-phase), Energy counters
- **Total Increasing Filter:** Prevents false counter resets in energy statistics
  - No warmup phase - immediate protection
  - Automatic reset on connection errors
  - Visible in logs with 20-cycle summaries
- **Auto MQTT Configuration:** Automatically uses Home Assistant MQTT credentials
- **TRACE Log Level:** Ultra-detailed debugging with Modbus byte arrays
- **Comprehensive Test Suite:** 86% code coverage with unit, integration, and E2E tests
- **Performance:** ~2-5s cycle, configurable poll interval (30-60s recommended)
- **Error Tracking:** Intelligent aggregation with downtime tracking
- **MQTT Stability:** Connection wait loop and retry logic
- **Cross-Platform:** All major architectures (aarch64, amd64, armhf, armv7, i386)

## 🚀 Quick Start

**New to huABus?** Installation is now easier than ever:

1. [![Add Repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Farboeh%2FhuABus)
2. Install "huABus | Huawei Solar Modbus to MQTT"
3. **Minimal Configuration:**
   ```yaml
   modbus_host: 192.168.1.100 # Your inverter IP
   modbus_auto_detect_slave_id: true # Automatic detection
   log_level: INFO
   ```
4. Start the addon - Slave ID will be detected automatically!
5. **Settings → Devices & Services → MQTT → "Huawei Solar Inverter"**

**Expected startup logs:**

```
INFO - Inverter: 192.168.1.100:502 (Slave ID: auto-detect)
INFO - Trying Slave ID 1... ✅
INFO - Connected (Slave ID: 1)
INFO - Registers: 67 essential
INFO - Published - PV 4500W ...
```

**Common first-time issues:**

| Symptom            | Quick Fix                             |
| ------------------ | ------------------------------------- |
| All Slave IDs fail | Check inverter IP, enable Modbus TCP  |
| No sensors appear  | Wait 30s, refresh MQTT integration    |
| Connection refused | Verify Modbus TCP enabled in inverter |

## Comparison: wlcrs/huawei_solar vs. This Addon

The `wlcrs/huawei_solar` is a **native Home Assistant integration**, while this is a **Home Assistant Addon**. Both use the same `huawei-solar` library but target different use cases:

| Feature                 | wlcrs/huawei_solar<br>(Integration) | This Addon<br>(MQTT Bridge)  |
| ----------------------- | ----------------------------------- | ---------------------------- |
| Installation            | Via HACS or manual                  | Via Addon Store              |
| Battery control         | ✅                                  | ❌ (read-only)               |
| MQTT-native             | ❌                                  | ✅                           |
| Auto Slave ID detection | ❌                                  | ✅                           |
| Total Increasing filter | ❌                                  | ✅                           |
| External integrations   | Limited                             | ✅ (EVCC, Node-RED, Grafana) |
| Cycle time              | Variable                            | 2-5s                         |
| Error tracking          | Basic                               | Advanced                     |
| Configuration           | UI or YAML                          | Addon UI                     |

**Important:** Both share the same limitation - only **ONE Modbus connection**. To use both simultaneously, you need a Modbus Proxy.

**When to use which?**

- **wlcrs (Integration):** Battery control + native HA integration + direct entity access
- **This Addon (MQTT Bridge):** MQTT monitoring + external system integration + automatic Slave ID detection + better error tracking

## Screenshots

### Home Assistant Integration

![Diagnostic Entities](images/diagnostics.png)  
_Diagnostic entities showing inverter status, temperature, and battery information_

![Sensor Overview](images/sensors.png)  
_Complete sensor overview with real-time power, energy, and grid data_

![MQTT Device Info](images/mqtt_info.png)  
_MQTT device integration details_

## Configuration

Configure via Home Assistant UI with translated field names:

### Modbus Settings

- **Modbus Host:** Inverter IP address (e.g. `192.168.1.100`)
- **Modbus Port:** Default: `502`
- **Auto-detect Slave ID:** Default: `true` (tries 1, 2, 100 automatically)
- **Slave ID (manual):** Only used when auto-detection disabled (usually `1`, sometimes `0` or `100`)

### MQTT Settings

- **MQTT Broker:** Default: `core-mosquitto` (leave empty for auto-config)
- **MQTT Port:** Default: `1883`
- **MQTT Username/Password:** Optional (leave empty to use HA MQTT Service credentials)
- **MQTT Topic:** Default: `huawei-solar`

### Advanced Settings

- **Log Level:** `TRACE` | `DEBUG` | `INFO` (recommended) | `WARNING` | `ERROR`
- **Status Timeout:** Default: `180s` (range: 30-600)
- **Poll Interval:** Default: `30s` (range: 10-300, recommended: 30-60s)

**💡 Pro Tip:** Leave MQTT credentials empty - the addon automatically uses Home Assistant MQTT Service settings!

### MQTT Topics

- **Sensor Data (JSON):** `huawei-solar` (all sensors + timestamp)
- **Status (online/offline):** `huawei-solar/status` (availability topic + LWT)

### Example MQTT Payload

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

_Full payload example: [mqtt_payload.json](examples/mqtt_payload.json)_

## Important Entities

| Category    | Sensors                                                                                    |
| ----------- | ------------------------------------------------------------------------------------------ |
| **Power**   | `solar_power`, `input_power`, `grid_power`, `battery_power`, `pv1-4_power`                 |
| **Energy**  | `daily_yield`, `total_yield`\*, `grid_exported/imported`\*                                 |
| **Battery** | `battery_soc`, `charge/discharge_today`, `total_charge/discharge`\*, `bus_voltage/current` |
| **Grid**    | `voltage_phase_a/b/c`, `line_voltage_ab/bc/ca`, `frequency`                                |
| **Meter**   | `meter_power_phase_a/b/c`, `meter_current_a/b/c`, `meter_reactive_power`                   |
| **Device**  | `model_name`, `serial_number`, `efficiency`, `temperature`, `rated_power`                  |
| **Status**  | `inverter_status`, `battery_status`, `meter_status`                                        |

_\* Protected by Total Increasing filter against false counter resets_

## Latest Updates

See [CHANGELOG.md](huawei_solar_modbus_mqtt/CHANGELOG.md) for detailed release notes.

**v1.8.0 Highlights (Feb 2026):**

- ✅ **Automatic Slave ID Detection:** No more guessing - tries 0, 1, 2, 100 automatically
- ✅ **Enhanced MQTT Auto-Config:** Seamlessly uses HA MQTT Service credentials
- ✅ **Dynamic Register Count:** Startup logs show exact number of registers
- ✅ **Improved Error Messages:** Better guidance for connection issues

**Previous releases:**

- ✅ **v1.7.4:** AppArmor backup support fixed, new Modbus registers
- ✅ **v1.7.3:** AppArmor security profile for container isolation
- ✅ **v1.7.2:** Enhanced test coverage (86%)
- ✅ **v1.7.1:** Restart zero-drop fix

## Troubleshooting

### ⚠️ Multiple Modbus Connections (Most Common!)

**Symptom:** Timeouts, "No response received", intermittent data loss

**Solution:**

1. Check **Settings → Devices & Services** for other Huawei integrations
2. Remove official `wlcrs/huawei_solar` and HACS integrations
3. Disable third-party monitoring software
4. Note: FusionSolar Cloud "Abnormal communication" is normal

### Other Common Issues

| Issue                    | Solution                                                                |
| ------------------------ | ----------------------------------------------------------------------- |
| **All Slave IDs fail**   | Enable Modbus TCP in inverter, verify IP, check firewall                |
| **Connection Timeouts**  | Check network latency, increase poll_interval to 60s                    |
| **MQTT Errors**          | Set broker to `core-mosquitto`, leave credentials empty                 |
| **Performance Warnings** | Increase poll_interval if cycle time > 80% of interval                  |
| **Filter Activity**      | Occasional filtering (1-2/hour) is normal; frequent = connection issues |
| **Missing Sensors**      | Normal for non-hybrid or inverters without battery/meter                |

**Logs:** Addon → Huawei Solar Modbus to MQTT → Log Tab

**Debug Mode:** Set `log_level: DEBUG` to see detailed Slave ID detection and connection attempts

## 💬 Community & Support

### Get Help

- 🐛 **[GitHub Issues](https://github.com/arboeh/huABus/issues/new/choose)** - Report bugs or request features
- 🧪 **[Compatibility Report](https://github.com/arboeh/huABus/issues/new?template=compatibility_report.yaml)** - Help test SUN3000/5000 models

### Community Discussions

Users also discuss huABus in these communities:

- [Home Assistant Community Forum](https://community.home-assistant.io/)

_These are independent communities - for official support, please use GitHub._

## Credits

**Based on:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)  
**Uses library:** [wlcrs/huawei-solar-lib](https://github.com/wlcrs/huawei-solar-lib)  
**Developed by:** [arboeh](https://github.com/arboeh) | **License:** MIT
