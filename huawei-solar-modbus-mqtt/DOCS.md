# huABus | Huawei Solar Modbus to MQTT

Reads data from your Huawei SUN2000 inverter via Modbus TCP and publishes it via MQTT with automatic Home Assistant discovery.

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

1. Settings → Add-ons → Add-on Store → ⋮ (top right) → Repositories
2. Add: `https://github.com/arboeh/huABus`
3. Install "huABus | Huawei Solar Modbus to MQTT"

### 2. Minimal Configuration

```yaml
modbus_host: "192.168.1.100"  # Your inverter IP
slave_id: 1                    # Try 0, 1, or 16 if timeout occurs
log_level: "INFO"
```

### 3. Verification

**Success indicators in logs:**
```
INFO - 🚀 Huawei Solar → MQTT starting
INFO - 🔌 Connected (Slave ID: 1)
INFO - Essential read: 2.1s (58/58)
INFO - 📊 Published - PV: 4500W | ...
```

**Enable sensors:**
- Settings → Devices & Services → MQTT → "Huawei Solar Inverter"

### 4. Common First-Time Issues

| Symptom | Quick Fix |
|---------|-----------|
| `ERROR - Timeout` | Try `slave_id: 0`, then `16` |
| `Connection refused` | Check inverter IP, enable Modbus TCP |
| `No sensors appear` | Wait 30s, refresh MQTT integration |

## Features

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
- **Health check** for container monitoring

## Configuration Options

### Modbus Settings

- **modbus_host** (required): IP address of inverter (e.g., `192.168.1.100`)
- **modbus_port** (default: `502`): Modbus TCP port
- **slave_id** (default: `1`, range: 0-247): Try `0`, `1`, or `16` on timeout

### MQTT Settings

- **mqtt_host** (default: `core-mosquitto`): Broker hostname
- **mqtt_port** (default: `1883`): Broker port
- **mqtt_user** (optional): Username (leave empty for auto-config)
- **mqtt_password** (optional): Password (leave empty for auto-config)
- **mqtt_topic** (default: `huawei-solar`): Base topic for data

### Advanced Settings

- **log_level** (default: `INFO`):
  - `DEBUG`: Detailed performance metrics, filter details at every event
  - `INFO`: Important events, filter summaries every 20 cycles (recommended)
  - `WARNING/ERROR`: Problems only
- **status_timeout** (default: `180s`, range: 30-600): Offline timeout
- **poll_interval** (default: `30s`, range: 10-300): Query interval
  - Recommended: 30-60s for optimal balance

## MQTT Topics

- **Sensor Data:** `huawei-solar` (JSON with all sensor data + timestamp)
- **Status:** `huawei-solar/status` (online/offline for availability)

## Home Assistant Entities

Find entities at: **Settings → Devices & Services → MQTT → "Huawei Solar Inverter"**

### Main Entities (enabled by default)

**Power:**
- `sensor.solar_power`, `sensor.input_power`, `sensor.grid_power`, `sensor.battery_power`, `sensor.pv1_power`

**Energy (filter-protected):**
- `sensor.solar_daily_yield`, `sensor.solar_total_yield`*
- `sensor.grid_energy_exported`*, `sensor.grid_energy_imported`*
- `sensor.battery_charge_today`, `sensor.battery_discharge_today`
- `sensor.battery_total_charge`*, `sensor.battery_total_discharge`*

*Filter-protected sensors use last valid value on Modbus errors instead of 0

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

| Scenario | Poll Interval | Status Timeout |
|----------|---------------|----------------|
| Standard | 30s | 180s |
| Fast | 20s | 120s |
| Slow Network | 60s | 300s |
| Debugging | 10s | 60s |

## Troubleshooting

### Connection Timeout

**Symptom:** `ERROR - Timeout while waiting for connection`

**Solutions:**
1. Try different Slave IDs: `0`, `1`, `16`
2. Increase `poll_interval` from `30` to `60`
3. Check network: `ping <inverter_ip>`
4. Enable `log_level: DEBUG` for details

### Connection Refused

**Symptom:** `ERROR - [Errno 111] Connection refused`

**Solutions:**
- Verify IP address and port
- Enable Modbus TCP in inverter web interface
- Check firewall rules

### MQTT Connection Error

**Symptom:** `ERROR - MQTT publish failed`

**Solutions:**
- Check MQTT Broker (Settings → Add-ons → Mosquitto)
- Set `mqtt_host: core-mosquitto`
- Verify credentials

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
1. Use `log_level: INFO`
2. Verify "Connected" and "TotalIncreasingFilter initialized" in logs
3. Wait for first data points
4. Enable desired entities in MQTT integration

### Troubleshooting
- Enable `log_level: DEBUG` for detailed diagnostics
- Check `binary_sensor.huawei_solar_status` for connection status
- Monitor filter summaries for data quality
- Watch Health Check in Add-on status

### Multi-Inverter Setup
- Install add-on multiple times with different names
- Use different `mqtt_topic` per instance
- Configure different `modbus_host` addresses

## Support

- **GitHub:** [arboeh/huABus](https://github.com/arboeh/huABus)
- **Issues:** [GitHub Issue Templates](https://github.com/arboeh/huABus/issues/new/choose)
- **Based on:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)
