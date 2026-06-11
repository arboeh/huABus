# tests/test_integration.py

"""Integration-Tests mit Mock-Inverter"""

import pytest
from bridge.total_increasing_filter import get_filter

from tests.fixtures.mock_inverter import MockHuaweiSolar

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _run_scenario(scenario: str, register: str, cycles: int) -> list:
    """Läuft n Cycles eines Szenarios und gibt gefilterte Werte zurück."""
    mock = MockHuaweiSolar()
    mock.load_scenario(scenario)
    instance = get_filter()
    results = []
    for _ in range(cycles):
        reg = await mock.get(register)
        filtered = instance.filter({register: reg.value})
        results.append(filtered[register])
        mock.next_cycle()
    return results


# ---------------------------------------------------------------------------
# TestScenarios
# ---------------------------------------------------------------------------


class TestScenarios:
    """Integration-Tests mit vordefinierten Mock-Inverter-Szenarien."""

    @pytest.mark.asyncio
    async def test_meter_change_small_values_pass_through(self):
        """Kleine Werte nach Meter-Wechsel (0.03 kWh) werden nicht gefiltert."""
        results = await _run_scenario("meter_change", "energy_grid_exported", 3)

        assert results[0] == 0, "Installation: 0 muss akzeptiert werden"
        assert results[1] == 0.03, "KRITISCH: 0.03 kWh muss durchkommen!"
        assert results[2] == 0.15, "Normale Werte müssen durchkommen"

    @pytest.mark.asyncio
    async def test_modbus_error_zero_drop_is_filtered(self):
        """Zero-Drop durch Modbus-Fehler wird durch letzten gültigen Wert ersetzt."""
        results = await _run_scenario("modbus_errors", "energy_grid_exported", 3)

        assert results[0] == 5432.1, "Normaler Wert"
        assert results[1] == 5432.1, "Drop auf 0 gefiltert → letzter Wert bleibt"
        assert results[2] == 5432.8, "Nach Fehler wieder normal"

    @pytest.mark.asyncio
    async def test_negative_values_are_filtered(self):
        """Negative Werte werden durch letzten gültigen Wert ersetzt."""
        results = await _run_scenario("negative_values", "energy_grid_exported", 3)

        assert results[0] == 5432.1, "Normaler Wert"
        assert results[1] == 5432.1, "Negativer Wert gefiltert"
        assert results[2] == 5432.8, "Wieder positiv"


# ---------------------------------------------------------------------------
# TestMultipleSensors
# ---------------------------------------------------------------------------


class TestMultipleSensors:
    """Tests für unabhängiges Filtern mehrerer Sensoren."""

    @pytest.mark.asyncio
    async def test_sensors_filtered_independently(self):
        """Jeder Sensor hat einen eigenen Filter-Zustand."""
        instance = get_filter()

        result1 = instance.filter(
            {
                "energy_grid_exported": 5432.1,
                "battery_charge_total": 1234.5,
            }
        )
        assert result1["energy_grid_exported"] == 5432.1
        assert result1["battery_charge_total"] == 1234.5

        result2 = instance.filter(
            {
                "energy_grid_exported": 0,  # Drop → gefiltert
                "battery_charge_total": 1235.0,  # Steigt → akzeptiert
            }
        )
        assert result2["energy_grid_exported"] == 5432.1
        assert result2["battery_charge_total"] == 1235.0

        result3 = instance.filter(
            {
                "energy_grid_exported": 5432.8,
                "battery_charge_total": 1235.5,
            }
        )
        assert result3["energy_grid_exported"] == 5432.8
        assert result3["battery_charge_total"] == 1235.5
