# tests\test_integration.py

"""Integration-Tests mit Mock-Inverter"""

import pytest  # type: ignore
from bridge.total_increasing_filter import (
    get_filter,
    reset_filter,
)

from tests.fixtures.mock_inverter import MockHuaweiSolar


@pytest.mark.asyncio
async def test_meter_change_scenario():
    """Test: Meter-Wechsel - kleine Werte (0.03 kWh) müssen durchkommen"""
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
        data = {"energy_grid_exported": value}
        filtered = filter_instance.filter(data)
        results.append(filtered["energy_grid_exported"])

        mock.next_cycle()

    # Assertions
    assert results[0] == 0, "Installation: 0 sollte akzeptiert werden"
    assert results[1] == 0.03, "KRITISCH: 0.03 kWh muss durchkommen!"
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

        # Filter anwenden
        data = {"energy_grid_exported": value}
        filtered = filter_instance.filter(data)
        results.append(filtered["energy_grid_exported"])

        mock.next_cycle()

    # Assertions
    assert results[0] == 5432.1, "Normaler Wert"
    assert results[1] == 5432.1, "Drop auf 0 gefiltert → letzter Wert bleibt"
    assert results[2] == 5432.8, "Nach Fehler wieder normal"


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

        # Filter anwenden
        data = {"energy_grid_exported": value}
        filtered = filter_instance.filter(data)
        results.append(filtered["energy_grid_exported"])

        mock.next_cycle()

    # Assertions
    assert results[0] == 5432.1, "Normaler Wert"
    assert results[1] == 5432.1, "Negativer Wert gefiltert"
    assert results[2] == 5432.8, "Wieder positiv"


@pytest.mark.asyncio
async def test_multiple_sensors_filtered_independently():
    """Test: Mehrere Sensoren werden unabhängig gefiltert"""
    reset_filter()
    filter_instance = get_filter()

    # Cycle 1: Beide Sensoren normal
    data1 = {
        "energy_grid_exported": 5432.1,
        "battery_charge_total": 1234.5,
    }
    result1 = filter_instance.filter(data1)
    assert result1["energy_grid_exported"] == 5432.1
    assert result1["battery_charge_total"] == 1234.5

    # Cycle 2: Ein Sensor droppt auf 0, anderer steigt
    data2 = {
        "energy_grid_exported": 0,  # Drop!
        "battery_charge_total": 1235.0,  # Steigt
    }
    result2 = filter_instance.filter(data2)
    assert result2["energy_grid_exported"] == 5432.1  # Gefiltert
    assert result2["battery_charge_total"] == 1235.0  # Akzeptiert

    # Cycle 3: Beide wieder normal
    data3 = {
        "energy_grid_exported": 5432.8,
        "battery_charge_total": 1235.5,
    }
    result3 = filter_instance.filter(data3)
    assert result3["energy_grid_exported"] == 5432.8
    assert result3["battery_charge_total"] == 1235.5
