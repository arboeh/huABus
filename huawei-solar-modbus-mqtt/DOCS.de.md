# huABus | Huawei Solar Modbus to MQTT

### Huawei Solar Modbus → Home Assistant via MQTT + Auto Discovery

Dieses Add-on liest Daten deines Huawei SUN2000 Wechselrichters per Modbus TCP aus und veröffentlicht sie über MQTT inklusive Home Assistant MQTT Discovery.

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
> 2. **Andere Software deaktivieren:**
>    - Monitoring-Tools (z.B. Solar-Analytics)
>    - Mobile Apps mit Modbus-Zugriff
>    - Weitere Home Assistant Instanzen
> 3. **FusionSolar Cloud:**
>    - Cloud funktioniert PARALLEL zu Modbus
>    - Aber: Cloud zeigt "Abnormale Kommunikation" → **ignorieren!**
>    - Cloud-Daten werden weiter übertragen
> 4. **Symptom bei mehreren Verbindungen:**
>    ```
>    ERROR - Timeout while waiting for connection
>    ERROR - No response received after 3 retries
>    ```
>    → Das liegt NICHT am Add-on, sondern an Konkurrenz um die Verbindung!
>
> **Regel:** NUR EINE Modbus-Verbindung zur selben Zeit = stabiles System ✅

## 🚀 Schnellstart (5 Minuten)

### 1. Vor der Installation (KRITISCH!)

✅ **Konkurrierende Modbus-Verbindungen entfernen:**

- Einstellungen → Geräte & Dienste → Suche "Huawei" → ALLE Integrationen entfernen
- Monitoring-Software, mobile Apps mit Modbus-Zugriff deaktivieren
- Nur EINE Modbus-Verbindung erlaubt!

✅ **Verbindungsdaten vorbereiten:**

- IP-Adresse des Inverters (z.B. `192.168.1.100`)
- Prüfen ob Inverter erreichbar: `ping 192.168.1.100`

### 2. Installation

1. Einstellungen → Add-ons → Add-on Store
2. Klick ⋮ (oben rechts) → Repositories
3. Hinzufügen: `https://github.com/arboeh/huABus`
4. Installiere "Huawei Solar Modbus to MQTT"

### 3. Konfiguration

**Minimalkonfiguration (erforderlich):**

```yaml
modbus_host: "192.168.1.100" # Deine Inverter-IP
slave_id: 1 # Starte mit 1
log_level: "INFO" # Guter Standard
```

**💡 Connection Timeout?** Probiere verschiedene Slave IDs:

```yaml
slave_id: 0 # oder 1, oder 16
```

### 4. Erster Start & Überprüfung

1. **Add-on starten** → Logs sofort prüfen
2. **Erfolgs-Indikatoren:**
   ```
   INFO - 🚀 Huawei Solar → MQTT starting
   INFO - 🔌 Connected (Slave ID: 1)
   INFO - Essential read: 2.1s (58/58)
   INFO - 📊 Published - PV: 4500W | ...
   ```
3. **Sensoren aktivieren:**
   - Einstellungen → Geräte & Dienste → MQTT
   - Finde "Huawei Solar Inverter"
   - Aktiviere gewünschte Sensoren

### 5. Häufige Erstinstallations-Probleme

| Symptom                     | Schnelle Lösung                                     |
| --------------------------- | --------------------------------------------------- |
| `ERROR - Timeout`           | Versuche `slave_id: 0`, dann `16`                   |
| `Connection refused`        | IP prüfen, Modbus TCP im Inverter aktivieren        |
| `Keine Sensoren erscheinen` | 30s warten, MQTT Integration neu laden              |
| Zu viele Sensoren!          | Normal! Ungenutzte in MQTT Integration deaktivieren |

**Immer noch Probleme?** Siehe vollständiges [Troubleshooting](#logging--fehleranalyse) unten.

## Funktionen

- **Schnelle Modbus TCP Verbindung** zum Huawei SUN2000 Inverter
  - 58 Essential Registers (kritische Werte + erweiterte Daten)
  - Typische Cycle-Time: 2-5 Sekunden
  - Empfohlenes Poll-Interval: 30-60 Sekunden
- **total_increasing Filter (NEU in 1.6.0):** Verhindert falsche Counter-Resets in Home Assistant
  - Filtert negative Werte und Drops > 5% (konfigurierbar)
  - Schützt Energie-Statistiken vor Modbus-Lesefehlern
  - Automatischer Reset bei Verbindungsfehlern
  - Filter-Status sichtbar in Logs mit 20-Cycle-Zusammenfassungen
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
  - `DEBUG`: Sehr detailliert - zeigt Performance-Metriken, einzelne Register-Reads, Zeitmessungen für jeden Schritt, Error-Details, **Filter-Details bei jedem Event**
  - `INFO`: Normal - zeigt wichtige Ereignisse und aktuelle Datenpunkte (Solar/Grid/Battery Power), Error-Recovery, **Filter-Zusammenfassungen alle 20 Cycles**
  - `WARNING`: Nur Warnungen und Fehler
  - `ERROR`: Nur Fehler

- **status_timeout** (Standard: `180`, Range: 30-600)  
  Zeit in Sekunden, nach der der Status auf `offline` gesetzt wird, wenn keine erfolgreiche Abfrage mehr erfolgt ist.

- **poll_interval** (Standard: `30`, Range: 10-300)  
  Abfrageintervall in Sekunden zwischen zwei Modbus-Reads.  
  **Empfehlung:** 30-60 Sekunden für optimale Balance zwischen Aktualität und Netzwerklast.

#### Filter-Einstellungen (ENV-Variablen, optional)

- **HUAWEI_FILTER_TOLERANCE** (Standard: `0.05`)  
  Toleranz für total_increasing Filter in Prozent (0.05 = 5%).  
  Werte die um mehr als diesen Prozentsatz fallen, werden als Lesefehler gefiltert.  
  **Empfehlung:** 5% (Standard) ist optimal für die meisten Installationen.  
  **Beispiel:** Bei 0.10 werden erst Drops > 10% gefiltert (weniger streng).

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
- `sensor.solar_total_yield` - Gesamtertrag _(geschützt durch Filter)_
- `sensor.grid_energy_exported` - Exportierte Energie (Einspeisung) _(geschützt durch Filter)_
- `sensor.grid_energy_imported` - Importierte Energie (Bezug) _(geschützt durch Filter)_
- `sensor.battery_charge_today` - Batterieladung heute
- `sensor.battery_discharge_today` - Batterieentladung heute
- `sensor.battery_total_charge` - Batterie Gesamtladung _(geschützt durch Filter)_
- `sensor.battery_total_discharge` - Batterie Gesamtentladung _(geschützt durch Filter)_

> **ℹ️ Filter-Schutz:** Sensoren mit _(geschützt durch Filter)_ werden automatisch vor falschen Counter-Resets geschützt. Bei Modbus-Lesefehlern wird der letzte gültige Wert verwendet statt 0.

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
- Inverter State-Details

## Performance & Optimierung

### Version 1.6.x - Aktuelle Features

**58 Essential Registers:**

- Erweiterte Register-Set mit allen wichtigen Werten
- Typische Cycle-Time: 2-5 Sekunden
- Empfohlenes Poll-Interval: **30-60 Sekunden**

**total_increasing Filter (NEU in 1.6.0):**

- Automatischer Schutz vor falschen Counter-Resets
- Filtert Drops > 5% als wahrscheinliche Lesefehler
- Ersetzt ungültige Werte durch letzten gültigen Wert
- Sichtbar in Logs mit 20-Cycle-Zusammenfassungen

**Error Tracking:**

- Intelligente Fehler-Aggregation
- Downtime-Tracking mit Recovery-Logging
- Format: `Connection restored after {downtime}s ({attempts} failed attempts, {types} error types)`

**Vorteile:**

- Minimale Netzwerklast
- Schnelle Updates der wichtigsten Werte
- Zuverlässige Verbindung auch bei langsamen Netzwerken
- Automatische Fehler-Recovery mit Statistiken
- Geschützte Energie-Statistiken (keine falschen Resets mehr!)

### Performance-Monitoring

Das Add-on überwacht automatisch die Cycle-Performance:

```
INFO - Essential read: 2.1s (58/58)
INFO - 📊 Published - PV: 4500W | AC Out: 4200W | Grid: -200W | Battery: 800W
DEBUG - Cycle: 2.3s (Modbus: 2.1s, Transform: 0.005s, MQTT: 0.194s)
```

**Mit Filter-Aktivität (wenn Werte gefiltert wurden):**

```
INFO - 📊 Published - PV: 788W | AC Out: 211W | Grid: 11W | Battery: 569W 🔍[2 filtered]
DEBUG - 🔍 Filter details: {'energy_yield_accumulated': 1, 'battery_charge_total': 1}
```

**Filter-Zusammenfassung alle 20 Cycles (INFO-Level):**

```
INFO - 🔍 Filter summary (last 20 cycles): 0 values filtered - all data valid ✓
```

oder bei Filterungen:

```
INFO - 🔍 Filter summary (last 20 cycles): 3 values filtered | Details: {'energy_yield_accumulated': 2, 'battery_charge_total': 1}
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
2026-01-25T12:51:23+0100 - huawei.main - INFO - 🚀 Huawei Solar → MQTT starting
2026-01-25T12:51:25+0100 - huawei.main - INFO - 🔌 Connected (Slave ID: 1)
2026-01-25T12:51:31+0100 - huawei.main - INFO - Essential read: 6.1s (57/57)
2026-01-25T12:51:31+0100 - huawei.filter - INFO - TotalIncreasingFilter initialized with 5% tolerance
2026-01-25T12:51:31+0100 - huawei.main - INFO - 📊 Published - PV: 744W | AC Out: 218W | Grid: -29W | Battery: 520W
2026-01-25T13:11:31+0100 - huawei.main - INFO - 🔍 Filter summary (last 20 cycles): 0 values filtered - all data valid ✓
```

**DEBUG** - Detailliert mit Performance-Metriken:

```
2026-01-25T12:51:23+0100 - huawei.main - DEBUG - Cycle #1
2026-01-25T12:51:23+0100 - huawei.main - DEBUG - Reading 58 essential registers
2026-01-25T12:51:31+0100 - huawei.main - INFO - Essential read: 6.1s (57/57)
2026-01-25T12:51:31+0100 - huawei.transform - DEBUG - Transforming 58 registers
2026-01-25T12:51:31+0100 - huawei.main - DEBUG - Cycle: 6.2s (Modbus: 6.1s, Transform: 0.008s, MQTT: 0.092s)
```

### Add-on Logs ansehen

**Einstellungen → Add-ons → Huawei Solar Modbus to MQTT → „Log"**

### Typische Fehler & Lösungen

#### Connection Timeout Fehler

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

#### Filter-Aktivität (NEU in 1.6.0)

**Symptom:**

```
INFO - 📊 Published - PV: 788W | AC Out: 211W | Grid: 11W | Battery: 569W 🔍[3 filtered]
```

**Bedeutung:** Das Add-on hat ungültige Counter-Werte erkannt und gefiltert (wahrscheinlich Modbus-Lesefehler)

**Normales Verhalten:** Gelegentliches Filtern (1-2 pro Stunde) ist zu erwarten und schützt deine Energie-Statistiken

**Untersuchung notwendig:** Häufiges Filtern (jeden Cycle) deutet auf Verbindungsprobleme hin

- DEBUG-Modus aktivieren um zu sehen welche Sensoren gefiltert werden
- Modbus-Verbindungsstabilität prüfen
- Erwäge `poll_interval` zu erhöhen

**Filter-Zusammenfassung verstehen:**

```
🔍 Filter summary (last 20 cycles): 0 values filtered - all data valid ✓
```

→ Perfekt! Keine Probleme in den letzten 20 Cycles

```
🔍 Filter summary (last 20 cycles): 3 values filtered | Details: {'energy_yield_accumulated': 2, 'battery_charge_total': 1}
```

→ 3 Werte in 20 Cycles gefiltert - akzeptabel, zeigt gelegentliche Lesefehler

#### Critical Key Warnings

**Symptom:**

```
WARNING - Critical 'meter_power_active' missing, using 0
```

**Ursache:** Dein Inverter hat keinen Power Meter oder andere Hardware-Konfiguration

**Lösung:** Warnung ist normal, Add-on setzt automatisch Fallback-Werte (0)

## Tipps & Best Practices

### Erste Inbetriebnahme

1. Setze `log_level: INFO`, um wichtige Events zu sehen
2. Starte das Add-on und prüfe die Logs
3. Warte auf „Connected (Slave ID: X)" und „TotalIncreasingFilter initialized"
4. Prüfe die ersten Datenpunkte im Log
5. Beobachte Filter-Summary nach 20 Cycles
6. Gehe zu MQTT Integration und aktiviere gewünschte Entitäten

### Bei Connection Timeout Problemen

1. **Slave ID variieren:**

   ```yaml
   slave_id: 0 # Versuche 0, 1, 16
   ```

2. **Poll Interval erhöhen:**

   ```yaml
   poll_interval: 60 # Statt 30
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
- Beobachte Filter-Summaries alle 20 Cycles
- Error Tracker zeigt automatisch Recovery-Statistiken

### Performance optimieren

- Achte auf WARNING-Meldungen im Log
- Bei Cycle-Times > 80% poll_interval → `poll_interval` erhöhen
- DEBUG-Level zeigt genaue Zeitmessungen für jeden Schritt
- Error Tracker gibt Einblick in Verbindungsstabilität
- Filter-Aktivität zeigt Datenqualität

### Fehlersuche

- DEBUG-Level zeigt genau, welche Register gelesen werden
- Prüfe `binary_sensor.huawei_solar_status` für Verbindungsstatus
- Logs regelmäßig auf Warnings/Errors prüfen
- Filter-Summaries zeigen Datenqualität
- Health Check im Home Assistant Add-on Status beachten
- Error Recovery Meldungen zeigen Downtime und Fehlertypen

### Filter-Monitoring (NEU in 1.6.0)

- **INFO-Level:** Filter-Summary alle 20 Cycles zeigt Langzeit-Trend
- **DEBUG-Level:** Detaillierte Filter-Info bei jedem Event
- **Inline-Indikator:** `🔍[X filtered]` zeigt sofort wenn gefiltert wurde
- **Gelegentliches Filtern:** 1-2 pro Stunde ist normal und akzeptabel
- **Häufiges Filtern:** Deutet auf Modbus-Verbindungsprobleme hin
- **Keine Filterung:** `0 values filtered - all data valid ✓` ist optimal

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

Vollständiger Changelog: [CHANGELOG.md](https://github.com/arboeh/huABus/blob/main/huawei-solar-modbus-mqtt/CHANGELOG.md)

## Support & Weiterentwicklung

- **GitHub Repository:** [arboeh/huABus](https://github.com/arboeh/huABus)
- **Issues & Feature Requests:** [GitHub Issue Templates](https://github.com/arboeh/huABus/issues/new/choose)
- **Basierend auf:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)
