# huABus - Huawei Solar Modbus via MQTT + Auto-Discovery

Reads data from your Huawei inverter via Modbus TCP and publishes it via MQTT with automatic Home Assistant discovery.

> **⚠️ CRITICAL: Only ONE Modbus Connection Allowed!**
>
> Huawei inverters have a **hardware limitation**: They allow **only ONE active Modbus TCP connection** at a time.
>
> ### Before Installation - CHECK:
>
> 1. **Remove competing connections:**
>    - Settings → Devices & Services → Remove ALL Huawei integrations
>    - Disable monitoring software and mobile apps with Modbus access
> 2. **FusionSolar Cloud:**
>    - Works parallel to Modbus but may show "Abnormal Communication" → **ignore it!**
> 3. **Symptom of multiple connections:**
>    ```
>    ERROR - Timeout while waiting for connection
>    ERROR - No response received after 3 retries
>    ```
>
> **Rule:** Only ONE Modbus connection = stable system ✅

## 🚀 Quick Start

### 1. Installation

1. Settings → Addons → Addon Store⋮ (top right) → Repositories
2. Add: `https://github.com/arboeh/huABus`
3. Install "huABus | Huawei Solar Modbus to MQTT"

### 2. Minimal Configuration

```yaml
modbus_host: "192.168.1.100" # Your inverter IP
modbus_auto_detect_slave_id: true # Auto-detect (default)
log_level: "INFO"
```

**Optional:** Set manual Slave ID if auto-detection fails:

```yaml
modbus_auto_detect_slave_id: false
slave_id: 1 # Try 0, 1, 2, or 100
```

### 3. Verification

**Success indicators in logs:**

```
INFO - Inverter: 192.168.1.100:502 (Slave ID: auto-detect)
INFO - Trying Slave ID 0... ⏸️
INFO - Trying Slave ID 1... ✅
INFO - Connected (Slave ID: 1)
INFO - Registers: 58 essential
INFO - 📊 Published - PV: 4500W | AC Out: 4200W | ...
```

**Enable sensors:**

- Settings → Devices & Services → MQTT → "Huawei Solar Inverter"

### 4. Common First-Time Issues

| Symptom              | Quick Fix                             |
| -------------------- | ------------------------------------- |
| All Slave IDs fail   | Check inverter IP, enable Modbus TCP  |
| `Connection refused` | Verify Modbus TCP enabled in inverter |
| No sensors appear    | Wait 30s, refresh MQTT integration    |

## Features

- **Automatic Slave ID Detection:** Tries common values (0, 1, 2, 100) automatically
- **Auto MQTT Configuration:** Uses Home Assistant MQTT Service credentials automatically
- **Fast Modbus TCP connection** (58 essential registers, 2-5s cycle time)
- **total_increasing Filter:** Prevents false counter resets
  - Filters negative values and counter decreases
  - No warmup phase - immediate protection
  - Automatic reset on connection errors
- **Error Tracking:** Intelligent error aggregation with downtime tracking
- **Comprehensive Monitoring:**
  - PV power (PV1-4 with voltage/current)
  - Grid power (Import/Export, 3-phase)
  - Battery (SOC, power, daily/total energy)
  - Smart Meter (3-phase, if available)
  - Inverter status and efficiency
- **Configurable logging** with TRACE, DEBUG, INFO, WARNING, ERROR levels
- **Performance monitoring** with automatic warnings

## Configuration Options

### Modbus Settings

- **modbus_host** (required): IP address of inverter (e.g., `192.168.1.100`)
- **modbus_port** (default: `502`): Modbus TCP port
- **modbus_auto_detect_slave_id** (default: `true`): Auto-detect Slave ID
- **slave_id** (default: `1`, range: 0-247): Manual Slave ID (only used when auto-detect disabled)

### MQTT Settings

- **mqtt_host** (default: `core-mosquitto`): Broker hostname (leave empty for auto-config)
- **mqtt_port** (default: `1883`): Broker port
- **mqtt_user** (optional): Username (leave empty to use HA MQTT Service)
- **mqtt_password** (optional): Password (leave empty to use HA MQTT Service)
- **mqtt_topic** (default: `huawei-solar`): Base topic for data

**💡 Pro Tip:** Leave MQTT credentials empty - automatically uses Home Assistant MQTT Service!

### Advanced Settings

- **log_level** (default: `INFO`):
  - `TRACE`: Ultra-detailed with Modbus byte arrays
  - `DEBUG`: Detailed performance metrics, Slave ID detection attempts
  - `INFO`: Important events, filter summaries every 20 cycles (recommended)
  - `WARNING/ERROR`: Problems only
- **status_timeout** (default: `180s`, range: 30-600): Offline timeout
- **poll_interval** (default: `30s`, range: 10-300): Modbus query interval  
  Recommended: **30-60s** for optimal stability

## MQTT Topics

- **Sensor Data:** `huawei-solar` (JSON with all sensor data + timestamp)
- **Status:** `huawei-solar/status` (online/offline for availability)

## Home Assistant Entities

Find entities at: **Settings → Devices & Services → MQTT → "Huawei Solar Inverter"**

### Main Entities (enabled by default)

**Power:**

- `sensor.solar_power`, `sensor.input_power`, `sensor.grid_power`, `sensor.battery_power`, `sensor.pv1_power`

**Energy (filter-protected):**

- `sensor.solar_daily_yield`, `sensor.solar_total_yield`\*
- `sensor.grid_energy_exported`_, `sensor.grid_energy_imported`_
- `sensor.battery_charge_today`, `sensor.battery_discharge_today`
- `sensor.battery_total_charge`_, `sensor.battery_total_discharge`_

\*Filter-protected sensors use last valid value on Modbus errors instead of 0

**Battery:**

- `sensor.battery_soc`, `sensor.battery_bus_voltage`, `sensor.battery_bus_current`

**Grid:**

- `sensor.grid_voltage_phase_a/b/c`, `sensor.grid_line_voltage_ab/bc/ca`
- `sensor.grid_frequency`, `sensor.grid_current_phase_a/b/c`

**Inverter:**

- `sensor.inverter_temperature`, `sensor.inverter_efficiency`
- `sensor.model_name`, `sensor.serial_number`

**Status:**

- `binary_sensor.huawei_solar_status` (online/offline)
- `sensor.inverter_status`, `sensor.battery_status`

### Diagnostic Entities (disabled by default)

Enable manually: PV2/3/4 details, phase currents, detailed powers

## Performance & Monitoring

**Cycle performance:**

```
INFO - Essential read: 2.1s (58/58)
INFO - 📊 Published - PV: 4500W | AC Out: 4200W | Grid: -200W | Battery: 800W
DEBUG - Cycle: 2.3s (Modbus: 2.1s, Transform: 0.005s, MQTT: 0.194s)
```

**Automatic Slave ID detection:**

```
INFO - Inverter: 192.168.1.100:502 (Slave ID: auto-detect)
INFO - Trying Slave ID 0... ⏸️
INFO - Trying Slave ID 1... ✅
INFO - Connected (Slave ID: 1)
```

**Filter activity (when values filtered):**

```
INFO - 📊 Published - PV: 788W | ... | Battery: 569W 🔍[2 filtered]
DEBUG - 🔍 Filter details: {'energy_yield_accumulated': 1, 'battery_charge_total': 1}
```

**Filter summary (every 20 cycles):**

```
INFO - 🔍 Filter summary (last 20 cycles): 0 values filtered - all data valid ✓
```

**Automatic warnings:**

```
WARNING - Cycle 52.1s > 80% poll_interval (30s)
```

**Error recovery:**

```
INFO - Connection restored after 47s (3 failed attempts, 2 error types)
```

### Recommended Settings

| Scenario     | Poll Interval | Status Timeout |
| ------------ | ------------- | -------------- |
| Standard     | 30s           | 180s           |
| Fast         | 20s           | 120s           |
| Slow Network | 60s           | 300s           |
| Debugging    | 10s           | 60s            |

## Troubleshooting

### All Slave IDs Fail

**Symptom:** `ERROR - All Slave IDs failed`

**Solutions:**

1. Check inverter IP: `ping <inverter_ip>`
2. Enable Modbus TCP in inverter web interface
3. Check firewall rules
4. Enable `log_level: DEBUG` to see each attempt

### Connection Timeout

**Symptom:** `ERROR - Timeout while waiting for connection`

**Solutions:**

1. Auto-detect disabled? Try manual Slave IDs: `0`, `1`, `2`, `100`
2. Increase `poll_interval` from `30` to `60`
3. Check network latency

### Connection Refused

**Symptom:** `ERROR - [Errno 111] Connection refused`

**Solutions:**

- Verify IP address and port
- Enable Modbus TCP in inverter web interface
- Check firewall rules

### MQTT Connection Error

**Symptom:** `ERROR - MQTT publish failed`

**Solutions:**

- Check MQTT Broker (Settings → Addons → Mosquitto)
- Set `mqtt_host: core-mosquitto`
- Leave credentials empty for auto-config

### Performance Issues

**Symptom:** `WARNING - Cycle 52.1s > 80% poll_interval`

**Solutions:**

- Increase `poll_interval` (e.g., from 30s to 60s)
- Check network latency
- Analyze timing in DEBUG logs

### Filter Activity

**Occasional filtering (1-2/hour):** Normal - protects energy statistics
**Frequent filtering (every cycle):** Connection issues - enable DEBUG mode

**Understanding filter summaries:**

- `0 values filtered - all data valid ✓` → Perfect!
- `3 values filtered | Details: {...}` → Acceptable (occasional read errors)

## Tips & Best Practices

### Initial Setup

1. Use default auto-detect Slave ID
2. Leave MQTT credentials empty for auto-config
3. Use `log_level: INFO`
4. Verify "Connected" in logs
5. Wait for first data points
6. Enable desired entities in MQTT integration

### Troubleshooting

- Enable `log_level: DEBUG` for detailed diagnostics
- Check `binary_sensor.huawei_solar_status` for connection status
- Monitor filter summaries for data quality
- Watch Slave ID detection attempts in DEBUG logs

## Support

- **GitHub:** [arboeh/huABus](https://github.com/arboeh/huABus)
- **Issues:** [GitHub Issue Templates](https://github.com/arboeh/huABus/issues/new/choose)
- **Based on:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)
