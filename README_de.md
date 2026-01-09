# Huawei Solar Modbus → Home Assistant via MQTT

🌐 [English](README.md) | 🇩🇪 **Deutsch**

[![aarch64](https://img.shields.io/badge/aarch64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![amd64](https://img.shields.io/badge/amd64-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armhf](https://img.shields.io/badge/armhf-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![armv7](https://img.shields.io/badge/armv7-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![i386](https://img.shields.io/badge/i386-yes-green.svg)](https://github.com/arboeh/homeassistant-huawei-solar-addon)
[![release](https://img.shields.io/github/v/release/arboeh/homeassistant-huawei-solar-addon?display_name=tag)](https://github.com/arboeh/homeassistant-huawei-solar-addon/releases/latest)

> **⚠️ WICHTIG: Nur EINE Modbus-Verbindung möglich**  
> Huawei-Wechselrichter erlauben **nur EINE aktive Modbus TCP-Verbindung** gleichzeitig. Dies ist ein häufiger Anfängerfehler bei der Integration von PV-Anlagen ins Smart Home.
>
> **Vor Installation dieses Add-ons:**
> - ✅ Deaktiviere oder entferne alle anderen Huawei Solar Integrationen (offizielle wlcrs/huawei_solar, HACS-Integrationen, etc.)
> - ✅ Stelle sicher, dass keine andere Software auf Modbus TCP zugreift (Monitoring-Tools, Apps, andere Home Assistant Instanzen)
> - ✅ Hinweis: FusionSolar Cloud zeigt möglicherweise "Abnormale Kommunikation" wenn Modbus aktiv ist - das ist normal
>
> Mehrere gleichzeitige Modbus-Verbindungen führen zu **Connection-Timeouts und Datenverlust** für alle Clients!

Home Assistant Add-on für Huawei SUN2000 Wechselrichter via Modbus TCP → MQTT mit Auto-Discovery.

**Version 1.4.2** – 58 Essential Registers, 69+ Entitäten, ~2–5 s Zykluszeit  
**Changelog** - [CHANGELOG.md](huawei-solar-modbus-mqtt/CHANGELOG.md)

## Features

- **Modbus TCP → MQTT:** 69+ Entitäten mit Auto-Discovery
- **Vollständiges Monitoring:** Batterie, PV (1-4), Netz (3-Phasen), Ertrag, Grid Power
- **Performance:** ~2-5s Cycle, konfigurierbar (30-60s empfohlen)
- **Error Tracking:** Intelligente Fehler-Aggregation mit Downtime-Tracking
- **Optimiertes Logging:** Bashio Log-Level Synchronisation
- **Plattformübergreifend:** Unterstützt alle gängigen Architekturen (aarch64, amd64, armhf, armv7, i386)

## Installation

1. [![Repository hinzufügen](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Farboeh%2Fhomeassistant-huawei-solar-addon)
2. "Huawei Solar Modbus to MQTT" installieren → Starten
3. **Einstellungen → Geräte & Dienste → MQTT → "Huawei Solar Inverter"**

## Konfiguration

Die Add-on-Konfiguration erfolgt über die Home Assistant UI mit übersetzten deutschen Feldnamen:

- **Modbus Host:** IP-Adresse des Huawei Solar Inverters (z.B. `192.168.1.100`)
- **Modbus Port:** Port für die Modbus-Verbindung (Standard: `502`)
- **Slave ID:** Modbus Slave ID des Inverters (meist `1`, manchmal `16` oder `0`)
- **MQTT Broker:** Hostname oder IP-Adresse des MQTT Brokers (z.B. `core-mosquitto`)
- **MQTT Port:** Port des MQTT Brokers (Standard: `1883`)
- **MQTT Benutzername:** Benutzername für die MQTT-Authentifizierung (optional)
- **MQTT Passwort:** Passwort für die MQTT-Authentifizierung (optional)
- **MQTT Topic:** Basis-Topic für MQTT-Nachrichten (Standard: `huawei-solar`)
- **Log-Level:** Detailgrad der Protokollierung (`DEBUG` | `INFO` | `WARNING` | `ERROR`)
- **Status Timeout:** Timeout in Sekunden für Statusprüfungen (30-600, Standard: `180`)
- **Abfrageintervall:** Intervall in Sekunden zwischen Modbus-Abfragen (10-300, Standard: `30`)

**Auto-MQTT:** MQTT Broker, Benutzername und Passwort leer lassen → nutzt HA MQTT Service automatisch

## Wichtige Entitäten

| Kategorie   | Sensoren                                                                                 |
| ----------- | ---------------------------------------------------------------------------------------- |
| **Power**   | `solar_power`, `input_power`, `grid_power`, `battery_power`, `pv1-4_power`               |
| **Energy**  | `daily_yield`, `total_yield`, `grid_exported/imported`                                   |
| **Battery** | `battery_soc`, `charge/discharge_today`, `total_charge/discharge`, `bus_voltage/current` |
| **Grid**    | `voltage_phase_a/b/c`, `line_voltage_ab/bc/ca`, `frequency`                              |
| **Meter**   | `meter_power_phase_a/b/c`, `meter_current_a/b/c`, `meter_reactive_power`                 |
| **Device**  | `model_name`, `serial_number`, `efficiency`, `temperature`, `rated_power`                |
| **Status**  | `inverter_status`, `battery_status`, `meter_status`                                      |

## Was ist neu in 1.4.2?

**Repository-Wartung:** `.gitattributes`, `.editorconfig` und `.gitignore` für besseren Entwicklungs-Workflow hinzugefügt; alle Dateien auf LF Line-Endings normalisiert (verhindert Linux/Docker-Kompatibilitätsprobleme)

**Behoben:** `pymodbus` Dependency-Version korrigiert; `.dockerignore` verbessert, um erforderliche Home Assistant Dokumentationsdateien einzuschließen

**Dokumentation:** GitHub Issue Templates für strukturierte Bug-Reports und Feature-Requests hinzugefügt; Troubleshooting-Guide für Connection-Timeout-Probleme

**Vorher (1.4.1):** Verbessertes Startup-Logging mit Emoji-Icons, visuelle Trennlinien, dynamische Log-Level-Synchronisation

**Vorher (1.4.0):** Error Tracker mit Downtime-Tracking, verbesserte Logging-Architektur, Abfrageintervall Standard auf 30s optimiert

## Fehlerbehebung

### ⚠️ Mehrere Modbus-Verbindungen (Häufigster Fehler!)

**Symptom:** Connection Timeouts, "No response received", intermittierende Datenverluste

**Ursache:** Huawei-Wechselrichter unterstützen **nur EINE Modbus TCP-Verbindung** gleichzeitig

**Lösung:**
1. Prüfe **Einstellungen → Geräte & Dienste** auf andere Huawei-Integrationen
2. Entferne oder deaktiviere:
   - Offizielle `wlcrs/huawei_solar` Integration
   - HACS-basierte Huawei-Integrationen
   - Monitoring-Software von Drittanbietern
3. Bei Nutzung von **FusionSolar Cloud**: Beachte, dass aktives Modbus "Abnormale Kommunikation" in der App anzeigen kann - das ist normal
4. Nur **EIN** System kann gleichzeitig auf Modbus zugreifen

### Weitere häufige Probleme

**Keine Verbindung:** Modbus TCP aktivieren, IP/Slave-ID prüfen (1/16/0 testen), Log-Level auf `DEBUG` setzen  
**Connection Timeouts:** Verschiedene Slave IDs testen (`0`, `1`, `16`); Abfrageintervall auf 60s erhöhen; prüfen, ob FusionSolar Cloud den Modbus-Zugriff blockiert  
**MQTT Fehler:** MQTT Broker auf `core-mosquitto` setzen, Credentials leer lassen  
**Performance:** Abfrageintervall auf 60 bei Cycle-Warnungen erhöhen

**Logs:** Add-ons → Huawei Solar Modbus to MQTT → Log-Tab

## Support & Issues

Bug gefunden oder Feature-Wunsch? Bitte nutze unsere [GitHub Issue Templates](https://github.com/arboeh/homeassistant-huawei-solar-addon/issues/new/choose) für strukturierte Meldungen.

## Dokumentation

- **[DOCS.md](huawei-solar-modbus-mqtt/DOCS.md)** - Vollständige Dokumentation
- **[CHANGELOG.md](huawei-solar-modbus-mqtt/CHANGELOG.md)** - Versionshistorie

## Credits

**Basiert auf der Idee von:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)  
**Verwendet die Huawei Modbus‑Bibliothek:** [wlcrs/huawei-solar-lib](https://github.com/wlcrs/huawei-solar-lib)  
**Entwickelt von:** [arboeh](https://github.com/arboeh) | **Lizenz:** MIT