# Huawei Solar Modbus to MQTT

> **⚠️ KRITISCH: Nur EINE Modbus-Verbindung erlaubt!**  
>
> Huawei-Wechselrichter haben eine **fundamentale Einschränkung**: Sie erlauben **nur EINE aktive Modbus TCP-Verbindung** zur selben Zeit. Dies ist eine **Hardware-Limitierung** und der häufigste Fehler bei der Smart-Home-Integration.
>
> ### Typische Fehlerszenarien:
>
> ❌ **Offizielle Huawei Solar Integration UND dieses Add-on** → Beide kämpfen um Verbindung  
> ❌ **Mehrere Home Assistant Instanzen** → Nur eine kann verbinden  
> ❌ **FusionSolar App + Modbus aktiv** → Cloud-Verbindung zeigt "Abnormal"  
> ❌ **Monitoring-Software + Home Assistant** → Intermittierende Timeouts  
>
> ### ✅ Vor Installation UNBEDINGT prüfen:
>
> 1. **Home Assistant Integrationen checken:**
>    - Einstellungen → Geräte & Dienste
>    - Suche nach "Huawei" oder "Solar"
>    - Entferne ALLE anderen Huawei-Integrationen (wlcrs/huawei_solar, HACS, etc.)
>
> 2. **Andere Software deaktivieren:**
>    - Monitoring-Tools (z.B. Solar-Analytics)
>    - Mobile Apps mit Modbus-Zugriff
>    - Weitere Home Assistant Instanzen
>
> 3. **FusionSolar Cloud:**
>    - Cloud funktioniert PARALLEL zu Modbus
>    - Aber: Cloud zeigt "Abnormale Kommunikation" → **ignorieren!**
>    - Cloud-Daten werden weiter übertragen
>
> 4. **Symptom bei mehreren Verbindungen:**
>    ```
>    ERROR - Timeout while waiting for connection
>    ERROR - No response received after 3 retries
>    ```
>    → Das liegt NICHT am Add-on, sondern an Konkurrenz um die Verbindung!
>
> **Regel:** NUR EINE Modbus-Verbindung zur selben Zeit = stabiles System ✅

Dieses Add-on liest Daten deines Huawei SUN2000 Wechselrichters per Modbus TCP aus und veröffentlicht sie über MQTT inklusive Home Assistant MQTT Discovery.

## Funktionen

- **Schnelle Modbus TCP Verbindung** zum Huawei SUN2000 Inverter
  - 58 Essential Registers (kritische Werte + erweiterte Daten)
  - Typische Cycle-Time: 2-5 Sekunden
  - Empfohlenes Poll-Interval: 30-60 Sekunden
- Veröffentlichung der Messwerte auf einem MQTT-Topic als JSON
- Automatische Erstellung von Home Assistant Entitäten via MQTT Discovery
- **Error Tracking:** Intelligente Fehler-Aggregation mit Downtime-Tracking
- Unterstützung für:
  - PV-Leistungen (PV1-4 mit Spannung und Strom)
  - Netzleistung (Import/Export, 3-phasig)
  - Batterie (SOC, Lade-/Entladeleistung, Tages- und Gesamtenergie)
  - 3-phasige Netzspannungen, Line-to-Line Spannungen
  - Smart Meter Integration (3-phasig)
  - Tages- und Gesamtenergieertrag
  - Inverter-Temperatur und Wirkungsgrad
- Online-/Offline-Status mit:
  - Binary Sensor „Huawei Solar Status"
  - Heartbeat/Timeout-Überwachung
  - MQTT Last Will (LWT) beim Broker
- Konfigurierbares Logging mit verschiedenen Log-Levels
- Performance-Monitoring und automatische Warnungen
- Health Check für Container-Überwachung

## Voraussetzungen

- Huawei SUN2000 Wechselrichter mit aktivierter Modbus TCP Schnittstelle
- Home Assistant mit konfigurierter MQTT-Integration
- MQTT Broker (z.B. Mosquitto), idealerweise über Home Assistant Supervisor bereitgestellt

## Konfiguration

Beispielkonfiguration im Add-on-UI:

```yaml
modbus_host: "192.168.1.100"
modbus_port: 502
slave_id: 1
mqtt_host: "core-mosquitto"
mqtt_port: 1883
mqtt_user: ""
mqtt_password: ""
mqtt_topic: "huawei-solar"
log_level: "INFO"
status_timeout: 180
poll_interval: 30
```

### Optionen

#### Modbus-Einstellungen

- **modbus_host** (erforderlich)  
  IP-Adresse deines Huawei Wechselrichters (z.B. `192.168.1.100`).

- **modbus_port** (Standard: `502`)  
  Modbus TCP Port.

- **slave_id** (Standard: `1`, Range: 0-247)  
  Modbus Slave ID des Inverters. In vielen Installationen ist dies `1`, in manchen `16` oder `0`.  
  **Tipp:** Bei Connection Timeouts verschiedene Werte testen (`0`, `1`, `16`).

#### MQTT-Einstellungen

- **mqtt_host** (Standard: `core-mosquitto`)  
  MQTT Broker Hostname. Leer lassen oder `core-mosquitto` für den HA Mosquitto Add-on.

- **mqtt_port** (Standard: `1883`)  
  MQTT Broker Port.

- **mqtt_user** (optional)  
  MQTT Benutzername. Leer lassen, um Credentials aus Home Assistant MQTT Service zu verwenden.

- **mqtt_password** (optional)  
  MQTT Passwort. Leer lassen, um Credentials aus Home Assistant MQTT Service zu verwenden.

- **mqtt_topic** (Standard: `huawei-solar`)  
  Basis-Topic, unter dem die Daten veröffentlicht werden.

#### Erweiterte Einstellungen

- **log_level** (Standard: `INFO`)  
  Logging-Detailgrad:

  - `DEBUG`: Sehr detailliert - zeigt Performance-Metriken, einzelne Register-Reads, Zeitmessungen für jeden Schritt, Error-Details
  - `INFO`: Normal - zeigt wichtige Ereignisse und aktuelle Datenpunkte (Solar/Grid/Battery Power), Error-Recovery
  - `WARNING`: Nur Warnungen und Fehler
  - `ERROR`: Nur Fehler

- **status_timeout** (Standard: `180`, Range: 30-600)  
  Zeit in Sekunden, nach der der Status auf `offline` gesetzt wird, wenn keine erfolgreiche Abfrage mehr erfolgt ist.

- **poll_interval** (Standard: `30`, Range: 10-300)  
  Abfrageintervall in Sekunden zwischen zwei Modbus-Reads.  
  **Empfehlung:** 30-60 Sekunden für optimale Balance zwischen Aktualität und Netzwerklast.

## MQTT Topics

- **Messdaten (JSON):**  
  `huawei-solar` (oder dein konfiguriertes Topic)  
  Enthält alle Sensordaten als JSON-Objekt mit `last_update` Timestamp.

- **Status (online/offline):**  
  `huawei-solar/status`  
  Wird genutzt für:
  - Binary Sensor „Huawei Solar Status"
  - `availability_topic` aller Sensoren
  - MQTT Last Will Testament (automatisch `offline` bei Verbindungsabbruch)

## Entitäten in Home Assistant

Nach dem Start des Add-ons werden automatisch MQTT Discovery Konfigurationen publiziert. Du findest die Entitäten dann unter:

**Einstellungen → Geräte & Dienste → MQTT → Geräte → „Huawei Solar Inverter"**

### Hauptentitäten (standardmäßig aktiviert)

#### Leistung

- `sensor.solar_power` - Aktuelle PV-Gesamtleistung
- `sensor.input_power` - DC-Eingangsleistung
- `sensor.grid_power` - Netzleistung (positiv = Bezug, negativ = Einspeisung)
- `sensor.battery_power` - Batterieleistung (positiv = Laden, negativ = Entladen)
- `sensor.pv1_power` - PV-String 1 Leistung

#### Energie

- `sensor.solar_daily_yield` - Tagesertrag
- `sensor.solar_total_yield` - Gesamtertrag
- `sensor.grid_energy_exported` - Exportierte Energie (Einspeisung)
- `sensor.grid_energy_imported` - Importierte Energie (Bezug)
- `sensor.battery_charge_today` - Batterieladung heute
- `sensor.battery_discharge_today` - Batterieentladung heute

#### Batterie

- `sensor.battery_soc` - Batterieladezustand (%)
- `sensor.battery_bus_voltage` - Batterie Bus-Spannung
- `sensor.battery_bus_current` - Batterie Bus-Strom

#### Netz

- `sensor.grid_voltage_phase_a/b/c` - 3-phasige Netzspannungen
- `sensor.grid_line_voltage_ab/bc/ca` - Line-to-Line Spannungen
- `sensor.grid_frequency` - Netzfrequenz
- `sensor.grid_current_phase_a/b/c` - 3-phasige Ströme

#### Smart Meter (falls vorhanden)

- `sensor.meter_power_phase_a/b/c` - Phasen-Leistung
- `sensor.meter_current_phase_a/b/c` - Phasen-Ströme
- `sensor.meter_reactive_power` - Blindleistung

#### Inverter

- `sensor.inverter_temperature` - Wechselrichter-Temperatur
- `sensor.inverter_efficiency` - Wirkungsgrad
- `sensor.model_name` - Inverter-Modell
- `sensor.serial_number` - Seriennummer

#### Status

- `binary_sensor.huawei_solar_status` - Online/Offline Status
- `sensor.inverter_status` - Textstatus (z.B. "Standby", "Grid-Connected")
- `sensor.battery_status` - Batteriestatus

### Diagnostik-Entitäten (standardmäßig deaktiviert)

Diese Entitäten können in Home Assistant manuell aktiviert werden:

- PV2/PV3/PV4 Leistung, Spannung, Strom
- Detaillierte Phasen-Ströme und -Leistungen
- Batterie Gesamtstatistiken (Total Charge/Discharge)
- Inverter State-Details

## Performance & Optimierung

### Version 1.4.x - Aktuelle Optimierungen

**58 Essential Registers:**

- Erweiterte Register-Set mit allen wichtigen Werten
- Typische Cycle-Time: 2-5 Sekunden
- Empfohlenes Poll-Interval: **30-60 Sekunden**

**Error Tracking (NEU in 1.4.0):**

- Intelligente Fehler-Aggregation
- Downtime-Tracking mit Recovery-Logging
- Format: `Connection restored after {downtime}s ({attempts} failed attempts, {types} error types)`

**Vorteile:**

- Minimale Netzwerklast
- Schnelle Updates der wichtigsten Werte
- Zuverlässige Verbindung auch bei langsamen Netzwerken
- Automatische Fehler-Recovery mit Statistiken

### Performance-Monitoring

Das Add-on überwacht automatisch die Cycle-Performance:

```
INFO - Essential read: 2.1s (58/58)
INFO - Published - Solar: 4500W | Grid: -200W | Battery: 800W (85.0%)
DEBUG - Cycle: 2.3s (Modbus: 2.1s, Transform: 0.005s, MQTT: 0.194s)
```

**Automatische Warnungen** bei langsamen Zyklen:

```
WARNING - Cycle 52.1s > 80% poll_interval (30s)
```

**Error Recovery Logging:**

```
INFO - Connection restored after 47s (3 failed attempts, 2 error types)
```

### Empfohlene Einstellungen

| Szenario               | Poll-Interval | Status-Timeout |
| ---------------------- | ------------- | -------------- |
| **Standard**           | 30s           | 180s           |
| **Schnell**            | 20s           | 120s           |
| **Langsames Netzwerk** | 60s           | 300s           |
| **Debugging**          | 10s           | 60s            |

## Logging & Fehleranalyse

### Log-Levels

**INFO (Standard)** - Übersichtlich für den normalen Betrieb:

```
2026-01-09T08:00:00+0100 - huawei.main - INFO - 🚀 Starting Huawei Solar → MQTT
2026-01-09T08:00:01+0100 - huawei.main - INFO - 🔌 Connected (Slave ID: 1)
2026-01-09T08:00:02+0100 - huawei.main - INFO - Essential read: 2.1s (58/58)
2026-01-09T08:00:02+0100 - huawei.main - INFO - Published - Solar: 4500W | Grid: -200W | Battery: 800W (85.0%)
```

**DEBUG** - Detailliert mit Performance-Metriken:

```
2026-01-09T08:00:02+0100 - huawei.main - DEBUG - Cycle #1
2026-01-09T08:00:02+0100 - huawei.main - DEBUG - Reading 58 essential registers
2026-01-09T08:00:03+0100 - huawei.main - INFO - Essential read: 2.1s (58/58)
2026-01-09T08:00:03+0100 - huawei.transform - DEBUG - Transforming 58 registers
2026-01-09T08:00:03+0100 - huawei.main - DEBUG - Cycle: 2.3s (Modbus: 2.1s, Transform: 0.005s, MQTT: 0.194s)
```

### Add-on Logs ansehen

**Einstellungen → Add-ons → Huawei Solar Modbus to MQTT → „Log"**

### Typische Fehler & Lösungen

#### Connection Timeout Fehler (NEU)

**Symptom:**

```
ERROR - Timeout while waiting for connection. Reconnecting
TimeoutError
```

**Lösungen:**

1. **Slave ID ändern** - Die häufigste Lösung!
   - Versuche: `0`, `1`, `16`
   - Manche Dongle nutzen andere IDs

2. **Poll Interval erhöhen**
   - Von `30` auf `60` oder höher
   - Gibt mehr Zeit für langsame Verbindungen

3. **Netzwerk prüfen**
   - Ping zum Inverter: `ping <IP>`
   - Latenz und Packet Loss checken

4. **FusionSolar Cloud prüfen**
   - Cloud-Verbindung kann Modbus blockieren
   - Temporär deaktivieren zum Testen

5. **DEBUG-Log aktivieren**
   - Zeigt genau, welches Register beim Timeout hängt

#### Modbus-Verbindungsfehler

**Symptom:**

```
ERROR - Connection failed: [Errno 111] Connection refused
```

**Lösungen:**

- IP-Adresse und Port prüfen
- Modbus TCP im Inverter-Webinterface aktivieren
- Verschiedene Slave IDs testen (0, 1, 16)
- Firewall-Regeln prüfen
- Bei `log_level: DEBUG` werden Details angezeigt

#### MQTT-Verbindungsfehler

**Symptom:**

```
ERROR - MQTT publish failed: [Errno 111] Connection refused
```

**Lösungen:**

- MQTT Broker in Home Assistant prüfen (Einstellungen → Add-ons → Mosquitto)
- Zugangsdaten kontrollieren
- `mqtt_host` auf `core-mosquitto` setzen
- Im DEBUG-Modus werden Verbindungsdetails geloggt

#### Performance-Probleme

**Symptom:**

```
WARNING - Cycle 52.1s > 80% poll_interval (30s)
```

**Lösungen:**

- `poll_interval` erhöhen (z.B. von 30s auf 60s oder 120s)
- Netzwerkverbindung zum Inverter prüfen
- Im DEBUG-Log Zeitmessungen analysieren
- Bei sehr langsamen Netzwerken `poll_interval: 120s` verwenden

#### Critical Key Warnings

**Symptom:**

```
WARNING - Critical 'meter_power_active' missing, using 0
```

**Ursache:** Dein Inverter hat keinen Power Meter oder andere Hardware-Konfiguration

**Lösung:** Warnung ist normal, Add-on setzt automatisch Fallback-Werte (0)

## Tipps & Best Practices

### Erste Inbetriebnahme

1. Setze `log_level: DEBUG`, um alle Details zu sehen
2. Starte das Add-on und prüfe die Logs
3. Warte auf „Connected (Slave ID: X)"
4. Prüfe die ersten Datenpunkte im Log
5. Gehe zu MQTT Integration und aktiviere gewünschte Entitäten

### Bei Connection Timeout Problemen

1. **Slave ID variieren:**
   ```yaml
   slave_id: 0  # Versuche 0, 1, 16
   ```

2. **Poll Interval erhöhen:**
   ```yaml
   poll_interval: 60  # Statt 30
   ```

3. **DEBUG aktivieren:**
   ```yaml
   log_level: DEBUG
   ```

4. **Netzwerk testen:**
   - SSH/Terminal: `ping <INVERTER_IP>`
   - Latenz unter 50ms = gut

### Normalbetrieb

- Nutze `log_level: INFO` für übersichtliche Logs
- `poll_interval: 30-60s` für optimale Performance
- Überwache gelegentlich die Cycle-Times im Log
- Error Tracker zeigt automatisch Recovery-Statistiken

### Performance optimieren

- Achte auf WARNING-Meldungen im Log
- Bei Cycle-Times > 80% poll_interval → `poll_interval` erhöhen
- DEBUG-Level zeigt genaue Zeitmessungen für jeden Schritt
- Error Tracker gibt Einblick in Verbindungsstabilität

### Fehlersuche

- DEBUG-Level zeigt genau, welche Register gelesen werden
- Prüfe `binary_sensor.huawei_solar_status` für Verbindungsstatus
- Logs regelmäßig auf Warnings/Errors prüfen
- Health Check im Home Assistant Add-on Status beachten
- Error Recovery Meldungen zeigen Downtime und Fehlertypen

### Multi-Inverter Setup

Das Add-on ist aktuell auf einen Inverter ausgelegt. Für mehrere Inverter:

- Installiere das Add-on mehrfach (unterschiedliche Namen)
- Verwende unterschiedliche `mqtt_topic` Werte
- Konfiguriere verschiedene `modbus_host` Adressen

## Health Check

Das Add-on verfügt über einen integrierten Health Check:

- Prüft alle 60 Sekunden, ob der Python-Prozess läuft
- Status sichtbar in: **Einstellungen → Add-ons → Huawei Solar → Status**
- Bei `unhealthy` → Add-on neu starten

## Changelog & Updates

Aktuelle Version: **1.4.2**

### Wichtigste Änderungen

- **1.4.2:** Repository-Wartung (Git-Konfiguration, Line-Endings), Dependencies korrigiert, GitHub Issue Templates
- **1.4.1:** Enhanced startup logging mit Emoji-Icons, visuelle Trennlinien
- **1.4.0:** Error Tracker mit Downtime-Tracking, optimierte Logging-Architektur, Poll-Interval Standard 30s
- **1.3.5:** Template variable warnings eliminated, dependency cleanup

Vollständiger Changelog: [CHANGELOG.md](https://github.com/arboeh/homeassistant-huawei-solar-addon/blob/main/huawei-solar-modbus-mqtt/CHANGELOG.md)

## Support & Weiterentwicklung

- **GitHub Repository:** [arboeh/homeassistant-huawei-solar-addon](https://github.com/arboeh/homeassistant-huawei-solar-addon)
- **Issues & Feature Requests:** [GitHub Issue Templates](https://github.com/arboeh/homeassistant-huawei-solar-addon/issues/new/choose)
- **Basierend auf:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)