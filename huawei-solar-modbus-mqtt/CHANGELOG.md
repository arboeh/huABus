# Changelog

## [1.4.1] - 2026-01-08

### Changed

- Enhanced startup logging with emoji icons (🚀🔌📡📍⏱️)
- Added visual separator lines in connection summary
- Set bashio log level dynamically based on HUAWEI_LOG_LEVEL
- Improved readability of startup configuration display

## [1.4.0] - 2026-01-08

**Features:**

- Error Tracker with intelligent error aggregation and downtime tracking
- Enhanced logging architecture with `log_cycle_summary()` function (supports JSON format for machine parsing)
- Bashio log level synchronization for consistent add-on logs across all components
- Performance optimization: `poll_interval` default lowered to 30s (previously 60s) for faster data updates

**Improvements:**

- ENV variables consistently named: `HUAWEI_SLAVE_ID` instead of `HUAWEI_MODBUS_DEVICE_ID` for better clarity
- Redundant logging removed: eliminated duplicate DEBUG statements in `main_once()` and `read_registers()`
- `publish_status()` optimized to DEBUG-level only (was INFO + DEBUG before)
- Dockerfile simplified: huawei_solar library patch removed (apply manually if needed for unknown enum values)
- run.sh refactored: removed legacy debug mode code, added case-based log level mapping
- DOCS.md fully synchronized with config.yaml defaults and updated examples

**Bugfixes:**

- Docstrings corrected: `publish_data()` now correctly documents exception behavior
- Connection recovery messages now include downtime duration in seconds
- Fixed inconsistent default values between config.yaml and main.py

**Technical Details:**

- Error recovery logging format: `Connection restored after {downtime}s ({attempts} failed attempts, {types} error types)`
- All configuration examples updated to reflect `poll_interval: 30` default
- Recommended settings table adjusted: Standard scenario now 30s instead of 60s

**Breaking Changes:** None - fully backwards-compatible with existing configurations

---

## [1.3.5] - 2026-01-03

**Bugfix:** Template variable warnings in Home Assistant eliminated

- All optional sensor definitions now include `default()` filters in `value_template` to prevent "dict object has no attribute" warnings
- Affected sensors: All battery values, PV strings 2-4, grid phases B/C, meter phases, efficiency, and status fields
- **Root cause:** `_cleanup_result()` removes `None` values from JSON payload → missing keys in MQTT message → Home Assistant template errors
- **Solution:** Custom `value_template` with `| default(0)` for numeric sensors and `| default('unknown')` for text sensors
- `_build_sensor_config()` now respects custom `value_template` from sensor definitions instead of always generating standard template

**Dependencies:** Cleaned up and corrected to installable versions

- **Removed:** `backoff` and `pytz` (not used in codebase)
- `paho-mqtt` 2.1.0 unchanged (current stable)
- Reduces installation footprint and eliminates dependency resolution conflicts

---

## [1.3.4] - 2025-12-16

**Bugfix:** Logging statement corrected - Solar power was displayed incorrectly

- Log line "Published - Solar: XW" incorrectly used `power_active` (AC output power of inverter) instead of `power_input` (DC input power from PV modules)
- **Register meanings:**
  - `power_input` (Register 32064) = actual solar/PV power (DC)
  - `power_active` (Register 32080) = inverter AC output (combined from PV + battery)
- **Symptom:** At night, e.g. 240W "solar" power was displayed, although this was actually battery discharge
- **Solution:** Logging now correctly uses `mqtt_data.get('power_input', 0)` for solar display
- Fixes confusing nighttime values in log; MQTT data and Home Assistant entities were already correct

---

## [1.3.3] - 2025-12-15

**Bugfix:** MQTT Discovery validation error fixed

- Unit for reactive power sensors corrected from `VAr` to `var` (Home Assistant requires lowercase for `device_class: reactive_power`)
- Fixes error: "The unit of measurement `VAr` is not valid together with device class `reactive_power`"
- Affects sensors: `power_reactive` and `meter_reactive_power`

---

## [1.3.2] - 2025-12-15

**Bugfixes:** Register names corrected for Battery Daily Charge/Discharge

- `storage_charge_capacity_today` → `storage_current_day_charge_capacity`
- `storage_discharge_capacity_today` → `storage_current_day_discharge_capacity`
- `alarm_1` register removed (not available on all inverter models, caused template errors)
- Fixes "Template variable warning: 'dict object' has no attribute" error in Home Assistant

**Dependencies:** All core dependencies updated to latest stable versions

- `huawei-solar`: 2.3.0 → **2.5.0**
- `paho-mqtt`: 1.6.1 → **2.1.0** (MQTT 5.0 support)
- `pymodbus`: 3.8.6 → **3.11.4**
- `pytz`: 2024.2 → **2025.2**

---

## [1.3.1] - 2025-12-10

- Register set expanded to **58 Essential Registers**; all names strictly aligned with `huawei-solar-lib` (including grid/meter registers and capitalization)
- Full 3-phase smart meter support: phase power, current, line-to-line voltages, frequency and power factor are now published as individual MQTT values
- MQTT Discovery sensors synchronized with new keys and consistently using `unit_of_measurement`, compliant with Home Assistant MQTT specification
- PV power sensors removed; only PV voltage/current are transmitted, allowing power calculation in Home Assistant via template if needed
- Add-on option `modbus_device_id` renamed to `slave_id` to avoid conflicts with Home Assistant device IDs

---

## [1.3.0] - 2025-12-09

**Config:** Configuration moved to config/ (registers.py, mappings.py, sensors_mqtt.py) with 47 Essential Registers and 58 sensors  
**Registers:** Five new registers (including smart meter power, battery today, meter status, grid reactive power) and 13 additional entities for battery bus and grid details
