# 🌞⚡huABus - Huawei Solar Modbus via MQTT

> This is the **huABus** Home Assistant Addon. Please refer to the
> [GitHub Repository](https://github.com/arboeh/huABus) for full documentation,
> configuration options, and troubleshooting guides.
>
> ⚠️ Huawei inverters allow only **one active Modbus TCP connection** at a time.
> Remove any other Huawei integrations before installing.

## About

Reads data from your Huawei inverter via Modbus TCP and publishes it via MQTT
with automatic Home Assistant discovery.

## Features

- **67 Essential Registers** for complete inverter monitoring
- **Automatic Slave ID Detection** — tries common values (1, 2, 100) automatically
- **Total Increasing Filter** — prevents false counter resets, active from first cycle
- **Intelligent error tracking** with downtime aggregation and recovery logging
- **MQTT Auto-Discovery** — all entities appear automatically under a single device
- **Auto MQTT credentials** — uses Home Assistant MQTT Service by default
- **Comprehensive test suite** — 88% coverage with unit, integration, and E2E tests
- **Multi-architecture support** (aarch64, amd64, armhf, armv7, i386)
