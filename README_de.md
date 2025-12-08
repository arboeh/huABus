# Huawei Solar Modbus → Home Assistant via MQTT

🌐 [English](README.md) | 🇩🇪 **Deutsch**

[![aarch64](https://img.shields.io/badge/aarch64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![amd64](https://img.shields.io/badge/amd64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armhf](https://img.shields.io/badge/armhf-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armv7](https://img.shields.io/badge/armv7-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![i386](https://img.shields.io/badge/i386-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![release](https://img.shields.io/github/v/release/arboeh/homeassistant-huawei-solar-addon?display_name=tag)](https://github.com/arboeh/homeassistant-huawei-solar-addon/releases/latest)

Home Assistant Add-on für Huawei SUN2000 Wechselrichter via Modbus TCP → MQTT mit automatischer Discovery.

**Version 1.1.2** - Optimiert für Performance (Cycle-Time < 3s, nur 21 Essential Registers)

## Features

- **Modbus TCP** Verbindung zum Huawei SUN2000 Wechselrichter
- **MQTT Auto-Discovery** für Home Assistant
- **Monitoring:** Batterie (SOC, Power, Energy), PV-Strings, Netz (Import/Export), Ertrag, Status
- **Online/Offline Status** mit Heartbeat & MQTT LWT
- **Performance:** Optimierte Register-Reads, typisch 1-3s Cycle-Time
- **Konfigurierbar:** Log-Levels (DEBUG/INFO/WARNING/ERROR), Poll-Interval, Timeouts

## Installation

1. [![Add Repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Farboeh%2Fhomeassistant-huawei-solar-addon)

2. Add-on Store → "Huawei Solar Modbus to MQTT" installieren
3. Konfigurieren (siehe unten)
4. Starten
5. Entities erscheinen automatisch unter: **Einstellungen → Geräte & Dienste → MQTT → "Huawei Solar Inverter"**

## Konfiguration

### Minimal (empfohlen)

    modbus_host: "192.168.1.100"
    modbus_device_id: 1
    poll_interval: 30

### Vollständig

    Modbus
    modbus_host: "192.168.1.100" # IP des Wechselrichters
    modbus_port: 502
    modbus_device_id: 1 # Slave ID (meist 1, manchmal 16)

    MQTT (Auto-Discovery aus HA)
    mqtt_host: "core-mosquitto" # Leer lassen für Auto
    mqtt_port: 1883
    mqtt_user: "" # Leer = Auto aus HA
    mqtt_password: ""
    mqtt_topic: "huawei-solar"

    Performance & Logging
    poll_interval: 30 # Empfehlung: 30-60s
    status_timeout: 180
    log_level: "INFO" # DEBUG/INFO/WARNING/ERROR

## MQTT Topics

- `huawei-solar` - JSON-Daten mit allen Werten
- `huawei-solar/status` - Status (online/offline)

## Wichtigste Entitäten

**Leistung:** `solar_power`, `grid_power`, `battery_power`, `pv1_power`  
**Energie:** `solar_daily_yield`, `solar_total_yield`, `grid_energy_exported/imported`  
**Batterie:** `battery_soc`, `battery_status`  
**Netz:** `grid_voltage_phase_a/b/c`, `grid_frequency`  
**Status:** `huawei_solar_status` (binary_sensor), `inverter_status`

**Viele weitere Diagnostik-Entitäten** sind standardmäßig deaktiviert und können in HA aktiviert werden.

## Fehlerbehebung

### Modbus-Fehler
- Modbus TCP am Inverter aktivieren (Webinterface)
- IP-Adresse prüfen
- Slave IDs testen: `1`, `16`, `0`
- `log_level: DEBUG` für Details

### MQTT-Fehler
- MQTT Broker Status prüfen (Add-ons → Mosquitto)
- `mqtt_host: "core-mosquitto"` verwenden
- Credentials leer lassen für Auto-Discovery

### Performance
- Bei Warnungen `poll_interval` erhöhen
- Empfohlene Werte: 30-60s (Standard), 120s (langsames Netzwerk)

**Logs ansehen:** Einstellungen → Add-ons → Huawei Solar → Log

## Changelog Highlights

### 1.1.2 (2025-12-08)
Code-Refactoring, dynamische Python-Version, Health Check, verbesserte MQTT-Fallbacks

### 1.1.1 (2025-12-08)
Essential Registers (nur 21 statt 500+), 94% Reduktion, Cycle < 3s

### 1.1.0 (2025-12-08)
Parallele Batch-Reads, 8x Performance-Boost (240s → 30s)

[Vollständiger Changelog](CHANGELOG.md)

## Dokumentation & Support

- **[Vollständige Dokumentation (Deutsch)](DOCS.md)** - Detaillierte Anleitung, Troubleshooting, Performance-Tuning
- **[Home Assistant Community](https://community.home-assistant.io)** - Diskussionen & Hilfe

## Credits

**Basiert auf:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)  
**Entwickelt von:** [arboeh](https://github.com/arboeh)  
**Lizenz:** MIT
