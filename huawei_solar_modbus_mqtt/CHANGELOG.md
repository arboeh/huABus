# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.4] - 2026-03-24

### Fixed

- **Poll interval not respected**: Inverter data was published as fast as the
  Modbus read completed (~5-8s) instead of respecting the configured poll interval
  - Root cause: `poll_interval` was read from config but never applied in the main loop —
    the previous ~20-30s cycle time was an accidental side effect of broken TCP teardown
    in v1.8.3 (now fixed), which unintentionally throttled the loop
  - Added `cycle_start` timestamp and `asyncio.sleep(remaining)` after each
    successful cycle to wait out the configured interval
  - Duplicate `error_tracker` instantiation removed (dead code)
  - `ImportError` fallback for pymodbus marked with `# pragma: no cover`

### Tests

- Fixed `auto_detect_slave_id` → `modbus_auto_detect_slave_id` attribute name
  mismatch in 7 test locations
- Added `test_main_loop_waits_poll_interval` to verify poll interval sleep behavior

## [1.8.3] - 2026-03-23

### Fixed

- Auto Slave ID Detection: `Request cancelled outside library` error for
  subsequent Slave IDs (2, 100) after a failed first attempt (#15)
  - Added `INTER_ATTEMPT_DELAY` (2s) between attempts to allow TCP teardown
  - Added timeout to `client.stop()` to prevent blocking on broken clients
  - `CancelledError` now correctly propagates instead of being swallowed

## [1.8.2] - 2026-03-02

### Changed

- **CI Pipeline**: Full migration to `uv` (replaces `pip`)
  - **Benefits**: 40% faster builds, reproducible environments (`uv.lock`)
  - **Jobs affected**: Lint, Test, Type-Check, Config-Validation
  - **Example**:
    ```yaml
    - name: uv sync & test
      run: |
        curl -LsSf https://astral.sh/uv/install.sh | sh
        uv sync --dev --frozen
        uv run pytest tests/
    ```

### Performance

| Job        | pip  | uv      | Δ        |
| ---------- | ---- | ------- | -------- |
| Test       | 45s  | 26s     | -42%     |
| Type Check | 12s  | 4s      | -67%     |
| **Total**  | 120s | **72s** | **-40%** |

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
