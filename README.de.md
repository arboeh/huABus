<img src="images/heading.svg" alt="huABus" height="40"/>

### Huawei Solar Modbus zu Home Assistant via MQTT + Auto-Discovery

[🇬🇧 English](README.md) | 🇩🇪 **Deutsch**

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

**67 essenzielle Register • 69+ Entitäten • optionaler MQTT-Heartbeat • 30s Polling**  
**Changelog:** [CHANGELOG.md](huawei_solar_modbus_mqtt/CHANGELOG.md)

> **⚠️ WICHTIG: Nur EINE Modbus-Verbindung möglich**
> Huawei-Wechselrichter erlauben **nur EINE aktive Modbus TCP-Verbindung**.
>
> - ✅ Entferne alle anderen Huawei Solar Integrationen (wlcrs/huawei_solar, HACS, etc.)
> - ✅ Deaktiviere Monitoring-Tools und Apps mit Modbus-Zugriff
> - ✅ Hinweis: FusionSolar Cloud zeigt möglicherweise "Abnormale Kommunikation" - das ist normal

## Features

- **Automatische Slave ID-Erkennung:** Probiert automatisch gängige Werte (1, 2, 100)
- **Modbus TCP → MQTT:** 69+ Entitäten mit Auto-Discovery
- **Vollständiges Monitoring:** Batterie, PV (1-4), Netz (3-Phasen), Energie-Counter
- **Total Increasing Filter:** Verhindert falsche Counter-Resets in Energie-Statistiken
- **Auto MQTT-Konfiguration:** Nutzt automatisch Home Assistant MQTT-Zugangsdaten
- **TRACE Log Level:** Ultra-detailliertes Debugging mit Modbus-Byte-Arrays
- **Umfassende Test-Suite:** 89% Code-Coverage
- **Performance:** ~2-5s Lesezyklus, konfigurierbares Poll-Intervall (30-60s empfohlen)
- **Plattformübergreifend:** Alle gängigen Architekturen (aarch64, amd64, armhf, armv7, i386)

## 🚀 Schnellstart

1. [![Repository hinzufügen](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Farboeh%2FhuABus)
2. "huABus | Huawei Solar Modbus to MQTT" installieren
3. **Minimale Konfiguration:**
   ```yaml
   modbus_host: 192.168.1.100
   modbus_auto_detect_slave_id: true
   log_level: INFO
   ```
4. Addon starten → **Einstellungen → Geräte & Dienste → MQTT → "Huawei Solar Inverter"**

## EVCC Integration (Kein Modbus Proxy!)

huABus stellt alle Daten in einem einzigen MQTT-Topic (`huawei-solar`) bereit, für direkte EVCC-Integration ohne Modbus-Proxy oder Konflikte.

**Voraussetzung:** MQTT im [evcc HA Addon](https://github.com/evcc-io/hassio-addon) aktivieren (evcc UI → Settings → MQTT).

**Netzzähler:**

```yaml
power:
  source: mqtt
  topic: huawei-solar
  jq: "(.meter_power_active * -1)"
```

**PV-Zähler:**

```yaml
power:
  source: mqtt
  topic: huawei-solar
  jq: ".power_input"
```

**Batterie (optional):**

```yaml
power:
  source: mqtt
  topic: huawei-solar
  jq: "(.battery_power * -1)"
soc:
  source: mqtt
  topic: huawei-solar
  jq: ".battery_soc"
capacity: 10
```

![EVCC Netzzähler Konfiguration](images/evcc_grid.png)  
![EVCC PV-Zähler Konfiguration](images/evcc_solar.png)  
![EVCC Batterie Konfiguration](images/evcc_battery.png)

## Vergleich: wlcrs/huawei_solar vs. dieses Addon

| Feature                 | wlcrs/huawei_solar<br>(Integration) | Dieses Addon<br>(MQTT-Bridge) |
| ----------------------- | ----------------------------------- | ----------------------------- |
| Batterie-Steuerung      | ✅                                  | ❌ (read-only)                |
| MQTT-nativ              | ❌                                  | ✅                            |
| Auto Slave ID-Erkennung | ❌                                  | ✅                            |
| Total Increasing Filter | ❌                                  | ✅                            |
| Externe Integrationen   | Begrenzt                            | ✅ (EVCC, Node-RED, Grafana)  |
| Error Tracking          | Basis                               | Advanced                      |

Beide teilen die gleiche Limitierung - nur **EINE Modbus-Verbindung**. Für gleichzeitige Nutzung wird ein Modbus Proxy benötigt.

## Screenshots

![Diagnostic Entities](images/diagnostics.png)  
![Sensor Overview](images/sensors.png)  
![MQTT Device Info](images/mqtt_info.png)

## Konfiguration

- **Modbus Host:** Inverter IP-Adresse (z.B. `192.168.1.100`)
- **Modbus Port:** Standard: `502`
- **Auto-Erkennung Slave ID:** Standard: `true` (probiert automatisch 1, 2, 100)
- **Slave ID (manuell):** Nur genutzt wenn Auto-Erkennung deaktiviert
- **MQTT Broker:** Standard: `core-mosquitto` (leer lassen für Auto-Config)
- **MQTT Port:** Standard: `1883`
- **MQTT Benutzername/Passwort:** Optional (leer lassen für HA MQTT-Zugangsdaten)
- **MQTT Topic:** Standard: `huawei-solar`
- **Log-Level:** `TRACE` | `DEBUG` | `INFO` (empfohlen) | `WARNING` | `ERROR`
- **Status Timeout:** Standard: `180s`
- **Abfrageintervall:** Standard: `30s` (empfohlen: 30-60s)

## Fehlerbehebung

**Mehrere Modbus-Verbindungen** (häufigster Fehler!): Alle anderen Huawei-Integrationen und Monitoring-Tools deaktivieren. Nur EINE Verbindung erlaubt.

**Alle Slave IDs schlagen fehl:** Modbus TCP im Wechselrichter aktivieren, IP-Adresse prüfen, Firewall checken.

**MQTT Fehler:** Broker auf `core-mosquitto` setzen, Credentials leer lassen.

**Logs:** Addon → Huawei Solar Modbus to MQTT → Log-Tab  
**Debug-Modus:** `log_level: DEBUG` setzen

## Aktuelle Updates

Siehe [CHANGELOG.md](huawei_solar_modbus_mqtt/CHANGELOG.md) für detaillierte Release-Notes.

- ✅ **v1.8.3:** Fix für intermittierenden Slave ID Auto-Detection Fehler (`Request cancelled outside library`)
- ✅ **v1.8.2:** CI-Migration zu `uv` (40% schnellere Builds)
- ✅ **v1.8.1:** Fix für Home Assistant 2025.1 Modbus Slave ID Handling
- ✅ **v1.8.0:** Automatische Slave ID-Erkennung

## Credits

**Basiert auf:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)  
**Verwendet Library:** [wlcrs/huawei-solar-lib](https://github.com/wlcrs/huawei-solar-lib)  
**Entwickelt von:** [arboeh](https://github.com/arboeh) | **Lizenz:** MIT
