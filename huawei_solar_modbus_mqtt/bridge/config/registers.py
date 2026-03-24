# huawei_solar_modbus_mqtt/bridge/config/registers.py

"""Essential Modbus registers for Huawei SUN2000 inverters.

This module defines which registers to read from the inverter. Register names
correspond to the huawei_solar library, based on the official Huawei Modbus
specification.

Strategy:
    Read only essential registers (58) instead of all available (100+) to
    reduce cycle time (2-3s vs 10+s), network load, and log size.

Hardware compatibility:
    Not all registers are available on all systems:
    - PV String 3/4: Only on larger inverters
    - Battery registers: Only with LUNA2000
    - Smart Meter: Only with SDongleA/DDSU666
    - Phase B/C: Only on 3-phase systems

    Missing registers return 65535 (Modbus "not available") and are
    automatically filtered.

See also:
    - mappings.py: Register names → MQTT keys
    - sensors_mqtt.py: MQTT keys → Home Assistant sensors
    - huawei_solar library docs: Complete register list
"""

ESSENTIAL_REGISTERS = [
    # Power (W) - Current instantaneous values
    "active_power",  # AC output power (to grid/house)
    "input_power",  # DC input power (solar generation)
    "power_meter_active_power",  # Smart meter power (+import/-export)
    "storage_charge_discharge_power",  # Battery power (+charge/-discharge)
    #
    # Battery status
    "storage_state_of_capacity",  # State of Charge (SOC) 0-100%
    #
    # Energy counters (kWh) - Accumulated values
    "daily_yield_energy",  # Daily yield (resets at midnight)
    "accumulated_yield_energy",  # Total yield since installation
    "grid_exported_energy",  # Total exported energy
    "grid_accumulated_energy",  # Total imported energy
    "storage_current_day_charge_capacity",  # Charged today
    "storage_current_day_discharge_capacity",  # Discharged today
    "storage_total_charge",  # Total charged (lifetime)
    "storage_total_discharge",  # Total discharged (lifetime)
    #
    # PV strings (up to 4 strings)
    "pv_01_voltage",
    "pv_01_current",
    "pv_02_voltage",
    "pv_02_current",
    "pv_03_voltage",  # Optional: Larger inverters only
    "pv_03_current",
    "pv_04_voltage",  # Optional: Larger inverters only
    "pv_04_current",
    #
    # Battery details
    "storage_bus_voltage",
    "storage_bus_current",
    "storage_running_status",  # 0=offline, 1=standby, 2=running, 3=fault
    #
    # Grid phases
    "grid_A_voltage",  # Phase-to-neutral
    "grid_B_voltage",  # 3-phase only
    "grid_C_voltage",  # 3-phase only
    "line_voltage_A_B",  # Line-to-line
    "line_voltage_B_C",
    "line_voltage_C_A",
    "grid_frequency",  # Hz (50 EU, 60 US)
    #
    # Smart meter (optional: SDongleA/DDSU666 required)
    "meter_status",  # 0=offline, 1=normal
    "power_meter_reactive_power",
    "active_grid_A_current",
    "active_grid_B_current",
    "active_grid_C_current",
    "active_grid_A_B_voltage",
    "active_grid_B_C_voltage",
    "active_grid_C_A_voltage",
    "active_grid_A_power",
    "active_grid_B_power",
    "active_grid_C_power",
    "active_grid_frequency",
    "active_grid_power_factor",
    #
    # Inverter diagnostics
    "internal_temperature",  # °C
    "day_active_power_peak",  # Max power today
    "power_factor",  # cos φ
    "efficiency",  # % (DC→AC conversion)
    "reactive_power",  # var
    "insulation_resistance",  # MΩ
    "device_status",  # Status code (see Huawei docs)
    "state_1",  # Status bitfield 1
    "state_2",  # Status bitfield 2
    #
    # Device information (static)
    "model_name",
    "serial_number",
    "rated_power",  # W
    "startup_time",  # Timestamp
    #
    # Alarm & Diagnostik
    "alarm_1",  # Alarm Bitfeld 1
    "alarm_2",  # Alarm Bitfeld 2
    "alarm_3",  # Alarm Bitfeld 3
    #
    # Optimizer (falls vorhanden)
    "nb_optimizers",  # Anzahl Optimizer
    "nb_online_optimizers",  # Online Optimizer
    #
    # Batterie Limits
    "storage_maximum_charge_power",  # Max Charge Power
    "storage_maximum_discharge_power",  # Max Discharge Power
    #
    # Multi-Modul Batterie (optional)
    "storage_unit_1_soc",  # Nur bei Multi-Modul
    "storage_unit_2_soc",
    "storage_unit_3_soc",
]
