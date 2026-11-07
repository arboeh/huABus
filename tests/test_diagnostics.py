# tests/test_diagnostics.py

"""Tests for diagnostics.py - Bridge diagnostic values."""

import pytest
from bridge.diagnostics import build_bridge_diagnostics
from bridge.error_tracker import ConnectionErrorTracker


@pytest.fixture
def tracker():
    return ConnectionErrorTracker(log_interval=60)


class TestBuildBridgeDiagnostics:
    """Reine Funktion: Werte und Typen der bridge_* Keys."""

    def test_contains_exactly_the_bridge_keys(self, tracker):
        result = build_bridge_diagnostics(
            tracker, start_time=1000.0, cycle_duration=1.5, batch_mode="batch", now=1100.0
        )
        assert set(result) == {"bridge_errors", "bridge_cycle_duration", "bridge_uptime", "bridge_batch_mode"}

    def test_values_and_types(self, tracker):
        tracker.track_error("timeout", "x")
        tracker.track_error("timeout", "x")

        result = build_bridge_diagnostics(
            tracker, start_time=1000.0, cycle_duration=1.2345, batch_mode="fallback", now=1090.7
        )

        assert result["bridge_errors"] == 2
        assert isinstance(result["bridge_errors"], int)
        assert result["bridge_uptime"] == 90
        assert isinstance(result["bridge_uptime"], int)
        assert result["bridge_cycle_duration"] == pytest.approx(1.23, abs=0.01)
        assert isinstance(result["bridge_cycle_duration"], float)
        assert result["bridge_batch_mode"] == "fallback"

    @pytest.mark.parametrize("mode", ["batch", "fallback", "sequential"])
    def test_batch_mode_passed_through(self, tracker, mode):
        result = build_bridge_diagnostics(tracker, start_time=0.0, cycle_duration=0.1, batch_mode=mode, now=1.0)
        assert result["bridge_batch_mode"] == mode

    def test_uptime_never_negative(self, tracker):
        """Uhr-Sprung rückwärts darf keine negative Uptime ergeben."""
        result = build_bridge_diagnostics(
            tracker, start_time=2000.0, cycle_duration=0.1, batch_mode="batch", now=1000.0
        )
        assert result["bridge_uptime"] == 0

    def test_cycle_duration_never_negative(self, tracker):
        result = build_bridge_diagnostics(tracker, start_time=0.0, cycle_duration=-0.5, batch_mode="batch", now=1.0)
        assert result["bridge_cycle_duration"] == 0.0

    def test_now_defaults_to_current_time(self, tracker):
        result = build_bridge_diagnostics(tracker, start_time=0.0, cycle_duration=0.1, batch_mode="batch")
        assert result["bridge_uptime"] > 0

    def test_does_not_mutate_tracker(self, tracker):
        tracker.track_error("timeout", "x")
        before = (tracker.lifetime_failures, dict(tracker.errors))

        build_bridge_diagnostics(tracker, start_time=0.0, cycle_duration=0.1, batch_mode="batch", now=1.0)

        assert (tracker.lifetime_failures, dict(tracker.errors)) == before

    def test_errors_survive_recovery(self, tracker):
        tracker.track_error("timeout", "x")
        tracker.mark_success()

        result = build_bridge_diagnostics(tracker, start_time=0.0, cycle_duration=0.1, batch_mode="batch", now=1.0)

        assert result["bridge_errors"] == 1
