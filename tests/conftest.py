# tests/conftest.py

"""Pytest Configuration"""

import sys
from pathlib import Path

# Füge den huawei_solar_modbus_mqtt Ordner hinzu
addon_path = Path(__file__).parent.parent / "huawei_solar_modbus_mqtt"
sys.path.insert(0, str(addon_path))

print(f"✅ conftest.py loaded! Added to sys.path: {addon_path}")
