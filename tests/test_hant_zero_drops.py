# tests/test_hant_zero_drops.py

"""
Tests für HANTs gemeldetes Problem: Zero Drops (Secondary Issue)
GitHub Issue: #7 - Secondary: Zero values from Modbus errors
"""

import pytest  # type: ignore
from modbus_energy_meter.total_increasing_filter import get_filter, reset_filter

from tests.fixtures.mock_inverter import MockHuaweiSolar
from tests.fixtures.mock_mqtt_broker import MockMQTTBroker


@pytest.mark.asyncio
async def test_hant_zero_drop_after_read_error():
    """
    HANT Issue #7 - Secondary: Zero values from Modbus errors

    Scenario:
    1. Normal operation: 9799.50 kWh
    2. Modbus error returns 0 (not timeout, but invalid value)
    3. Filter must replace with last valid value
    """
    reset_filter()
    filter_instance = get_filter()

    # Cycle 1: Normal
    data1 = {"energy_grid_exported": 9799.50}
    result1 = filter_instance.filter(data1)
    assert result1["energy_grid_exported"] == 9799.50

    # Cycle 2: Zero drop (Modbus error)
    data2 = {"energy_grid_exported": 0}  # Key exists, but invalid!
    result2 = filter_instance.filter(data2)

    # ✅ Filter must replace zero
    assert result2["energy_grid_exported"] == 9799.50

    print("✅ HANT Test: Zero drop filtered")


@pytest.mark.asyncio
async def test_hant_legitimate_zero_on_first_read():
    """
    Edge Case: Legitimer Zero-Wert beim ersten Read

    Scenario:
    - System startet
    - Erste Werte sind tatsächlich 0 (z.B. nachts, keine Batterie)

    Filter sollte 0 als ersten Wert akzeptieren!
    """
    reset_filter()
    filter_instance = get_filter()

    # Cycle 1: Erste Werte sind 0 (legitim!)
    data1 = {
        "battery_charge_total": 0,  # Noch nie geladen
        "battery_discharge_total": 0,  # Noch nie entladen
    }
    result1 = filter_instance.filter(data1)

    # ✅ Erste Werte müssen akzeptiert werden (auch wenn 0)
    assert result1["battery_charge_total"] == 0
    assert result1["battery_discharge_total"] == 0

    # Cycle 2: Werte steigen
    data2 = {
        "battery_charge_total": 1.5,
        "battery_discharge_total": 0.8,
    }
    result2 = filter_instance.filter(data2)

    assert result2["battery_charge_total"] == 1.5
    assert result2["battery_discharge_total"] == 0.8

    # Cycle 3: Zero-Drop (jetzt invalid!)
    data3 = {
        "battery_charge_total": 0,  # Drop zurück auf 0!
        "battery_discharge_total": 0,
    }
    result3 = filter_instance.filter(data3)

    # ✅ Jetzt muss gefiltert werden
    assert result3["battery_charge_total"] == 1.5  # Last valid
    assert result3["battery_discharge_total"] == 0.8

    print("✅ HANT Test: Legitimate zero on first read, invalid zero filtered later")


@pytest.mark.asyncio
async def test_hant_negative_value_drops():
    """
    Zusätzlich zu Zero: Auch negative Werte müssen gefiltert werden

    total_increasing Sensoren dürfen NIEMALS fallen!
    """
    reset_filter()
    filter_instance = get_filter()

    # Cycle 1: Normal
    data1 = {"energy_grid_exported": 9799.50}
    filter_instance.filter(data1)

    # Cycle 2: Negativer Wert (Modbus-Fehler)
    data2 = {"energy_grid_exported": -123.45}
    result2 = filter_instance.filter(data2)

    # ✅ Negativer Wert muss gefiltert werden
    assert result2["energy_grid_exported"] == 9799.50

    # Cycle 3: Rückgang (vereinfachter Filter filtert JEDEN Rückgang)
    data3 = {"energy_grid_exported": 9300.00}  # -499.50 kWh
    result3 = filter_instance.filter(data3)

    # ✅ Rückgang muss gefiltert werden
    assert result3["energy_grid_exported"] == 9799.50

    print("✅ HANT Test: Negative values and drops filtered")


@pytest.mark.asyncio
async def test_hant_zero_drop_statistics():
    """
    Filter-Statistiken für Zero-Drops

    Prüft ob Filter korrekt zählt wie viele Werte gefiltert wurden
    """
    reset_filter()
    filter_instance = get_filter()

    # Cycle 1: Normal
    data1 = {
        "energy_grid_exported": 9799.50,
        "energy_yield_accumulated": 18052.68,
    }
    filter_instance.filter(data1)

    # Initial: Keine Filterungen
    stats = filter_instance.get_stats()
    assert stats.get("energy_grid_exported", 0) == 0
    assert stats.get("energy_yield_accumulated", 0) == 0

    # Cycle 2: Beide Sensoren zero-drop
    data2 = {
        "energy_grid_exported": 0,
        "energy_yield_accumulated": 0,
    }
    filter_instance.filter(data2)

    # Nach Filterung: Beide gezählt
    stats = filter_instance.get_stats()
    assert stats["energy_grid_exported"] == 1
    assert stats["energy_yield_accumulated"] == 1

    # Cycle 3: Nur ein Sensor zero-drop
    data3 = {
        "energy_grid_exported": 0,  # Zero
        "energy_yield_accumulated": 18053.20,  # Valid
    }
    filter_instance.filter(data3)

    # Statistiken aktualisiert
    stats = filter_instance.get_stats()
    assert stats["energy_grid_exported"] == 2  # 2x gefiltert
    assert stats["energy_yield_accumulated"] == 1  # Immer noch 1x

    print(f"✅ HANT Test: Filter statistics correct: {stats}")


@pytest.mark.asyncio
async def test_hant_zero_drop_e2e_with_mock():
    """
    End-to-End Test: Zero-Drops mit Mock Inverter
    """
    reset_filter()
    mock_modbus = MockHuaweiSolar()
    mock_modbus.load_scenario("zero_drop_errors")
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)
    filter_instance = get_filter()

    mqtt_values = []

    for cycle in range(6):
        register = await mock_modbus.get("energy_grid_exported")
        raw_value = register.value

        # Filter
        filtered = filter_instance.filter({"energy_grid_exported": raw_value})
        mqtt_value = filtered["energy_grid_exported"]

        # Publish zu MQTT
        mock_mqtt.publish("huawei-solar", str(filtered))
        mqtt_values.append(mqtt_value)

        mock_modbus.next_cycle()

    # ✅ Prüfe: Keine Zeros in MQTT-Werten (außer legitimer erster Wert)
    for i, value in enumerate(mqtt_values):
        if i > 0:  # Nach erstem Wert
            assert value > 0, f"Cycle {i}: Zero value reached MQTT! {mqtt_values}"

    # ✅ Prüfe: Werte monoton steigend (oder gleich)
    for i in range(1, len(mqtt_values)):
        assert (
            mqtt_values[i] >= mqtt_values[i - 1]
        ), f"Value dropped: {mqtt_values[i-1]} → {mqtt_values[i]}"

    print(f"✅ HANT E2E Test: No zeros in MQTT, values: {mqtt_values}")


@pytest.mark.asyncio
async def test_hant_after_midnight_reset():
    """
    Edge Case: Counter-Reset um Mitternacht

    Manche Sensoren (energy_yield_day) resetten täglich.
    Diese sollten 0 akzeptieren, aber nur als "expected reset".

    (Aktuell werden daily-Counter NICHT gefiltert - nur total_increasing!)
    """
    reset_filter()
    filter_instance = get_filter()

    # Diese Sensoren sollten NICHT im TOTAL_INCREASING_KEYS sein
    assert "energy_yield_day" not in filter_instance.TOTAL_INCREASING_KEYS
    assert "battery_charge_day" not in filter_instance.TOTAL_INCREASING_KEYS

    # Cycle 1: Tageswerte
    data1 = {
        "energy_yield_day": 25.5,  # Daily counter
        "energy_yield_accumulated": 18052.68,  # Total counter
    }
    result1 = filter_instance.filter(data1)
    assert result1["energy_yield_day"] == 25.5
    assert result1["energy_yield_accumulated"] == 18052.68

    # Cycle 2: Midnight reset
    data2 = {
        "energy_yield_day": 0,  # Reset auf 0 (LEGITIM!)
        "energy_yield_accumulated": 18053.00,  # Weiter steigend
    }
    result2 = filter_instance.filter(data2)

    # ✅ Daily-Counter-Reset wird durchgelassen (nicht gefiltert)
    assert result2["energy_yield_day"] == 0  # Durchgelassen

    # ✅ Total-Counter wird normal behandelt
    assert result2["energy_yield_accumulated"] == 18053.00

    print("✅ HANT Test: Daily counter reset allowed, total counter protected")


@pytest.mark.asyncio
async def test_hant_utility_meter_with_zero_drops():
    """
    Simuliert was HA Utility Meter bei Zero-Drops sieht

    OHNE Filter: Utility Meter würde springen
    MIT Filter: Utility Meter stabil
    """
    reset_filter()
    filter_instance = get_filter()

    # Simuliere Utility Meter Tracking
    utility_meter_value = 0.0
    utility_meter_readings = []

    test_data = [
        9799.50,  # Cycle 1
        9800.20,  # Cycle 2: +0.7 kWh
        0,  # Cycle 3: Zero-drop! (OHNE Filter würde springen)
        9801.00,  # Cycle 4: +0.8 kWh
        0,  # Cycle 5: Nochmal Zero-drop!
        9801.50,  # Cycle 6: +0.5 kWh
    ]

    last_value = 0.0
    for raw_value in test_data:
        # Filter
        filtered = filter_instance.filter({"energy_grid_exported": raw_value})
        mqtt_value = filtered["energy_grid_exported"]

        # Simuliere Utility Meter (berechnet Differenz)
        if last_value > 0:
            delta = mqtt_value - last_value
            if delta >= 0:  # Utility Meter ignoriert Rückgänge
                utility_meter_value += delta

        utility_meter_readings.append(utility_meter_value)
        last_value = mqtt_value

    # ✅ Utility Meter sollte korrekte Summe haben
    # Total increase: 0.7 + 0.8 + 0.5 = 2.0 kWh
    expected_total = 2.0
    assert (
        abs(utility_meter_readings[-1] - expected_total) < 0.1
    ), f"Utility Meter incorrect: {utility_meter_readings[-1]} vs {expected_total}"

    print(
        f"✅ HANT Test: Utility Meter stable with zero-drops: {utility_meter_readings}"
    )
