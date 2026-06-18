# tests/test_filter_logging.py

"""Tests for logging behavior of TotalIncreasingFilter."""

import logging

from bridge.total_increasing_filter import get_filter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_filter_with_baseline(key, value):
    """Returns a fresh filter instance with one baseline value already set."""
    instance = get_filter()
    instance.filter({key: value})
    return instance


# ---------------------------------------------------------------------------
# TestFilterLogging
# ---------------------------------------------------------------------------


class TestFilterLogging:
    """Logging-Verhalten des TotalIncreasingFilter."""

    def test_filtered_value_logs_shield_icon_or_filtered_keyword(self, caplog):
        """Bei gefiltertem Wert erscheint 🛡️ oder 'FILTERED' im Log."""
        caplog.set_level(logging.WARNING)
        instance = _setup_filter_with_baseline("energy_grid_exported", 1000.0)

        caplog.clear()
        instance.filter({"energy_grid_exported": 0})

        assert "🛡️" in caplog.text or "FILTERED" in caplog.text
        assert "energy_grid_exported" in caplog.text

    def test_filtered_value_logs_drop_details(self, caplog):
        """Log enthält alten und neuen Wert beim Filtern."""
        caplog.set_level(logging.WARNING)
        instance = _setup_filter_with_baseline("energy_grid_exported", 5432.1)

        caplog.clear()
        instance.filter({"energy_grid_exported": 0})

        assert "5432.1" in caplog.text
        assert "0" in caplog.text or "drop" in caplog.text.lower()

    def test_valid_increasing_value_produces_no_warning(self, caplog):
        """Gültige aufsteigende Werte erzeugen keine Filter-Warnung."""
        caplog.set_level(logging.WARNING)
        instance = _setup_filter_with_baseline("energy_grid_exported", 1000.0)

        caplog.clear()
        instance.filter({"energy_grid_exported": 1001.0})

        assert "FILTERED" not in caplog.text
        assert "🛡️" not in caplog.text

    def test_multiple_filtered_keys_each_logged(self, caplog):
        """Jeder gefilterte Key wird separat geloggt."""
        caplog.set_level(logging.WARNING)
        instance = get_filter()
        instance.filter(
            {
                "energy_grid_exported": 1000.0,
                "energy_yield_accumulated": 5000.0,
            }
        )

        caplog.clear()
        instance.filter(
            {
                "energy_grid_exported": 0,
                "energy_yield_accumulated": 0,
            }
        )

        assert caplog.text.count("🛡️") >= 2 or caplog.text.count("FILTERED") >= 2
