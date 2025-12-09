# transform.py
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("huawei.transform")


def get_value(register_value: Any) -> Optional[Any]:
    """Extract value from register object safely and filter invalid Modbus values."""
    if register_value is None:
        return None

    try:
        # Extract value
        if hasattr(register_value, 'value'):
            value = register_value.value

            if hasattr(value, 'name'):  # Enum
                return value.name
            if hasattr(value, 'isoformat'):  # Datetime
                return value.isoformat()
        else:
            value = register_value

        # Filter invalid Modbus values (silent)
        if isinstance(value, (int, float)):
            # Common Modbus "not available" markers
            if value in (65535, 32767, -32768):
                return None

        return value

    except Exception as e:
        logger.warning(
            f"Value extract failed: {type(register_value).__name__}: {e}")
        return None


def transform_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform Huawei register data to MQTT format."""
    logger.debug(f"Transforming {len(data)} registers")
    start = time.time()

    # Complete register → MQTT key mapping
    mapping = {
        # Power
        'active_power': 'power_active',
        'input_power': 'power_input',
        'day_active_power_peak': 'power_active_peak_day',
        'reactive_power': 'power_reactive',

        # Energy
        'daily_yield_energy': 'energy_yield_day',
        'accumulated_yield_energy': 'energy_yield_accumulated',
        'grid_exported_energy': 'energy_grid_exported',
        'grid_accumulated_energy': 'energy_grid_accumulated',
        'grid_accumulated_reactive_power': 'energy_grid_accumulated_reactive',

        # PV Strings
        'pv_01_power': 'power_PV1',
        'pv_01_voltage': 'voltage_PV1',
        'pv_01_current': 'current_PV1',
        'pv_02_power': 'power_PV2',
        'pv_02_voltage': 'voltage_PV2',
        'pv_02_current': 'current_PV2',
        'pv_03_power': 'power_PV3',
        'pv_03_voltage': 'voltage_PV3',
        'pv_03_current': 'current_PV3',
        'pv_04_power': 'power_PV4',
        'pv_04_voltage': 'voltage_PV4',
        'pv_04_current': 'current_PV4',

        # Grid (3-phase)
        'grid_A_voltage': 'voltage_grid_A',
        'grid_A_current': 'current_grid_A',
        'phase_A_active_power': 'power_grid_A',
        'grid_B_voltage': 'voltage_grid_B',
        'grid_B_current': 'current_grid_B',
        'phase_B_active_power': 'power_grid_B',
        'grid_C_voltage': 'voltage_grid_C',
        'grid_C_current': 'current_grid_C',
        'phase_C_active_power': 'power_grid_C',
        'grid_frequency': 'frequency_grid',
        'line_voltage_A_B': 'voltage_line_AB',
        'line_voltage_B_C': 'voltage_line_BC',
        'line_voltage_C_A': 'voltage_line_CA',

        # Power Meter
        'active_grid_power_peak': 'meter_power_active',

        # Battery
        'storage_state_of_capacity': 'battery_soc',
        'storage_charge_discharge_power': 'battery_power',
        'storage_bus_voltage': 'battery_bus_voltage',
        'storage_bus_current': 'battery_bus_current',
        'storage_day_charge': 'battery_charge_day',
        'storage_day_discharge': 'battery_discharge_day',
        'storage_total_charge': 'battery_charge_total',
        'storage_total_discharge': 'battery_discharge_total',

        # Status
        'device_status': 'inverter_status',
        'state_1': 'inverter_state_1',
        'state_2': 'inverter_state_2',
        'state_3': 'inverter_state_3',
        'startup_time': 'inverter_startup_time',
        'storage_status': 'battery_status',
        'meter_status': 'meter_status',

        # Inverter metrics
        'internal_temperature': 'inverter_temperature',
        'efficiency': 'inverter_efficiency',
        'insulation_resistance': 'inverter_insulation_resistance',
        'power_factor': 'power_factor',
    }

    # Transform with mapping
    result = {mqtt_key: get_value(data.get(register_key))
              for register_key, mqtt_key in mapping.items()}

    # Critical keys must never be None (EVCC, etc.)
    critical_defaults = {
        'power_active': 0,
        'power_input': 0,
        'meter_power_active': 0,
        'battery_power': 0,
        'battery_soc': 0
    }

    for key, default in critical_defaults.items():
        if result.get(key) is None:
            logger.warning(f"Critical '{key}' missing, using {default}")
            result[key] = default

    # Clean up result
    result = _cleanup_result(result)

    duration = time.time() - start
    logger.debug(f"Transform complete: {len(result)} values ({duration:.3f}s)")

    return result


def _cleanup_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values and convert complex types to str."""
    cleaned = {}

    for key, value in data.items():
        if value is None:
            continue

        # Special handling for lists (inverter states)
        if isinstance(value, list):
            logger.debug(f"Converting {key}: list → str")
            value = ','.join(str(v)
                             for v in value if v)  # Join non-empty values
            if not value:  # Empty list or all None
                continue

        elif not isinstance(value, (int, float, str, bool)):
            logger.debug(f"Converting {key}: {type(value).__name__} → str")
            value = str(value)

        cleaned[key] = value

    return cleaned
