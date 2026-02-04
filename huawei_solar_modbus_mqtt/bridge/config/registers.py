# bridge/config/registers.py

"""
Essential Registers Definition für Huawei SUN2000 Inverter.

Diese Liste definiert welche Modbus-Register vom Inverter gelesen werden sollen.
Die Register-Namen entsprechen den Namen aus der huawei_solar Library, die
wiederum auf der offiziellen Huawei Modbus-Spezifikation basieren.

Philosophie "Essential Registers":
    Statt alle verfügbaren Register zu lesen (100+), konzentrieren wir uns
    auf die wichtigsten für Home Assistant Integration. Dies reduziert:
    - Read-Zeit (2-3s statt 10+s pro Cycle)
    - Netzwerk-Last (weniger Modbus-Requests)
    - Log-Größe (weniger Daten zum Verarbeiten)

Register-Kategorien:
    - Leistung & Energie (Power, Yield, Grid)
    - PV-Strings (Voltage, Current für bis zu 4 Strings)
    - Batterie (SOC, Power, Charge/Discharge Stats)
    - Smart Meter (3-Phasen Details, optional)
    - Netz-Phasen (Voltage, Frequency)
    - Inverter-Status (Temperature, Efficiency, Status Codes)
    - Device-Info (Model, Serial, Rated Power)

Hardware-Abhängigkeit:
    Nicht alle Register sind bei allen Systemen verfügbar:
    - PV String 3/4: Nur bei größeren Invertern
    - Batterie-Register: Nur wenn LUNA2000 angeschlossen
    - Smart Meter: Nur wenn SDongleA/DDSU666 verbunden
    - Phase B/C: Nur bei 3-Phasen-Systemen

    Fehlende Register liefern 65535 (Modbus "nicht verfügbar") und
    werden automatisch gefiltert (siehe transform.py).

Read-Performance:
    Typisch 2-5 Sekunden für alle 58 Register (abhängig von:)
    - Netzwerk-Latenz zum Inverter
    - Inverter-Last (während Optimierung langsamer)
    - Modbus-Timeout-Einstellungen

Erweiterung:
    Um weitere Register hinzuzufügen:
    1. Register-Name aus huawei_solar Library Doku nehmen
    2. Hier zu ESSENTIAL_REGISTERS hinzufügen
    3. In mappings.py Mapping zu MQTT-Key definieren
    4. Optional in sensors_mqtt.py Sensor-Config hinzufügen

Beispiel huawei_solar Register-Namen:
    - Aus Library: "active_power", "input_power", "storage_state_of_capacity"
    - Modbus-Adresse: Automatisch von Library gemappt (z.B. 32080 für active_power)
    - Unit: Automatisch erkannt (RegisterValue hat .unit Attribut)

Siehe auch:
    - mappings.py: Register-Namen → MQTT-Keys
    - sensors_mqtt.py: MQTT-Keys → Home Assistant Sensors
    - huawei_solar Library Doku: Vollständige Register-Liste
"""

# Essential Registers Liste
# Format: Liste von Register-Namen wie in huawei_solar Library definiert
# Reihenfolge ist egal (wird sequentiell gelesen, nicht nach Adresse sortiert)
ESSENTIAL_REGISTERS = [
    # === Leistung (Power) ===
    # Aktuelle Momentan-Leistungswerte in Watt
    "active_power",  # AC-Ausgangsleistung des Inverters (was ins Netz/Haus geht)
    "input_power",  # DC-Eingangsleistung von PV-Strings (Solar-Erzeugung)
    "power_meter_active_power",  # Smart Meter Leistung (Netz: pos=Bezug, neg=Einspeisung)
    "storage_charge_discharge_power",  # Batterie-Leistung (pos=Laden, neg=Entladen)
    # === Batterie Status ===
    "storage_state_of_capacity",  # State of Charge (SOC) in % (0-100)
    # === Energie-Counter (Energy) ===
    # Akkumulierte Energie-Werte in kWh
    "daily_yield_energy",  # Tagesertrag (resettet um Mitternacht)
    "accumulated_yield_energy",  # Gesamtertrag seit Installation
    "grid_exported_energy",  # Total eingespeiste Energie
    "grid_accumulated_energy",  # Total bezogene Energie
    # Batterie Tages-Energie
    "storage_current_day_charge_capacity",  # Geladene Energie heute
    "storage_current_day_discharge_capacity",  # Entladene Energie heute
    # === PV-Strings (bis zu 4 Strings möglich) ===
    # Spannung (V) und Strom (A) pro String
    "pv_01_voltage",  # String 1 Spannung
    "pv_01_current",  # String 1 Strom
    "pv_02_voltage",  # String 2 Spannung
    "pv_02_current",  # String 2 Strom
    "pv_03_voltage",  # String 3 Spannung (optional, kleinere Inverter haben nur 2)
    "pv_03_current",  # String 3 Strom
    "pv_04_voltage",  # String 4 Spannung (optional)
    "pv_04_current",  # String 4 Strom
    # === Batterie Gesamt-Statistiken ===
    "storage_total_charge",  # Total geladene Energie seit Installation
    "storage_total_discharge",  # Total entladene Energie seit Installation
    "storage_bus_voltage",  # Bus-Spannung der Batterie
    "storage_bus_current",  # Bus-Strom der Batterie
    # === Netz-Phasen (Grid Phases) ===
    # Phase-zu-Neutral Spannungen
    "grid_A_voltage",  # Phase A Spannung (immer vorhanden)
    "grid_B_voltage",  # Phase B Spannung (nur 3-Phasen)
    "grid_C_voltage",  # Phase C Spannung (nur 3-Phasen)
    # Phase-zu-Phase Spannungen (Line-to-Line)
    "line_voltage_A_B",  # A-B Spannung
    "line_voltage_B_C",  # B-C Spannung
    "line_voltage_C_A",  # C-A Spannung
    # Netzfrequenz
    "grid_frequency",  # Netzfrequenz in Hz (50 Hz EU, 60 Hz US)
    # === Smart Meter (optional, nur wenn SDongleA/DDSU666 angeschlossen) ===
    "meter_status",  # Meter-Status (0=offline, 1=normal)
    "power_meter_reactive_power",  # Blindleistung in var
    # Smart Meter: 3-Phasen Ströme
    "active_grid_A_current",  # Phase A Strom
    "active_grid_B_current",  # Phase B Strom
    "active_grid_C_current",  # Phase C Strom
    # Smart Meter: 3-Phasen Spannungen (Line-to-Line)
    "active_grid_A_B_voltage",  # A-B Spannung
    "active_grid_B_C_voltage",  # B-C Spannung
    "active_grid_C_A_voltage",  # C-A Spannung
    # Smart Meter: 3-Phasen Leistungen
    "active_grid_A_power",  # Phase A Leistung
    "active_grid_B_power",  # Phase B Leistung
    "active_grid_C_power",  # Phase C Leistung
    # Smart Meter: Weitere Messwerte
    "active_grid_frequency",  # Netzfrequenz vom Meter
    "active_grid_power_factor",  # Leistungsfaktor (cos φ)
    # === Inverter Diagnose & Status ===
    "internal_temperature",  # Innentemperatur in °C
    "day_active_power_peak",  # Maximale Leistung heute
    "power_factor",  # Leistungsfaktor des Inverters
    "efficiency",  # Wirkungsgrad in % (DC→AC Umwandlung)
    "reactive_power",  # Blindleistung in var
    "insulation_resistance",  # Isolationswiderstand in MΩ (wichtig für Sicherheit)
    # Status-Codes (Bitfelder, siehe Huawei Doku für Interpretation)
    "device_status",  # Device-Status Code
    "state_1",  # State 1 Bitfeld
    "state_2",  # State 2 Bitfeld
    # === Device-Informationen ===
    # Statische Informationen (ändern sich nicht)
    "model_name",  # Modellbezeichnung (z.B. "SUN2000-10KTL-M1")
    "serial_number",  # Seriennummer des Inverters
    "rated_power",  # Nennleistung in W (z.B. 10000)
    "startup_time",  # Startup-Zeitpunkt (timestamp)
    # === Batterie Status ===
    "storage_running_status",  # Batterie Laufstatus (0=offline, 1=standby, 2=running, 3=fault)
]
