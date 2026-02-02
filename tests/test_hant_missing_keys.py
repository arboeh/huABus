# tests/test_hant_missing_keys.py

"""
Tests für HANTs gemeldetes Problem: Missing Keys bei Register-Timeouts
GitHub Issue: #7 - Root Cause: Missing keys from register timeouts
"""

import pytest  # type: ignore
from modbus_energy_meter.total_increasing_filter import (
    get_filter,
    reset_filter,
)

from tests.fixtures.mock_inverter import MockHuaweiSolar
from tests.fixtures.mock_mqtt_broker import MockMQTTBroker


@pytest.mark.asyncio
async def test_hant_missing_key_after_timeout():
    """
    HANT Issue #7 - Root Cause: Register timeout → key missing from payload

    Scenario:
    1. Cycle 1: Normal operation with all keys
    2. Cycle 2: Register timeout → energy_grid_exported MISSING
    3. Filter must insert last valid value
    4. MQTT payload complete → HA Utility Meter safe
    """
    reset_filter()
    filter_instance = get_filter()

    # Cycle 1: Normal - beide Keys vorhanden
    data1 = {
        "energy_grid_exported": 9799.50,
        "energy_yield_accumulated": 18052.68,
    }
    result1 = filter_instance.filter(data1)

    assert "energy_grid_exported" in result1
    assert result1["energy_grid_exported"] == 9799.50
    assert "energy_yield_accumulated" in result1
    assert result1["energy_yield_accumulated"] == 18052.68

    # Cycle 2: Register timeout → energy_grid_exported FEHLT!
    data2 = {
        # energy_grid_exported MISSING (timeout!)
        "energy_yield_accumulated": 18053.20,
    }
    result2 = filter_instance.filter(data2)

    # ✅ Filter muss fehlenden Key mit last valid value füllen!
    assert "energy_grid_exported" in result2, "Missing key must be filled!"
    assert result2["energy_grid_exported"] == 9799.50, "Must use last valid value!"
    assert result2["energy_yield_accumulated"] == 18053.20

    print("✅ HANT Test: Missing key filled with last valid value")


@pytest.mark.asyncio
async def test_hant_missing_key_without_previous_value():
    """
    Edge Case: Key fehlt, aber noch nie gesehen (kein last_value)

    Scenario:
    - Cycle 1: Key fehlt (Register timeout beim ersten Read)
    - Cycle 2: Key kommt zurück
    - Cycle 3: Key fehlt wieder
    """
    reset_filter()
    filter_instance = get_filter()

    # Cycle 1: Key fehlt - noch nie gesehen
    data1 = {
        "energy_yield_accumulated": 18052.68,
        # energy_grid_exported FEHLT (und noch nie gesehen!)
    }
    result1 = filter_instance.filter(data1)

    # Key sollte NICHT ergänzt werden (kein last_value vorhanden)
    assert "energy_grid_exported" not in result1

    # Cycle 2: Key erscheint
    data2 = {
        "energy_yield_accumulated": 18053.20,
        "energy_grid_exported": 9799.50,  # Jetzt da!
    }
    result2 = filter_instance.filter(data2)

    assert result2["energy_grid_exported"] == 9799.50

    # Cycle 3: Key fehlt wieder
    data3 = {
        "energy_yield_accumulated": 18054.00,
        # energy_grid_exported fehlt wieder
    }
    result3 = filter_instance.filter(data3)

    # Jetzt MUSS Key ergänzt werden (last_value = 9799.50)
    assert "energy_grid_exported" in result3
    assert result3["energy_grid_exported"] == 9799.50

    print("✅ HANT Test: Missing key without previous value handled correctly")


@pytest.mark.asyncio
async def test_hant_missing_and_invalid_combined():
    """
    Real-World Scenario: Gleichzeitig fehlende UND invalide Werte

    Scenario:
    - Key A: fehlt (timeout)
    - Key B: invalid value (0)
    - Key C: valid value

    Filter muss beide Fälle behandeln
    """
    reset_filter()
    filter_instance = get_filter()

    # Cycle 1: Alle valid
    data1 = {
        "energy_grid_exported": 9799.50,
        "energy_yield_accumulated": 18052.68,
        "battery_charge_total": 1234.56,
    }
    filter_instance.filter(data1)

    # Cycle 2: Gemischte Probleme
    data2 = {
        # energy_grid_exported FEHLT (timeout)
        "energy_yield_accumulated": 0,  # Invalid (zero drop)
        "battery_charge_total": 1234.60,  # Valid
    }
    result2 = filter_instance.filter(data2)

    # ✅ Fehlender Key gefüllt
    assert "energy_grid_exported" in result2
    assert result2["energy_grid_exported"] == 9799.50

    # ✅ Invalider Wert gefiltert
    assert result2["energy_yield_accumulated"] == 18052.68  # Last valid

    # ✅ Valider Wert durchgelassen
    assert result2["battery_charge_total"] == 1234.60

    print("✅ HANT Test: Missing and invalid values handled together")


@pytest.mark.asyncio
async def test_hant_e2e_with_mock_inverter():
    """
    End-to-End Test mit Mock Inverter:
    Simuliert kompletten Cycle mit Register-Timeouts
    """
    reset_filter()
    mock_modbus = MockHuaweiSolar()
    mock_modbus.load_scenario("register_timeouts")
    filter_instance = get_filter()

    mqtt_payloads = []

    for cycle in range(3):
        # Read all registers (some may timeout → missing keys)
        raw_data = {}

        try:
            reg = await mock_modbus.get("energy_grid_exported")
            if reg.value != 65535:  # Not timeout
                raw_data["energy_grid_exported"] = reg.value
        except Exception:
            pass  # Timeout → key missing

        try:
            reg = await mock_modbus.get("energy_yield_accumulated")
            if reg.value != 65535:
                raw_data["energy_yield_accumulated"] = reg.value
        except Exception:
            pass

        # Filter (muss fehlende Keys füllen!)
        filtered_data = filter_instance.filter(raw_data)

        mqtt_payloads.append(filtered_data)
        mock_modbus.next_cycle()

    # ✅ Alle Payloads müssen vollständig sein
    for i, payload in enumerate(mqtt_payloads):
        if i > 0:  # Ab Cycle 2 (haben last_values)
            assert "energy_grid_exported" in payload, f"Cycle {i}: Key missing!"
            assert "energy_yield_accumulated" in payload, f"Cycle {i}: Key missing!"

    print(f"✅ HANT E2E Test: All payloads complete: {mqtt_payloads}")


@pytest.mark.asyncio
async def test_hant_addon_restart_scenario():
    """
    HANT's Problem: Add-on restart → Sensor unavailable → Returns with value

    Szenario:
    1. Normaler Betrieb: 5432.1 kWh
    2. Add-on restart → Filter reset
    3. Sensor kommt zurück: 5433.5 kWh

    Erwartung:
    - Filter akzeptiert 5433.5 als "first value" nach Reset
    - MQTT empfängt: 5432.1 → 5432.8 → 5433.5 → 5434.2 (kein Sprung!)
    - Utility Meter sollte keine Spikes sehen
    """
    reset_filter()
    mock_modbus = MockHuaweiSolar()
    mock_modbus.load_scenario("addon_restart")
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)
    filter_instance = get_filter()

    results = []

    # Cycle 0 + 1: Normaler Betrieb
    for _ in range(2):
        register = await mock_modbus.get("energy_grid_exported")
        value = register.value

        filtered_data = filter_instance.filter({"energy_grid_exported": value})
        mqtt_data = {"energy_grid_exported": filtered_data["energy_grid_exported"]}

        mock_mqtt.publish("huawei-solar", str(mqtt_data))
        results.append(mqtt_data["energy_grid_exported"])

        mock_modbus.next_cycle()

    # === SIMULIERE RESTART ===
    reset_filter()
    filter_instance = get_filter()

    # Cycle 2 + 3: Nach Restart
    for _ in range(2):
        register = await mock_modbus.get("energy_grid_exported")
        value = register.value

        filtered_data = filter_instance.filter({"energy_grid_exported": value})
        mqtt_data = {"energy_grid_exported": filtered_data["energy_grid_exported"]}

        mock_mqtt.publish("huawei-solar", str(mqtt_data))
        results.append(mqtt_data["energy_grid_exported"])

        mock_modbus.next_cycle()

    # Assertions
    assert results == [5432.1, 5432.8, 5433.5, 5434.2]

    for i in range(1, len(results)):
        diff = abs(results[i] - results[i - 1])
        assert diff < 10.0, f"Unrealistic jump: {results[i-1]} → {results[i]} (+{diff})"

    print("✅ HANT Test: No spikes after restart")


@pytest.mark.asyncio
async def test_hant_overnight_shutdown():
    """
    HANT's Szenario: Add-on läuft nicht über Nacht, startet morgens
    """
    reset_filter()
    mock_modbus = MockHuaweiSolar()
    mock_modbus.load_scenario("startup_with_previous_value")
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)
    filter_instance = get_filter()

    register = await mock_modbus.get("energy_grid_exported")
    evening_value = register.value

    filtered = filter_instance.filter({"energy_grid_exported": evening_value})
    mock_mqtt.publish("huawei-solar", str(filtered))

    # === OVERNIGHT SHUTDOWN ===
    reset_filter()
    filter_instance = get_filter()

    mock_modbus.next_cycle()

    register = await mock_modbus.get("energy_grid_exported")
    morning_value = register.value

    filtered = filter_instance.filter({"energy_grid_exported": morning_value})
    mock_mqtt.publish("huawei-solar", str(filtered))

    assert morning_value > evening_value
    assert filtered["energy_grid_exported"] == morning_value

    diff = morning_value - evening_value
    assert diff < 50.0

    print(f"✅ HANT Test: Overnight increase {diff:.1f} kWh accepted")


@pytest.mark.asyncio
async def test_hant_intermittent_failures_dont_reach_mqtt():
    """
    HANT's Beobachtung: Intermittierende Fehler werden korrekt gefiltert
    """
    import modbus_energy_meter.total_increasing_filter as filter_module

    # Singleton clearen
    filter_module._filter_instance = None

    mock_modbus = MockHuaweiSolar()
    mock_modbus.load_scenario("intermittent_modbus_failures")
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)

    filter_instance = filter_module.get_filter()

    mqtt_values = []

    for cycle in range(6):
        register = await mock_modbus.get("energy_grid_exported")
        raw_value = register.value

        filtered = filter_instance.filter({"energy_grid_exported": raw_value})
        mqtt_value = filtered["energy_grid_exported"]

        mock_mqtt.publish("huawei-solar", str(filtered))
        mqtt_values.append(mqtt_value)

        mock_modbus.next_cycle()

    # ✅ Mit vereinfachtem Filter: ALLE Zeros werden gefiltert (kein Warmup!)
    expected = [5432.1, 5432.8, 5432.8, 5433.5, 5433.5, 5434.2]
    #                           ↑ gefiltert     ↑ gefiltert

    assert mqtt_values == expected

    stats = filter_instance.get_stats()
    filtered_count = stats.get("energy_grid_exported", 0)

    assert filtered_count == 2, f"Expected 2 filtered, got {filtered_count}"

    print("✅ HANT Test: Both zeros filtered (no warmup)")


@pytest.mark.asyncio
async def test_hant_utility_meter_simulation():
    """
    Simuliert was HA Utility Meter sieht
    """
    reset_filter()
    mock_modbus = MockHuaweiSolar()
    mock_modbus.load_scenario("utility_meter_reset_simulation")
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)
    filter_instance = get_filter()

    mqtt_values = []
    timestamps = []

    for _ in range(3):
        register = await mock_modbus.get("energy_grid_exported")
        value = register.value

        filtered = filter_instance.filter({"energy_grid_exported": value})
        mqtt_values.append(filtered["energy_grid_exported"])

        timestamps.append(f"cycle_{len(mqtt_values)}")

        mock_modbus.next_cycle()

    # Werte müssen monoton steigend sein
    for i in range(1, len(mqtt_values)):
        assert (
            mqtt_values[i] >= mqtt_values[i - 1]
        ), f"❌ Value dropped: {mqtt_values[i-1]} → {mqtt_values[i]}"

    print(f"✅ HANT Test: Utility Meter simulation OK, values: {mqtt_values}")
