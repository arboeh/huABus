"""Integration-Tests mit Mock-Inverter"""

import sys
from pathlib import Path

import pytest  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent / "huawei-solar-modbus-mqtt"))

from modbus_energy_meter.total_increasing_filter import (
    get_filter,
    reset_filter,
)

from tests.fixtures.mock_inverter import MockHuaweiSolar


@pytest.mark.asyncio
async def test_meter_change_scenario():
    """Test: HANT's Szenario - Meter-Wechsel, 0.03 kWh muss durchkommen"""
    # Setup
    reset_filter()
    mock = MockHuaweiSolar()
    mock.load_scenario("meter_change")
    filter_instance = get_filter()

    results = []

    # 3 Cycles durchlaufen
    for _ in range(3):
        register = await mock.get("energy_grid_exported")
        value = register.value

        # Filter anwenden
        if not filter_instance.should_filter("energy_grid_exported", value):
            results.append(value)
        else:
            last = filter_instance.get_last_value("energy_grid_exported")
            results.append(last)

        mock.next_cycle()

    # Assertions
    assert results[0] == 0, "Installation: 0 sollte akzeptiert werden"
    assert results[1] == 0.03, "KRITISCH: 0.03 kWh muss durchkommen (HANT's Szenario)!"
    assert results[2] == 0.15, "Normale Werte sollten durchkommen"


@pytest.mark.asyncio
async def test_modbus_errors_filtered():
    """Test: Modbus-Fehler (Drops auf 0) werden gefiltert"""
    reset_filter()
    mock = MockHuaweiSolar()
    mock.load_scenario("modbus_errors")
    filter_instance = get_filter()

    results = []

    for _ in range(3):
        register = await mock.get("energy_grid_exported")
        value = register.value

        if not filter_instance.should_filter("energy_grid_exported", value):
            results.append(value)
        else:
            last = filter_instance.get_last_value("energy_grid_exported")
            results.append(last)

        mock.next_cycle()

    # Assertions
    assert results[0] == 5432.1, "Normaler Wert"
    assert results[1] == 5432.1, "Drop auf 0 gefiltert → letzter Wert bleibt"
    assert results[2] == 5432.8, "Nach Fehler wieder normal"


@pytest.mark.asyncio
async def test_tolerance_edge_cases():
    """Test: 5% Toleranz-Grenze korrekt"""
    reset_filter()
    mock = MockHuaweiSolar()
    mock.load_scenario("tolerance_edge")
    filter_instance = get_filter()

    results = []

    for _ in range(4):
        register = await mock.get("energy_grid_exported")
        value = register.value

        if not filter_instance.should_filter("energy_grid_exported", value):
            results.append(value)
        else:
            last = filter_instance.get_last_value("energy_grid_exported")
            results.append(last)

        mock.next_cycle()

    # Assertions
    assert results[0] == 10000.0, "Baseline"
    assert results[1] == 9510.0, "4.9% Drop → akzeptiert (innerhalb Toleranz)"
    assert results[2] == 10000.0, "Zurück zu Baseline"
    assert results[3] == 10000.0, "5.1% Drop → gefiltert (außerhalb Toleranz)"


@pytest.mark.asyncio
async def test_negative_values_scenario():
    """Test: Negative Werte werden gefiltert"""
    reset_filter()
    mock = MockHuaweiSolar()
    mock.load_scenario("negative_values")
    filter_instance = get_filter()

    results = []

    for _ in range(3):
        register = await mock.get("energy_grid_exported")
        value = register.value

        if not filter_instance.should_filter("energy_grid_exported", value):
            results.append(value)
        else:
            last = filter_instance.get_last_value("energy_grid_exported")
            results.append(last)

        mock.next_cycle()

    # Assertions
    assert results[0] == 5432.1, "Normaler Wert"
    assert results[1] == 5432.1, "Negativer Wert gefiltert"
    assert results[2] == 5432.8, "Wieder positiv"
