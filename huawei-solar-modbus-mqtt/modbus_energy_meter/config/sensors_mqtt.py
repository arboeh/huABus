# modbus_energy_meter/config/sensors_mqtt.py

"""
MQTT Sensor Definitions für Home Assistant Discovery.

Diese Datei definiert alle Sensoren die in Home Assistant via MQTT Discovery
automatisch angelegt werden. Jeder Sensor beschreibt wie ein Wert aus dem
MQTT-Payload extrahiert und in HA dargestellt werden soll.

Sensor-Typen:
    - NUMERIC_SENSORS: Sensoren mit numerischen Werten und unit_of_measurement
    - TEXT_SENSORS: Sensoren mit String-Werten (Status, Modellname, etc.)

MQTT Discovery:
    Beim Start publiziert das Add-on für jeden Sensor eine Config-Message zu:
    homeassistant/sensor/huawei_solar/{key}/config

    Home Assistant liest diese Config und erstellt automatisch Entities:
    sensor.solar_power, sensor.battery_soc, sensor.grid_power, etc.

Wichtige Config-Keys:
    - name: Anzeigename in Home Assistant UI
    - key: MQTT-Key aus transform.py (z.B. "power_active")
    - unit_of_measurement: Einheit (W, kWh, V, A, %, °C, Hz)
    - device_class: HA Device Class (power, energy, voltage, current, battery, ...)
    - state_class: State Class für Statistiken
        * measurement: Momentanwert (kann steigen/fallen)
        * total: Akkumulierter Wert mit Resets (täglich)
        * total_increasing: Akkumulierter Wert ohne Resets (lifetime)
    - value_template: Jinja2 Template zum Extrahieren & Filtern
    - icon: MDI Icon (mdi:solar-power, mdi:battery, ...)
    - enabled: Sensor standardmäßig aktiviert? (False = manuell aktivieren)
    - entity_category: Kategorie (diagnostic = unter "Diagnose", None = Haupt-Entity)

value_template mit default():
    Problem: Wenn ein Key im MQTT-Payload fehlt (Register nicht gelesen),
    würde HA Template-Error "dict object has no attribute" werfen.

    Lösung: {{ value_json.key | default(0) }}
    - Key vorhanden → Wert wird verwendet
    - Key fehlt → Fallback auf default-Wert

    Verwendet für:
    - Optional hardware (Batterie, Meter, String 3/4)
    - Register die manchmal ungültig sind (65535 gefiltert)

    Siehe auch: total_increasing_filter.py (filtert zusätzlich auf Python-Ebene)

state_class Wahl:
    - measurement: Leistung (W), Spannung (V), Strom (A), Temperatur, SOC
      → Kann jederzeit steigen oder fallen
      → HA Statistiken: Min, Max, Mean

    - total_increasing: Energie-Counter die nur steigen (mit Filter!)
      → energy_yield_accumulated, battery_charge_total, ...
      → HA interpretiert Rückgänge als Counter-Reset (daher Filter essentiell!)
      → HA Statistiken: Total, Differenzen für Energy Dashboard

    - total: Counter mit erwarteten Resets
      → Aktuell nicht verwendet (alle total_increasing)
      → Wäre sinnvoll für Tageswerte (energy_yield_day resettet nachts)

enabled Strategie:
    - True (Standard): Wichtige Haupt-Sensoren (Leistung, Energie, SOC)
    - False: Optionale/detaillierte Sensoren
      * String 2/3/4 (viele Anlagen haben nur 1-2 Strings)
      * Diagnostik-Werte (State Bitfelder, Startup Time)
      * Detaillierte Phasen-Werte (bei einfachen Installationen nicht nötig)

    User kann in HA UI jederzeit deaktivierte Sensoren aktivieren.

entity_category:
    - None (default): Haupt-Entity, erscheint prominent in UI
    - "diagnostic": Diagnose-Entity, unter "Diagnose" gruppiert
      * Temperatur, Effizienz, Isolationswiderstand
      * Status-Codes, State-Bitfelder
      * Modellname, Seriennummer

Hardware-Kompatibilität:
    Nicht alle Sensoren sind bei allen Systemen verfügbar:
    - Batterie-Sensoren: Nur mit LUNA2000 oder kompatibel
    - Smart Meter: Nur mit SDongleA/DDSU666
    - String 3/4: Nur größere Inverter-Modelle
    - Phase B/C: Nur 3-Phasen-Systeme

    Fehlende Register → value_template mit default() verhindert Errors

Erweiterung:
    Neuen Sensor hinzufügen:
    1. Register zu registers.py hinzufügen
    2. Mapping in mappings.py definieren
    3. Hier Sensor-Config erstellen:
       {
           "name": "Display Name",
           "key": "mqtt_key_from_mappings",
           "unit_of_measurement": "...",
           "device_class": "...",
           "state_class": "measurement",
           "value_template": "{{ value_json.mqtt_key | default(0) }}",
           "enabled": True,
       }

Siehe auch:
    - mqtt_client.py: Verwendet diese Configs für Discovery
    - mappings.py: Definiert MQTT-Keys
    - registers.py: Definiert welche Register gelesen werden
    - Home Assistant MQTT Discovery Doku
"""

from typing import Any, Dict, List

# Numerische Sensoren mit unit_of_measurement
# Diese erscheinen in HA als sensor.{entity_id} mit numerischem State
NUMERIC_SENSORS: List[Dict[str, Any]] = [
    # === Core Power Values ===
    # Diese 4 Sensoren sind die wichtigsten - immer enabled, keine defaults nötig
    # (werden in transform.py via CRITICAL_DEFAULTS auf 0 gesetzt falls fehlend)
    {
        "name": "Solar Power",  # AC-Ausgangsleistung des Inverters
        "key": "power_active",
        "unit_of_measurement": "W",
        "device_class": "power",  # HA erkennt automatisch als Leistung
        "state_class": "measurement",  # Momentanwert (steigt/fällt)
        "icon": "mdi:solar-power",
        "enabled": True,
    },
    {
        "name": "Input Power",  # DC-Eingangsleistung von PV-Strings
        "key": "power_input",
        "unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "icon": "mdi:solar-panel",
        "enabled": True,
    },
    {
        "name": "Grid Power",  # Netzleistung vom Smart Meter (pos=Bezug, neg=Einspeisung)
        "key": "meter_power_active",
        "unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "icon": "mdi:transmission-tower",
        "enabled": True,
    },
    {
        "name": "Battery Power",  # Batterie-Leistung (pos=Laden, neg=Entladen)
        "key": "battery_power",
        "unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "icon": "mdi:battery-charging",
        "value_template": "{{ value_json.battery_power | default(0) }}",
        "enabled": True,
    },
    # === Energy Values ===
    # Energie-Counter für Home Assistant Energy Dashboard
    {
        "name": "Solar Daily Yield",  # Tagesertrag (resettet um Mitternacht)
        "key": "energy_yield_day",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",  # Counter (mit Filter gegen falsche Resets!)
        "icon": "mdi:solar-power",
        "enabled": True,
    },
    {
        "name": "Solar Total Yield",  # Gesamtertrag seit Installation
        "key": "energy_yield_accumulated",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",  # Lifetime-Counter (niemals fällt)
        "icon": "mdi:solar-power",
        "enabled": True,
    },
    {
        "name": "Grid Energy Exported",  # Total eingespeiste Energie
        "key": "energy_grid_exported",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "icon": "mdi:transmission-tower-export",
        "value_template": "{{ value_json.energy_grid_exported | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Grid Energy Imported",  # Total bezogene Energie
        "key": "energy_grid_accumulated",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "icon": "mdi:transmission-tower-import",
        "enabled": True,
    },
    # === Battery ===
    # Alle Batterie-Sensoren haben default(), da optional (keine LUNA2000)
    {
        "name": "Battery SOC",  # State of Charge in %
        "key": "battery_soc",
        "unit_of_measurement": "%",
        "device_class": "battery",  # HA zeigt Batterie-Icon mit %
        "state_class": "measurement",
        "icon": "mdi:battery",
        "value_template": "{{ value_json.battery_soc | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Battery Charge Today",  # Geladene Energie heute
        "key": "battery_charge_day",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",  # Resettet täglich
        "icon": "mdi:battery-plus",
        "value_template": "{{ value_json.battery_charge_day | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Battery Discharge Today",  # Entladene Energie heute
        "key": "battery_discharge_day",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",  # Resettet täglich
        "icon": "mdi:battery-minus",
        "value_template": "{{ value_json.battery_discharge_day | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Battery Total Charge",  # Total geladene Energie (Lifetime)
        "key": "battery_charge_total",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "value_template": "{{ value_json.battery_charge_total | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Battery Total Discharge",  # Total entladene Energie (Lifetime)
        "key": "battery_discharge_total",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "value_template": "{{ value_json.battery_discharge_total | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Battery Bus Voltage",  # DC-Bus Spannung
        "key": "battery_bus_voltage",
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "value_template": "{{ value_json.battery_bus_voltage | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Battery Bus Current",  # DC-Bus Strom
        "key": "battery_bus_current",
        "unit_of_measurement": "A",
        "device_class": "current",
        "state_class": "measurement",
        "value_template": "{{ value_json.battery_bus_current | default(0) }}",
        "enabled": True,
    },
    # === PV Strings ===
    # String 1: Meist vorhanden, enabled
    # String 2/3/4: Optional (kleinere Anlagen), disabled by default
    {
        "name": "PV1 Voltage",
        "key": "voltage_PV1",
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "value_template": "{{ value_json.voltage_PV1 | default(0) }}",  # Nachts = 0
        "enabled": True,
    },
    {
        "name": "PV1 Current",
        "key": "current_PV1",
        "unit_of_measurement": "A",
        "device_class": "current",
        "state_class": "measurement",
        "value_template": "{{ value_json.current_PV1 | default(0) }}",  # Nachts = 0
        "enabled": True,
    },
    {
        "name": "PV2 Voltage",
        "key": "voltage_PV2",
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "value_template": "{{ value_json.voltage_PV2 | default(0) }}",
        "enabled": False,  # User aktiviert falls benötigt
    },
    {
        "name": "PV2 Current",
        "key": "current_PV2",
        "unit_of_measurement": "A",
        "device_class": "current",
        "state_class": "measurement",
        "value_template": "{{ value_json.current_PV2 | default(0) }}",
        "enabled": False,
    },
    {
        "name": "PV3 Voltage",
        "key": "voltage_PV3",
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "value_template": "{{ value_json.voltage_PV3 | default(0) }}",
        "enabled": False,  # Nur größere Inverter
    },
    {
        "name": "PV3 Current",
        "key": "current_PV3",
        "unit_of_measurement": "A",
        "device_class": "current",
        "state_class": "measurement",
        "value_template": "{{ value_json.current_PV3 | default(0) }}",
        "enabled": False,
    },
    {
        "name": "PV4 Voltage",
        "key": "voltage_PV4",
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "value_template": "{{ value_json.voltage_PV4 | default(0) }}",
        "enabled": False,  # Nur größere Inverter
    },
    {
        "name": "PV4 Current",
        "key": "current_PV4",
        "unit_of_measurement": "A",
        "device_class": "current",
        "state_class": "measurement",
        "value_template": "{{ value_json.current_PV4 | default(0) }}",
        "enabled": False,
    },
    # === Inverter Diagnostics ===
    # Diagnose-Werte, entity_category="diagnostic"
    {
        "name": "Inverter Temperature",
        "key": "inverter_temperature",
        "unit_of_measurement": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "value_template": "{{ value_json.inverter_temperature | default(0) }}",
        "enabled": True,
        "entity_category": "diagnostic",  # Unter "Diagnose" gruppiert
    },
    {
        "name": "Inverter Efficiency",  # DC→AC Wirkungsgrad in %
        "key": "inverter_efficiency",
        "unit_of_measurement": "%",
        "state_class": "measurement",
        "icon": "mdi:gauge",
        "value_template": "{{ value_json.inverter_efficiency | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Day Peak Power",  # Maximale Leistung heute
        "key": "power_active_peak_day",
        "unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "value_template": "{{ value_json.power_active_peak_day | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Reactive Power",  # Blindleistung in var
        "key": "power_reactive",
        "unit_of_measurement": "var",
        "device_class": "reactive_power",
        "state_class": "measurement",
        "value_template": "{{ value_json.power_reactive | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Power Factor",  # Leistungsfaktor (cos φ)
        "key": "power_factor",
        "unit_of_measurement": "",  # Dimensionslos (-1 bis +1)
        "state_class": "measurement",
        "icon": "mdi:sine-wave",
        "value_template": "{{ value_json.power_factor | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Insulation Resistance",  # Isolationswiderstand (Sicherheit)
        "key": "inverter_insulation_resistance",
        "unit_of_measurement": "MΩ",
        "state_class": "measurement",
        "icon": "mdi:lightning-bolt-circle",
        "value_template": "{{ value_json.inverter_insulation_resistance | default(0) }}",
        "enabled": True,
        "entity_category": "diagnostic",
    },
    # === Grid Voltages ===
    # 3-Phasen System: Alle 3 Phasen + Line-to-Line
    # 1-Phasen System: Nur Phase A hat Wert, Rest = 0 (default)
    {
        "name": "Grid Voltage Phase A",  # Phase-zu-Neutral
        "key": "voltage_grid_A",
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "value_template": "{{ value_json.voltage_grid_A | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Grid Voltage Phase B",  # Nur 3-Phasen
        "key": "voltage_grid_B",
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "value_template": "{{ value_json.voltage_grid_B | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Grid Voltage Phase C",  # Nur 3-Phasen
        "key": "voltage_grid_C",
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "value_template": "{{ value_json.voltage_grid_C | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Line Voltage A-B",  # Phase-zu-Phase (√3 × Phase-zu-Neutral)
        "key": "voltage_line_AB",
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "value_template": "{{ value_json.voltage_line_AB | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Line Voltage B-C",
        "key": "voltage_line_BC",
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "value_template": "{{ value_json.voltage_line_BC | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Line Voltage C-A",
        "key": "voltage_line_CA",
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "value_template": "{{ value_json.voltage_line_CA | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Grid Frequency",  # 50 Hz (EU) oder 60 Hz (US/JP)
        "key": "frequency_grid",
        "unit_of_measurement": "Hz",
        "device_class": "frequency",
        "state_class": "measurement",
        "value_template": "{{ value_json.frequency_grid | default(50) }}",  # Default 50 Hz
        "enabled": True,
    },
    # === Smart Meter Values ===
    # Alle optional (nur mit SDongleA/DDSU666)
    {
        "name": "Meter Reactive Power",
        "key": "meter_reactive_power",
        "unit_of_measurement": "var",
        "device_class": "reactive_power",
        "state_class": "measurement",
        "value_template": "{{ value_json.meter_reactive_power | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Meter Power Phase A",  # 3-Phasen Details vom Meter
        "key": "power_meter_A",
        "unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "icon": "mdi:transmission-tower",
        "value_template": "{{ value_json.power_meter_A | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Meter Power Phase B",
        "key": "power_meter_B",
        "unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "icon": "mdi:transmission-tower",
        "value_template": "{{ value_json.power_meter_B | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Meter Power Phase C",
        "key": "power_meter_C",
        "unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "icon": "mdi:transmission-tower",
        "value_template": "{{ value_json.power_meter_C | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Meter Line Voltage A-B",  # Spannungen vom Meter
        "key": "voltage_meter_line_AB",
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "value_template": "{{ value_json.voltage_meter_line_AB | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Meter Line Voltage B-C",
        "key": "voltage_meter_line_BC",
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "value_template": "{{ value_json.voltage_meter_line_BC | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Meter Line Voltage C-A",
        "key": "voltage_meter_line_CA",
        "unit_of_measurement": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "value_template": "{{ value_json.voltage_meter_line_CA | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Meter Current Phase A",  # Ströme vom Meter
        "key": "current_meter_A",
        "unit_of_measurement": "A",
        "device_class": "current",
        "state_class": "measurement",
        "value_template": "{{ value_json.current_meter_A | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Meter Current Phase B",
        "key": "current_meter_B",
        "unit_of_measurement": "A",
        "device_class": "current",
        "state_class": "measurement",
        "value_template": "{{ value_json.current_meter_B | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Meter Current Phase C",
        "key": "current_meter_C",
        "unit_of_measurement": "A",
        "device_class": "current",
        "state_class": "measurement",
        "value_template": "{{ value_json.current_meter_C | default(0) }}",
        "enabled": True,
    },
    {
        "name": "Meter Frequency",  # Frequenz vom Meter
        "key": "frequency_meter",
        "unit_of_measurement": "Hz",
        "device_class": "frequency",
        "state_class": "measurement",
        "value_template": "{{ value_json.frequency_meter | default(50) }}",
        "enabled": True,
    },
    {
        "name": "Meter Power Factor",  # Leistungsfaktor vom Meter
        "key": "power_factor_meter",
        "unit_of_measurement": "",
        "state_class": "measurement",
        "icon": "mdi:sine-wave",
        "value_template": "{{ value_json.power_factor_meter | default(0) }}",
        "enabled": True,
    },
    # === Static Device Info ===
    {
        "name": "Rated Power",  # Nennleistung (z.B. 10000 W)
        "key": "rated_power",
        "unit_of_measurement": "W",
        "device_class": "power",
        "state_class": "measurement",
        "icon": "mdi:gauge",
        "enabled": True,
        "entity_category": "diagnostic",
    },
]

# Text-Sensoren ohne unit_of_measurement
# Für Status-Strings, Modellnamen, etc.
TEXT_SENSORS: List[Dict[str, Any]] = [
    {
        "name": "Inverter Status",  # Status-Code als String
        "key": "inverter_status",
        "icon": "mdi:information",
        "value_template": "{{ value_json.inverter_status | default('unknown') }}",
        "enabled": True,
        "entity_category": "diagnostic",
    },
    {
        "name": "Battery Status",  # Batterie-Status (0=offline, 1=standby, 2=running, 3=fault)
        "key": "battery_status",
        "icon": "mdi:battery-heart",
        "value_template": "{{ value_json.battery_status | default('unknown') }}",
        "enabled": True,
        "entity_category": "diagnostic",
    },
    {
        "name": "Meter Status",  # Meter-Status (0=offline, 1=normal)
        "key": "meter_status",
        "icon": "mdi:meter-electric",
        "value_template": "{{ value_json.meter_status | default('unknown') }}",
        "enabled": True,
        "entity_category": "diagnostic",
    },
    {
        "name": "Model Name",  # z.B. "SUN2000-10KTL-M1"
        "key": "model_name",
        "icon": "mdi:information",
        "value_template": "{{ value_json.model_name | default('N/A') }}",
        "enabled": True,
        "entity_category": "diagnostic",
    },
    {
        "name": "Serial Number",  # Seriennummer
        "key": "serial_number",
        "icon": "mdi:barcode",
        "value_template": "{{ value_json.serial_number | default('N/A') }}",
        "enabled": True,
        "entity_category": "diagnostic",
    },
    {
        "name": "Inverter State 1",  # Bitfeld (siehe Huawei Doku)
        "key": "inverter_state_1",
        "value_template": "{{ value_json.inverter_state_1 | default('') }}",
        "enabled": False,  # Für Experten
        "entity_category": "diagnostic",
    },
    {
        "name": "Inverter State 2",  # Bitfeld (siehe Huawei Doku)
        "key": "inverter_state_2",
        "value_template": "{{ value_json.inverter_state_2 | default('') }}",
        "enabled": False,  # Für Experten
        "entity_category": "diagnostic",
    },
    {
        "name": "Inverter Startup Time",  # Timestamp (HA zeigt als Datum/Zeit)
        "key": "startup_time",
        "device_class": "timestamp",
        "value_template": "{{ value_json.startup_time | default(None) }}",
        "enabled": False,  # Meist nicht relevant
        "entity_category": "diagnostic",
    },
]
