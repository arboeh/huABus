# modbus_energy_meter/config/mappings.py

"""
Register-Mappings von huawei_solar Library zu MQTT-Keys.

Diese Datei definiert das Mapping zwischen:
- Modbus-Register-Namen (wie von huawei_solar Library verwendet)
- MQTT-Key-Namen (wie in Home Assistant verwendet)

Zweck:
    Die huawei_solar Library verwendet spezifische Register-Namen die direkt
    aus der Modbus-Spezifikation kommen (z.B. "active_power", "pv_01_voltage").
    Für MQTT/Home Assistant wollen wir aber kürzere, konsistentere Namen
    (z.B. "power_active", "voltage_PV1").

Struktur:
    REGISTER_MAPPING: Haupt-Mapping Dictionary
    CRITICAL_DEFAULTS: Fallback-Werte für essenzielle Sensoren

Verwendung:
    transform.py verwendet diese Mappings um Modbus-Daten in MQTT-Format
    zu konvertieren. Fehlende kritische Keys werden mit Defaults befüllt.
"""

from typing import Dict

# Haupt-Mapping: Modbus-Register-Name → MQTT-Key
# Format: {"register_name_from_library": "mqtt_key_for_ha"}
REGISTER_MAPPING: Dict[str, str] = {
    # === Inverter Leistung & Energie ===
    # AC-Output des Inverters (was ins Netz/Haus geht)
    "active_power": "power_active",  # Aktuelle AC-Leistung in W
    "input_power": "power_input",  # Aktuelle DC-Eingangsleistung von PV in W
    "day_active_power_peak": "power_active_peak_day",  # Maximale Leistung heute in W
    "reactive_power": "power_reactive",  # Blindleistung in var
    # Energie-Counter (Tagesertrag & Gesamtertrag)
    "daily_yield_energy": "energy_yield_day",  # Ertrag heute in kWh (resettet um Mitternacht)
    "accumulated_yield_energy": "energy_yield_accumulated",  # Gesamtertrag seit Installation
    # Netz-Energie (Einspeisung & Bezug)
    "grid_exported_energy": "energy_grid_exported",  # Total eingespeiste Energie in kWh
    "grid_accumulated_energy": "energy_grid_accumulated",  # Total bezogene Energie in kWh
    # === PV-Strings (Spannung & Strom) ===
    # Bis zu 4 PV-Strings möglich (abhängig von Inverter-Modell)
    # Nicht alle Inverter haben 4 Strings - fehlende liefern 65535 (gefiltert)
    "pv_01_voltage": "voltage_PV1",  # String 1 Spannung in V
    "pv_01_current": "current_PV1",  # String 1 Strom in A
    "pv_02_voltage": "voltage_PV2",  # String 2 Spannung in V
    "pv_02_current": "current_PV2",  # String 2 Strom in A
    "pv_03_voltage": "voltage_PV3",  # String 3 Spannung in V (optional)
    "pv_03_current": "current_PV3",  # String 3 Strom in A (optional)
    "pv_04_voltage": "voltage_PV4",  # String 4 Spannung in V (optional)
    "pv_04_current": "current_PV4",  # String 4 Strom in A (optional)
    # === Netz-Phasen (Inverter-seitig) ===
    # Phase-zu-Neutral Spannungen
    "grid_A_voltage": "voltage_grid_A",  # Phase A Spannung in V
    "grid_B_voltage": "voltage_grid_B",  # Phase B Spannung in V (3-Phasen)
    "grid_C_voltage": "voltage_grid_C",  # Phase C Spannung in V (3-Phasen)
    # Phase-zu-Phase Spannungen (Line-to-Line)
    "line_voltage_A_B": "voltage_line_AB",  # A-B Spannung in V
    "line_voltage_B_C": "voltage_line_BC",  # B-C Spannung in V
    "line_voltage_C_A": "voltage_line_CA",  # C-A Spannung in V
    # Netzfrequenz
    "grid_frequency": "frequency_grid",  # Netzfrequenz in Hz (50 Hz EU, 60 Hz US)
    # === Smart Meter (optional) ===
    # Nur verfügbar wenn Smart Meter am Inverter angeschlossen
    # Misst tatsächlichen Netz-Anschluss (Hausanschluss)
    "power_meter_active_power": "meter_power_active",  # Netzleistung in W
    "power_meter_reactive_power": "meter_reactive_power",  # Blindleistung in var
    "meter_status": "meter_status",  # Meter-Status (0=offline, 1=normal)
    # Smart Meter: 3-Phasen Details
    "active_grid_A_power": "power_meter_A",  # Phase A Leistung in W
    "active_grid_B_power": "power_meter_B",  # Phase B Leistung in W
    "active_grid_C_power": "power_meter_C",  # Phase C Leistung in W
    # Smart Meter: Spannungen
    "active_grid_A_B_voltage": "voltage_meter_line_AB",  # A-B Spannung in V
    "active_grid_B_C_voltage": "voltage_meter_line_BC",  # B-C Spannung in V
    "active_grid_C_A_voltage": "voltage_meter_line_CA",  # C-A Spannung in V
    # Smart Meter: Ströme
    "active_grid_A_current": "current_meter_A",  # Phase A Strom in A
    "active_grid_B_current": "current_meter_B",  # Phase B Strom in A
    "active_grid_C_current": "current_meter_C",  # Phase C Strom in A
    # Smart Meter: Weitere Messwerte
    "active_grid_frequency": "frequency_meter",  # Netzfrequenz vom Meter in Hz
    "active_grid_power_factor": "power_factor_meter",  # Leistungsfaktor (cos φ)
    # === Batterie (optional) ===
    # Nur verfügbar wenn Batterie-System angeschlossen (z.B. LUNA2000)
    "storage_state_of_capacity": "battery_soc",  # State of Charge in % (0-100)
    "storage_charge_discharge_power": "battery_power",  # Lade-/Entladeleistung in W
    "storage_bus_voltage": "battery_bus_voltage",  # Bus-Spannung in V
    "storage_bus_current": "battery_bus_current",  # Bus-Strom in A
    # Batterie: Tages-Energie (resettet um Mitternacht)
    "storage_current_day_charge_capacity": "battery_charge_day",  # Geladene Energie heute in kWh
    "storage_current_day_discharge_capacity": "battery_discharge_day",  # Entladene Energie
    # Batterie: Gesamt-Energie (seit Installation)
    "storage_total_charge": "battery_charge_total",  # Total geladene Energie in kWh
    "storage_total_discharge": "battery_discharge_total",  # Total entladene Energie in kWh
    # Batterie: Status
    "storage_running_status": "battery_status",  # Laufstatus
    # === Inverter Status & Diagnose ===
    "device_status": "inverter_status",  # Device-Status Code (siehe Huawei-Doku)
    "state_1": "inverter_state_1",  # State 1 Bitfeld (siehe Huawei-Doku)
    "state_2": "inverter_state_2",  # State 2 Bitfeld (siehe Huawei-Doku)
    "startup_time": "startup_time",  # Startup-Zeitpunkt (timestamp)
    "internal_temperature": "inverter_temperature",  # Innentemperatur in °C
    "efficiency": "inverter_efficiency",  # Wirkungsgrad in % (DC→AC)
    "insulation_resistance": "inverter_insulation_resistance",  # Isolationswiderstand in MΩ
    "power_factor": "power_factor",  # Leistungsfaktor (cos φ)
    # === Geräte-Informationen ===
    "model_name": "model_name",  # Modellbezeichnung (z.B. "SUN2000-10KTL-M1")
    "serial_number": "serial_number",  # Seriennummer
    "rated_power": "rated_power",  # Nennleistung in W (z.B. 10000)
}

# Critical Defaults: Fallback-Werte für essenzielle Sensoren
#
# Diese Werte werden in transform.py verwendet wenn ein kritischer
# Sensor-Key nach dem Mapping fehlt (Register nicht gelesen/ungültig).
#
# Zweck:
#   Verhindert dass wichtige Sensoren in Home Assistant auf "unknown"
#   oder "unavailable" gehen. Stattdessen zeigen sie 0 (logischer Fallback).
#
# Warum diese Keys kritisch sind:
#   - power_active: Zentral für Energie-Dashboard, Automationen
#   - power_input: Wichtig für PV-Ertrags-Berechnung
#   - meter_power_active: Essentiell für Eigenverbrauchs-Berechnung
#   - battery_power: Wichtig für Batterie-Logik
#   - battery_soc: Kritisch für Batterie-Management
#
# Wann werden Defaults verwendet?
#   1. Modbus-Register liefert ungültigen Wert (65535, 32767, -32768)
#   2. Register wird vom Inverter nicht unterstützt (z.B. kein Meter)
#   3. Lesefehler bei einzelnem Register (Timeout, CRC-Error)
#
# Default-Wert 0:
#   - Bei Leistung (W): 0W = keine Leistung (sinnvoller Fallback)
#   - Bei SOC (%): 0% = leer (konservativer Fallback, Nutzer wird informiert)
#
# Alternative wäre None → Sensor unavailable:
#   Problem: HA-Automationen basierend auf diesen Sensoren würden fehlschlagen
#   Lösung: 0 als "sicherer Fallback" → Automationen laufen weiter
#
CRITICAL_DEFAULTS: Dict[str, int] = {
    "power_active": 0,  # AC-Leistung: 0W wenn nicht lesbar
    "power_input": 0,  # DC-Leistung: 0W wenn nicht lesbar
    "meter_power_active": 0,  # Netz-Leistung: 0W wenn kein Meter oder Fehler
    "battery_power": 0,  # Batterie-Leistung: 0W wenn keine Batterie oder Fehler
    "battery_soc": 0,  # SOC: 0% wenn keine Batterie oder Fehler (konservativ)
}
