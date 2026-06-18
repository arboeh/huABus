# tests/test_hant_zero_drops.py

"""
Tests für HANTs gemeldetes Problem: Zero Drops (Secondary Issue)
GitHub Issue: #7 - Secondary: Zero values from Modbus errors
"""

import pytest
from bridge.total_increasing_filter import get_filter

from tests.fixtures.mock_inverter import MockHuaweiSolar
from tests.fixtures.mock_mqtt_broker import MockMQTTBroker

# ---------------------------------------------------------------------------
# TestZeroDropFiltering
# ---------------------------------------------------------------------------


class TestZeroDropFiltering:
    """Filter-Verhalten bei Zero-Drops durch Modbus-Fehler."""

    @pytest.mark.asyncio
    async def test_zero_after_valid_value_is_replaced(self):
        """Zero-Drop nach gültigem Wert wird durch letzten gültigen Wert ersetzt."""
        instance = get_filter()
        instance.filter({"energy_grid_exported": 9799.50})

        result = instance.filter({"energy_grid_exported": 0})

        assert result["energy_grid_exported"] == 9799.50

    @pytest.mark.asyncio
    async def test_negative_value_is_filtered(self):
        """Negativer Wert wird als ungültig erkannt und gefiltert."""
        instance = get_filter()
        instance.filter({"energy_grid_exported": 9799.50})

        result = instance.filter({"energy_grid_exported": -123.45})

        assert result["energy_grid_exported"] == 9799.50

    @pytest.mark.asyncio
    async def test_any_drop_is_filtered(self):
        """Jeder Rückgang (auch nicht-null) wird durch letzten gültigen Wert ersetzt."""
        instance = get_filter()
        instance.filter({"energy_grid_exported": 9799.50})

        result = instance.filter({"energy_grid_exported": 9300.00})

        assert result["energy_grid_exported"] == 9799.50

    @pytest.mark.asyncio
    async def test_legitimate_zero_on_first_read_accepted(self):
        """Erster Wert 0 ist legitim und wird akzeptiert."""
        instance = get_filter()
        result = instance.filter(
            {
                "battery_charge_total": 0,
                "battery_discharge_total": 0,
            }
        )
        assert result["battery_charge_total"] == 0
        assert result["battery_discharge_total"] == 0

    @pytest.mark.asyncio
    async def test_zero_drop_after_nonzero_is_filtered(self):
        """Nach echten Werten wird Zero als Fehler erkannt und gefiltert."""
        instance = get_filter()
        instance.filter({"battery_charge_total": 0, "battery_discharge_total": 0})
        instance.filter({"battery_charge_total": 1.5, "battery_discharge_total": 0.8})

        result = instance.filter({"battery_charge_total": 0, "battery_discharge_total": 0})

        assert result["battery_charge_total"] == 1.5
        assert result["battery_discharge_total"] == 0.8


# ---------------------------------------------------------------------------
# TestFilterStatistics
# ---------------------------------------------------------------------------


class TestFilterStatistics:
    """Statistiken über gefilterte Zero-Drops."""

    @pytest.mark.asyncio
    async def test_initial_stats_are_zero(self):
        """Vor dem ersten Filter-Vorgang sind alle Zähler auf 0."""
        instance = get_filter()
        instance.filter(
            {
                "energy_grid_exported": 9799.50,
                "energy_yield_accumulated": 18052.68,
            }
        )
        stats = instance.get_stats()
        assert stats.get("energy_grid_exported", 0) == 0
        assert stats.get("energy_yield_accumulated", 0) == 0

    @pytest.mark.asyncio
    async def test_stats_count_each_filtered_value(self):
        """Jede Filterung erhöht den Zähler des betroffenen Keys."""
        instance = get_filter()
        instance.filter(
            {
                "energy_grid_exported": 9799.50,
                "energy_yield_accumulated": 18052.68,
            }
        )
        instance.filter({"energy_grid_exported": 0, "energy_yield_accumulated": 0})

        stats = instance.get_stats()
        assert stats["energy_grid_exported"] == 1
        assert stats["energy_yield_accumulated"] == 1

    @pytest.mark.asyncio
    async def test_stats_track_independently_per_key(self):
        """Zähler werden pro Key unabhängig aktualisiert."""
        instance = get_filter()
        instance.filter(
            {
                "energy_grid_exported": 9799.50,
                "energy_yield_accumulated": 18052.68,
            }
        )
        instance.filter({"energy_grid_exported": 0, "energy_yield_accumulated": 0})
        instance.filter({"energy_grid_exported": 0, "energy_yield_accumulated": 18053.20})

        stats = instance.get_stats()
        assert stats["energy_grid_exported"] == 2
        assert stats["energy_yield_accumulated"] == 1


# ---------------------------------------------------------------------------
# TestDailyCounterHandling
# ---------------------------------------------------------------------------


class TestDailyCounterHandling:
    """Midnight-Reset bei Daily-Countern darf nicht gefiltert werden."""

    @pytest.mark.asyncio
    async def test_daily_counters_not_in_total_increasing_keys(self):
        """Daily-Counter-Keys sind nicht in TOTAL_INCREASING_KEYS."""
        instance = get_filter()
        assert "energy_yield_day" not in instance.TOTAL_INCREASING_KEYS
        assert "battery_charge_day" not in instance.TOTAL_INCREASING_KEYS

    @pytest.mark.asyncio
    async def test_midnight_reset_of_daily_counter_passes_through(self):
        """Zero nach Midnight-Reset bei Daily-Counter wird durchgelassen."""
        instance = get_filter()
        instance.filter(
            {
                "energy_yield_day": 25.5,
                "energy_yield_accumulated": 18052.68,
            }
        )

        result = instance.filter(
            {
                "energy_yield_day": 0,
                "energy_yield_accumulated": 18053.00,
            }
        )

        assert result["energy_yield_day"] == 0
        assert result["energy_yield_accumulated"] == 18053.00


# ---------------------------------------------------------------------------
# TestE2EZeroDrops
# ---------------------------------------------------------------------------


class TestE2EZeroDrops:
    """End-to-End Tests mit Mock Inverter und MQTT."""

    @pytest.mark.asyncio
    async def test_no_zeros_reach_mqtt_after_first_cycle(self):
        """Ab Cycle 2 erscheinen keine Zero-Werte in MQTT-Payloads."""
        mock_modbus = MockHuaweiSolar()
        mock_modbus.load_scenario("zero_drop_errors")
        mock_mqtt = MockMQTTBroker()
        mock_mqtt.connect("localhost", 1883)
        instance = get_filter()
        mqtt_values = []

        for _ in range(6):
            reg = await mock_modbus.get("energy_grid_exported")
            filtered = instance.filter({"energy_grid_exported": reg.value})
            mqtt_values.append(filtered["energy_grid_exported"])
            mock_mqtt.publish("huawei-solar", str(filtered))
            mock_modbus.next_cycle()

        for i, value in enumerate(mqtt_values):
            if i > 0:
                assert value > 0, f"Cycle {i}: Zero reached MQTT! {mqtt_values}"

        for i in range(1, len(mqtt_values)):
            assert mqtt_values[i] >= mqtt_values[i - 1], f"Value dropped: {mqtt_values[i - 1]} → {mqtt_values[i]}"

    @pytest.mark.asyncio
    async def test_utility_meter_stable_despite_zero_drops(self):
        """HA Utility Meter berechnet korrekte Summe trotz Zero-Drops."""
        instance = get_filter()

        test_sequence = [9799.50, 9800.20, 0, 9801.00, 0, 9801.50]
        utility_meter = 0.0
        last_value = 0.0

        for raw in test_sequence:
            filtered = instance.filter({"energy_grid_exported": raw})
            mqtt_value = filtered["energy_grid_exported"]
            if last_value > 0:
                delta = mqtt_value - last_value
                if delta >= 0:
                    utility_meter += delta
            last_value = mqtt_value

        assert abs(utility_meter - 2.0) < 0.1, f"Utility Meter incorrect: {utility_meter} vs 2.0"
