# huABus | Huawei Solar Modbus to MQTT

### Huawei Solar Modbus → Home Assistant via MQTT + Auto Discovery

This add-on reads data from your Huawei SUN2000 inverter via Modbus TCP and publishes it via MQTT including Home Assistant MQTT Discovery.

> **⚠️ CRITICAL: Only ONE Modbus Connection Allowed!**
>
> Huawei inverters have a **fundamental limitation**: They allow **only ONE active Modbus TCP connection** at the same time. This is a **hardware limitation** and the most common error in smart home integration.
>
> ### Typical Error Scenarios:
>
> ❌ **Official Huawei Solar Integration AND this add-on** → Both fighting for connection  
> ❌ **Multiple Home Assistant Instances** → Only one can connect  
> ❌ **FusionSolar App + Modbus active** → Cloud shows "Abnormal"  
> ❌ **Monitoring Software + Home Assistant** → Intermittent timeouts
>
> ### ✅ Before installation, CHECK:
>
> 1. **Home Assistant Integrations:**
>    - Settings → Devices & Services
>    - Search for "Huawei" or "Solar"
>    - Remove ALL other Huawei integrations (wlcrs/huawei_solar, HACS, etc.)
> 2. **Disable other software:**
>    - Monitoring tools (e.g., Solar-Analytics)
>    - Mobile apps with Modbus access
>    - Other Home Assistant instances
> 3. **FusionSolar Cloud:**
>    - Cloud works PARALLEL to Modbus
>    - But: Cloud shows "Abnormal Communication" → **ignore it!**
>    - Cloud data continues to be transmitted
> 4. **Symptom with multiple connections:**
>    ```
>    ERROR - Timeout while waiting for connection
>    ERROR - No response received after 3 retries
>    ```
>    → This is NOT the add-on's fault, but competition for the connection!
>
> **Rule:** ONLY ONE Modbus connection at a time = stable system ✅

## 🚀 Quick Start (5 Minutes)

### 1. Before Installation (CRITICAL!)

✅ **Remove competing Modbus connections:**

- Settings → Devices & Services → Search "Huawei" → Remove ALL integrations
- Disable monitoring software, mobile apps with Modbus access
- Only ONE Modbus connection allowed!

✅ **Prepare connection details:**

- Inverter IP address (e.g., `192.168.1.100`)
- Check inverter is pingable: `ping 192.168.1.100`

### 2. Installation

1. Settings → Add-ons → Add-on Store
2. Click ⋮ (top right) → Repositories
3. Add: `https://github.com/arboeh/huABus`
4. Install "Huawei Solar Modbus to MQTT"

### 3. Configuration

**Minimal configuration (required):**

```yaml
modbus_host: "192.168.1.100" # Your inverter IP
slave_id: 1 # Start with 1
log_level: "INFO" # Good default
```

**💡 Connection timeout?** Try different Slave IDs:

```yaml
slave_id: 0 # or 1, or 16
```

### 4. First Start & Verification

1. **Start the add-on** → Check logs immediately
2. **Success indicators:**
   ```
   INFO - 🚀 Huawei Solar → MQTT starting
   INFO - 🔌 Connected (Slave ID: 1)
   INFO - Essential read: 2.1s (58/58)
   INFO - 📊 Published - PV: 4500W | ...
   ```
3. **Enable sensors:**
   - Settings → Devices & Services → MQTT
   - Find "Huawei Solar Inverter"
   - Enable desired sensors

### 5. Common First-Time Issues

| Symptom              | Quick Fix                                                 |
| -------------------- | --------------------------------------------------------- |
| `ERROR - Timeout`    | Try `slave_id: 0`, then `16`                              |
| `Connection refused` | Check inverter IP, enable Modbus TCP in inverter settings |
| `No sensors appear`  | Wait 30s, refresh MQTT integration                        |
| Too many sensors!    | Normal! Disable unused in MQTT integration                |

**Still having issues?** See full [Troubleshooting](#logging--troubleshooting) section below.

## Features

- **Fast Modbus TCP connection** to Huawei SUN2000 Inverter
  - 58 Essential Registers (critical values + extended data)
  - Typical cycle time: 2-5 seconds
  - Recommended poll interval: 30-60 seconds
- **total_increasing Filter (NEW in 1.6.0):** Prevents false counter resets in Home Assistant
  - Filters negative values and drops > 5% (configurable)
  - Protects energy statistics from Modbus read errors
  - Automatic reset on connection errors
  - Filter status visible in logs with 20-cycle summaries
- Publishing sensor data to MQTT topic as JSON
- Automatic Home Assistant entity creation via MQTT Discovery
- **Error Tracking:** Intelligent error aggregation with downtime tracking
- Support for:
  - PV power (PV1-4 with voltage and current)
  - Grid power (Import/Export, 3-phase)
  - Battery (SOC, charge/discharge power, daily and total energy)
  - 3-phase grid voltages, line-to-line voltages
  - Smart Meter integration (3-phase)
  - Daily and total energy yield
  - Inverter temperature and efficiency
- Online/Offline status with:
  - Binary Sensor "Huawei Solar Status"
  - Heartbeat/Timeout monitoring
  - MQTT Last Will (LWT) at broker
- Configurable logging with multiple log levels
- Performance monitoring and automatic warnings
- Health check for container monitoring

## Prerequisites

- Huawei SUN2000 inverter with enabled Modbus TCP interface
- Home Assistant with configured MQTT integration
- MQTT Broker (e.g., Mosquitto), ideally provided via Home Assistant Supervisor

## Configuration

Example configuration in Add-on UI:

```yaml
modbus_host: "192.168.1.100"
modbus_port: 502
slave_id: 1
mqtt_host: "core-mosquitto"
mqtt_port: 1883
mqtt_user: ""
mqtt_password: ""
mqtt_topic: "huawei-solar"
log_level: "INFO"
status_timeout: 180
poll_interval: 30
```

### Options

#### Modbus Settings

- **modbus_host** (required)  
  IP address of your Huawei inverter (e.g., `192.168.1.100`).

- **modbus_port** (default: `502`)  
  Modbus TCP port.

- **slave_id** (default: `1`, range: 0-247)  
  Modbus Slave ID of the inverter. In many installations this is `1`, sometimes `16` or `0`.  
  **Tip:** Try different values (`0`, `1`, `16`) if you experience connection timeouts.

#### MQTT Settings

- **mqtt_host** (default: `core-mosquitto`)  
  MQTT Broker hostname. Leave empty or use `core-mosquitto` for HA Mosquitto Add-on.

- **mqtt_port** (default: `1883`)  
  MQTT Broker port.

- **mqtt_user** (optional)  
  MQTT username. Leave empty to use credentials from Home Assistant MQTT Service.

- **mqtt_password** (optional)  
  MQTT password. Leave empty to use credentials from Home Assistant MQTT Service.

- **mqtt_topic** (default: `huawei-solar`)  
  Base topic under which data is published.

#### Advanced Settings

- **log_level** (default: `INFO`)  
  Logging detail level:
  - `DEBUG`: Very detailed - shows performance metrics, individual register reads, timing measurements, error details, **filter details at every event**
  - `INFO`: Normal - shows important events and current data points (Solar/Grid/Battery Power), error recovery, **filter summaries every 20 cycles**
  - `WARNING`: Only warnings and errors
  - `ERROR`: Only errors

- **status_timeout** (default: `180`, range: 30-600)  
  Time in seconds after which status is set to `offline` if no successful query occurred.

- **poll_interval** (default: `30`, range: 10-300)  
  Query interval in seconds between two Modbus reads.  
  **Recommendation:** 30-60 seconds for optimal balance between freshness and network load.

#### Filter Settings (ENV variables, optional)

- **HUAWEI_FILTER_TOLERANCE** (default: `0.05`)  
  Tolerance for total_increasing filter as percentage (0.05 = 5%).  
  Values dropping more than this percentage are filtered as read errors.  
  **Recommendation:** 5% (default) is optimal for most installations.  
  **Example:** At 0.10, only drops > 10% are filtered (less strict).

## MQTT Topics

- **Sensor Data (JSON):**  
  `huawei-solar` (or your configured topic)  
  Contains all sensor data as JSON object with `last_update` timestamp.

- **Status (online/offline):**  
  `huawei-solar/status`  
  Used for:
  - Binary Sensor "Huawei Solar Status"
  - `availability_topic` of all sensors
  - MQTT Last Will Testament (automatically `offline` on connection loss)

## Home Assistant Entities

After starting the add-on, MQTT Discovery configurations are automatically published. You'll find the entities at:

**Settings → Devices & Services → MQTT → Devices → "Huawei Solar Inverter"**

### Main Entities (enabled by default)

#### Power

- `sensor.solar_power` - Current total PV power
- `sensor.input_power` - DC input power
- `sensor.grid_power` - Grid power (positive = import, negative = export)
- `sensor.battery_power` - Battery power (positive = charging, negative = discharging)
- `sensor.pv1_power` - PV String 1 power

#### Energy

- `sensor.solar_daily_yield` - Daily yield
- `sensor.solar_total_yield` - Total yield _(protected by filter)_
- `sensor.grid_energy_exported` - Exported energy (feed-in) _(protected by filter)_
- `sensor.grid_energy_imported` - Imported energy (consumption) _(protected by filter)_
- `sensor.battery_charge_today` - Battery charge today
- `sensor.battery_discharge_today` - Battery discharge today
- `sensor.battery_total_charge` - Battery total charge _(protected by filter)_
- `sensor.battery_total_discharge` - Battery total discharge _(protected by filter)_

> **ℹ️ Filter Protection:** Sensors marked with _(protected by filter)_ are automatically protected against false counter resets. On Modbus read errors, the last valid value is used instead of 0.

#### Battery

- `sensor.battery_soc` - Battery state of charge (%)
- `sensor.battery_bus_voltage` - Battery bus voltage
- `sensor.battery_bus_current` - Battery bus current

#### Grid

- `sensor.grid_voltage_phase_a/b/c` - 3-phase grid voltages
- `sensor.grid_line_voltage_ab/bc/ca` - Line-to-line voltages
- `sensor.grid_frequency` - Grid frequency
- `sensor.grid_current_phase_a/b/c` - 3-phase currents

#### Smart Meter (if available)

- `sensor.meter_power_phase_a/b/c` - Phase power
- `sensor.meter_current_phase_a/b/c` - Phase currents
- `sensor.meter_reactive_power` - Reactive power

#### Inverter

- `sensor.inverter_temperature` - Inverter temperature
- `sensor.inverter_efficiency` - Efficiency
- `sensor.model_name` - Inverter model
- `sensor.serial_number` - Serial number

#### Status

- `binary_sensor.huawei_solar_status` - Online/Offline status
- `sensor.inverter_status` - Text status (e.g., "Standby", "Grid-Connected")
- `sensor.battery_status` - Battery status

### Diagnostic Entities (disabled by default)

These entities can be manually enabled in Home Assistant:

- PV2/PV3/PV4 power, voltage, current
- Detailed phase currents and powers
- Inverter state details

## Performance & Optimization

### Version 1.6.x - Current Features

**58 Essential Registers:**

- Extended register set with all important values
- Typical cycle time: 2-5 seconds
- Recommended poll interval: **30-60 seconds**

**total_increasing Filter (NEW in 1.6.0):**

- Automatic protection against false counter resets
- Filters drops > 5% as probable read errors
- Replaces invalid values with last valid value
- Visible in logs with 20-cycle summaries

**Error Tracking:**

- Intelligent error aggregation
- Downtime tracking with recovery logging
- Format: `Connection restored after {downtime}s ({attempts} failed attempts, {types} error types)`

**Benefits:**

- Minimal network load
- Fast updates of most important values
- Reliable connection even on slow networks
- Automatic error recovery with statistics
- Protected energy statistics (no false resets!)

### Performance Monitoring

The add-on automatically monitors cycle performance:

```
INFO - Essential read: 2.1s (58/58)
INFO - 📊 Published - PV: 4500W | AC Out: 4200W | Grid: -200W | Battery: 800W
DEBUG - Cycle: 2.3s (Modbus: 2.1s, Transform: 0.005s, MQTT: 0.194s)
```

**With filter activity (when values were filtered):**

```
INFO - 📊 Published - PV: 788W | AC Out: 211W | Grid: 11W | Battery: 569W 🔍[2 filtered]
DEBUG - 🔍 Filter details: {'energy_yield_accumulated': 1, 'battery_charge_total': 1}
```

**Filter summary every 20 cycles (INFO level):**

```
INFO - 🔍 Filter summary (last 20 cycles): 0 values filtered - all data valid ✓
```

or with filtering:

```
INFO - 🔍 Filter summary (last 20 cycles): 3 values filtered | Details: {'energy_yield_accumulated': 2, 'battery_charge_total': 1}
```

**Automatic warnings** for slow cycles:

```
WARNING - Cycle 52.1s > 80% poll_interval (30s)
```

**Error recovery logging:**

```
INFO - Connection restored after 47s (3 failed attempts, 2 error types)
```

### Recommended Settings

| Scenario         | Poll-Interval | Status-Timeout |
| ---------------- | ------------- | -------------- |
| **Standard**     | 30s           | 180s           |
| **Fast**         | 20s           | 120s           |
| **Slow Network** | 60s           | 300s           |
| **Debugging**    | 10s           | 60s            |

## Logging & Troubleshooting

### Log Levels

**INFO (Default)** - Clear overview for normal operation:

```
2026-01-25T12:51:23+0100 - huawei.main - INFO - 🚀 Huawei Solar → MQTT starting
2026-01-25T12:51:25+0100 - huawei.main - INFO - 🔌 Connected (Slave ID: 1)
2026-01-25T12:51:31+0100 - huawei.main - INFO - Essential read: 6.1s (57/57)
2026-01-25T12:51:31+0100 - huawei.filter - INFO - TotalIncreasingFilter initialized with 5% tolerance
2026-01-25T12:51:31+0100 - huawei.main - INFO - 📊 Published - PV: 744W | AC Out: 218W | Grid: -29W | Battery: 520W
2026-01-25T13:11:31+0100 - huawei.main - INFO - 🔍 Filter summary (last 20 cycles): 0 values filtered - all data valid ✓
```

**DEBUG** - Detailed with performance metrics:

```
2026-01-25T12:51:23+0100 - huawei.main - DEBUG - Cycle #1
2026-01-25T12:51:23+0100 - huawei.main - DEBUG - Reading 58 essential registers
2026-01-25T12:51:31+0100 - huawei.main - INFO - Essential read: 6.1s (57/57)
2026-01-25T12:51:31+0100 - huawei.transform - DEBUG - Transforming 58 registers
2026-01-25T12:51:31+0100 - huawei.main - DEBUG - Cycle: 6.2s (Modbus: 6.1s, Transform: 0.008s, MQTT: 0.092s)
```

### View Add-on Logs

**Settings → Add-ons → Huawei Solar Modbus to MQTT → "Log"**

### Common Issues & Solutions

#### Connection Timeout Error

**Symptom:**

```
ERROR - Timeout while waiting for connection. Reconnecting
TimeoutError
```

**Solutions:**

1. **Change Slave ID** - Most common solution!
   - Try: `0`, `1`, `16`
   - Some dongles use different IDs

2. **Increase Poll Interval**
   - From `30` to `60` or higher
   - Gives more time for slow connections

3. **Check Network**
   - Ping inverter: `ping <IP>`
   - Check latency and packet loss

4. **Check FusionSolar Cloud**
   - Cloud connection can block Modbus
   - Temporarily disable for testing

5. **Enable DEBUG Log**
   - Shows exactly which register hangs on timeout

#### Modbus Connection Error

**Symptom:**

```
ERROR - Connection failed: [Errno 111] Connection refused
```

**Solutions:**

- Check IP address and port
- Enable Modbus TCP in inverter web interface
- Try different Slave IDs (0, 1, 16)
- Check firewall rules
- With `log_level: DEBUG`, details are shown

#### MQTT Connection Error

**Symptom:**

```
ERROR - MQTT publish failed: [Errno 111] Connection refused
```

**Solutions:**

- Check MQTT Broker in Home Assistant (Settings → Add-ons → Mosquitto)
- Verify credentials
- Set `mqtt_host` to `core-mosquitto`
- In DEBUG mode, connection details are logged

#### Performance Issues

**Symptom:**

```
WARNING - Cycle 52.1s > 80% poll_interval (30s)
```

**Solutions:**

- Increase `poll_interval` (e.g., from 30s to 60s or 120s)
- Check network connection to inverter
- Analyze timing measurements in DEBUG log
- For very slow networks, use `poll_interval: 120s`

#### Filter Activity (NEW in 1.6.0)

**Symptom:**

```
INFO - 📊 Published - PV: 788W | AC Out: 211W | Grid: 11W | Battery: 569W 🔍[3 filtered]
```

**Meaning:** The add-on detected and filtered invalid counter values (likely Modbus read errors)

**Normal behavior:** Occasional filtering (1-2 per hour) is expected and protects your energy statistics

**Investigate if:** Frequent filtering (every cycle) indicates connection issues

- Enable DEBUG mode to see which sensors are filtered
- Check Modbus connection stability
- Consider increasing poll_interval

**Understanding filter summaries:**

```
🔍 Filter summary (last 20 cycles): 0 values filtered - all data valid ✓
```

→ Perfect! No problems in the last 20 cycles

```
🔍 Filter summary (last 20 cycles): 3 values filtered | Details: {'energy_yield_accumulated': 2, 'battery_charge_total': 1}
```

→ 3 values filtered in 20 cycles - acceptable, shows occasional read errors

#### Critical Key Warnings

**Symptom:**

```
WARNING - Critical 'meter_power_active' missing, using 0
```

**Cause:** Your inverter has no Power Meter or different hardware configuration

**Solution:** Warning is normal, add-on automatically sets fallback values (0)

## Tips & Best Practices

### Initial Setup

1. Set `log_level: INFO` to see important events
2. Start the add-on and check logs
3. Wait for "Connected (Slave ID: X)" and "TotalIncreasingFilter initialized"
4. Check first data points in log
5. Observe filter summary after 20 cycles
6. Go to MQTT Integration and enable desired entities

### Connection Timeout Problems

1. **Vary Slave ID:**

   ```yaml
   slave_id: 0 # Try 0, 1, 16
   ```

2. **Increase Poll Interval:**

   ```yaml
   poll_interval: 60 # Instead of 30
   ```

3. **Enable DEBUG:**

   ```yaml
   log_level: DEBUG
   ```

4. **Test Network:**
   - SSH/Terminal: `ping <INVERTER_IP>`
   - Latency under 50ms = good

### Normal Operation

- Use `log_level: INFO` for clear logs
- `poll_interval: 30-60s` for optimal performance
- Occasionally monitor cycle times in log
- Observe filter summaries every 20 cycles
- Error tracker automatically shows recovery statistics

### Performance Optimization

- Watch for WARNING messages in log
- If cycle times > 80% poll_interval → increase `poll_interval`
- DEBUG level shows exact timing measurements for each step
- Error tracker provides insight into connection stability
- Filter activity shows data quality

### Troubleshooting

- DEBUG level shows exactly which registers are read
- Check `binary_sensor.huawei_solar_status` for connection status
- Regularly check logs for warnings/errors
- Filter summaries show data quality
- Watch Health Check in Home Assistant Add-on status
- Error recovery messages show downtime and error types

### Filter Monitoring (NEW in 1.6.0)

- **INFO level:** Filter summary every 20 cycles shows long-term trend
- **DEBUG level:** Detailed filter info at every event
- **Inline indicator:** `🔍[X filtered]` shows immediately when filtered
- **Occasional filtering:** 1-2 per hour is normal and acceptable
- **Frequent filtering:** Indicates Modbus connection problems
- **No filtering:** `0 values filtered - all data valid ✓` is optimal

### Multi-Inverter Setup

The add-on is currently designed for one inverter. For multiple inverters:

- Install the add-on multiple times (different names)
- Use different `mqtt_topic` values
- Configure different `modbus_host` addresses

## Health Check

The add-on has an integrated health check:

- Checks every 60 seconds if Python process is running
- Status visible at: **Settings → Add-ons → Huawei Solar → Status**
- If `unhealthy` → restart add-on

Full changelog: [CHANGELOG.md](https://github.com/arboeh/huABus/blob/main/huawei-solar-modbus-mqtt/CHANGELOG.md)

## Support & Development

- **GitHub Repository:** [arboeh/huABus](https://github.com/arboeh/huABus)
- **Issues & Feature Requests:** [GitHub Issue Templates](https://github.com/arboeh/huABus/issues/new/choose)
- **Based on:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)
