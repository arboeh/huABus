# 🌞⚡huABus - Huawei Solar Modbus via MQTT

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-41BDF5?logo=home-assistant)](https://www.home-assistant.io/)
[![release](https://img.shields.io/github/v/release/arboeh/huABus?display_name=tag)](https://github.com/arboeh/huABus/releases/latest)
[![Tests](https://github.com/arboeh/huABus/workflows/Tests/badge.svg)](https://github.com/arboeh/huABus/actions)
[![codecov](https://codecov.io/gh/arboeh/huABus/branch/main/graph/badge.svg)](https://codecov.io/gh/arboeh/huABus)
[![Security](https://img.shields.io/badge/Security-Policy-blue?logo=github)](https://github.com/arboeh/huABus/blob/main/SECURITY.md)  
[![maintained](https://img.shields.io/maintenance/yes/2026)](https://github.com/arboeh/huABus/graphs/commit-activity)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/arboeh/huABus/blob/main/LICENSE)  
[![aarch64](https://img.shields.io/badge/aarch64-yes-green.svg)](https://github.com/arboeh/huABus)
[![amd64](https://img.shields.io/badge/amd64-yes-green.svg)](https://github.com/arboeh/huABus)
[![armhf](https://img.shields.io/badge/armhf-yes-green.svg)](https://github.com/arboeh/huABus)
[![armv7](https://img.shields.io/badge/armv7-yes-green.svg)](https://github.com/arboeh/huABus)
[![i386](https://img.shields.io/badge/i386-yes-green.svg)](https://github.com/arboeh/huABus)

> This is the **huABus** Home Assistant App. Please refer to the  
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
- **Comprehensive test suite** — 89% coverage with unit, integration, and E2E tests
- **Multi-architecture support** (aarch64, amd64, armhf, armv7, i386)
