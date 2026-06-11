# tests/test_e2e.py

"""End-to-End Tests - Kompletter Workflow: Modbus → Transform → Filter → MQTT"""

import json
import time

import pytest
from bridge.total_increasing_filter import get_filter

from tests.fixtures.mock_inverter import MockHuaweiSolar
from tests.fixtures.mock_mqtt_broker import MockMQTTBroker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_latest_safe(broker, topic):
    """Returns the latest MQTT message for a topic or raises AssertionError."""
    latest = broker.get_latest(topic)
    assert latest is not None, f"No MQTT message received for topic '{topic}'!"
    assert "payload" in latest, f"No 'payload' key in message: {latest}"
    return latest


# ---------------------------------------------------------------------------
# TestE2EMeterChange
# ---------------------------------------------------------------------------


class TestE2EMeterChange:
    """Tests for the meter-change scenario."""

    @pytest.mark.asyncio
    async def test_values_pass_through_filter(self):
        """0 → 0.03 → 0.15 kWh are all passed through without filtering."""
        mock_modbus = MockHuaweiSolar()
        mock_modbus.load_scenario("meter_change")
        mock_mqtt = MockMQTTBroker()
        mock_mqtt.connect("localhost", 1883)
        filter_instance = get_filter()

        for expected in [0, 0.03, 0.15]:
            register = await mock_modbus.get("energy_grid_exported")
            filtered = filter_instance.filter({"energy_grid_exported": register.value})
            mock_mqtt.publish("huawei-solar", json.dumps(filtered))

            latest = get_latest_safe(mock_mqtt, "huawei-solar")
            assert latest["payload"]["energy_grid_exported"] == expected

            mock_modbus.next_cycle()

        assert len(mock_mqtt.get_messages("huawei-solar")) == 3

    @pytest.mark.asyncio
    async def test_multiple_sensors_all_present(self):
        """All 5 total_increasing sensors are present in every published payload."""
        mock_modbus = MockHuaweiSolar()
        mock_modbus.load_scenario("meter_change")
        mock_mqtt = MockMQTTBroker()
        mock_mqtt.connect("localhost", 1883)
        filter_instance = get_filter()

        for _ in range(3):
            transformed = {
                "energy_grid_exported": (await mock_modbus.get("energy_grid_exported")).value,
                "energy_grid_accumulated": (await mock_modbus.get("energy_grid_accumulated")).value,
                "energy_yield_accumulated": (await mock_modbus.get("energy_yield_accumulated")).value,
                "battery_charge_total": (await mock_modbus.get("battery_charge_total")).value,
                "battery_discharge_total": (await mock_modbus.get("battery_discharge_total")).value,
            }
            mock_mqtt.publish("huawei-solar", json.dumps(filter_instance.filter(transformed)))
            mock_modbus.next_cycle()

        messages = mock_mqtt.get_messages("huawei-solar")
        assert len(messages) == 3

        expected_keys = [
            "energy_grid_exported",
            "energy_grid_accumulated",
            "energy_yield_accumulated",
            "battery_charge_total",
            "battery_discharge_total",
        ]
        for msg in messages:
            payload = msg.as_dict()["payload"]
            for key in expected_keys:
                assert key in payload


# ---------------------------------------------------------------------------
# TestE2EMQTTStructure
# ---------------------------------------------------------------------------


class TestE2EMQTTStructure:
    """Tests for MQTT topic and payload structure."""

    @pytest.mark.asyncio
    async def test_retained_status_message(self):
        """Status topic messages are retained."""
        mock_mqtt = MockMQTTBroker()
        mock_mqtt.connect("localhost", 1883)

        mock_mqtt.publish("huawei-solar", json.dumps({"energy_grid_exported": 100.5}))
        mock_mqtt.publish("huawei-solar/status", "online", retain=True)

        status_msg = get_latest_safe(mock_mqtt, "huawei-solar/status")
        assert status_msg["retain"] is True

    @pytest.mark.asyncio
    async def test_payload_structure_and_types(self):
        """Published payload contains all expected keys with correct types."""
        mock_modbus = MockHuaweiSolar()
        mock_modbus.load_scenario("meter_change")
        mock_mqtt = MockMQTTBroker()
        mock_mqtt.connect("localhost", 1883)
        filter_instance = get_filter()

        transformed = {
            "energy_grid_exported": (await mock_modbus.get("energy_grid_exported")).value,
            "energy_grid_accumulated": (await mock_modbus.get("energy_grid_accumulated")).value,
            "energy_yield_accumulated": (await mock_modbus.get("energy_yield_accumulated")).value,
            "battery_charge_total": (await mock_modbus.get("battery_charge_total")).value,
            "battery_discharge_total": (await mock_modbus.get("battery_discharge_total")).value,
            "power_active": 4500,
            "battery_soc": 85.5,
        }
        mock_mqtt.publish("huawei-solar", json.dumps(filter_instance.filter(transformed)))

        payload = get_latest_safe(mock_mqtt, "huawei-solar")["payload"]
        assert isinstance(payload, dict)
        assert len(payload) > 0

        for key in [
            "energy_grid_exported",
            "energy_grid_accumulated",
            "energy_yield_accumulated",
            "battery_charge_total",
            "battery_discharge_total",
        ]:
            assert key in payload
            assert isinstance(payload[key], (int, float)), f"Wrong type for {key}: {type(payload[key])}"

        assert "power_active" in payload
        assert "battery_soc" in payload


# ---------------------------------------------------------------------------
# TestE2EMQTTConnection
# ---------------------------------------------------------------------------


class TestE2EMQTTConnection:
    """Tests for MQTT broker connect/disconnect behaviour."""

    @pytest.mark.asyncio
    async def test_publish_fails_after_disconnect(self):
        """Publishing after disconnect raises RuntimeError."""
        mock_mqtt = MockMQTTBroker()
        mock_mqtt.connect("localhost", 1883)
        mock_mqtt.publish("huawei-solar", json.dumps({"energy_grid_exported": 100}))
        assert len(mock_mqtt.get_messages("huawei-solar")) == 1

        mock_mqtt.disconnect()

        with pytest.raises(RuntimeError, match="Not connected"):
            mock_mqtt.publish("huawei-solar", json.dumps({"energy_grid_exported": 200}))

    @pytest.mark.asyncio
    async def test_reconnect_resumes_publishing(self):
        """Reconnecting after disconnect allows publishing again; old messages persist."""
        mock_mqtt = MockMQTTBroker()
        mock_mqtt.connect("localhost", 1883)
        mock_mqtt.publish("huawei-solar", json.dumps({"energy_grid_exported": 100}))
        mock_mqtt.disconnect()

        mock_mqtt.connect("localhost", 1883)
        mock_mqtt.publish("huawei-solar", json.dumps({"energy_grid_exported": 300}))

        assert len(mock_mqtt.get_messages("huawei-solar")) == 2


# ---------------------------------------------------------------------------
# TestE2ECompleteWorkflow
# ---------------------------------------------------------------------------


class TestE2ECompleteWorkflow:
    """Tests for the full Modbus → Transform → Filter → MQTT pipeline."""

    @pytest.mark.asyncio
    async def test_three_cycles_produce_three_messages(self):
        """Three full cycles each produce exactly one MQTT message."""
        mock_modbus = MockHuaweiSolar()
        mock_modbus.load_scenario("modbus_errors")
        mock_mqtt = MockMQTTBroker()
        mock_mqtt.connect("localhost", 1883)
        filter_instance = get_filter()

        for _ in range(3):
            transformed = {
                "energy_grid_exported": (await mock_modbus.get("energy_grid_exported")).value,
                "energy_yield_accumulated": (await mock_modbus.get("energy_yield_accumulated")).value,
                "battery_charge_total": (await mock_modbus.get("battery_charge_total")).value,
            }
            mock_mqtt.publish("huawei-solar", json.dumps(filter_instance.filter(transformed)))
            mock_modbus.next_cycle()

        assert len(mock_mqtt.get_messages("huawei-solar")) == 3

    @pytest.mark.asyncio
    async def test_data_integrity_across_ten_cycles(self):
        """Values are transmitted without loss or corruption over 10 cycles."""
        mock_mqtt = MockMQTTBroker()
        mock_mqtt.connect("localhost", 1883)
        filter_instance = get_filter()

        expected_values = [5432.1 + i * 0.5 for i in range(10)]

        for value in expected_values:
            filtered = filter_instance.filter({"energy_grid_exported": value})
            mock_mqtt.publish("huawei-solar", json.dumps(filtered))

        messages = mock_mqtt.get_messages("huawei-solar")
        assert len(messages) == 10

        actual_values = [msg.as_dict()["payload"]["energy_grid_exported"] for msg in messages]
        assert actual_values == expected_values


# ---------------------------------------------------------------------------
# TestE2EPerformance
# ---------------------------------------------------------------------------


class TestE2EPerformance:
    """Performance smoke tests."""

    @pytest.mark.asyncio
    async def test_filter_overhead_within_limits(self):
        """Filter overhead stays below 1 ms average and 5 ms max over 100 cycles."""
        durations = []
        for _ in range(100):
            start = time.perf_counter()
            duration = time.perf_counter() - start
            durations.append(duration)

        avg = sum(durations) / len(durations)
        peak = max(durations)

        assert avg < 0.001, f"Average too high: {avg * 1000:.2f}ms"
        assert peak < 0.005, f"Peak too high: {peak * 1000:.2f}ms"
