# tests\fixtures\mock_inverter.py

"""Mock für AsyncHuaweiSolar mit Test-Szenarien"""

from pathlib import Path
from typing import Any, cast

import yaml


class MockRegisterValue:
    """Simuliert RegisterValue-Objekt von huawei-solar"""

    def __init__(self, value, unit=""):
        self.value = value
        self.unit = unit


class ModbusException(Exception):  # noqa: N818
    """Mock für Modbus-Exception"""

    pass


class MockHuaweiSolar:
    """Mock für AsyncHuaweiSolar mit konfigurierbaren Szenarien"""

    def __init__(self, scenario_file: str | None = None):
        if scenario_file is None:
            scenario_file = str(Path(__file__).parent / "scenarios.yaml")

        self.scenario_file = scenario_file
        self.cycle = 0
        self.scenarios = self._load_scenarios()
        self.current_scenario = None

    def _load_scenarios(self) -> dict[str, Any]:
        """Lädt Test-Szenarien aus YAML"""
        with open(self.scenario_file, encoding="utf-8") as f:
            return cast(dict[str, Any], yaml.safe_load(f))

    def load_scenario(self, name: str):
        """Aktiviert ein Test-Szenario"""
        if name not in self.scenarios:
            raise ValueError(f"Scenario '{name}' not found. Available: {list(self.scenarios.keys())}")

        self.current_scenario = self.scenarios[name]
        self.cycle = 0

    async def get(self, register_name: str):
        """Simuliert Modbus-Read mit konfigurierten Werten/Fehlern"""
        if not self.current_scenario:
            raise ValueError("No scenario loaded! Call load_scenario() first")

        cycles = self.current_scenario["cycles"]
        cycle_data = cycles[min(self.cycle, len(cycles) - 1)]

        # NEU: Simuliere Modbus-Fehler (errors-Liste)
        if register_name in cycle_data.get("errors", []):
            raise ModbusException(f"Simulated timeout for {register_name}")

        # NEU: Simuliere Register-Timeout (Key fehlt komplett im Payload)
        if register_name not in cycle_data:
            # Option A: Exception werfen (realistisch)
            raise TimeoutError(f"Register {register_name} not available (timeout)")

            # Option B: None zurückgeben (caller muss behandeln)
            # return None

        # Gebe konfigurierten Wert zurück
        value = cycle_data[register_name]
        return MockRegisterValue(value)

    def next_cycle(self):
        """Nächster Cycle für Tests"""
        self.cycle += 1
