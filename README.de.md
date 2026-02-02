<img src="logo.svg" alt="huABus" height="40"/>

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
> Huawei-Wechselrichter erlauben **nur EINE aktive Modbus TCP-Verbindung**. Dies ist ein häufiger Anfängerfehler.
>
> **Vor Installation:**
>
> - ✅ Entferne alle anderen Huawei Solar Integrationen (wlcrs/huawei_solar, HACS, etc.)
> - ✅ Deaktiviere Monitoring-Tools und Apps mit Modbus-Zugriff
> - ✅ Hinweis: FusionSolar Cloud zeigt möglicherweise "Abnormale Kommunikation" - das ist normal
>
> Mehrere Verbindungen führen zu **Timeouts und Datenverlust**!

**58 Essenzielle Registers, 69+ Entitäten, ~2–5s Laufzeit**  
**Changelog:** [CHANGELOG.md](huawei-solar-modbus-mqtt/CHANGELOG.md)

## Features

- **Modbus TCP → MQTT:** 69+ Entitäten mit Auto-Discovery
- **Vollständiges Monitoring:** Batterie, PV (1-4), Netz (3-Phasen), Energie-Counter
- **total_increasing Filter:** Verhindert falsche Counter-Resets in Energie-Statistiken
  - Keine Warmup-Phase - sofortiger Schutz
  - Automatischer Reset bei Verbindungsfehlern
  - Sichtbar in Logs mit 20-Cycle-Zusammenfassungen
- **TRACE Log Level:** Ultra-detailliertes Debugging mit Modbus-Byte-Arrays
- **Umfassende Test-Suite:** 86% Code-Coverage mit Unit-, Integration- und E2E-Tests
- **Performance:** ~2-5s Cycle, konfigurierbares Poll-Intervall (30-60s empfohlen)
- **Error Tracking:** Intelligente Aggregation mit Downtime-Tracking
- **MQTT-Stabilität:** Connection Wait-Loop und Retry-Logik
- **Plattformübergreifend:** Alle gängigen Architekturen (aarch64, amd64, armhf, armv7, i386)

## 🚀 Schnellstart

**Neu bei huABus?** Schau dir unseren [5-Minuten-Schnellstart-Guide](huawei-solar-modbus-mqtt/DOCS.de.md#-schnellstart) an:

- ✅ Schritt-für-Schritt Installation mit erwarteten Ausgaben
- ✅ Verbindungsprobleme lösen (Slave ID, Timeouts)
- ✅ Klare Erfolgsindikatoren
- ✅ Häufige Erstinstallations-Probleme gelöst

Perfekt für Einsteiger! Erfahrene Nutzer: springe zu [Konfiguration](#konfiguration).

## Vergleich: wlcrs/huawei_solar vs. dieses Add-on

Beide nutzen die gleiche `huawei-solar` Library, haben aber unterschiedliche Anwendungsfälle:

| Feature | wlcrs/huawei_solar | Dieses Add-on |
|---------|-------------------|---------------|
| Batterie-Steuerung | ✅ | ❌ (read-only) |
| MQTT-nativ | ❌ | ✅ |
| total_increasing Filter | ❌ | ✅ |
| Externe Integrationen | Begrenzt | ✅ (EVCC, Node-RED, Grafana) |
| Zykluszeit | Variabel | 2-5s |
| Error Tracking | Basis | Advanced |

**Wichtig:** Beide teilen die gleiche Limitierung - nur **EINE Modbus-Verbindung**. Für gleichzeitige Nutzung wird ein Modbus Proxy benötigt.

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

Konfiguration über Home Assistant UI mit deutschen Feldnamen:

- **Modbus Host:** Inverter IP-Adresse (z.B. `192.168.1.100`)
- **Modbus Port:** Standard: `502`
- **Slave ID:** Meist `1`, manchmal `16` oder `0` (verschiedene Werte bei Timeout testen)
- **MQTT Broker:** Standard: `core-mosquitto`
- **MQTT Port:** Standard: `1883`
- **MQTT Benutzername/Passwort:** Optional (leer lassen für Auto-Config)
- **MQTT Topic:** Standard: `huawei-solar`
- **Log-Level:** `TRACE` | `DEBUG` | `INFO` (empfohlen) | `WARNING` | `ERROR`
- **Status Timeout:** Standard: `180s` (Range: 30-600)
- **Abfrageintervall:** Standard: `30s` (Range: 10-300, empfohlen: 30-60s)

**Auto-MQTT:** Broker-Zugangsdaten leer lassen → nutzt automatisch HA MQTT Service

### MQTT Topics

- **Messdaten (JSON):** `huawei-solar` (alle Sensoren + Timestamp)
- **Status (online/offline):** `huawei-solar/status` (Availability-Topic + LWT)

### Beispiel MQTT Payload

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
}
```

_Komplettbeispiel: [examples/mqtt_payload.json](examples/mqtt_payload.json)_

## Wichtige Entitäten

| Kategorie | Sensoren |
|-----------|----------|
| **Power** | `solar_power`, `input_power`, `grid_power`, `battery_power`, `pv1-4_power` |
| **Energy** | `daily_yield`, `total_yield`*, `grid_exported/imported`* |
| **Battery** | `battery_soc`, `charge/discharge_today`, `total_charge/discharge`*, `bus_voltage/current` |
| **Grid** | `voltage_phase_a/b/c`, `line_voltage_ab/bc/ca`, `frequency` |
| **Meter** | `meter_power_phase_a/b/c`, `meter_current_a/b/c`, `meter_reactive_power` |
| **Device** | `model_name`, `serial_number`, `efficiency`, `temperature`, `rated_power` |
| **Status** | `inverter_status`, `battery_status`, `meter_status` |

_* Durch total_increasing Filter vor falschen Counter-Resets geschützt_

## Aktuelle Updates

Siehe [CHANGELOG.md](huawei-solar-modbus-mqtt/CHANGELOG.md) für detaillierte Release-Notes.

**Letzte Highlights:**
- ✅ Restart Zero-Drop Fix (Filter vor erstem Cycle initialisiert)
- ✅ 86% Code-Coverage mit umfassender Test-Suite
- ✅ Filter-Vereinfachung (keine Warmup, keine Toleranz)
- ✅ TRACE Log Level für tiefes Debugging
- ✅ Erweiterte Übersetzungen (EN/DE)

## Fehlerbehebung

### ⚠️ Mehrere Modbus-Verbindungen (Häufigster Fehler!)

**Symptom:** Timeouts, "No response received", intermittierende Datenverluste

**Lösung:**
1. Prüfe **Einstellungen → Geräte & Dienste** auf andere Huawei-Integrationen
2. Entferne offizielle `wlcrs/huawei_solar` und HACS-Integrationen
3. Deaktiviere Monitoring-Software von Drittanbietern
4. Hinweis: FusionSolar Cloud "Abnormale Kommunikation" ist normal

### Weitere häufige Probleme

| Problem | Lösung |
|---------|--------|
| **Keine Verbindung** | Modbus TCP aktivieren, IP/Slave-ID prüfen (0/1/16 testen), `log_level: DEBUG` setzen |
| **Connection Timeouts** | Verschiedene Slave IDs testen; poll_interval auf 60s erhöhen |
| **MQTT Fehler** | Broker auf `core-mosquitto` setzen, Credentials leer lassen |
| **Performance-Warnungen** | Poll-Interval erhöhen wenn Cycle-Zeit > 80% des Intervalls |
| **Filter-Aktivität** | Gelegentliches Filtern (1-2/Stunde) ist normal; häufig = Verbindungsprobleme |

**Logs:** Add-ons → Huawei Solar Modbus to MQTT → Log-Tab

## Support & Issues

Bug gefunden oder Feature-Wunsch? Nutze unsere [GitHub Issue Templates](https://github.com/arboeh/huABus/issues/new/choose).

## Dokumentation

- 🇩🇪 **[DOCS.de.md](huawei-solar-modbus-mqtt/DOCS.de.md)** - Vollständige Dokumentation
- 🇬🇧 **[DOCS.md](huawei-solar-modbus-mqtt/DOCS.md)** - Complete Documentation

## Credits

**Basiert auf:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)  
**Verwendet Library:** [wlcrs/huawei-solar-lib](https://github.com/wlcrs/huawei-solar-lib)  
**Entwickelt von:** [arboeh](https://github.com/arboeh) | **Lizenz:** MIT
