# Changelog

All notable changes to this project will be documented in this file.

## [1.6.1] - 2026-01-29

### Fixed

- **Critical Bug Fix**: `total_increasing` filter now applies **before** MQTT publish instead of after
  - **Problem**: Previously the filter ran after MQTT publish, allowing zero values from Modbus read errors to reach Home Assistant for a brief moment
  - **Impact**: Utility Meter helpers would see the zero value and calculate incorrect daily totals (jumping by total accumulated energy)
  - **Solution**: Filter now runs in the data pipeline before publishing: `Modbus Read → Transform → Filter → MQTT Publish`
  - **Result**: Zero values are replaced with last valid value before they reach Home Assistant
- Fixes issue [#7](https://github.com/arboeh/huABus/issues/7) - Export energy counter drops to zero causing Utility Meter jumps

### Changed

- Filter now integrated into `main_once()` pipeline as explicit step
- Added filter timing measurement for performance monitoring
- Improved filter logging with cycle-by-cycle statistics

### Documentation

- **Quick Start Guide**: Added 5-minute onboarding for new users
  - Step-by-step installation with expected log outputs
  - Troubleshooting table for common first-time issues
  - Clear success indicators after first start

- **README Structure**: Improved hierarchy and navigation
  - Quick Start positioned before Features
  - Architecture badges added for platform visibility
  - Better visual separation between sections

## [1.6.0] - 2026-01-25

### Added

- **total_increasing Filter**: Prevents false counter resets in Home Assistant energy statistics
  - Filters negative values for energy counters (physically impossible)
  - Filters drops > 5% as likely Modbus read errors
  - Replaces invalid values with last valid value instead of 0
  - Configurable via `HUAWEI_FILTER_TOLERANCE` ENV variable (default: 0.05 = 5%)
  - Protects sensors: `energy_yield_accumulated`, `energy_grid_exported`, `energy_grid_accumulated`, `battery_charge_total`, `battery_discharge_total`

- **Automatic Filter Reset**: Filter state is reset on connection errors to prevent stale values
  - Reset triggers: Timeout, Modbus exception, Connection refused, Unexpected errors
  - Ensures fresh state after inverter restart or reconnect

- **Filter Status Indication**: Cycle summary now shows when values were filtered
  - INFO level: `📊 Published - PV: 788W | AC Out: 211W | Grid: 11W | Battery: 569W 🔍[2 filtered]`
  - DEBUG level: Detailed filter statistics showing which sensors were affected
  - Helps quickly identify Modbus read issues during operation

- **Filter Statistics Logging**: Comprehensive filter monitoring at different log levels
  - INFO level: Summary every 20 cycles when filters were active
  - DEBUG level: Detailed statistics after each filtered cycle
  - Format: `🔍 Filter details: {'energy_yield_accumulated': 2, 'battery_charge_total': 1}`

### Fixed

- **datetime Serialization**: `startup_time` register now correctly converted to ISO string for JSON compatibility
  - Fixes "Object of type datetime is not JSON serializable" error
  - Converts to ISO format: `2026-01-25T06:30:00`

- **Exception Handling**: Improved Modbus exception catching to avoid BaseException errors
  - Simplified to single `except Exception` with internal type checking
  - More robust handling when pymodbus exceptions are not available

### Changed

- **Enhanced Code Documentation**: Extensive German inline comments added across all modules
  - Every function documented with purpose, logic, examples
  - Technical decisions explained (why 5% tolerance, why filter reset, etc.)
  - Hardware dependencies and optional features clearly marked
  - Improved maintainability for future development

- **Cycle Summary Logging**: `log_cycle_summary()` now includes real-time filter status
  - Shows count of filtered values in main INFO log line
  - No additional log lines needed for basic filter awareness
  - Detailed breakdown available at DEBUG level

### Technical Details

- New module: `modbus_energy_meter/total_increasing_filter.py`
  - Singleton pattern with `get_filter()` and `reset_filter()` functions
  - Stores last valid values per sensor key
  - 5% tolerance prevents false positives during concurrent register updates
  - Filter statistics tracking for debugging and monitoring

- `transform.py` enhancements:
  - `_apply_total_increasing_filter()` function integrated into transform pipeline
  - `get_value()` now handles datetime objects via `.isoformat()`
  - Filter applied after mapping but before cleanup

- `main.py` improvements:
  - Filter reset added to all error handlers (timeout, modbus_exception, connection_refused, unexpected)
  - `log_cycle_summary()` enhanced with inline filter status indicator
  - Filter statistics logged at INFO level (periodic) and DEBUG level (detailed)
  - Simplified exception handling structure

**Breaking Changes:** None - fully backwards compatible

**Upgrade Notes:**

- Filter is enabled by default with 5% tolerance
- Filter activity visible at INFO level in cycle summary
- Detailed filter statistics available with `HUAWEI_LOG_LEVEL=DEBUG`

## [1.5.1] - 2026-01-18

### Fixed

- **Library Version Detection**: Startup logs now correctly display installed versions of `huawei-solar`, `pymodbus`, and `paho-mqtt`
  - Previously showed "unknown" due to hardcoded placeholder in `run.sh`
  - Now dynamically detects versions via Python's `__version__` attribute

### Changed

- **Startup Information**: Enhanced system info display with actual library versions

  [18:01:44] INFO: >> System Info:  
  [18:01:44] INFO: - Python: 3.12.12  
  [18:01:44] INFO: - huawei-solar: 2.5.0  
  [18:01:44] INFO: - pymodbus: 3.11.4  
  [18:01:44] INFO: - paho-mqtt: 2.1.0

### Technical Details

- `run.sh`: Added dynamic version detection using Python imports
- `main.py`: Enhanced `log_cycle_summary()` to include `battery_soc` in human-readable output
- No breaking changes - fully backwards compatible

## [1.5.0] - 2026-01-16

### Added

- **MQTT Connection Stability**: Wait loop and retry logic for reliable MQTT publishing
- **Connection State Tracking**: Global `_is_connected` flag prevents "not connected" errors
- **Development Environment**: PowerShell runner (`run_local.ps1`) and `.env` support for local testing
- **Exception Handling**: Improved Modbus exception handling with `is_modbus_exception()` helper

### Fixed

- **MQTT Publish Failures**: Added `wait_for_publish()` to all MQTT operations
- **Race Condition**: 1-second delay after MQTT connect ensures stable connection before publishing
- **paho-mqtt 2.x Support**: Version-compatible client creation with `CallbackAPIVersion.VERSION2`

### Changed

- **MQTT Client**: Callbacks now properly update connection state for reliable publish operations
- **Connection Timeout**: Increased from implicit to explicit 10-second wait with proper error handling

### Technical Details

- Connection wait loop polls `_is_connected` flag every 100ms up to 10 seconds
- All `publish()` calls now wait for confirmation with 1-2 second timeout
- Exception handling no longer uses `isinstance()` directly in except clauses to avoid BaseException errors

## [1.4.2] - 2026-01-09

### Added

- `.gitattributes` for enforced LF line endings across all text files (Linux/Docker compatibility)
- `.editorconfig` for standardized editor configuration (indent, charset, line endings)
- `.gitignore` with comprehensive Python/Docker/IDE exclusions
- GitHub Issue Templates for structured bug reports and feature requests
- GitHub Release Workflow for automated releases

### Changed

- Normalized all repository files to LF line endings (prevents `/bin/sh: bad interpreter` errors)
- Enhanced `.dockerignore` to properly include required Home Assistant files (CHANGELOG.md, DOCS.md)
- Improved `__init__.py` files with package docstrings for better code organization
- Updated `requirements.txt` with version constraints to prevent breaking changes

### Fixed

- Corrected `pymodbus` version requirement from non-existent `3.11.4` to `>=3.7.4,<4.0.0`
- Fixed potential line ending issues on Windows development environments
- Resolved `.dockerignore` accidentally excluding required add-on documentation

### Documentation

- Added troubleshooting guide for connection timeout issues (Slave ID configuration)
- Updated community support information with GitHub Issues link

## [1.4.1] - 2026-01-08

### Changed

- Enhanced startup logging with emoji icons (🚀🔌📡📍⏱️)
- Added visual separator lines in connection summary
- Set bashio log level dynamically based on HUAWEI_LOG_LEVEL
- Improved readability of startup configuration display

## [1.4.0] - 2026-01-08

### Features

- Error Tracker with intelligent error aggregation and downtime tracking
- Enhanced logging architecture with `log_cycle_summary()` function (supports JSON format for machine parsing)
- Bashio log level synchronization for consistent add-on logs across all components
- Performance optimization: `poll_interval` default lowered to 30s (previously 60s) for faster data updates

### Improvements

- ENV variables consistently named: `HUAWEI_SLAVE_ID` instead of `HUAWEI_MODBUS_DEVICE_ID` for better clarity
- Redundant logging removed: eliminated duplicate DEBUG statements in `main_once()` and `read_registers()`
- `publish_status()` optimized to DEBUG-level only (was INFO + DEBUG before)
- Dockerfile simplified: huawei_solar library patch removed (apply manually if needed for unknown enum values)
- run.sh refactored: removed legacy debug mode code, added case-based log level mapping
- DOCS.md fully synchronized with config.yaml defaults and updated examples

### Bugfixes

- Docstrings corrected: `publish_data()` now correctly documents exception behavior
- Connection recovery messages now include downtime duration in seconds
- Fixed inconsistent default values between config.yaml and main.py

### Technical Details

- Error recovery logging format: `Connection restored after {downtime}s ({attempts} failed attempts, {types} error types)`
- All configuration examples updated to reflect `poll_interval: 30` default
- Recommended settings table adjusted: Standard scenario now 30s instead of 60s

**Breaking Changes:** None - fully backwards-compatible with existing configurations
