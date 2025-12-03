# Huawei Solar Modbus to MQTT

Dieses Add-on liest Daten deines Huawei SUN2000 Wechselrichters per Modbus TCP aus und veröffentlicht sie über MQTT inklusive Home Assistant MQTT Discovery. Dadurch tauchen die meisten Entitäten automatisch im MQTT-Integration-Panel von Home Assistant auf.

## Funktionen

- Modbus TCP Verbindung zum Huawei SUN2000 Inverter
- Veröffentlichung der Messwerte auf einem MQTT-Topic als JSON
- Automatische Erstellung von Home Assistant Entitäten via MQTT Discovery
- Unterstützung für:
  - PV-Leistungen (PV1/PV2, optional PV3/PV4)
  - Netzleistung (Import/Export)
  - Batterie (SOC, Lade-/Entladeleistung, Tages- und Gesamtenergie)
  - 3-phasige Netzspannungen
  - Tages- und Gesamtenergieertrag
  - Inverter-Temperatur und Wirkungsgrad
- Online-/Offline-Status mit:
  - Binary Sensor „Huawei Solar Status“
  - Heartbeat/Timeout-Überwachung
  - MQTT Last Will (LWT) beim Broker

## Voraussetzungen

- Huawei SUN2000 Wechselrichter mit aktivierter Modbus TCP Schnittstelle
- Home Assistant mit konfigurierter MQTT-Integration
- MQTT Broker (z.B. Mosquitto), idealerweise über Home Assistant Supervisor bereitgestellt

## Konfiguration

Beispielkonfiguration im Add-on-UI:

    modbus_host: "192.168.1.100"
    modbus_port: 502
    modbus_device_id: 1
    mqtt_topic: "huawei-solar"
    debug: false
    status_timeout: 180
    poll_interval: 60

### Optionen

- modbus_host  
  IP-Adresse deines Huawei Wechselrichters.

- modbus_port  
  Modbus TCP Port (Standard: 502).

- modbus_device_id  
  Modbus Slave ID des Inverters. In vielen Installationen ist dies `1`, in manchen `16` oder `0`.

- mqtt_topic  
  Basis-Topic, unter dem die Daten veröffentlicht werden (z.B. `huawei-solar`).

- debug  
  `true` für ausführliche Logs (nur für Tests), `false` für normalen Betrieb.

- status_timeout  
  Zeit in Sekunden, nach der der Status auf `offline` gesetzt wird, wenn keine erfolgreiche Abfrage mehr erfolgt ist (z.B. 180 Sekunden).

- poll_interval  
  Abfrageintervall in Sekunden zwischen zwei Modbus-Reads (z.B. 60 Sekunden).

## MQTT Topics

- Messdaten (JSON):  
  `huawei-solar` (oder dein konfiguriertes Topic)

- Status (online/offline):  
  `huawei-solar/status`  
  Wird genutzt für:
  - Binary Sensor „Huawei Solar Status“
  - availability_topic aller Sensoren

## Entitäten in Home Assistant

Nach dem Start des Add-ons werden automatisch MQTT Discovery Konfigurationen publiziert. Du findest die Entitäten dann unter:

- Einstellungen → Geräte & Dienste → MQTT → Geräte → „Huawei Solar Inverter“

Typische Entitäten:

- Leistung:
  - `sensor.solar_power`
  - `sensor.grid_power`
  - `sensor.battery_power`
  - `sensor.pv1_power`, `sensor.pv2_power`
- Energie:
  - `sensor.solar_daily_yield`
  - `sensor.solar_total_yield`
  - `sensor.grid_energy_exported`
  - `sensor.grid_energy_imported`
  - `sensor.battery_charge_today`
  - `sensor.battery_discharge_today`
- Batterie:
  - `sensor.battery_soc`
- Netz:
  - `sensor.grid_voltage_phase_a/b/c`
  - `sensor.grid_frequency`
- Status:
  - `binary_sensor.huawei_solar_status` (online/offline)
  - `sensor.inverter_status` (Textstatus)

Zusätzliche „diagnostic“ Entitäten (z.B. detaillierte Ströme, Spannungen, Bus-Werte) sind standardmäßig deaktiviert und können bei Bedarf in Home Assistant manuell aktiviert werden.

## Logs & Fehleranalyse

- Add-on Logs:
  - Einstellungen → Add-ons → Huawei Solar Modbus to MQTT → „Log“
- Typische Fehler:
  - Modbus-Verbindungsfehler:
    - IP/Port prüfen
    - Modbus TCP im Inverter aktivieren
    - Slave ID testen (0, 1, 16, 100)
  - MQTT-Verbindungsfehler:
    - MQTT Broker in Home Assistant prüfen
    - Zugangsdaten kontrollieren

## Tipps

- Für die erste Inbetriebnahme `debug: true` setzen, um mehr Details in den Logs zu sehen.
- Wenn du einen zweiten Inverter nachrüsten solltest, kannst du später die Logik erweitern – aktuell ist das Add-on bewusst auf einen Inverter ausgelegt.
