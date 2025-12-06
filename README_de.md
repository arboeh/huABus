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
- Direkte Modbus TCP Verbindung zum Huawei Wechselrichter
- Automatische Home Assistant MQTT Discovery
- Batterie-Monitoring (SOC, Lade-/Entladeleistung, Tagesenergie)
- PV-String-Monitoring (PV1/PV2, optional PV3/PV4)
- Netz-Monitoring (Import/Export, 3-phasige Spannung)
- Energieertrag-Tracking (Tages-/Gesamtertrag)
- Wechselrichter-Status, Temperatur, Wirkungsgrad
- Online/Offline-Status mit Heartbeat-Überwachung
- Automatisches Reconnect bei Kommunikationsfehlern
- Robuste Fehlerbehandlung für unbekannte Register-Werte

## Installation
1. [![Add Repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Farboeh%2Fhomeassistant-huawei-solar-addon)

2. Add-on Store → "Huawei Solar Modbus to MQTT" installieren
3. Add-on konfigurieren (siehe unten)
4. Add-on starten
5. Entities erscheinen automatisch in Home Assistant via MQTT Discovery

## Konfiguration

### Modbus-Einstellungen
- **modbus_host**: IP-Adresse des Huawei Wechselrichters (z.B. `192.168.1.100`)
- **modbus_port**: Modbus TCP Port (Standard: `502`)
- **modbus_device_id**: Modbus Slave-ID (Standard: `1`)

### MQTT-Einstellungen
- **mqtt_host**: MQTT Broker Adresse (Standard: `core-mosquitto` für HA integrierten Broker)
- **mqtt_port**: MQTT Broker Port (Standard: `1883`)
- **mqtt_user**: MQTT Benutzername (leer lassen, falls keine Authentifizierung)
- **mqtt_password**: MQTT Passwort (leer lassen, falls keine Authentifizierung)
- **mqtt_topic**: Basis-Topic für MQTT-Nachrichten (Standard: `huawei-solar`)

### Erweiterte Einstellungen
- **debug**: Debug-Logging aktivieren (Standard: `false`)
- **status_timeout**: Sekunden, nach denen der Status auf offline gesetzt wird, wenn kein erfolgreicher Read (Standard: `180`)
- **poll_interval**: Intervall in Sekunden zwischen Datenabfragen (Standard: `60`)

### Beispiel-Konfiguration

    modbus_host: 192.168.1.100
    modbus_port: 502
    modbus_device_id: 1
    mqtt_host: core-mosquitto
    mqtt_port: 1883
    mqtt_user: ""
    mqtt_password: ""
    mqtt_topic: huawei-solar
    debug: false
    status_timeout: 180
    poll_interval: 60


## MQTT Topics
- `<mqtt_topic>` - JSON-Daten mit allen Wechselrichter-Werten
- `<mqtt_topic>/status` - Status (online/offline)
- `homeassistant/sensor/<mqtt_topic>/*` - Auto-Discovery Topics

## Überwachte Daten
- Batterie-Ladezustand (SOC)
- Batterie Lade-/Entladeleistung
- PV-String Spannungen und Ströme (PV1-PV4)
- Netzleistung (Einspeisung/Bezug)
- Netzspannung (3-phasig)
- Tages- und Gesamtertrag
- Wechselrichter-Temperatur
- Wechselrichter-Wirkungsgrad
- Gerätestatus

## Fehlerbehebung
- Stelle sicher, dass Modbus TCP am Huawei Wechselrichter aktiviert ist
- Überprüfe die Netzwerkverbindung zwischen Home Assistant und Wechselrichter
- Verifiziere, dass der MQTT Broker läuft und erreichbar ist
- Aktiviere den Debug-Modus für detailliertes Logging
- Prüfe die Add-on Logs auf Fehlermeldungen

## Support
- [Home Assistant Community](https://community.home-assistant.io)
- [GitHub Issues](https://github.com/arboeh/homeassistant-huawei-solar-addon/issues)

**Basierend auf [huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)**
