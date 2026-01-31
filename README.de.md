<img src="logo.svg" alt="jaABlu" height="40"/>

### Huawei Solar Modbus → Home Assistant via MQTT + Auto-Discovery

[🇬🇧 English](README.md) | 🇩🇪 **Deutsch**

[![release](https://img.shields.io/github/v/release/arboeh/huABus?display_name=tag)](https://github.com/arboeh/huABus/releases/latest)
[![Tests](https://github.com/arboeh/huABus/workflows/Tests/badge.svg)](https://github.com/arboeh/huABus/actions)
[![codecov](https://codecov.io/gh/arboeh/huABus/branch/main/graph/badge.svg)](https://codecov.io/gh/arboeh/huABus)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/arboeh/huABus/blob/main/LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-41BDF5?logo=home-assistant)](https://www.home-assistant.io/)  
[![aarch64](https://img.shields.io/badge/aarch64-yes-green.svg)](https://github.com/arboeh/huABus)
[![amd64](https://img.shields.io/badge/amd64-yes-green.svg)](https://github.com/arboeh/huABus)
[![armhf](https://img.shields.io/badge/armhf-yes-green.svg)](https://github.com/arboeh/huABus)
[![armv7](https://img.shields.io/badge/armv7-yes-green.svg)](https://github.com/arboeh/huABus)
[![i386](https://img.shields.io/badge/i386-yes-green.svg)](https://github.com/arboeh/huABus)

> **⚠️ WICHTIG: Nur EINE Modbus-Verbindung möglich**  
> Huawei-Wechselrichter erlauben **nur EINE aktive Modbus TCP-Verbindung**. Dies ist ein häufiger Anfängerfehler bei der Integration von Huawei-PV-Anlagen ins Smart Home.
>
> **Vor Installation dieses Add-ons:**
>
> - ✅ Deaktiviere oder entferne alle anderen Huawei Solar Integrationen (offizielle wlcrs/huawei_solar, HACS-Integrationen, etc.)
> - ✅ Stelle sicher, dass keine andere Software auf Modbus TCP zugreift (Monitoring-Tools, Apps, andere Home Assistant Instanzen)
> - ✅ Hinweis: FusionSolar Cloud zeigt möglicherweise "Abnormale Kommunikation" wenn Modbus aktiv ist - das ist normal
>
> Mehrere gleichzeitige Modbus-Verbindungen führen zu **Connection-Timeouts und Datenverlust** für alle Clients!

**Version 1.7.1** – 58 Essenzielle Registers, 69+ Entitäten, ~2–5 s Laufzeit  
**Changelog** - [CHANGELOG.md](huawei-solar-modbus-mqtt/CHANGELOG.md)

## Features

- **Modbus TCP → MQTT:** 69+ Entitäten mit Auto-Discovery
- **Vollständiges Monitoring:** Batterie, PV (1-4), Netz (3-Phasen), Ertrag, Grid Power
- **total_increasing Filter:** Verhindert falsche Counter-Resets in Home Assistant Energie-Statistiken
  - Warmup-Period (60s) für stabile Filter-Initialisierung
  - Automatischer Schutz vor Modbus-Lesefehlern
- **TRACE Log Level (NEU):** Ultra-detailliertes Logging für tiefes Debugging mit Modbus-Byte-Arrays
- **Umfassende Test-Suite (NEU):** 43 Tests für alle kritischen Funktionen
  - Unit Tests für Filter-Logik
  - Integration Tests für Komponenten-Interaktion
  - E2E Tests für komplette Workflows
  - Regression Tests für Bug-Fixes
- **Performance:** ~2-5s Cycle, konfigurierbar (30-60s empfohlen)
- **Error Tracking:** Intelligente Fehler-Aggregation mit Downtime-Tracking
- **MQTT-Stabilität:** Connection Wait-Loop und Retry-Logik für zuverlässiges Publishing
- **Optimiertes Logging:** Bashio Log-Level Synchronisation mit Filter-Status-Indikatoren
- **Plattformübergreifend:** Unterstützt alle gängigen Architekturen (aarch64, amd64, armhf, armv7, i386)

## 🚀 Schnellstart

**Neu bei huABus?** Schau dir unseren [5-Minuten-Schnellstart-Guide](huawei-solar-modbus-mqtt/DOCS.de.md#-schnellstart-5-minuten) an:

- ✅ Schritt-für-Schritt Installation mit erwarteten Ausgaben
- ✅ Verbindungsprobleme lösen (Slave ID, Timeouts)
- ✅ Klare Erfolgsindikatoren
- ✅ Häufige Erstinstallations-Probleme gelöst

Perfekt für Erstnutzer! Erfahrene Nutzer springen direkt zu [Konfiguration](#konfiguration).

## Vergleich: wlcrs/huawei_solar vs. dieses Add-on

Beide Lösungen nutzen die gleiche `huawei-solar` Library, haben aber unterschiedliche Anwendungsfälle:

**wlcrs/huawei_solar** (Native HA Integration):

- ✅ Batterie-Steuerung (Lade-/Entlade-Befehle)
- ✅ GUI-Konfiguration
- ✅ Optimizer-Monitoring
- ✅ RS485 Serial-Support

**Dieses Add-on** (MQTT Bridge):

- ✅ MQTT-nativ (Daten für [EVCC](https://evcc.io/), Node-RED, Grafana, etc.)
- ✅ total_increasing Filter (schützt Energie-Statistiken vor falschen Resets)
- ✅ Advanced Error Tracking & Performance Monitoring
- ✅ Schnelle 2-5s Zykluszeiten
- ✅ Read-only Monitoring

**Wichtig:** Beide teilen die gleiche Limitierung - Huawei-Inverter erlauben **nur EINE Modbus-Verbindung**. Für gleichzeitige Nutzung wird ein Modbus Proxy benötigt.

**Wann welches nutzen?**

- **wlcrs:** Batterie-Steuerung + native HA-Integration
- **Dieses Add-on:** MQTT-Monitoring + externe System-Integration

## Screenshots

### Home Assistant Integration

![Diagnostic Entities](screenshots/diagnostics.png)

_Diagnose-Entitäten mit Inverter-Status, Temperatur und Batterie-Informationen_

![Sensor Overview](screenshots/sensors.png)

_Vollständige Sensorübersicht mit Echtzeit-Leistung, Energie und Netzdaten_

![MQTT Device Info](screenshots/mqtt-info.png)

_MQTT-Geräteintegrations-Details_

## Installation

1. [![Repository hinzufügen](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Farboeh%2FhuABus)
2. "huABus | Huawei Solar Modbus to MQTT" installieren → Starten
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

### MQTT Topics

- **Messdaten (JSON)**: `huawei-solar` (oder dein konfiguriertes Topic)  
  Enthält alle Sensordaten als JSON-Objekt mit `last_update` Timestamp.
- **Status (online/offline)**: `huawei-solar/status`  
  Wird genutzt für Binary Sensor, `availability_topic`, und Last Will Testament.

### Beispiel MQTT Payload

Veröffentlicht auf Topic `huawei-solar`:

```json
{
  "power_active": 1609,
  "power_input": 2620,
  "battery_soc": 32,
  "battery_power": 1020,
  "meter_power_active": 50,
  "voltage_grid_A": 239.3,
  "inverter_temperature": 32.4,
  "inverter_status": "On-grid",
  "model_name": "SUN2000-6KTL-M1",
  "last_update": 1768649491
  ...
  ..
  .
}
```

_Komplettbeispiel mit allen 58+ Datenpunkten: siehe [examples/mqtt_payload.json](examples/mqtt_payload.json)_

## Wichtige Entitäten

| Kategorie   | Sensoren                                                                                   |
| ----------- | ------------------------------------------------------------------------------------------ |
| **Power**   | `solar_power`, `input_power`, `grid_power`, `battery_power`, `pv1-4_power`                 |
| **Energy**  | `daily_yield`, `total_yield`_, `grid_exported/imported`_                                   |
| **Battery** | `battery_soc`, `charge/discharge_today`, `total_charge/discharge`\*, `bus_voltage/current` |
| **Grid**    | `voltage_phase_a/b/c`, `line_voltage_ab/bc/ca`, `frequency`                                |
| **Meter**   | `meter_power_phase_a/b/c`, `meter_current_a/b/c`, `meter_reactive_power`                   |
| **Device**  | `model_name`, `serial_number`, `efficiency`, `temperature`, `rated_power`                  |
| **Status**  | `inverter_status`, `battery_status`, `meter_status`                                        |

_\* Sensoren mit Sternchen sind durch total_increasing Filter vor falschen Counter-Resets geschützt_

## Was ist neu in 1.7.1?

**Bugfix-Release - Zero-Drops bei Restart behoben (HANT Issue)**

- **Behoben**: Zero-Drops beim Add-on-Neustart
  - Filter wird jetzt vor dem ersten Cycle initialisiert
  - Kein ungeschützter Moment beim Start mehr
  - Energie-Counter von Anfang an geschützt

- **Behoben**: Verbesserte Behandlung negativer Werte
- **Behoben**: Singleton-Reset-Verhalten
- **Neu**: 12 umfassende Restart-Schutz-Tests

Alle Tests bestehen: 51/51 ✅

**Vorher (1.7.0):** Filter-Vereinfachung - Keine Warmup, keine Toleranz  
**Vorher (1.6.2):** TRACE Log Level, umfassende Tests

## Fehlerbehebung

### ⚠️ Mehrere Modbus-Verbindungen (Häufigster Fehler!)

**Symptom:** Connection Timeouts, "No response received", intermittierende Datenverluste

**Ursache:** Huawei-Wechselrichter unterstützen **nur EINE aktive Modbus TCP-Verbindung**

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
**Performance:** Abfrageintervall auf 60s bei Cycle-Warnungen erhöhen  
**Filter-Aktivität:** Gelegentliches Filtern (1-2 pro Stunde) ist normal; häufiges Filtern deutet auf Verbindungsprobleme hin - DEBUG-Modus aktivieren

**Logs:** Add-ons → Huawei Solar Modbus to MQTT → Log-Tab

## Support & Issues

Bug gefunden oder Feature-Wunsch? Bitte nutze unsere [GitHub Issue Templates](https://github.com/arboeh/huABus/issues/new/choose) für strukturierte Meldungen.

## Dokumentation

- 🇩🇪 **[DOCS.de.md](huawei-solar-modbus-mqtt/DOCS.de.md)** - Vollständige Dokumentation
- 🇬🇧 **[DOCS.md](huawei-solar-modbus-mqtt/DOCS.md)** - Complete Documentation

## Credits

**Basiert auf der Idee von:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)  
**Verwendet die Huawei Modbus‑Bibliothek:** [wlcrs/huawei-solar-lib](https://github.com/wlcrs/huawei-solar-lib)  
**Entwickelt von:** [arboeh](https://github.com/arboeh) | **Lizenz:** MIT
