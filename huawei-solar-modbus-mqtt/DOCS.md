# Huawei Solar Modbus to MQTT

Dieses Add-on liest Daten deines Huawei SUN2000 Wechselrichters per Modbus TCP aus und veröffentlicht sie über MQTT inklusive Home Assistant MQTT Discovery. Dadurch tauchen die meisten Entitäten automatisch im MQTT-Integration-Panel von Home Assistant auf.

## Funktionen

- **Schnelle Modbus TCP Verbindung** zum Huawei SUN2000 Inverter
  - Optimierte Essential Registers (nur 21 kritische Werte)
  - Typische Cycle-Time: 1-3 Sekunden
  - Empfohlenes Poll-Interval: 30-60 Sekunden
- Veröffentlichung der Messwerte auf einem MQTT-Topic als JSON
- Automatische Erstellung von Home Assistant Entitäten via MQTT Discovery
- Unterstützung für:
  - PV-Leistungen (PV1, optional PV2/PV3/PV4)
  - Netzleistung (Import/Export)
  - Batterie (SOC, Lade-/Entladeleistung, Tages- und Gesamtenergie)
  - 3-phasige Netzspannungen
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

    modbus_host: "192.168.1.100"
    modbus_port: 502
    modbus_device_id: 1
    mqtt_host: "core-mosquitto"
    mqtt_port: 1883
    mqtt_user: ""
    mqtt_password: ""
    mqtt_topic: "huawei-solar"
    log_level: "INFO"
    status_timeout: 180
    poll_interval: 30


### Optionen

#### Modbus-Einstellungen

- **modbus_host** (erforderlich)  
  IP-Adresse deines Huawei Wechselrichters (z.B. `192.168.1.100`).

- **modbus_port** (Standard: `502`)  
  Modbus TCP Port.

- **modbus_device_id** (Standard: `1`, Range: 1-247)  
  Modbus Slave ID des Inverters. In vielen Installationen ist dies `1`, in manchen `16` oder `0`.

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
  - `DEBUG`: Sehr detailliert - zeigt Performance-Metriken, einzelne Register-Reads, Zeitmessungen für jeden Schritt
  - `INFO`: Normal - zeigt wichtige Ereignisse und aktuelle Datenpunkte (Solar/Grid/Battery Power)
  - `WARNING`: Nur Warnungen und Fehler
  - `ERROR`: Nur Fehler

- **status_timeout** (Standard: `180`, Range: 30-600)  
  Zeit in Sekunden, nach der der Status auf `offline` gesetzt wird, wenn keine erfolgreiche Abfrage mehr erfolgt ist.

- **poll_interval** (Standard: `60`, Range: 10-300)  
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

#### Netz
- `sensor.grid_voltage_phase_a/b/c` - 3-phasige Netzspannungen
- `sensor.grid_frequency` - Netzfrequenz

#### Inverter
- `sensor.inverter_temperature` - Wechselrichter-Temperatur
- `sensor.inverter_efficiency` - Wirkungsgrad

#### Status
- `binary_sensor.huawei_solar_status` - Online/Offline Status
- `sensor.inverter_status` - Textstatus (z.B. "Standby", "Grid-Connected")
- `sensor.battery_status` - Batteriestatus

### Diagnostik-Entitäten (standardmäßig deaktiviert)

Diese Entitäten können in Home Assistant manuell aktiviert werden:

- PV2/PV3/PV4 Leistung, Spannung, Strom
- Detaillierte Phasen-Ströme und -Leistungen
- Line-to-Line Spannungen
- Batterie Bus-Spannung und -Strom
- Inverter State-Details
- Gesamtstatistiken (Total Charge/Discharge)

## Performance & Optimierung

### Version 1.1.2 - Aktuelle Optimierungen

**Essential Registers Ansatz:**
- Nur 21 kritische Register werden gelesen (statt 500+)
- Typische Cycle-Time: 1-3 Sekunden
- Empfohlenes Poll-Interval: **30-60 Sekunden**

**Vorteile:**
- Minimale Netzwerklast
- Schnelle Updates der wichtigsten Werte
- Zuverlässige Verbindung auch bei langsamen Netzwerken

### Performance-Monitoring

Das Add-on überwacht automatisch die Cycle-Performance:

    INFO - Essential read: 1.8s (21/21)
    INFO - Published - Solar: 4500W | Grid: -200W | Battery: 800W (85.0%)
    DEBUG - Cycle: 1.9s (Modbus: 1.8s, Transform: 0.003s, MQTT: 0.124s)


**Automatische Warnungen** bei langsamen Zyklen:

    WARNING - Cycle 52.1s > 80% poll_interval (60s)


### Empfohlene Einstellungen

| Szenario | Poll-Interval | Status-Timeout |
|----------|---------------|----------------|
| **Standard** | 60s | 180s |
| **Schnell** | 30s | 120s |
| **Langsames Netzwerk** | 120s | 300s |
| **Debugging** | 10s | 60s |

## Logging & Fehleranalyse

### Log-Levels

**INFO (Standard)** - Übersichtlich für den normalen Betrieb:

    2025-12-08T19:00:00+0100 - huawei.main - INFO - Logging initialized: INFO
    2025-12-08T19:00:00+0100 - huawei.main - INFO - Huawei Solar → MQTT starting
    2025-12-08T19:00:01+0100 - huawei.main - INFO - Connected (Slave ID: 1)
    2025-12-08T19:00:02+0100 - huawei.main - INFO - Essential read: 1.8s (21/21)
    2025-12-08T19:00:02+0100 - huawei.main - INFO - Published - Solar: 4500W | Grid: -200W | Battery: 800W (85.0%)


**DEBUG** - Detailliert mit Performance-Metriken:

    2025-12-08T19:00:02+0100 - huawei.main - DEBUG - Cycle #1
    2025-12-08T19:00:02+0100 - huawei.main - DEBUG - Starting cycle
    2025-12-08T19:00:02+0100 - huawei.main - DEBUG - Reading 21 essential registers
    2025-12-08T19:00:03+0100 - huawei.main - INFO - Essential read: 1.8s (21/21)
    2025-12-08T19:00:03+0100 - huawei.transform - DEBUG - Transforming 21 registers
    2025-12-08T19:00:03+0100 - huawei.transform - DEBUG - Transform complete: 18 values (0.003s)
    2025-12-08T19:00:03+0100 - huawei.mqtt - DEBUG - Publishing: Solar=4500W, Grid=-200W, Battery=800W
    2025-12-08T19:00:03+0100 - huawei.mqtt - DEBUG - Data published: 18 keys
    2025-12-08T19:00:03+0100 - huawei.main - DEBUG - Cycle: 1.9s (Modbus: 1.8s, Transform: 0.003s, MQTT: 0.124s)


### Add-on Logs ansehen

**Einstellungen → Add-ons → Huawei Solar Modbus to MQTT → „Log"**

### Typische Fehler & Lösungen

#### Modbus-Verbindungsfehler

**Symptom:**

    ERROR - Connection failed: [Errno 111] Connection refused


**Lösungen:**
- IP-Adresse und Port prüfen
- Modbus TCP im Inverter-Webinterface aktivieren
- Verschiedene Slave IDs testen (0, 1, 16, 100)
- Firewall-Regeln prüfen
- Bei `log_level: DEBUG` werden Details angezeigt

#### MQTT-Verbindungsfehler

**Symptom:**

    ERROR - MQTT publish failed: [Errno 111] Connection refused


**Lösungen:**
- MQTT Broker in Home Assistant prüfen (Einstellungen → Add-ons → Mosquitto)
- Zugangsdaten kontrollieren
- `mqtt_host` auf `core-mosquitto` setzen
- Im DEBUG-Modus werden Verbindungsdetails geloggt

#### Performance-Probleme

**Symptom:**

    WARNING - Cycle 52.1s > 80% poll_interval (60s)


**Lösungen:**
- `poll_interval` erhöhen (z.B. von 60s auf 120s)
- Netzwerkverbindung zum Inverter prüfen
- Im DEBUG-Log Zeitmessungen analysieren
- Bei sehr langsamen Netzwerken `poll_interval: 120s` verwenden

#### Critical Key Warnings

**Symptom:**

    WARNING - Critical 'meter_power_active' missing, using 0


**Ursache:** Dein Inverter hat keinen Power Meter oder andere Hardware-Konfiguration

**Lösung:** Warnung ist normal, Add-on setzt automatisch Fallback-Werte (0)

## Tipps & Best Practices

### Erste Inbetriebnahme
1. Setze `log_level: DEBUG`, um alle Details zu sehen
2. Starte das Add-on und prüfe die Logs
3. Warte auf „Connected (Slave ID: X)"
4. Prüfe die ersten Datenpunkte im Log
5. Gehe zu MQTT Integration und aktiviere gewünschte Entitäten

### Normalbetrieb
- Nutze `log_level: INFO` für übersichtliche Logs
- `poll_interval: 30-60s` für optimale Performance
- Überwache gelegentlich die Cycle-Times im Log

### Performance optimieren
- Achte auf WARNING-Meldungen im Log
- Bei Cycle-Times > 80% poll_interval → `poll_interval` erhöhen
- DEBUG-Level zeigt genaue Zeitmessungen für jeden Schritt
- Essential Registers (Version 1.1.1+) sind bereits optimiert

### Fehlersuche
- DEBUG-Level zeigt genau, welche Register gelesen werden
- Prüfe `binary_sensor.huawei_solar_status` für Verbindungsstatus
- Logs regelmäßig auf Warnings/Errors prüfen
- Health Check im Home Assistant Add-on Status beachten

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

Aktuelle Version: **1.1.2**

### Wichtigste Änderungen
- **1.1.2:** Code-Refactoring, dynamischer Python-Version-Support, verbesserte MQTT-Fallbacks
- **1.1.1:** Essential Registers (nur 21 statt 500+), Cycle-Time < 3s
- **1.1.0:** Parallele Batch-Reads (8x Performance-Boost)
- **1.0.7:** Kritische Bugfixes, bashio-Kompatibilität

Vollständiger Changelog: [CHANGELOG.md](https://github.com/arboeh/homeassistant-huawei-solar-addon/blob/main/CHANGELOG.md)

## Support & Weiterentwicklung

- **GitHub Repository:** [arboeh/homeassistant-huawei-solar-addon](https://github.com/arboeh/homeassistant-huawei-solar-addon)
- **Basierend auf:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)
