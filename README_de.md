# Huawei Solar Modbus → Home Assistant via MQTT

🌐 [English](README.md) | 🇩🇪 **Deutsch**

[![aarch64](https://img.shields.io/badge/aarch64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![amd64](https://img.shields.io/badge/amd64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armhf](https://img.shields.io/badge/armhf-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armv7](https://img.shields.io/badge/armv7-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![i386](https://img.shields.io/badge/i386-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![Repository](https://img.shields.io/badge/Add%20to%20Home%20Assistant-Repository-blue)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![release](https://img.shields.io/github/v/release/arboeh/homeassistant-huawei-solar-addon?display_name=tag)](https://github.com/arboeh/homeassistant-huawei-solar-addon/releases/latest)

Home Assistant Add-on: Huawei SUN2000 Wechselrichter per Modbus TCP → MQTT mit Auto-Discovery.

## Features
- Direkte Modbus TCP Verbindung zum Huawei Inverter
- Automatische Home Assistant MQTT Discovery
- Batterie (SOC, Lade-/Entladeleistung, Tagesenergie)
- PV-Strings (PV1/PV2, optional PV3/PV4)
- Netz (Import/Export, 3-phasige Spannung)
- Energieertrag (Tages-/Gesamt)
- Inverter-Status, Temperatur, Wirkungsgrad
- Online/Offline-Status mit Heartbeat
- Automatisches Reconnect

## Installation
1. **[Repository hinzufügen](https://github.com/arboeh/homeassistant-huawei-solar-addon)**
2. Add-on Store → "Huawei Solar Modbus to MQTT" installieren
3. Konfigurieren und starten
4. Entities erscheinen automatisch in HA

## Konfiguration

    modbushost: 192.168.1.100
    modbusport: 502
    modbusdeviceid: 1
    mqtttopic: huawei-solar
    debug: false
    statustimeout: 180
    pollinterval: 60


## MQTT Topics
- `huawei-solar` (JSON Daten)
- `huawei-solar/status` (online/offline)

## Support
- [GitHub Issues](https://github.com/arboeh/homeassistant-huawei-solar-addon/issues)
- [HA Community](https://community.home-assistant.io)

**Basierend auf [huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)**
