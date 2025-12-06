# Changelog

## [Unreleased]
### Added
- [ ] Neue Features hier dokumentieren

### Fixed
- [ ] Bugfixes hier dokumentieren

### Changed
- [ ] Änderungen hier dokumentieren

## [1.0.2] - 2025-12-06
### Fixed
- HuaweiSolarBridge.create() Parameter-Fehler behoben (explizite Keyword-Argumente)
- DecodeError-Handling für unbekannte Register-Werte (z.B. Unit-Code 780) verbessert
- Robustere Fehlerbehandlung bei Modbus-Kommunikationsproblemen
- Verhindert Absturz des Add-ons bei einzelnen fehlerhaften Registern
- `heartbeat`-Funktion korrekt platziert (behebt "name 'heartbeat' is not defined" Fehler)

### Changed
- Aktualisierte `huawei-solar` Library auf Version >=2.3.0
- Aktualisierte `pymodbus` auf Version >=3.8.6 zur Verbesserung der Protokoll-Kompatibilität
- Erweiterte Logging-Ausgaben für besseres Debugging
- Separate Exception-Behandlung für `DecodeError` und `ReadException`

## [1.0.1] - 2025-12-05
### Fixed
- DecodeError handling für unbekannte Register-Werte
- Verbesserte Fehlerbehandlung bei Modbus-Kommunikation

### Changed
- Aktualisierte huawei-solar Library auf neueste Version
- Erweiterte Logging-Ausgaben für besseres Debugging

## [1.0.0] - 2025-12-04
### Added
- Erste stabile Version des Add-ons
- Versionierung und Release-Workflow mit GitHub Actions
- Badge für aktuelle Release-Version in der README

### Changed
- Wechsel von 0.9.0-beta auf 1.0.0 ohne Breaking Changes

## [0.9.0-beta] - 2025-12-03
### Added
- Initial beta release
- Modbus TCP Verbindung zu Huawei Solar Inverter
- Automatische MQTT Discovery für Home Assistant
- Batterie-Monitoring (SOC, Lade-/Entladeleistung)
- PV-String-Monitoring (PV1/PV2, optional PV3/PV4)
- Netz-Monitoring (Import/Export, 3-phasig)
- Energie-Statistiken (T
