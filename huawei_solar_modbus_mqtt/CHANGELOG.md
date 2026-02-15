# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.1] - 2026-02-15

### Fixed

- **Slave ID 0 Auto-Detection Issue**: Removed broadcast address from auto-detection sequence
  - **Root cause**: Slave ID 0 is reserved as broadcast address in Modbus specification (write-only, no responses expected)
  - **Impact**: Home Assistant 2025.1+ enforces Modbus specification more strictly, causing timeouts during auto-detection
  - **Solution**: Updated auto-detection sequence from `[0, 1, 2, 100]` to `[1, 2, 100]`
  - **Benefits**:
    - Eliminates timeout errors on HA 2025.1+
    - Faster auto-detection (one less attempt)
    - Compliant with Modbus specification
  - Fixes compatibility with Home Assistant 2025.1 and later versions

### Technical Details

**Before:**

```python
SLAVE_IDS_TO_TRY =   # Slave ID 0 caused timeouts [github](https://github.com/arboeh/huABus)
```

**After:**

```python
SLAVE_IDS_TO_TRY =   # Slave ID 0 removed [community.home-assistant](https://community.home-assistant.io/t/app-huabus-huawei-solar-modbus-to-mqtt-sun2-3-5-000-mqtt-home-assistant-auto-discovery/958230)
```

**Affected Versions:**

- Home Assistant 2025.1 and later with stricter Modbus handling

**Workaround (if using older addon version):**

```yaml
modbus:
  auto_detect_slave_id: false
  slave_id: 2 # Use your actual Slave ID
```

### Credits

Thanks to **HANT** for the detailed bug report! 🙏

## [1.8.0] - 2026-02-10

### Added

- **Automatic Slave ID Detection**: No more guessing! The addon now automatically detects the correct Slave ID
  - Tries common values (0, 1, 2, 100) and uses the first working one
  - New config option: `modbus_auto_detect_slave_id` (enabled by default)
  - UI toggle in add-on configuration for easy enable/disable
  - Fallback to manual Slave ID if auto-detection disabled
  - Detailed logging shows which Slave IDs were tried
  - Eliminates "Timeout while waiting for connection" errors for new users

- **Dynamic Register Count Display**: Startup logs now show exact number of registers being read
  - Calculated dynamically from `ESSENTIAL_REGISTERS` constant
  - Example: `INFO - Registers: 63 essential`

### Changed

- **Improved Error Messages**: More helpful guidance for common connection issues
  - Connection errors now suggest trying different Slave IDs
  - Better context in log messages (shows attempted Slave ID)
  - Clearer distinction between timeout and connection refused errors

- **Configuration UI**: Reorganized for better user experience
  - Auto-detect option prominently displayed
  - Manual Slave ID clearly marked as "only used when auto-detection disabled"
  - Better descriptions with practical examples

### Fixed

- **MQTT Auto-Configuration**: Restored automatic credential detection from Home Assistant MQTT service
  - Feature was accidentally removed in previous development iterations
  - Now properly uses Home Assistant MQTT service credentials when available
  - Falls back to custom credentials from config if specified
  - Clear logging indicates whether using HA service or custom config

### Technical Details

**Logging Examples:**

```
# With auto-detection:
INFO - Inverter: 192.168.1.100:502 (Slave ID: auto-detect)
INFO - Trying Slave ID 0... ⏸️
INFO - Trying Slave ID 1... ✅
INFO - Connected (Slave ID: 1)

# Manual configuration:
INFO - Inverter: 192.168.1.100:502 (Slave ID: 1)
INFO - Connected (Slave ID: 1)
```

**Configuration:**

```yaml
# New option (default: true)
modbus_auto_detect_slave_id: true

# Only used when auto_detect = false
slave_id: 1
```

**Backward Compatibility:**

- Existing configurations without `modbus_auto_detect_slave_id` default to `true`
- Existing `slave_id` values preserved and used when auto-detection disabled
- No configuration migration needed

**Performance:**

- Auto-detection adds 0-3 seconds to startup (depends on how many IDs tried)
- Once connected, no performance difference

**When to Disable Auto-Detection:**

- You know your exact Slave ID and want faster startup
- You use a non-standard Slave ID not in the auto-detect list
- For debugging purposes

## [1.7.4] - 2026-02-04

### Fixed

- **AppArmor supervisor backup support**: Resolved permission issues preventing backup operations
  - Fixed `apparmor="DENIED"` errors for cgroup access during container startup
  - Backup creation and restoration now fully functional

### Added

- **New Modbus registers**: Additional inverter data points
  - Added missing energy and power registers from Huawei Solar library
  - More comprehensive inverter monitoring

- **Type checking support**: Enhanced IDE integration
  - Added `pyrightconfig.json` for better import resolution
  - Improved autocomplete and code navigation in VS Code

### Refactored

- **Project structure**: Renamed main package to `bridge` for cleaner imports
  - Better code organization and maintainability
  - All functionality preserved - internal change only

## [1.7.3] - 2026-02-03

### Infrastructure & Build System

- **Docker Build Compatibility**: Added `requirements.txt` for improved build reliability
  - Explicit dependency file for Docker image building
  - Ensures consistent builds across all architectures

### Security

- **AppArmor Profile**: Added container security profile for better isolation
  - Restricts container access to essential system resources only
  - Maintains compatibility with S6-Overlay init system
- **Network Configuration**: Changed `host_network: false` for improved security rating
  - Addon no longer requires host network access
  - Improves container isolation without functionality loss

### Documentation

- **README.md**: Added addon information display for Home Assistant UI
  - "About" section now visible in Add-on Info tab
- **Maintenance Badge**: Added to repository badges for transparency

## [1.7.2] - 2026-02-02

### Testing & Quality

- **Enhanced test coverage**: Added 31 comprehensive tests for improved reliability
  - 15 tests for HANT issue #7 (filter logic, missing keys, zero drops)
  - 16 tests for main.py (ENV validation, heartbeat, error handling)
- **Code coverage improvement**: 77% → 86% (+9 percentage points)

### Documentation

- **Enhanced translation coverage** (EN/DE)
  - Improved configuration field descriptions with concrete examples
  - Better guidance for beginners
  - Multi-line descriptions for better readability

## [1.7.1] - 2026-01-31

### Fixed

- **Zero-drops on addon restart**: Filter now initialized before first cycle (reported by HANT)
  - Filter was previously initialized AFTER first data publish
  - Now initialized in `main()` before any data is published
  - Ensures all values protected from first cycle onwards

- **Negative value handling**: Improved filter behavior for invalid counter values
  - Negative values now properly removed from result dictionary

- **Singleton reset behavior**: `reset_filter()` now properly clears filter instance

### Added

- **Comprehensive restart protection tests**: 12 new tests covering addon restart scenarios

Thanks to **HANT** for the detailed bug report with screenshots! 🙏

## [1.7.0] - 2026-01-31

### Changed

- **TotalIncreasingFilter Simplification**: Removed warmup period and tolerance configuration
  - **No more warmup phase**: First value immediately accepted as valid baseline
  - **No more tolerance**: ANY drop in counter values is filtered
  - **Simpler configuration**: Removed `HUAWEI_FILTER_TOLERANCE` environment variable
  - **Reduced complexity**: Code reduced from ~300 to ~120 lines (-60%)
  - **All protection remains**: Negative values, zero-drops, and counter drops still filtered

### Removed

- **Warmup Period**: No longer necessary - filter starts immediately
- **Tolerance Configuration**: Filter behavior now consistent and non-configurable

### Added

- **Development Tools**: Pre-commit hooks with ruff linter and formatter

**Breaking Changes:**

- `HUAWEI_FILTER_TOLERANCE` environment variable no longer has effect (silently ignored)
- Filter now rejects small drops that were previously accepted (< 5%)

## [1.6.1] - 2026-01-29

### Fixed

- **Critical Bug Fix**: `total_increasing` filter now applies **before** MQTT publish instead of after
  - **Problem**: Previously the filter ran after MQTT publish, allowing zero values to reach Home Assistant
  - **Impact**: Utility Meter helpers would calculate incorrect daily totals
  - **Solution**: Filter now runs in pipeline before publishing: `Modbus Read → Transform → Filter → MQTT Publish`
- Fixes issue [#7](https://github.com/arboeh/huABus/issues/7) - Export energy counter drops to zero

### Documentation

- **Quick Start Guide**: Added 5-minute onboarding for new users
  - Step-by-step installation with expected log outputs
  - Troubleshooting table for common issues
- **README Structure**: Improved hierarchy and navigation
