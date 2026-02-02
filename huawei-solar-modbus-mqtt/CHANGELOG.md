# Changelog

All notable changes to this project will be documented in this file.

## [1.7.2] - 2026-02-02

### Testing & Quality

- **Enhanced test coverage**: Added 31 comprehensive tests for improved reliability
  - 15 tests for HANT issue #7 (filter logic, missing keys, zero drops)
  - 16 tests for main.py (ENV validation, heartbeat, error handling)
  - All critical paths now tested (filter, restart scenarios, error recovery)
- **Code coverage improvement**: 77% → 86% (+9 percentage points)
  - `total_increasing_filter.py`: 97% coverage
  - `mqtt_client.py`: 97% coverage
  - `main.py`: 73% coverage (up from 52%)
  - `error_tracker.py`: 100% coverage
  - `transform.py`: 100% coverage

### Documentation

- **Enhanced translation coverage** (EN/DE)
  - Improved configuration field descriptions with concrete examples
  - Better guidance for beginners (e.g., "Try different Slave IDs if connection fails")
  - Added practical tips (e.g., "Use core-mosquitto for Home Assistant add-on")
  - Multi-line descriptions for better readability
- **Addon information display** improved for Home Assistant UI

### Internal

- Comprehensive test suite for filter edge cases
- Integration tests for restart protection
- E2E tests with mock inverter scenarios
- Improved code maintainability and documentation

**No user-facing functional changes** - This release focuses on code quality and test coverage improvements.

## [1.7.1] - 2026-01-31

### Fixed

- **Zero-drops on addon restart**: Filter now initialized before first cycle (reported by HANT)
  - Filter was previously initialized AFTER first data publish, leaving brief unprotected moment
  - Now initialized in `main()` before any data is published
  - Ensures all values protected from first cycle onwards
  - Log order after fix:
    1. 🔌 Connected (Slave ID: X)
    2. 🔍 TotalIncreasingFilter initialized (simplified)
    3. ⏱️ Poll interval: Xs
    4. 📊 Published (with filter protection) ✅

- **Negative value handling**: Improved filter behavior for invalid counter values
  - Negative values now properly removed from result dictionary
  - Fixed `_should_filter()` method to avoid side effects (no storing in check method)
  - Storing moved to `filter()` method for cleaner separation of concerns

- **Singleton reset behavior**: `reset_filter()` now properly clears filter instance
  - Previous behavior only cleared internal state but kept instance alive
  - Now fully resets singleton for clean restart
  - Next `get_filter()` call creates fresh instance

### Added

- **Comprehensive restart protection tests**: 12 new tests covering addon restart scenarios
  - Tests verify first value acceptance after restart
  - Edge cases: negative values, zero values, large jumps, multiple restarts
  - Validates no zero-drops visible in Home Assistant
  - All tests passing ✅

### Changed

- **Updated existing tests**: Refactored to use public API instead of private methods
  - Tests now use `filter()` instead of `_should_filter()`
  - Better test isolation and maintainability
  - Total test count: 51 tests passing

### Technical Details

**Fix Impact:**

- Prevents zero-drops in Home Assistant energy dashboard during addon restarts
- Eliminates brief unprotected moment between startup and first filter application
- More robust handling of edge cases (negative values, missing keys)

**Test Coverage:**

- Unit tests: 27 (filter logic, transform, error tracking)
- Integration tests: 12 (restart protection, singleton behavior)
- E2E tests: 12 (complete workflows, MQTT lifecycle)

Thanks to **HANT** for the detailed bug report with screenshots! 🙏

## [1.7.0] - 2026-01-31

### Changed

- **TotalIncreasingFilter Simplification**: Removed warmup period and tolerance configuration for more predictable behavior
  - **No more warmup phase**: First value is immediately accepted as valid baseline (no 60-second learning period)
  - **No more tolerance**: ANY drop in counter values is filtered (previously allowed 5% tolerance)
  - **Simpler configuration**: Removed `HUAWEI_FILTER_TOLERANCE` environment variable
  - **Reduced complexity**: Code reduced from ~300 to ~120 lines (-60%)
  - **All protection remains**: Negative values, zero-drops, and counter drops still filtered
  - **Improved logging**: Filter statistics now show exactly which values were filtered
  - **Result**: More strict but more predictable filtering - suitable for stable Modbus connections

### Removed

- **Warmup Period**: No longer necessary - filter starts immediately with first valid value
  - Removes 60-second startup delay
  - Removes warmup status indicators (`🔥 Warmup active`)
  - First read establishes baseline immediately
- **Tolerance Configuration**: Filter behavior now consistent and non-configurable
  - No more `HUAWEI_FILTER_TOLERANCE` environment variable
  - Previous 5% tolerance removed - all drops filtered equally
  - Eliminates configuration confusion

### Added

- **Development Tools**: Pre-commit hooks with ruff linter and formatter
  - Automatic code quality checks before each commit
  - Ensures consistent code style across project
  - Configured in `.pre-commit-config.yaml`

### Technical Details

**Filter Behavior Changes:**

Before (1.6.x):

```python
# Warmup: First 60 seconds accepted all values
# Tolerance: Drops < 5% accepted
10000 → 9510  # 4.9% drop → ACCEPTED ✅
10000 → 9490  # 5.1% drop → FILTERED ❌
```

Now (1.7.0):

```python
# No warmup: First value = baseline
# No tolerance: All drops filtered
10000 → 9999  # ANY drop → FILTERED ❌
10000 → 9510  # ANY drop → FILTERED ❌
```

**Filter Protection Still Active:**

- ✅ Negative values filtered
- ✅ Zero-drops filtered (e.g., 9799.5 → 0)
- ✅ Counter decreases filtered
- ✅ Missing keys handled (filled with last valid value)
- ✅ First value always accepted

**When to Upgrade:**

- ✅ **Stable Modbus connection**: Stricter filtering improves data quality
- ⚠️ **Unstable connection**: Monitor logs after upgrade - may need poll_interval increase

**Breaking Changes:**

- `HUAWEI_FILTER_TOLERANCE` environment variable no longer has effect (silently ignored)
- Filter now rejects small drops that were previously accepted (< 5% of previous value)
- Log messages changed:
  - Removed: `🔥 Warmup active (X/60s)` and `✅ Warmup complete`
  - Removed: `TotalIncreasingFilter initialized with X% tolerance`
  - New: Simpler `TotalIncreasingFilter initialized` message

**Migration Guide:**

1. No configuration changes needed - filter works out of the box
2. After upgrade, monitor filter summaries in logs:
   ```
   INFO - 🔍 Filter summary (last 20 cycles): X values filtered
   ```
3. If you see frequent filtering (every cycle), consider:
   - Increasing `poll_interval` from 30s to 60s
   - Checking Modbus connection stability
   - Reviewing network latency to inverter

**Upgrade Notes:**

- Existing configurations continue to work without changes
- `HUAWEI_FILTER_TOLERANCE` in config silently ignored (backward compatible)
- First cycle after upgrade establishes new baseline immediately
- No data loss - filter continues protecting energy statistics

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
