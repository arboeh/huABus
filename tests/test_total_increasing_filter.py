# tests/test_filter.py

import pytest  # type: ignore
from modbus_energy_meter.total_increasing_filter import TotalIncreasingFilter


class TestBasicFiltering:

    def test_first_value_accepted(self):
        """Erster Wert wird immer akzeptiert (auch 0)"""
        filter_instance = TotalIncreasingFilter()

        # ✅ Mit Unterstrich!
        assert filter_instance._should_filter("energy_grid_exported", 0) is False
        assert filter_instance._should_filter("energy_yield_accumulated", 0.03) is False
        assert filter_instance._should_filter("battery_charge_total", 100.5) is False

    def test_increasing_values_accepted(self):
        """Steigende Werte werden immer akzeptiert"""
        filter_instance = TotalIncreasingFilter()

        filter_instance._should_filter("energy_grid_exported", 0)
        assert filter_instance._should_filter("energy_grid_exported", 0.03) is False
        assert filter_instance._should_filter("energy_grid_exported", 0.15) is False

    def test_equal_values_accepted(self):
        """Gleiche Werte werden akzeptiert"""
        filter_instance = TotalIncreasingFilter()

        filter_instance._should_filter("energy_grid_exported", 100.0)
        assert filter_instance._should_filter("energy_grid_exported", 100.0) is False

    def test_non_energy_sensors_not_filtered(self):
        """Nicht-Energy-Sensoren werden nicht gefiltert"""
        filter_instance = TotalIncreasingFilter()

        filter_instance._should_filter("power_active", 5000)
        assert filter_instance._should_filter("power_active", 0) is False


class TestDropsAndRest:
    """Test für Drops und Resets."""

    def test_drop_to_zero_passed_through(self):
        """Drop auf 0 wird durchgelassen (Filter nur für Negative)."""
        filter_obj = TotalIncreasingFilter()
        filter_obj.reset()

        data1 = {"energy_day": 10.5}
        result1 = filter_obj.filter(data1)
        assert result1["energy_day"] == 10.5

        data2 = {"energy_day": 0.0}
        result2 = filter_obj.filter(data2)
        assert result2["energy_day"] == 0.0  # Durchgelassen!

    def test_counter_drop_passed_through(self):
        """Counter-Drop wird durchgelassen (kein Filter)."""
        filter_obj = TotalIncreasingFilter()
        filter_obj.reset()

        data1 = {"energy_day": 100}
        result1 = filter_obj.filter(data1)
        assert result1["energy_day"] == 100

        data2 = {"energy_day": 50}
        result2 = filter_obj.filter(data2)
        assert result2["energy_day"] == 50


class TestNegativeValues:
    """Tests für negative Werte in total_increasing Sensoren."""

    def test_negative_values_filtered(self):
        """Negative Werte werden immer gefiltert"""
        filter_instance = TotalIncreasingFilter()

        filter_instance._should_filter("energy_grid_exported", 5432.1)
        assert filter_instance._should_filter("energy_grid_exported", -10) is True
        assert filter_instance._should_filter("energy_grid_exported", -0.5) is True

    def test_first_negative_value_removed_from_result(self):
        """Erster Wert negativ → Komplett aus Result entfernt."""
        filter_obj = TotalIncreasingFilter()
        filter_obj.reset()

        data = {
            "energy_yield_accumulated": -5,  # ← MUSS in TOTAL_INCREASING_KEYS sein!
            "energy_grid_exported": 100,
        }

        result = filter_obj.filter(data)

        # DEBUG
        print(f"DEBUG: result = {result}")
        print(f"DEBUG: stats = {filter_obj.get_stats()}")

        # energy_yield_accumulated sollte entfernt sein
        assert "energy_yield_accumulated" not in result
        assert result["energy_grid_exported"] == 100

        stats = filter_obj.get_stats()
        assert stats.get("energy_yield_accumulated") == 1


class TestFilterStatistics:

    def test_filter_statistics(self):
        """Filter-Statistik wird korrekt gezählt"""
        filter_instance = TotalIncreasingFilter()

        # ✅ NICHT _should_filter() nutzen, sondern filter()!
        # Setup: Erste Werte setzen
        filter_instance.filter({"energy_grid_exported": 5432.1})
        filter_instance.filter({"battery_charge_total": 4804.5})

        # Fehler provozieren (werden gefiltert)
        filter_instance.filter({"energy_grid_exported": 0})  # Gefiltert
        filter_instance.filter({"battery_charge_total": 0})  # Gefiltert
        filter_instance.filter({"energy_grid_exported": 0})  # Nochmal gefiltert

        stats = filter_instance.get_stats()
        assert stats["energy_grid_exported"] == 2
        assert stats["battery_charge_total"] == 1


class TestResetFunctionality:
    """Test für reset() und reset_stats()."""

    def test_reset_clears_state(self):
        """reset() löscht alle internen States."""
        filter_obj = TotalIncreasingFilter()

        filter_obj.filter({"energy_day": 10.0})
        filter_obj.reset()

        result = filter_obj.filter({"energy_day": 5.0})
        assert result["energy_day"] == 5.0


class TestNonNumericValues:
    """Test Verhalten bei nicht-numerischen Werten."""

    def test_non_numeric_values_skipped(self):
        """String-Werte und None werden übersprungen (nicht gefiltert)."""
        filter_obj = TotalIncreasingFilter()
        filter_obj.reset()

        data = {
            "energy_day": 10.5,
            "device_status": "online",  # String → nicht gefiltert, bleibt im Result
            "model": "SUN2000",  # String → nicht gefiltert, bleibt im Result
            "energy_total": None,  # None → nicht gefiltert, bleibt im Result
        }

        result = filter_obj.filter(data)

        # Alle Werte bleiben (auch nicht-numerische)
        assert result == data

        # Aber: Keine Filter-Stats für nicht-numerische Werte
        stats = filter_obj.get_stats()
        assert "device_status" not in stats
        assert "model" not in stats
        assert "energy_total" not in stats
