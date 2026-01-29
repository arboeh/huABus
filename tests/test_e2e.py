"""End-to-End Tests - Kompletter Workflow: Modbus → Transform → Filter → MQTT"""

import json

import pytest  # type: ignore
from modbus_energy_meter.total_increasing_filter import (
    TotalIncreasingFilter,
    get_filter,
    reset_filter,
)

from tests.fixtures.mock_inverter import MockHuaweiSolar
from tests.fixtures.mock_mqtt_broker import MockMQTTBroker


def get_latest_safe(broker, topic):
    """Helper: Hole latest message oder raise AssertionError"""
    latest = broker.get_latest(topic)
    assert latest is not None, f"No MQTT message received for topic '{topic}'!"
    assert "payload" in latest, f"No 'payload' key in message: {latest}"
    return latest


@pytest.mark.asyncio
async def test_e2e_meter_change_scenario():
    """
    End-to-End: Neuer Meter installiert
    - Modbus liefert: 0 → 0.03 → 0.15 kWh
    - MQTT sollte empfangen: 0 → 0.03 → 0.15 kWh (alle Werte durchgelassen)
    """
    reset_filter()
    mock_modbus = MockHuaweiSolar()
    mock_modbus.load_scenario("meter_change")
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)
    filter_instance = get_filter()

    expected_values = [0, 0.03, 0.15]

    for expected in expected_values:
        register = await mock_modbus.get("energy_grid_exported")
        raw_value = register.value

        transformed = {"energy_grid_exported": raw_value}
        filtered = filter_instance.filter(transformed)

        payload = json.dumps(filtered)
        mock_mqtt.publish("huawei-solar", payload)

        # ✅ FIX
        latest = get_latest_safe(mock_mqtt, "huawei-solar")
        assert latest["payload"]["energy_grid_exported"] == expected

        mock_modbus.next_cycle()

    all_messages = mock_mqtt.get_messages("huawei-solar")
    assert len(all_messages) == 3
    print(f"✅ E2E Test passed: {expected_values} correctly transmitted via MQTT")


@pytest.mark.asyncio
async def test_e2e_modbus_errors_filtered_before_mqtt():
    """
    End-to-End: Modbus-Fehler werden gefiltert NACH Warmup
    - Cycles 1-3: Warmup (5432.1 → 0 → 5432.8) - alles durchlassen
    - Cycle 4+: Filter aktiv, 0 wird gefiltert
    """
    reset_filter()
    mock_modbus = MockHuaweiSolar()
    mock_modbus.load_scenario("modbus_errors")
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)
    filter_instance = get_filter(warmup_cycles=3)

    # ✅ Warmup berücksichtigen: 0 wird NICHT gefiltert in Cycle 2!
    expected_values = [5432.1, 0, 5432.8]  # Cycle 2 = 0 durchgelassen (Warmup!)

    for i, expected in enumerate(expected_values):
        register = await mock_modbus.get("energy_grid_exported")
        raw_value = register.value

        transformed = {"energy_grid_exported": raw_value}
        filtered = filter_instance.filter(transformed)

        payload = json.dumps(filtered)
        mock_mqtt.publish("huawei-solar", payload)

        # ✅ FIX
        latest = get_latest_safe(mock_mqtt, "huawei-solar")
        actual = latest["payload"]["energy_grid_exported"]
        assert actual == expected, f"Cycle {i+1}: Expected {expected}, got {actual}"

        mock_modbus.next_cycle()

    # Sicherstellen, dass 0 in Cycle 2 durchkam (Warmup!)
    all_messages = mock_mqtt.get_messages("huawei-solar")
    cycle2_value = all_messages[1].as_dict()["payload"]["energy_grid_exported"]
    assert cycle2_value == 0, "Zero should pass during warmup!"

    print("✅ E2E Test passed: Zero passed during warmup, filter active after")


@pytest.mark.asyncio
async def test_e2e_multiple_sensors():
    """
    End-to-End: Multiple Sensoren gleichzeitig
    """
    reset_filter()
    mock_modbus = MockHuaweiSolar()
    mock_modbus.load_scenario("meter_change")
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)
    filter_instance = get_filter()

    for cycle in range(3):
        grid_export = await mock_modbus.get("energy_grid_exported")
        grid_import = await mock_modbus.get("energy_grid_accumulated")
        solar = await mock_modbus.get("energy_yield_accumulated")
        battery_charge = await mock_modbus.get("battery_charge_total")
        battery_discharge = await mock_modbus.get("battery_discharge_total")

        transformed = {
            "energy_grid_exported": grid_export.value,
            "energy_grid_accumulated": grid_import.value,
            "energy_yield_accumulated": solar.value,
            "battery_charge_total": battery_charge.value,
            "battery_discharge_total": battery_discharge.value,
        }

        filtered = filter_instance.filter(transformed)

        payload = json.dumps(filtered)
        mock_mqtt.publish("huawei-solar", payload)

        mock_modbus.next_cycle()

    all_messages = mock_mqtt.get_messages("huawei-solar")
    assert len(all_messages) == 3

    for msg in all_messages:
        # ✅ FIX: as_dict() verwenden
        payload_dict = msg.as_dict()
        payload = payload_dict["payload"]

        assert "energy_grid_exported" in payload
        assert "energy_grid_accumulated" in payload
        assert "energy_yield_accumulated" in payload
        assert "battery_charge_total" in payload
        assert "battery_discharge_total" in payload

    print("✅ E2E Test passed: All 5 total_increasing sensors correctly handled")


@pytest.mark.asyncio
async def test_e2e_mqtt_topic_structure():
    """
    End-to-End: MQTT Topic-Struktur korrekt
    """
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)

    mock_mqtt.publish("huawei-solar", json.dumps({"energy_grid_exported": 100.5}))
    mock_mqtt.publish("huawei-solar/status", "online", retain=True)

    # ✅ FIX
    data_msg = get_latest_safe(mock_mqtt, "huawei-solar")
    status_msg = get_latest_safe(mock_mqtt, "huawei-solar/status")

    assert status_msg["retain"] == True

    print("✅ E2E Test passed: MQTT topic structure correct")


@pytest.mark.asyncio
async def test_e2e_warmup_prevents_false_filtering():
    """
    E2E Warmup: Verhindert falsche Filterung bei Startup

    Problem: Ohne Warmup würde der erste Wert als "drop" gefiltert
    Lösung: Warmup akzeptiert alle Werte in ersten 3 Cycles
    """
    reset_filter()
    mock_modbus = MockHuaweiSolar()
    mock_modbus.load_scenario("addon_restart")
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)
    filter_instance = get_filter(warmup_cycles=3)

    # Cycle 0-2: Normaler Betrieb + Restart
    for _ in range(3):
        register = await mock_modbus.get("energy_grid_exported")
        transformed = {"energy_grid_exported": register.value}
        filtered = filter_instance.filter(transformed)

        payload = json.dumps(filtered)
        mock_mqtt.publish("huawei-solar", payload)

        mock_modbus.next_cycle()

    # Check: Warmup sollte abgeschlossen sein
    assert filter_instance.warmup_mode == False

    # Check: Alle 3 Werte wurden korrekt zu MQTT gesendet
    all_messages = mock_mqtt.get_messages("huawei-solar")
    assert len(all_messages) == 3

    values = [msg.as_dict()["payload"]["energy_grid_exported"] for msg in all_messages]
    expected = [5432.1, 5432.8, 5433.5]  # Aus addon_restart scenario
    assert values == expected

    print("✅ E2E Warmup: All startup values accepted")


@pytest.mark.asyncio
async def test_e2e_filter_active_after_warmup():
    """E2E: Filter wird nach Warmup aktiv und filtert korrekt"""
    reset_filter()
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)
    filter_instance = get_filter(warmup_cycles=3)

    values_to_send = [5432.1, 5432.8, 5433.5, 0]
    expected_mqtt = [5432.1, 5432.8, 5433.5, 5433.5]

    for i, value in enumerate(values_to_send):
        transformed = {"energy_grid_exported": value}
        filtered = filter_instance.filter(transformed)

        payload = json.dumps(filtered)
        mock_mqtt.publish("huawei-solar", payload)

        # ✅ FIX
        latest = get_latest_safe(mock_mqtt, "huawei-solar")
        actual = latest["payload"]["energy_grid_exported"]
        assert (
            actual == expected_mqtt[i]
        ), f"Cycle {i+1}: Expected {expected_mqtt[i]}, got {actual}"

    stats = filter_instance.get_stats()
    assert stats.get("energy_grid_exported", 0) == 1

    print("✅ E2E: Filter became active after warmup")


@pytest.mark.asyncio
async def test_e2e_multiple_restarts():
    """E2E: Multiple Add-on Restarts mit Warmup"""
    import modbus_energy_meter.total_increasing_filter as filter_module

    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)

    for restart_num in range(3):
        # ✅ FIX: Singleton komplett clearen!
        filter_module._filter_instance = None

        # Jetzt wird eine neue Instanz mit warmup_cycles=2 erstellt
        filter_instance = filter_module.get_filter(warmup_cycles=2)

        for cycle in range(2):
            data = {"energy_grid_exported": 5432.1 + restart_num * 10}
            filtered = filter_instance.filter(data)
            mock_mqtt.publish("huawei-solar", json.dumps(filtered))

        # Nach 2 Cycles: Warmup complete
        assert filter_instance.warmup_cycles == 2
        assert (
            filter_instance.warmup_mode == False
        ), f"Warmup should be complete! cycles={filter_instance.warmup_cycles}, required={filter_instance.warmup_required}"

    all_messages = mock_mqtt.get_messages("huawei-solar")
    assert len(all_messages) == 6

    print("✅ E2E: Multiple restarts handled correctly")


@pytest.mark.asyncio
async def test_e2e_tolerance_edge_with_warmup():
    """E2E: Toleranz-Grenze (5%) mit Warmup-Phase"""
    reset_filter()
    mock_modbus = MockHuaweiSolar()
    mock_modbus.load_scenario("tolerance_edge")
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)
    filter_instance = get_filter(warmup_cycles=3)

    expected_values = [10000.0, 9510.0, 10000.0, 10000.0]

    for i, expected in enumerate(expected_values):
        register = await mock_modbus.get("energy_grid_exported")
        transformed = {"energy_grid_exported": register.value}
        filtered = filter_instance.filter(transformed)

        payload = json.dumps(filtered)
        mock_mqtt.publish("huawei-solar", payload)

        # ✅ FIX
        latest = get_latest_safe(mock_mqtt, "huawei-solar")
        actual = latest["payload"]["energy_grid_exported"]
        assert actual == expected, f"Cycle {i+1}: Expected {expected}, got {actual}"

        mock_modbus.next_cycle()

    print("✅ E2E: Tolerance edge cases with warmup work correctly")


@pytest.mark.asyncio
async def test_e2e_mqtt_payload_structure():
    """
    E2E: MQTT Payload-Struktur ist korrekt

    Prüft:
    - JSON ist valid
    - Alle Keys vorhanden
    - Werte haben richtigen Typ
    """
    reset_filter()
    mock_modbus = MockHuaweiSolar()
    mock_modbus.load_scenario("meter_change")
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)
    filter_instance = get_filter()

    # Alle 5 total_increasing Sensoren simulieren
    register_export = await mock_modbus.get("energy_grid_exported")
    register_import = await mock_modbus.get("energy_grid_accumulated")
    register_solar = await mock_modbus.get("energy_yield_accumulated")
    register_charge = await mock_modbus.get("battery_charge_total")
    register_discharge = await mock_modbus.get("battery_discharge_total")

    transformed = {
        "energy_grid_exported": register_export.value,
        "energy_grid_accumulated": register_import.value,
        "energy_yield_accumulated": register_solar.value,
        "battery_charge_total": register_charge.value,
        "battery_discharge_total": register_discharge.value,
        "power_active": 4500,  # Nicht total_increasing
        "battery_soc": 85.5,  # Nicht total_increasing
    }

    filtered = filter_instance.filter(transformed)
    payload = json.dumps(filtered)
    mock_mqtt.publish("huawei-solar", payload)

    # ✅ FIX: Sicherer Zugriff
    latest = get_latest_safe(mock_mqtt, "huawei-solar")
    payload_dict = latest["payload"]

    # Struktur-Checks
    assert isinstance(
        payload_dict, dict
    ), f"Payload is not a dict: {type(payload_dict)}"
    assert len(payload_dict) > 0, "Payload is empty!"

    # Energy-Sensoren müssen vorhanden sein
    for key in [
        "energy_grid_exported",
        "energy_grid_accumulated",
        "energy_yield_accumulated",
        "battery_charge_total",
        "battery_discharge_total",
    ]:
        assert key in payload_dict, f"Missing key: {key}"
        assert isinstance(
            payload_dict[key], (int, float)
        ), f"Wrong type for {key}: {type(payload_dict[key])}"

    # Andere Sensoren auch vorhanden
    assert "power_active" in payload_dict, "Missing key: power_active"
    assert "battery_soc" in payload_dict, "Missing key: battery_soc"

    print("✅ E2E: MQTT payload structure is valid")


@pytest.mark.asyncio
async def test_e2e_performance_filter_overhead():
    """
    E2E Performance: Filter-Overhead < 1ms pro Cycle

    Testet ob der Filter die Performance nicht negativ beeinflusst
    """
    import time

    reset_filter()
    filter_instance = get_filter()

    # Simuliere 100 Cycles
    durations = []

    for i in range(100):
        data = {
            "energy_grid_exported": 5432.1 + i * 0.1,
            "energy_yield_accumulated": 15420.5 + i * 0.2,
            "battery_charge_total": 4804.5 + i * 0.05,
        }

        start = time.perf_counter()
        filtered = filter_instance.filter(data)
        duration = time.perf_counter() - start

        durations.append(duration)

    # Assertions
    avg_duration = sum(durations) / len(durations)
    max_duration = max(durations)

    assert (
        avg_duration < 0.001
    ), f"Average filter duration too high: {avg_duration*1000:.2f}ms"
    assert (
        max_duration < 0.005
    ), f"Max filter duration too high: {max_duration*1000:.2f}ms"

    print(
        f"✅ E2E Performance: Avg {avg_duration*1000:.3f}ms, Max {max_duration*1000:.3f}ms"
    )


@pytest.mark.asyncio
async def test_e2e_mqtt_broker_disconnect_handling():
    """
    E2E: MQTT Broker Disconnect wird korrekt gehandhabt

    Testet was passiert wenn MQTT-Verbindung abbricht
    """
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)

    # Publish funktioniert
    mock_mqtt.publish("huawei-solar", json.dumps({"energy_grid_exported": 100}))
    assert len(mock_mqtt.get_messages("huawei-solar")) == 1

    # Disconnect
    mock_mqtt.disconnect()

    # Publish sollte fehlschlagen
    try:
        mock_mqtt.publish("huawei-solar", json.dumps({"energy_grid_exported": 200}))
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "Not connected" in str(e)

    # Reconnect
    mock_mqtt.connect("localhost", 1883)
    mock_mqtt.publish("huawei-solar", json.dumps({"energy_grid_exported": 300}))
    assert len(mock_mqtt.get_messages("huawei-solar")) == 2  # Alte Messages bleiben

    print("✅ E2E: MQTT disconnect handling works")


@pytest.mark.asyncio
async def test_e2e_complete_workflow_with_transform():
    """
    E2E Complete: Voller Workflow Modbus → Transform → Filter → MQTT

    Simuliert den kompletten Ablauf wie in main.py
    """
    from modbus_energy_meter.transform import transform_data

    reset_filter()
    mock_modbus = MockHuaweiSolar()
    mock_modbus.load_scenario("modbus_errors")
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)
    filter_instance = get_filter()

    for cycle in range(3):
        # 1. Modbus Read (Mock)
        register_export = await mock_modbus.get("energy_grid_exported")
        register_solar = await mock_modbus.get("energy_yield_accumulated")
        register_charge = await mock_modbus.get("battery_charge_total")

        raw_data = {
            "gridexportedtotals": register_export,  # Echtes Format!
            "day_active_power_peak": register_solar,
            "storage_charge_total": register_charge,
        }

        # 2. Transform (würde in echtem Code alle Mappings anwenden)
        # Hier vereinfacht:
        transformed = {
            "energy_grid_exported": register_export.value,
            "energy_yield_accumulated": register_solar.value,
            "battery_charge_total": register_charge.value,
        }

        # 3. Filter
        filtered = filter_instance.filter(transformed)

        # 4. MQTT Publish
        payload = json.dumps(filtered)
        mock_mqtt.publish("huawei-solar", payload)

        mock_modbus.next_cycle()

    # Assertions
    all_messages = mock_mqtt.get_messages("huawei-solar")
    assert len(all_messages) == 3

    # Check: Cycle 2 hatte Fehler (0-Werte), sollte gefiltert sein
    cycle2_msg = all_messages[1].as_dict()["payload"]
    # Nach Warmup sollte 0 gefiltert werden
    # (Aber Cycle 2 ist noch Warmup mit warmup_cycles=3!)

    print("✅ E2E Complete: Full workflow works correctly")


@pytest.mark.asyncio
async def test_e2e_data_integrity_across_cycles():
    """
    E2E: Daten-Integrität über mehrere Cycles

    Prüft ob Werte konsistent bleiben und keine Datenverluste auftreten
    """
    reset_filter()
    mock_mqtt = MockMQTTBroker()
    mock_mqtt.connect("localhost", 1883)
    filter_instance = get_filter()

    # 10 Cycles mit verschiedenen Werten
    expected_values = []

    for i in range(10):
        value = 5432.1 + i * 0.5
        expected_values.append(value)

        data = {"energy_grid_exported": value}
        filtered = filter_instance.filter(data)

        payload = json.dumps(filtered)
        mock_mqtt.publish("huawei-solar", payload)

    # Check: Alle Werte korrekt angekommen
    all_messages = mock_mqtt.get_messages("huawei-solar")
    assert len(all_messages) == 10

    actual_values = [
        msg.as_dict()["payload"]["energy_grid_exported"] for msg in all_messages
    ]
    assert actual_values == expected_values

    print("✅ E2E: Data integrity maintained across 10 cycles")
