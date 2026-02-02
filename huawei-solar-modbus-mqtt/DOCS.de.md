# huABus | Huawei Solar Modbus to MQTT

Liest Daten deines Huawei SUN2000 Wechselrichters per Modbus TCP aus und veröffentlicht sie über MQTT mit automatischer Home Assistant Discovery.

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

1. Einstellungen → Add-ons → Add-on Store → ⋮ (oben rechts) → Repositories
2. Hinzufügen: `https://github.com/arboeh/huABus`
3. Installiere "huABus | Huawei Solar Modbus to MQTT"

### 2. Minimalkonfiguration

```yaml
modbus_host: "192.168.1.100"  # Deine Inverter-IP
slave_id: 1                    # Versuche 0, 1, oder 16 bei Timeout
log_level: "INFO"
```

### 3. Überprüfung

**Erfolgs-Indikatoren in Logs:**
```
INFO - 🚀 Huawei Solar → MQTT starting
INFO - 🔌 Connected (Slave ID: 1)
INFO - Essential read: 2.1s (58/58)
INFO - 📊 Published - PV: 4500W | ...
```

**Sensoren aktivieren:**
- Einstellungen → Geräte & Dienste → MQTT → "Huawei Solar Inverter"

### 4. Häufige Erstinstallations-Probleme

| Symptom | Schnelle Lösung |
|---------|-----------------|
| `ERROR - Timeout` | Versuche `slave_id: 0`, dann `16` |
| `Connection refused` | IP prüfen, Modbus TCP im Inverter aktivieren |
| `Keine Sensoren erscheinen` | 30s warten, MQTT Integration neu laden |

## Funktionen

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
- **Health Check** für Container-Überwachung

## Konfigurationsoptionen

### Modbus-Einstellungen

- **modbus_host** (erforderlich): IP-Adresse des Inverters (z.B. `192.168.1.100`)
- **modbus_port** (Standard: `502`): Modbus TCP Port
- **slave_id** (Standard: `1`, Range: 0-247): Versuche `0`, `1` oder `16` bei Timeout

### MQTT-Einstellungen

- **mqtt_host** (Standard: `core-mosquitto`): Broker Hostname
- **mqtt_port** (Standard: `1883`): Broker Port
- **mqtt_user** (optional): Benutzername (leer lassen für Auto-Config)
- **mqtt_password** (optional): Passwort (leer lassen für Auto-Config)
- **mqtt_topic** (Standard: `huawei-solar`): Basis-Topic für Daten

### Erweiterte Einstellungen

- **log_level** (Standard: `INFO`):
  - `DEBUG`: Detaillierte Performance-Metriken, Filter-Details bei jedem Event
  - `INFO`: Wichtige Ereignisse, Filter-Zusammenfassungen alle 20 Cycles (empfohlen)
  - `WARNING/ERROR`: Nur Probleme
- **status_timeout** (Standard: `180s`, Range: 30-600): Offline-Timeout
- **poll_interval** (Standard: `30s`, Range: 10-300): Abfrageintervall
  - Empfohlen: 30-60s für optimale Balance

## MQTT Topics

- **Messdaten:** `huawei-solar` (JSON mit allen Sensordaten + Timestamp)
- **Status:** `huawei-solar/status` (online/offline für Verfügbarkeit)

## Home Assistant Entitäten

Entitäten unter: **Einstellungen → Geräte & Dienste → MQTT → "Huawei Solar Inverter"**

### Hauptentitäten (standardmäßig aktiviert)

**Leistung:**
- `sensor.solar_power`, `sensor.input_power`, `sensor.grid_power`, `sensor.battery_power`, `sensor.pv1_power`

**Energie (Filter-geschützt):**
- `sensor.solar_daily_yield`, `sensor.solar_total_yield`*
- `sensor.grid_energy_exported`*, `sensor.grid_energy_imported`*
- `sensor.battery_charge_today`, `sensor.battery_discharge_today`
- `sensor.battery_total_charge`*, `sensor.battery_total_discharge`*

*Filter-geschützte Sensoren verwenden bei Modbus-Fehlern letzten gültigen Wert statt 0

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

| Szenario | Poll Interval | Status Timeout |
|----------|---------------|----------------|
| Standard | 30s | 180s |
| Schnell | 20s | 120s |
| Langsames Netzwerk | 60s | 300s |
| Debugging | 10s | 60s |

## Fehleranalyse

### Connection Timeout

**Symptom:** `ERROR - Timeout while waiting for connection`

**Lösungen:**
1. Verschiedene Slave IDs testen: `0`, `1`, `16`
2. `poll_interval` von `30` auf `60` erhöhen
3. Netzwerk prüfen: `ping <inverter_ip>`
4. `log_level: DEBUG` für Details aktivieren

### Connection Refused

**Symptom:** `ERROR - [Errno 111] Connection refused`

**Lösungen:**
- IP-Adresse und Port prüfen
- Modbus TCP im Inverter-Webinterface aktivieren
- Firewall-Regeln prüfen

### MQTT-Verbindungsfehler

**Symptom:** `ERROR - MQTT publish failed`

**Lösungen:**
- MQTT Broker prüfen (Einstellungen → Add-ons → Mosquitto)
- `mqtt_host: core-mosquitto` setzen
- Zugangsdaten kontrollieren

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
1. `log_level: INFO` verwenden
2. "Connected" und "TotalIncreasingFilter initialized" in Logs prüfen
3. Erste Datenpunkte beobachten
4. Gewünschte Entitäten in MQTT Integration aktivieren

### Fehlersuche
- `log_level: DEBUG` für detaillierte Diagnose aktivieren
- `binary_sensor.huawei_solar_status` für Verbindungsstatus prüfen
- Filter-Zusammenfassungen für Datenqualität beobachten
- Health Check im Add-on Status überwachen

### Multi-Inverter Setup
- Add-on mehrfach installieren mit verschiedenen Namen
- Verschiedene `mqtt_topic` pro Instanz verwenden
- Unterschiedliche `modbus_host` Adressen konfigurieren

## Support

- **GitHub:** [arboeh/huABus](https://github.com/arboeh/huABus)
- **Issues:** [GitHub Issue Templates](https://github.com/arboeh/huABus/issues/new/choose)
- **Basierend auf:** [mjaschen/huawei-solar-modbus-to-mqtt](https://github.com/mjaschen/huawei-solar-modbus-to-mqtt)
