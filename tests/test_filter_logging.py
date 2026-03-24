# tests/test_filter_logging.py

"""Tests for logging behavior of TotalIncreasingFilter."""

import logging

from bridge.total_increasing_filter import get_filter, reset_filter


def test_filter_logs_with_shield_icon(caplog):
    """Filter should log with 🛡️ icon when filtering values."""
    caplog.set_level(logging.WARNING)
    reset_filter()
    filter_instance = get_filter()

    # Setup: First value
    filter_instance.filter({"energy_grid_exported": 1000.0})

    # Trigger filter (drop to zero)
    caplog.clear()
    filter_instance.filter({"energy_grid_exported": 0})

    # Check logging
    assert "🛡️" in caplog.text or "FILTERED" in caplog.text
    assert "energy_grid_exported" in caplog.text


def test_filter_logs_drop_details(caplog):
    """Filter should log drop details (old → new)."""
    caplog.set_level(logging.WARNING)
    reset_filter()
    filter_instance = get_filter()

    filter_instance.filter({"energy_grid_exported": 5432.1})

    caplog.clear()
    filter_instance.filter({"energy_grid_exported": 0})

    # Should show: 5432.1 → 0 (filtered)
    assert "5432.1" in caplog.text
    assert "0" in caplog.text or "drop" in caplog.text.lower()


def test_filter_does_not_log_valid_values(caplog):
    """Filter should NOT log when values are valid."""
    caplog.set_level(logging.WARNING)
    reset_filter()
    filter_instance = get_filter()

    filter_instance.filter({"energy_grid_exported": 1000.0})

    caplog.clear()
    filter_instance.filter({"energy_grid_exported": 1001.0})

    # No filter warnings
    assert "FILTERED" not in caplog.text
    assert "🛡️" not in caplog.text


def test_filter_logs_multiple_keys_filtered(caplog):
    """Filter should log each filtered key separately."""
    caplog.set_level(logging.WARNING)
    reset_filter()
    filter_instance = get_filter()

    # Setup
    filter_instance.filter(
        {
            "energy_grid_exported": 1000.0,
            "energy_yield_accumulated": 5000.0,
        }
    )

    # Both drop to zero
    caplog.clear()
    filter_instance.filter(
        {
            "energy_grid_exported": 0,
            "energy_yield_accumulated": 0,
        }
    )

    # Both should be logged
    assert caplog.text.count("🛡️") >= 2 or caplog.text.count("FILTERED") >= 2
