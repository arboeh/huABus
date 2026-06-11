# tests/test_restart_protection.py

"""
Tests für Restart-Protection des TotalIncreasingFilters.

Szenario (HANT Issue):
- Add-on startet neu
- Home Assistant hat noch alte Werte im State
- Erster Read liefert gültige Counter-Werte
- Filter muss diese akzeptieren (nicht als Drop interpretieren)
"""

import pytest
from bridge.total_increasing_filter import (
    TotalIncreasingFilter,
    get_filter,
    reset_filter,
)


@pytest.fixture(autouse=True)
def clean_filter():
    reset_filter()
    yield
    reset_filter()


# ---------------------------------------------------------------------------
# TestRestartProtection
# ---------------------------------------------------------------------------


class TestRestartProtection:
    """Addon-Restart Szenarien."""

    def test_first_value_after_restart_accepted(self):
        """Erster Wert nach Restart wird als Baseline akzeptiert, nichts gefiltert."""
        instance = TotalIncreasingFilter()
        data = {
            "energy_yield_accumulated": 12345.6,
            "battery_charge_total": 5678.9,
            "other_sensor": 42,
        }

        result = instance.filter(data)

        assert result == data
        assert instance.get_stats() == {}

    def test_multiple_restarts_each_establish_new_baseline(self):
        """Nach jedem Restart wird der erste Wert akzeptiert, auch wenn er niedriger ist."""
        filter1 = TotalIncreasingFilter()
        assert filter1.filter({"energy_yield_accumulated": 12000.0})["energy_yield_accumulated"] == 12000.0

        reset_filter()
        filter2 = get_filter()
        result2 = filter2.filter({"energy_yield_accumulated": 12100.0})
        assert result2["energy_yield_accumulated"] == 12100.0
        assert filter2.get_stats() == {}

        reset_filter()
        filter3 = get_filter()
        # Niedrigerer Wert als Restart #2 – nach Restart trotzdem OK
        result3 = filter3.filter({"energy_yield_accumulated": 12050.0})
        assert result3["energy_yield_accumulated"] == 12050.0
        assert filter3.get_stats() == {}

    def test_no_zero_drop_on_restart(self):
        """Erster Cycle nach Restart erzeugt keinen Zero-Drop in Home Assistant."""
        instance = TotalIncreasingFilter()
        data = {
            "energy_yield_accumulated": 9799.5,
            "battery_charge_total": 1234.5,
            "energy_grid_exported": 5678.9,
        }

        result = instance.filter(data)

        assert result["energy_yield_accumulated"] == 9799.5
        assert result["battery_charge_total"] == 1234.5
        assert result["energy_grid_exported"] == 5678.9
        assert instance.get_stats() == {}, f"Unexpected filtering on first cycle: {instance.get_stats()}"

    def test_subsequent_cycles_after_restart_are_protected(self):
        """Nach Baseline: Steigende Werte akzeptiert, Drops gefiltert."""
        instance = TotalIncreasingFilter()

        instance.filter({"energy_yield_accumulated": 12345.6})
        assert instance.filter({"energy_yield_accumulated": 12346.2})["energy_yield_accumulated"] == 12346.2

        result = instance.filter({"energy_yield_accumulated": 12340.0})
        assert result["energy_yield_accumulated"] == 12346.2
        assert instance.get_stats() == {"energy_yield_accumulated": 1}

    def test_mixed_sensors_first_cycle_pass_through(self):
        """Erster Cycle mit total_increasing und anderen Sensoren – alle unverändert."""
        instance = TotalIncreasingFilter()
        data = {
            "energy_yield_accumulated": 12345.6,
            "battery_charge_total": 5678.9,
            "power_active": 4500,
            "battery_soc": 85.5,
            "voltage_PV1": 380.2,
        }

        result = instance.filter(data)

        assert result == data
        assert instance.get_stats() == {}

    def test_zero_values_on_first_cycle_accepted_as_baseline(self):
        """Zero-Werte beim ersten Cycle sind valider Startzustand (z.B. nachts)."""
        instance = TotalIncreasingFilter()
        data = {
            "energy_yield_accumulated": 0.0,
            "battery_charge_total": 0.0,
            "energy_grid_exported": 0.0,
        }

        result = instance.filter(data)

        assert result == data
        assert instance.get_stats() == {}

    def test_negative_values_filtered_even_on_first_cycle(self):
        """Negative Werte sind physikalisch unmöglich und werden immer entfernt."""
        instance = TotalIncreasingFilter()
        data = {
            "energy_yield_accumulated": -123.4,
            "battery_charge_total": 5678.9,
        }

        result = instance.filter(data)

        assert "energy_yield_accumulated" not in result
        assert result["battery_charge_total"] == 5678.9
        assert instance.get_stats() == {"energy_yield_accumulated": 1}


# ---------------------------------------------------------------------------
# TestSingletonBehavior
# ---------------------------------------------------------------------------


class TestSingletonBehavior:
    """Singleton-Verhalten von get_filter() über Restarts hinweg."""

    def test_get_filter_returns_same_instance(self):
        """Mehrere Aufrufe von get_filter() liefern dasselbe Objekt."""
        filter1 = get_filter()
        filter2 = get_filter()
        assert filter1 is filter2

    def test_reset_filter_creates_new_instance_on_next_call(self):
        """Nach reset_filter() liefert get_filter() ein frisches Objekt."""
        filter1 = get_filter()
        filter1.filter({"energy_yield_accumulated": 12345.6})

        reset_filter()
        filter2 = get_filter()

        assert filter2 is not filter1
        assert filter2.get_stats() == {}


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge Cases rund um das Restart-Szenario."""

    def test_very_small_increment_after_restart_accepted(self):
        """Winziger Increment (+0.001 kWh) nach Restart wird nicht gefiltert."""
        instance = get_filter()
        instance.filter({"energy_yield_accumulated": 12345.678})

        result = instance.filter({"energy_yield_accumulated": 12345.679})

        assert result["energy_yield_accumulated"] == 12345.679
        assert instance.get_stats() == {}

    def test_large_jump_after_restart_accepted(self):
        """Großer Sprung beim ersten Wert nach Restart wird akzeptiert."""
        instance = get_filter()

        result = instance.filter({"energy_yield_accumulated": 15000.0})

        assert result["energy_yield_accumulated"] == 15000.0
        assert instance.get_stats() == {}

    def test_no_total_increasing_keys_on_first_cycle(self):
        """Erster Cycle ohne total_increasing Keys gibt Daten unverändert zurück."""
        instance = get_filter()
        data = {"power_active": 4500, "battery_soc": 85, "voltage_PV1": 380}

        result = instance.filter(data)

        assert result == data
        assert instance.get_stats() == {}
