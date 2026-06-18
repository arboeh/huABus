# tests/test_filter.py

"""Tests für TotalIncreasingFilter."""

import pytest
from bridge.total_increasing_filter import TotalIncreasingFilter


@pytest.fixture(autouse=True)
def fresh_filter(request):
    """Stellt sicher, dass jede Testmethode eine frische Instanz bekommt."""
    # Instanz wird per self._filter nicht geteilt – jede Klasse erstellt lokal.
    pass


# ---------------------------------------------------------------------------
# TestBasicFiltering
# ---------------------------------------------------------------------------


class TestBasicFiltering:
    """Grundlegendes Akzeptanz- und Durchlass-Verhalten."""

    def test_first_value_always_accepted(self):
        """Erster Wert wird immer akzeptiert, auch wenn er 0 ist."""
        instance = TotalIncreasingFilter()
        assert instance._should_filter("energy_grid_exported", 0) is False
        assert instance._should_filter("energy_yield_accumulated", 0.03) is False
        assert instance._should_filter("battery_charge_total", 100.5) is False

    def test_increasing_values_accepted(self):
        """Monoton steigende Werte werden durchgelassen."""
        instance = TotalIncreasingFilter()
        instance._should_filter("energy_grid_exported", 0)
        assert instance._should_filter("energy_grid_exported", 0.03) is False
        assert instance._should_filter("energy_grid_exported", 0.15) is False

    def test_equal_values_accepted(self):
        """Gleicher Wert wie zuvor wird akzeptiert."""
        instance = TotalIncreasingFilter()
        instance._should_filter("energy_grid_exported", 100.0)
        assert instance._should_filter("energy_grid_exported", 100.0) is False

    def test_non_energy_sensors_always_pass(self):
        """Sensoren außerhalb von TOTAL_INCREASING_KEYS werden nie gefiltert."""
        instance = TotalIncreasingFilter()
        instance._should_filter("power_active", 5000)
        assert instance._should_filter("power_active", 0) is False


# ---------------------------------------------------------------------------
# TestDropsAndResets
# ---------------------------------------------------------------------------


class TestDropsAndResets:
    """Drops und Counter-Resets (kein Filter außer für Negative)."""

    def test_drop_to_zero_passes_through(self):
        """Drop auf 0 wird nicht gefiltert (nur negative Werte werden blockiert)."""
        instance = TotalIncreasingFilter()
        assert instance.filter({"energy_day": 10.5})["energy_day"] == 10.5
        assert instance.filter({"energy_day": 0.0})["energy_day"] == 0.0

    def test_counter_drop_passes_through(self):
        """Rückgang auf positiven Wert wird ebenfalls durchgelassen."""
        instance = TotalIncreasingFilter()
        assert instance.filter({"energy_day": 100})["energy_day"] == 100
        assert instance.filter({"energy_day": 50})["energy_day"] == 50


# ---------------------------------------------------------------------------
# TestNegativeValues
# ---------------------------------------------------------------------------


class TestNegativeValues:
    """Negative Werte in total_increasing-Sensoren."""

    def test_negative_values_filtered_via_should_filter(self):
        """_should_filter() erkennt negative Werte als ungültig."""
        instance = TotalIncreasingFilter()
        instance._should_filter("energy_grid_exported", 5432.1)
        assert instance._should_filter("energy_grid_exported", -10) is True
        assert instance._should_filter("energy_grid_exported", -0.5) is True

    def test_first_negative_value_removed_from_result(self):
        """Erster Wert negativ → Key wird aus dem Result entfernt und gezählt."""
        instance = TotalIncreasingFilter()
        instance.reset()

        result = instance.filter(
            {
                "energy_yield_accumulated": -5,
                "energy_grid_exported": 100,
            }
        )

        assert "energy_yield_accumulated" not in result
        assert result["energy_grid_exported"] == 100
        assert instance.get_stats().get("energy_yield_accumulated") == 1


# ---------------------------------------------------------------------------
# TestFilterStatistics
# ---------------------------------------------------------------------------


class TestFilterStatistics:
    """Korrektheit der Filter-Statistiken."""

    def test_filter_counts_each_filtered_call(self):
        """Jede Filterung erhöht den Zähler des betroffenen Keys."""
        instance = TotalIncreasingFilter()
        instance.filter({"energy_grid_exported": 5432.1})
        instance.filter({"battery_charge_total": 4804.5})

        instance.filter({"energy_grid_exported": 0})  # gefiltert
        instance.filter({"battery_charge_total": 0})  # gefiltert
        instance.filter({"energy_grid_exported": 0})  # nochmal

        stats = instance.get_stats()
        assert stats["energy_grid_exported"] == 2
        assert stats["battery_charge_total"] == 1


# ---------------------------------------------------------------------------
# TestResetFunctionality
# ---------------------------------------------------------------------------


class TestResetFunctionality:
    """reset() löscht den kompletten internen Zustand."""

    def test_reset_clears_last_values(self):
        """Nach reset() wird der nächste Wert wieder als Baseline akzeptiert."""
        instance = TotalIncreasingFilter()
        instance.filter({"energy_day": 10.0})
        instance.reset()

        result = instance.filter({"energy_day": 5.0})
        assert result["energy_day"] == 5.0


# ---------------------------------------------------------------------------
# TestNonNumericValues
# ---------------------------------------------------------------------------


class TestNonNumericValues:
    """Nicht-numerische Werte werden vom Filter ignoriert."""

    def test_strings_and_none_pass_through_unmodified(self):
        """String- und None-Werte bleiben im Result, erzeugen keine Stats."""
        instance = TotalIncreasingFilter()
        instance.reset()

        data = {
            "energy_day": 10.5,
            "device_status": "online",
            "model": "SUN2000",
            "energy_total": None,
        }

        result = instance.filter(data)

        assert result == data
        stats = instance.get_stats()
        assert "device_status" not in stats
        assert "model" not in stats
        assert "energy_total" not in stats


# ---------------------------------------------------------------------------
# TestResetStats
# ---------------------------------------------------------------------------


class TestResetStats:
    """reset_stats() löscht nur die Statistiken, nicht die last_values."""

    def test_reset_stats_clears_counts_but_keeps_last_values(self):
        """Nach reset_stats() sind Stats leer, _last_values bleiben erhalten."""
        instance = TotalIncreasingFilter()
        instance.filter({"energy_yield_accumulated": 100.0})
        instance.filter({"energy_yield_accumulated": 150.0})
        instance.filter({"energy_yield_accumulated": 120.0})  # Drop → gefiltert

        assert instance.get_stats().get("energy_yield_accumulated", 0) >= 1
        assert instance._last_values["energy_yield_accumulated"] == 150.0

        instance.reset_stats()

        assert instance.get_stats() == {}
        assert instance._last_values["energy_yield_accumulated"] == 150.0
