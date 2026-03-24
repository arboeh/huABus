# huABus | Huawei Solar Modbus to MQTT

Liest Daten deines Huawei Wechselrichters per Modbus TCP aus und veröffentlicht sie über MQTT mit automatischer Home Assistant Discovery.

> **⚠️ KRITISCH: Nur EINE Modbus-Verbindung erlaubt!**
>
> Huawei-Wechselrichter haben eine **Hardware-Limitierung**: Sie erlauben **nur EINE aktive Modbus TCP-Verbindung** zur selben Zeit.
>
> ### Vor Installation UNBEDINGT prüfen:
>
> 1. **Konkurrierende Verbindungen entfernen:**
>    - Einstellungen → Geräte & Dienste → ALLE Huawei-Integrationen entfernen
>    - Monitoring-Software und mobile Apps mit Modbus-Zugriff deaktivieren
> 2. **FusionSolar Cloud:**
>    - Funktioniert parallel zu Modbus, zeigt aber "Abnormale Kommunikation" → **ignorieren!**
> 3. **Symptom bei mehreren Verbindungen:**
>    ```
>    ERROR - Timeout while waiting for connection
>    ERROR - No response received after 3 retries
>    ```
>
> **Regel:** Nur EINE Modbus-Verbindung = stabiles System ✅

## 🚀 Schnellstart

### 1. Installation

1. Einstellungen → Addons → Addon Store⋮ (oben rechts) → Repositories
2. Hinzufügen: `https://github.com/arboeh/huABus`
3. Installiere "huABus | Huawei Solar Modbus to MQTT"

### 2. Minimalkonfiguration

```yaml
modbus_host: "192.168.1.100" # Deine Inverter-IP
modbus_auto_detect_slave_id: true # Auto-Erkennung (Standard)
log_level: "INFO"
```

**Optional:** Manuelle Slave ID setzen, falls Auto-Erkennung fehlschlägt:

```yaml
modbus_auto_detect_slave_id: false
slave_id: 1 # Versuche 0, 1, 2 oder 100
```

### 3. Überprüfung

**Erfolgs-Indikatoren in Logs:**

```
INFO - Inverter: 192.168.1.100:502 (Slave ID: auto-detect)
INFO - Trying Slave ID 0... ⏸️
INFO - Trying Slave ID 1... ✅
INFO - Connected (Slave ID: 1)
INFO - Registers: 58 essential
INFO - 📊 Published - PV: 4500W | AC Out: 4200W | ...
```

**Sensoren aktivieren:**

- Einstellungen → Geräte & Dienste → MQTT → "Huawei Solar Inverter"

### 4. Häufige Erstinstallations-Probleme

| Symptom                      | Schnelle Lösung                              |
| ---------------------------- | -------------------------------------------- |
| Alle Slave IDs schlagen fehl | IP prüfen, Modbus TCP im Inverter aktivieren |
| `Connection refused`         | Modbus TCP im Inverter aktiviert?            |
| Keine Sensoren erscheinen    | 30s warten, MQTT Integration neu laden       |

## Funktionen

- **Automatische Slave ID-Erkennung:** Probiert automatisch gängige Werte (0, 1, 2, 100)
  - hält Home Assistant Sensoren kontinuierlich aktualisiert
  - verbessert die Kompatibilität mit Energiemanagement-Systemen (z.B. EVCC)
  - vollständig optional aktivierbar
- **Auto MQTT-Konfiguration:** Nutzt automatisch Home Assistant MQTT Service-Zugangsdaten
- **Schnelle Modbus TCP Verbindung** (58 Register, 2-5s Cycle-Time)
- **total_increasing Filter:** Verhindert falsche Counter-Resets
  - Filtert negative Werte und Counter-Rückgänge
  - Keine Warmup-Phase - sofortiger Schutz
  - Automatischer Reset bei Verbindungsfehlern
- **Error Tracking:** Intelligente Fehler-Aggregation mit Downtime-Tracking
- **Umfassende Überwachung:**
  - PV-Leistungen (PV1-4 mit Spannung/Strom)
  - Netzleistung (Import/Export, 3-phasig)
  - Batterie (SOC, Leistung, Tages-/Gesamtenergie)
  - Smart Meter (3-phasig, falls vorhanden)
  - Inverter-Status und Wirkungsgrad
- **Konfigurierbares Logging** mit TRACE, DEBUG, INFO, WARNING, ERROR
- **Performance-Monitoring** mit automatischen Warnungen

## Konfigurationsoptionen

### Modbus-Einstellungen

- **modbus_host** (erforderlich): IP-Adresse des Inverters (z.B. `192.168.1.100`)
- **modbus_port** (Standard: `502`): Modbus TCP Port
- **modbus_auto_detect_slave_id** (Standard: `true`): Automatische Slave ID-Erkennung
- **slave_id** (Standard: `1`, Range: 0-247): Manuelle Slave ID (nur genutzt wenn Auto-Erkennung deaktiviert)

### MQTT-Einstellungen

- **mqtt_host** (Standard: `core-mosquitto`): Broker Hostname (leer lassen für Auto-Config)
- **mqtt_port** (Standard: `1883`): Broker Port
- **mqtt_user** (optional): Benutzername (leer lassen um HA MQTT Service zu nutzen)
- **mqtt_password** (optional): Passwort (leer lassen um HA MQTT Service zu nutzen)
- **mqtt_topic** (Standard: `huawei-solar`): Basis-Topic für Daten

**💡 Pro-Tipp:** Lass MQTT-Zugangsdaten leer - nutzt automatisch Home Assistant MQTT Service!

### Erweiterte Einstellungen

- **log_level** (Standard: `INFO`):
  - `TRACE`: Ultra-detailliert mit Modbus-Byte-Arrays
  - `DEBUG`: Detaillierte Performance-Metriken, Slave ID-Erkennungsversuche
  - `INFO`: Wichtige Ereignisse, Filter-Zusammenfassungen alle 20 Cycles (empfohlen)
  - `WARNING/ERROR`: Nur Probleme
- **status_timeout** (Standard: `180s`, Range: 30-600): Offline-Timeout
- **poll_interval** (Standard: `30s`, Range: 10-300): Abfrageintervall für Modbus
  - Empfohlen: **30-60s** für stabile Verbindungen

## MQTT Topics

- **Messdaten:** `huawei-solar` (JSON mit allen Sensordaten + Timestamp)
- **Status:** `huawei-solar/status` (online/offline für Verfügbarkeit)

## Home Assistant Entitäten

Entitäten unter: **Einstellungen → Geräte & Dienste → MQTT → "Huawei Solar Inverter"**

### Hauptentitäten (standardmäßig aktiviert)

**Leistung:**

- `sensor.solar_power`, `sensor.input_power`, `sensor.grid_power`, `sensor.battery_power`, `sensor.pv1_power`

**Energie (Filter-geschützt):**

- `sensor.solar_daily_yield`, `sensor.solar_total_yield`\*
- `sensor.grid_energy_exported`_, `sensor.grid_energy_imported`_
- `sensor.battery_charge_today`, `sensor.battery_discharge_today`
- `sensor.battery_total_charge`_, `sensor.battery_total_discharge`_

\*Filter-geschützte Sensoren verwenden bei Modbus-Fehlern letzten gültigen Wert statt 0

**Batterie:**

- `sensor.battery_soc`, `sensor.battery_bus_voltage`, `sensor.battery_bus_current`

**Netz:**

- `sensor.grid_voltage_phase_a/b/c`, `sensor.grid_line_voltage_ab/bc/ca`
- `sensor.grid_frequency`, `sensor.grid_current_phase_a/b/c`

**Inverter:**

- `sensor.inverter_temperature`, `sensor.inverter_efficiency`
- `sensor.model_name`, `sensor.serial_number`

**Status:**

- `binary_sensor.huawei_solar_status` (online/offline)
- `sensor.inverter_status`, `sensor.battery_status`

### Diagnostik-Entitäten (standardmäßig deaktiviert)

Manuell aktivieren: PV2/3/4 Details, Phasen-Ströme, detaillierte Leistungen

## Performance & Monitoring

**Cycle-Performance:**

```
INFO - Essential read: 2.1s (58/58)
INFO - 📊 Published - PV: 4500W | AC Out: 4200W | Grid: -200W | Battery: 800W
DEBUG - Cycle: 2.3s (Modbus: 2.1s, Transform: 0.005s, MQTT: 0.194s)
```

**Automatische Slave ID-Erkennung:**

```
INFO - Inverter: 192.168.1.100:502 (Slave ID: auto-detect)
INFO - Trying Slave ID 0... ⏸️
INFO - Trying Slave ID 1... ✅
INFO - Connected (Slave ID: 1)
```

**Filter-Aktivität (wenn Werte gefiltert):**

```
INFO - 📊 Published - PV: 788W | ... | Battery: 569W 🔍[2 filtered]
DEBUG - 🔍 Filter details: {'energy_yield_accumulated': 1, 'battery_charge_total': 1}
```

**Filter-Zusammenfassung (alle 20 Cycles):**

```
INFO - 🔍 Filter summary (last 20 cycles): 0 values filtered - all data valid ✓
```

**Automatische Warnungen:**

```
WARNING - Cycle 52.1s > 80% poll_interval (30s)
```

**Error Recovery:**

```
INFO - Connection restored after 47s (3 failed attempts, 2 error types)
```

### Empfohlene Einstellungen

| Szenario           | Poll Interval | Status Timeout |
| ------------------ | ------------- | -------------- |
| Standard           | 30s           | 180s           |
| Schnell            | 20s           | 120s           |
| Langsames Netzwerk | 60s           | 300s           |
| Debugging          | 10s           | 60s            |

## Fehleranalyse

### Alle Slave IDs schlagen fehl

**Symptom:** `ERROR - All Slave IDs failed`

**Lösungen:**

1. Inverter-IP prüfen: `ping <inverter_ip>`
2. Modbus TCP im Inverter-Webinterface aktivieren
3. Firewall-Regeln prüfen
4. `log_level: DEBUG` aktivieren um jeden Versuch zu sehen

### Connection Timeout

**Symptom:** `ERROR - Timeout while waiting for connection`

**Lösungen:**

1. Auto-Erkennung deaktiviert? Versuche manuelle Slave IDs: `0`, `1`, `2`, `100`
2. `poll_interval` von `30` auf `60` erhöhen
3. Netzwerk-Latenz prüfen

### Connection Refused

**Symptom:** `ERROR - [Errno 111] Connection refused`

**Lösungen:**

- IP-Adresse und Port prüfen
- Modbus TCP im Inverter-Webinterface aktivieren
- Firewall-Regeln prüfen

### MQTT-Verbindungsfehler

**Symptom:** `ERROR - MQTT publish failed`

**Lösungen:**

- MQTT Broker prüfen (Einstellungen → Addons → Mosquitto)
- `mqtt_host: core-mosquitto` setzen
- Zugangsdaten leer lassen für Auto-Config

### Performance-Probleme

**Symptom:** `WARNING - Cycle 52.1s > 80% poll_interval`

**Lösungen:**

- `poll_interval` erhöhen (z.B. von 30s auf 60s)
- Netzwerk-Latenz prüfen
- Zeitmessungen in DEBUG-Logs analysieren

### Filter-Aktivität

**Gelegentliches Filtern (1-2/Stunde):** Normal - schützt Energie-Statistiken
**Häufiges Filtern (jeden Cycle):** Verbindungsprobleme - DEBUG-Modus aktivieren

**Filter-Zusammenfassungen verstehen:**

- `0 values filtered - all data valid ✓` → Perfekt!
- `3 values filtered | Details: {...}` → Akzeptabel (gelegentliche Lesefehler)

## Tipps & Best Practices

### Erste Inbetriebnahme

1. Standard Auto-Erkennung für Slave ID nutzen
2. MQTT-Zugangsdaten leer lassen für Auto-Config
3. `log_level: INFO` verwenden
4. "Connected" in Logs prüfen
5. Erste Datenpunkte beobachten
6. Gewünschte Entitäten in MQTT Integration aktivieren

### Fehlersuche

- `log_level: DEBUG` für detaillierte Diagnose aktivieren
- `binary_sensor.huawei_solar_status` für Verbindungsstatus prüfen
- Filter-Zusammenfassungen für Datenqualität beobachten
- Slave ID-Erkennungsversuche in DEBUG-Logs beobachten

## Support

- **GitHub:** [arboeh/huABus](https://github.com/arboeh/huABus)
- **Issues:** [GitHub Issue Templates](https://github.com/arboeh/huABus/issues/new/choose)
- **Basierend auf:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)
