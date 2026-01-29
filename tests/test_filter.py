"""Unit-Tests für TotalIncreasingFilter"""

from modbus_energy_meter.total_increasing_filter import (
    TotalIncreasingFilter,
)


class TestTotalIncreasingFilter:
    """Test-Suite für Filter-Logik"""

    def test_first_value_accepted(self):
        """Erster Wert wird immer akzeptiert (auch 0)"""
        filter_instance = TotalIncreasingFilter()

        # Erste Werte verschiedener Sensoren
        assert filter_instance.should_filter("energy_grid_exported", 0) is False
        assert filter_instance.should_filter("energy_yield_accumulated", 0.03) is False
        assert filter_instance.should_filter("battery_charge_total", 100.5) is False

    def test_increasing_values_accepted(self):
        """Steigende Werte werden immer akzeptiert"""
        filter_instance = TotalIncreasingFilter()

        # Sequenz: 0 → 0.03 → 0.15
        filter_instance.should_filter("energy_grid_exported", 0)
        assert filter_instance.should_filter("energy_grid_exported", 0.03) is False
        assert filter_instance.should_filter("energy_grid_exported", 0.15) is False

    def test_equal_values_accepted(self):
        """Gleiche Werte werden akzeptiert (kein Anstieg, aber kein Drop)"""
        filter_instance = TotalIncreasingFilter()

        filter_instance.should_filter("energy_grid_exported", 100.0)
        assert filter_instance.should_filter("energy_grid_exported", 100.0) is False

    def test_drop_to_zero_filtered(self):
        """Drop von 5432 auf 0 wird gefiltert"""
        filter_instance = TotalIncreasingFilter()

        filter_instance.should_filter("energy_grid_exported", 5432.1)
        assert filter_instance.should_filter("energy_grid_exported", 0) is True

        # Letzter gültiger Wert sollte erhalten bleiben
        assert filter_instance.get_last_value("energy_grid_exported") == 5432.1

    def test_tolerance_threshold_accepted(self):
        """4.9% Drop wird akzeptiert (innerhalb 5% Toleranz)"""
        filter_instance = TotalIncreasingFilter(tolerance=0.05)

        filter_instance.should_filter("energy_grid_exported", 10000.0)

        # 4.9% Drop → Akzeptiert (innerhalb Toleranz)
        assert filter_instance.should_filter("energy_grid_exported", 9510.0) is False

    def test_tolerance_threshold_filtered(self):
        """5.1% Drop wird gefiltert (außerhalb 5% Toleranz)"""
        filter_instance = TotalIncreasingFilter(tolerance=0.05)

        filter_instance.should_filter("energy_grid_exported", 10000.0)

        # 5.1% Drop → Gefiltert (außerhalb Toleranz)
        assert filter_instance.should_filter("energy_grid_exported", 9490.0) is True

    def test_negative_values_filtered(self):
        """Negative Werte werden immer gefiltert"""
        filter_instance = TotalIncreasingFilter()

        filter_instance.should_filter("energy_grid_exported", 5432.1)
        assert filter_instance.should_filter("energy_grid_exported", -10) is True
        assert filter_instance.should_filter("energy_grid_exported", -0.5) is True

    def test_non_energy_sensors_not_filtered(self):
        """Nicht-Energy-Sensoren werden nicht gefiltert"""
        filter_instance = TotalIncreasingFilter()

        # power_active ist kein total_increasing Sensor
        filter_instance.should_filter("power_active", 5000)
        assert filter_instance.should_filter("power_active", 0) is False  # Kein Filter!

    def test_filter_statistics(self):
        """Filter-Statistik wird korrekt gezählt"""
        filter_instance = TotalIncreasingFilter()

        # Setup
        filter_instance.should_filter("energy_grid_exported", 5432.1)
        filter_instance.should_filter("battery_charge_total", 4804.5)

        # Fehler provozieren
        filter_instance.should_filter("energy_grid_exported", 0)  # Gefiltert
        filter_instance.should_filter("battery_charge_total", 0)  # Gefiltert
        filter_instance.should_filter("energy_grid_exported", 0)  # Nochmal gefiltert

        stats = filter_instance.get_stats()
        assert stats["energy_grid_exported"] == 2
        assert stats["battery_charge_total"] == 1

    def test_reset_clears_state(self):
        """Reset löscht alle gespeicherten Werte"""
        filter_instance = TotalIncreasingFilter()

        # Werte setzen
        filter_instance.should_filter("energy_grid_exported", 5432.1)
        assert filter_instance.get_last_value("energy_grid_exported") == 5432.1

        # Reset
        filter_instance.reset()

        # Nach Reset: Kein gespeicherter Wert mehr
        assert filter_instance.get_last_value("energy_grid_exported") is None
