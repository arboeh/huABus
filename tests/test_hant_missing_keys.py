# tests/test_hant_missing_keys.py

"""
Tests für HANTs gemeldetes Problem: Missing Keys bei Register-Timeouts
GitHub Issue: #7 - Root Cause: Missing keys from register timeouts
"""

import pytest
from bridge.total_increasing_filter import get_filter, reset_filter

from tests.fixtures.mock_inverter import MockHuaweiSolar
from tests.fixtures.mock_mqtt_broker import MockMQTTBroker

# ---------------------------------------------------------------------------
# TestMissingKeyHandling
# ---------------------------------------------------------------------------


class TestMissingKeyHandling:
    """Filter-Verhalten bei fehlenden Keys durch Register-Timeouts."""

    @pytest.mark.asyncio
    async def test_missing_key_filled_with_last_valid_value(self):
        """Fehlender Key in Cycle 2 wird mit letztem gültigem Wert aufgefüllt."""
        instance = get_filter()
        instance.filter(
            {
                "energy_grid_exported": 9799.50,
                "energy_yield_accumulated": 18052.68,
            }
        )

        result = instance.filter({"energy_yield_accumulated": 18053.20})

        assert "energy_grid_exported" in result, "Missing key must be filled!"
        assert result["energy_grid_exported"] == 9799.50
        assert result["energy_yield_accumulated"] == 18053.20

    @pytest.mark.asyncio
    async def test_missing_key_without_previous_value_not_filled(self):
        """Key ohne bekannten Vorwert wird nicht ergänzt."""
        instance = get_filter()
        result1 = instance.filter({"energy_yield_accumulated": 18052.68})
        assert "energy_grid_exported" not in result1

    @pytest.mark.asyncio
    async def test_missing_key_reappears_then_disappears_again(self):
        """Key der wieder auftaucht und erneut fehlt wird korrekt behandelt."""
        instance = get_filter()

        instance.filter({"energy_yield_accumulated": 18052.68})
        instance.filter(
            {
                "energy_yield_accumulated": 18053.20,
                "energy_grid_exported": 9799.50,
            }
        )

        result = instance.filter({"energy_yield_accumulated": 18054.00})

        assert "energy_grid_exported" in result
        assert result["energy_grid_exported"] == 9799.50

    @pytest.mark.asyncio
    async def test_missing_and_invalid_values_handled_together(self):
        """Gleichzeitig fehlende und invalide Werte werden korrekt behandelt."""
        instance = get_filter()
        instance.filter(
            {
                "energy_grid_exported": 9799.50,
                "energy_yield_accumulated": 18052.68,
                "battery_charge_total": 1234.56,
            }
        )

        result = instance.filter(
            {
                "energy_yield_accumulated": 0,  # invalid (zero drop)
                "battery_charge_total": 1234.60,  # valid
                # energy_grid_exported missing (timeout)
            }
        )

        assert result["energy_grid_exported"] == 9799.50
        assert result["energy_yield_accumulated"] == 18052.68
        assert result["battery_charge_total"] == 1234.60


# ---------------------------------------------------------------------------
# TestE2EWithMockInverter
# ---------------------------------------------------------------------------


class TestE2EWithMockInverter:
    """End-to-End Tests mit MockHuaweiSolar für realistische Szenarien."""

    @pytest.mark.asyncio
    async def test_register_timeout_payloads_remain_complete(self):
        """Ab Cycle 2 enthält jeder Payload alle Keys, auch nach Timeouts."""
        mock_modbus = MockHuaweiSolar()
        mock_modbus.load_scenario("register_timeouts")
        instance = get_filter()
        payloads = []

        for _ in range(3):
            raw = {}
            for key in ("energy_grid_exported", "energy_yield_accumulated"):
                try:
                    reg = await mock_modbus.get(key)
                    if reg.value != 65535:
                        raw[key] = reg.value
                except Exception:
                    pass
            payloads.append(instance.filter(raw))
            mock_modbus.next_cycle()

        for i, payload in enumerate(payloads):
            if i > 0:
                assert "energy_grid_exported" in payload, f"Cycle {i}: Key missing!"
                assert "energy_yield_accumulated" in payload, f"Cycle {i}: Key missing!"

    @pytest.mark.asyncio
    async def test_intermittent_zeros_filtered_correctly(self):
        """Intermittierende Zero-Werte werden gefiltert; zwei Zeros erwartet."""
        import bridge.total_increasing_filter as filter_module

        mock_modbus = MockHuaweiSolar()
        mock_modbus.load_scenario("intermittent_modbus_failures")
        mock_mqtt = MockMQTTBroker()
        mock_mqtt.connect("localhost", 1883)
        instance = filter_module.get_filter()
        mqtt_values = []

        for _ in range(6):
            reg = await mock_modbus.get("energy_grid_exported")
            filtered = instance.filter({"energy_grid_exported": reg.value})
            mqtt_values.append(filtered["energy_grid_exported"])
            mock_mqtt.publish("huawei-solar", str(filtered))
            mock_modbus.next_cycle()

        expected = [5432.1, 5432.8, 5432.8, 5433.5, 5433.5, 5434.2]
        assert mqtt_values == expected

        stats = instance.get_stats()
        assert stats.get("energy_grid_exported", 0) == 2

    @pytest.mark.asyncio
    async def test_utility_meter_values_are_monotonically_increasing(self):
        """MQTT-Werte sind für den HA Utility Meter immer monoton steigend."""
        mock_modbus = MockHuaweiSolar()
        mock_modbus.load_scenario("utility_meter_reset_simulation")
        mock_mqtt = MockMQTTBroker()
        mock_mqtt.connect("localhost", 1883)
        instance = get_filter()
        values = []

        for _ in range(3):
            reg = await mock_modbus.get("energy_grid_exported")
            filtered = instance.filter({"energy_grid_exported": reg.value})
            values.append(filtered["energy_grid_exported"])
            mock_mqtt.publish("huawei-solar", str(filtered))
            mock_modbus.next_cycle()

        for i in range(1, len(values)):
            assert values[i] >= values[i - 1], f"Value dropped: {values[i - 1]} → {values[i]}"


# ---------------------------------------------------------------------------
# TestRestartScenarios
# ---------------------------------------------------------------------------


class TestRestartScenarios:
    """Szenarien mit Add-on-Restart und Filter-Reset."""

    @pytest.mark.asyncio
    async def test_no_spikes_after_addon_restart(self):
        """Nach Restart werden keine unrealistischen Sprünge an MQTT gesendet."""
        mock_modbus = MockHuaweiSolar()
        mock_modbus.load_scenario("addon_restart")
        mock_mqtt = MockMQTTBroker()
        mock_mqtt.connect("localhost", 1883)
        instance = get_filter()
        results = []

        for _ in range(2):
            reg = await mock_modbus.get("energy_grid_exported")
            filtered = instance.filter({"energy_grid_exported": reg.value})
            mock_mqtt.publish("huawei-solar", str(filtered))
            results.append(filtered["energy_grid_exported"])
            mock_modbus.next_cycle()

        reset_filter()
        instance = get_filter()

        for _ in range(2):
            reg = await mock_modbus.get("energy_grid_exported")
            filtered = instance.filter({"energy_grid_exported": reg.value})
            mock_mqtt.publish("huawei-solar", str(filtered))
            results.append(filtered["energy_grid_exported"])
            mock_modbus.next_cycle()

        assert results == [5432.1, 5432.8, 5433.5, 5434.2]
        for i in range(1, len(results)):
            assert abs(results[i] - results[i - 1]) < 10.0

    @pytest.mark.asyncio
    async def test_overnight_shutdown_morning_value_accepted(self):
        """Nach Overnight-Shutdown wird der Morgenwert als neuer Startwert akzeptiert."""
        reset_filter()
        mock_modbus = MockHuaweiSolar()
        mock_modbus.load_scenario("startup_with_previous_value")
        mock_mqtt = MockMQTTBroker()
        mock_mqtt.connect("localhost", 1883)
        instance = get_filter()

        reg = await mock_modbus.get("energy_grid_exported")
        evening_value = reg.value
        instance.filter({"energy_grid_exported": evening_value})
        mock_mqtt.publish("huawei-solar", str({"energy_grid_exported": evening_value}))

        reset_filter()
        instance = get_filter()
        mock_modbus.next_cycle()

        reg = await mock_modbus.get("energy_grid_exported")
        morning_value = reg.value
        filtered = instance.filter({"energy_grid_exported": morning_value})
        mock_mqtt.publish("huawei-solar", str(filtered))

        assert float(morning_value) > float(evening_value)
        assert filtered["energy_grid_exported"] == morning_value
        assert (float(morning_value) - float(evening_value)) < 50.0
