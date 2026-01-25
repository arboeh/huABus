# modbus_energy_meter/transform.py
import logging
import time
from typing import Optional, Dict, Any

from .config.mappings import REGISTER_MAPPING, CRITICAL_DEFAULTS

logger = logging.getLogger("huawei.transform")


def transform_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform Huawei register data to MQTT format."""
    logger.debug(f"Transforming {len(data)} registers")
    start = time.time()

    # Transform with mapping
    result = {
        mqtt_key: get_value(data.get(register_key))
        for register_key, mqtt_key in REGISTER_MAPPING.items()
    }

    # Critical defaults for missing keys
    for key, default in CRITICAL_DEFAULTS.items():
        if result.get(key) is None:
            logger.warning(f"Critical '{key}' missing, using {default}")
            result[key] = default

    # Clean up result
    result = _cleanup_result(result)

    duration = time.time() - start
    logger.debug(f"Transform complete: {len(result)} values ({duration:.3f}s)")

    return result


def get_value(register_value: Any) -> Optional[Any]:
    """Extract value from register object safely and filter invalid Modbus values."""
    if register_value is None:
        return None

    try:
        # Extract value
        if hasattr(register_value, "value"):
            value = register_value.value

            if hasattr(value, "name"):  # Enum
                return value.name
            if hasattr(value, "isoformat"):  # Datetime
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
        logger.warning(f"Value extract failed: {type(register_value).__name__}: {e}")
        return None


def _cleanup_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values and convert complex types to str."""
    cleaned = {}

    for key, value in data.items():
        if value is None:
            continue

        # Special handling for lists (inverter states)
        if isinstance(value, list):
            logger.debug(f"Converting {key}: list → str")
            value = ",".join(str(v) for v in value if v)  # Join non-empty values
            if not value:  # Empty list or all None
                continue

        elif not isinstance(value, (int, float, str, bool)):
            logger.debug(f"Converting {key}: {type(value).__name__} → str")
            value = str(value)

        cleaned[key] = value

    return cleaned
