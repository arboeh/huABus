# Huawei Solar Modbus → Home Assistant via MQTT

🌐 [English](README.md) | 🇩🇪 **Deutsch**

[![aarch64](https://img.shields.io/badge/aarch64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![amd64](https://img.shields.io/badge/amd64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armhf](https://img.shields.io/badge/armhf-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armv7](https://img.shields.io/badge/armv7-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![i386](https://img.shields.io/badge/i386-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![release](https://img.shields.io/github/v/release/arboeh/homeassistant-huawei-solar-addon?display_name=tag)](https://github.com/arboeh/homeassistant-huawei-solar-addon/releases/latest)

Home Assistant Add-on für Huawei SUN2000 Wechselrichter via Modbus TCP → MQTT mit Auto-Discovery.

**Version 1.3.4** – 57 Register, 69+ Entitäten, ~5–6 s Zykluszeit  
**Changelog** - [CHANGELOG](huawei-solar-modbus-mqtt/CHANGELOG.md)

## Features

- **Modbus TCP → MQTT:** 69+ Entitäten mit Auto-Discovery
- **Vollständiges Monitoring:** Batterie, PV (1-4), Netz (3-Phasen), Ertrag, Grid Power
- **Performance:** ~5s Cycle, konfigurierbar (30-60s empfohlen)

## Installation

1. [![Repository hinzufügen](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Farboeh%2Fhomeassistant-huawei-solar-addon)
2. "Huawei Solar Modbus to MQTT" installieren → Starten
3. **Einstellungen → Geräte & Dienste → MQTT → "Huawei Solar Inverter"**

## Konfiguration

    modbus_host: "192.168.1.100" # Inverter IP
    modbus_device_id: 1 # Slave ID (1 oder 16)
    mqtt_topic: "huawei-solar"
    poll_interval: 30 # Sekunden
    log_level: "INFO"

**Auto-MQTT:** `mqtt_host` leer lassen → nutzt HA MQTT Service automatisch

## Wichtige Entitäten

| Kategorie | Sensoren |
|-----------|----------|
| **Power** | `solar_power`, `grid_power`, `battery_power`, `pv1-4_power` |
| **Energy** | `daily_yield`, `total_yield`, `grid_exported/imported` |
| **Battery** | `battery_soc`, `charge/discharge_today`, `bus_voltage/current` |
| **Grid** | `voltage_phase_a/b/c`, `line_voltage_ab/bc/ca`, `frequency` |
| **Device** | `model_name`, `serial_number`, `efficiency`, `temperature` |

## Fehlerbehebung

**Keine Verbindung:** Modbus TCP aktivieren, IP/Slave-ID prüfen (1/16/0 testen), `log_level: DEBUG`  
**MQTT Fehler:** `mqtt_host: "core-mosquitto"` nutzen, Credentials leer lassen  
**Performance:** `poll_interval: 60` bei Cycle-Warnungen

**Logs:** Add-ons → Huawei Solar → Log-Tab

## Credits

**Basiert auf der Idee von:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)  
**Verwendet Offizielle Huawei Modbus‑Bibliothek:** [wlcrs/huawei-solar-lib](https://github.com/wlcrs/huawei-solar-lib)  
**Entwickelt von:** [arboeh](https://github.com/arboeh) | **Lizenz:** MIT
