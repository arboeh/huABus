# Changelog

## [1.1.2] - 2025-12-08
### 🧹 **CODE QUALITY & BUG FIXES**

### Changed
- **Code-Refactoring:** Alle Python-Dateien aufgeräumt (-32% Zeilen)
  - `huawei2mqtt.py`: Entfernung ungenutzter Imports (`traceback`)
  - `mqtt.py`: Konsistente Formatierung, präzisere Type Hints
  - `transform.py`: Kompakteres Register-Mapping, bessere Lesbarkeit
- **Dockerfile:** Dynamische Python-Version für Library-Patching
  - Funktioniert jetzt mit Python 3.10/3.11/3.12/3.13+
  - Health Check hinzugefügt (prüft Python-Prozess)
  - Metadata Labels für Home Assistant
- **run.sh:** Verbesserte MQTT-Fallback-Logik
  - Prüft ob Config-Werte nicht-leer sind vor Verwendung
  - Übersichtlichere Startup-Logs mit Trennlinien
- **config.yaml:** MQTT-Defaults hinzugefügt (`core-mosquitto:1883`)
  - Schema-Validierung mit sinnvollen Ranges
  - `startup: services` und `boot: auto` Optionen

### Fixed
- **Doppelte Mapping-Keys in `transform.py` entfernt**
  - `grid_A_voltage` hatte 2 verschiedene Ziele (Konflikt)
  - Python-Dicts können nur 1 Wert pro Key haben
- **Empty-String-Handling in MQTT-Konfiguration**
  - Leere Strings (`''`) werden jetzt als "nicht gesetzt" erkannt
  - Korrekter Fallback zu HA MQTT Service

### Technical Debt
- PEP8-Formatierung durchgehend angewendet
- Konsistente 4-Space-Einrückung
- Reduzierte Code-Duplikation

---

## [1.1.1] - 2025-12-08
### 🚀 **ULTIMATIVE PERFORMANCE-OPTIMIERUNG**

### Changed
- `read_registers_batched()` → `read_registers_filtered()` (sequentielle Reads)
- **Nur 21 Essential Registers** statt 500+ (94% Reduktion)
- `ESSENTIAL_REGISTERS` Liste für kritische Werte (Leistung, Batterie, Grid, PV1)
- Logging für Essential-Reads optimiert

### Fixed
- `meter_power_active` Critical Key Warnings (HV-Meter)
- Cycle-Überlappung bei kurzen poll_intervals

**`.env` Empfehlung:** `HUAWEI_POLL_INTERVAL=30`

---

## [1.1.0] - 2025-12-08
### ✨ MAJOR PERFORMANCE UPGRADE (240s → 30s)
**8x schneller durch parallele Modbus-Requests!**

### Added
- **`read_registers_batched()` Funktion:** Parallele Register-Reads in Batches
  - Performance-Boost: 240s → 30-45s pro Cycle (8x schneller!)
  - Batch-Verarbeitung: 20 Register parallel pro Batch (konfigurierbar)
  - Stabile parallele Ausführung: `asyncio.gather()` mit `return_exceptions=True`
- **Batch-Monitoring:** Detaillierte Logs pro Batch (`Batch 1/8: 20/20 successful in 1.23s`)
- **Inter-Batch-Pausen:** 100ms zwischen Batches verhindert Inverter-Überlastung

### Changed
- **`main_once()` komplett überarbeitet**
- Sequenzielle `for register in REGISTERS` → **`read_registers_batched()`**
- Cycle-Time: 240s → 30-45s
- Verbesserte Performance-Logs mit Batch-Statistiken
- `poll_interval: 60s` jetzt realistisch (vorher unmöglich bei 240s Cycles)

---

## [1.0.7] - 2025-12-08
### Fixed
- **Kritischer Fix:** `UnboundLocalError` in `mqtt.py::get_mqtt_client()`
- **bashio-Kompatibilität:** `#!/usr/bin/with-contenv bashio` Shebang
- **Python Logging:** Vollständige Handler-Initialisierung
- **ENV-Variablen:** Robuste Validierung/Fallbacks

### Changed
- **`run.sh` stabilisiert:** Original mit `python3 -u` (max. Kompatibilität)
- **Logging-Format:** `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

### Added
- Automatische StreamHandler für modulare Logger
- ENV-Variablen-Debug in `init()`

---

## [1.0.6] - 2025-12-08
### Added
- Detailiertes ENV-Variablen-Debug-Logging
- Performance-Metriken (Modbus/Transform/MQTT Timings)

### Changed
- `run.sh` bashio-optimiert
- Legacy `debug` Flag Integration

### Fixed
- Fehlende Python-Logs
- `HUAWEI_LOG_LEVEL` korrekt gesetzt
- `AsyncHuaweiSolar` API vollständig

---

## [1.0.5] - 2025-12-08
### Added
- Pymodbus Log-Level-Kontrolle
- MQTT `retain=True` für Integrationen
- Null-Werte-Fallback (0 für kritische Keys)
- Separate Logger-Konfiguration

### Changed
- MQTT-Daten mit `retain=True`
- Pymodbus-Logs optimiert
- Kritische Sensor-Werte nie `null`

### Fixed
- Integration "outdated" Fehler
- `strconv.ParseFloat: "<nil>"` Fehler
- Übermäßige pymodbus ERROR-Logs

---

## [1.0.4] - 2025-12-08
### Added
- Konfigurierbarer `log_level` (DEBUG/INFO/WARNING/ERROR)
- Modulare Logger (`huawei.main/mqtt/transform`)
- Performance-Messung pro Zyklus
- Register-Read-Statistiken
- Cycle-Time-Warnungen (>80% poll_interval)

### Changed
- Logging-Format standardisiert
- `get_value()` optimiert
- Enum/Datetime Auto-Konvertierung

### Removed
- Unnötige `transform.py` Hilfsfunktionen

---

## [1.0.3] - 2025-12-07
### Fixed
- `HuaweiSolarBridge` → `AsyncHuaweiSolar` Migration
- Bridge-Instantiierungsfehler
- Nicht unterstützte Register ohne Absturz

### Changed
- Registerbasiertes `AsyncHuaweiSolar.get()`
- Erweiterte fehlgeschlagene Register Logs

---

## [1.0.2] - 2025-12-06
### Fixed
- `HuaweiSolarBridge.create()` Parameter
- DecodeError Unit-Code 780
- Robustere Modbus-Fehlerbehandlung
- `heartbeat` Funktionsplatzierung

### Changed
- `huawei-solar` >=2.3.0
- `pymodbus` >=3.8.6
- Separate Exception-Behandlung

---

## [1.0.1] - 2025-12-05
### Fixed
- DecodeError für unbekannte Register
- Modbus-Kommunikation verbessert

### Changed
- huawei-solar Library Update
- Erweiterte Logging-Ausgaben

---

## [1.0.0] - 2025-12-04
### Added
- Erste stabile Version
- GitHub Actions Release-Workflow
- Version-Badge in README

### Changed
- 0.9.0-beta → 1.0.0 (keine Breaking Changes)

---

## [0.9.0-beta] - 2025-12-03
### Added
- Initial beta release
- Modbus TCP Huawei Solar Inverter
- MQTT Discovery Home Assistant
- Batterie/PV/Netz-Monitoring
- HA UI Konfiguration

### Known Issues
- Erweiterte Tests laufen noch
