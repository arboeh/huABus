# Home Assistant App: huABus | Huawei Solar Modbus to MQTT

Reads data from your Huawei inverter via Modbus TCP and publishes it via MQTT with automatic Home Assistant discovery.

## About

This app monitors your Huawei solar inverter using Modbus TCP protocol and publishes all data to MQTT with automatic Home Assistant discovery. It provides comprehensive monitoring of:

- PV power generation (up to 4 strings)
- Battery status and energy flow
- Grid import/export (3-phase)
- Smart meter data (if available)
- Inverter status and diagnostics

### Features

- **58 Essential Registers** for complete monitoring
- **total_increasing Filter** prevents false counter resets in energy statistics
- **2-5s cycle time** for real-time data
- **Comprehensive error tracking** with intelligent aggregation
- **MQTT Auto-Discovery** for seamless Home Assistant integration
- **Multi-architecture support** (aarch64, amd64, armhf, armv7, i386)

For more information, please see [GitHub Repository](https://github.com/arboeh/huABus).
