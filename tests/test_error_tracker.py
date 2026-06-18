# tests/test_error_tracker.py

"""Tests für Connection Error Tracker."""

import logging
from unittest.mock import patch

from bridge.error_tracker import ConnectionErrorTracker

# ---------------------------------------------------------------------------
# TestBasicErrorTracking
# ---------------------------------------------------------------------------


class TestBasicErrorTracking:
    """Grundlegende Fehler-Tracking-Funktionalität."""

    def test_first_error_is_logged(self, caplog):
        """Erster Verbindungsfehler wird sofort auf ERROR-Level geloggt."""
        tracker = ConnectionErrorTracker(log_interval=60)

        result = tracker.track_error("timeout", "Connection timed out")

        assert result is True
        assert "Connection error: timeout" in caplog.text
        assert "ERROR" in caplog.text

    def test_repeated_error_within_interval_not_logged(self, caplog):
        """Gleicher Fehler innerhalb des Intervals wird nicht nochmal geloggt."""
        tracker = ConnectionErrorTracker(log_interval=60)

        tracker.track_error("timeout", "Connection timed out")
        assert len(caplog.records) == 1

        caplog.clear()
        result = tracker.track_error("timeout", "Connection timed out")

        assert result is False
        assert len(caplog.records) == 0
        assert tracker.get_status()["total_failures"] == 2

    def test_repeated_error_after_interval_is_logged(self, caplog):
        """Fehler nach Ablauf des Intervals wird als WARNING mit Aggregation geloggt."""
        tracker = ConnectionErrorTracker(log_interval=60)

        with patch("bridge.error_tracker.time.time", return_value=1000.0):
            tracker.track_error("timeout", "Connection timed out")

        with patch("bridge.error_tracker.time.time", return_value=1010.0):
            tracker.track_error("timeout", "Connection timed out")

        caplog.clear()
        with patch("bridge.error_tracker.time.time", return_value=1065.0):
            result = tracker.track_error("timeout", "Connection timed out")

        assert result is True
        assert "Still failing: timeout" in caplog.text
        assert "3 attempts" in caplog.text
        assert "WARNING" in caplog.text


# ---------------------------------------------------------------------------
# TestRecoveryScenarios
# ---------------------------------------------------------------------------


class TestRecoveryScenarios:
    """Recovery-Logging und Downtime-Berechnung."""

    def test_recovery_logs_downtime_and_stats(self, caplog):
        """Recovery-Log enthält Downtime, Fehleranzahl und Fehlertypen."""
        caplog.set_level(logging.INFO, logger="huawei.errors")
        tracker = ConnectionErrorTracker(log_interval=60)

        with patch("time.time") as mock_time:
            mock_time.return_value = 1000.0
            tracker.track_error("timeout", "Connection timed out")

            for i in range(1, 10):
                mock_time.return_value = 1000.0 + i * 30
                tracker.track_error("timeout", "Connection timed out")

            mock_time.return_value = 1300.0
            tracker.mark_success()

        assert "Connection restored" in caplog.text
        assert "after 300s" in caplog.text
        assert "10 failed attempts" in caplog.text
        assert "1 error types" in caplog.text

    def test_recovery_resets_error_state(self, caplog):
        """Nach Recovery ist der Error-State vollständig zurückgesetzt."""
        caplog.set_level(logging.INFO, logger="huawei.errors")
        tracker = ConnectionErrorTracker(log_interval=60)

        tracker.track_error("timeout", "Error 1")
        tracker.mark_success()

        status = tracker.get_status()
        assert status["active_errors"] == 0
        assert status["total_failures"] == 0

        result = tracker.track_error("connection_refused", "Error 2")
        assert result is True

    def test_no_recovery_log_if_no_errors(self, caplog):
        """mark_success() ohne vorherige Fehler erzeugt keinen Log-Eintrag."""
        caplog.set_level(logging.INFO, logger="huawei.errors")
        tracker = ConnectionErrorTracker(log_interval=60)

        caplog.clear()
        tracker.mark_success()

        assert len(caplog.records) == 0


# ---------------------------------------------------------------------------
# TestMultipleErrorTypes
# ---------------------------------------------------------------------------


class TestMultipleErrorTypes:
    """Aggregation verschiedener Fehlertypen."""

    def test_different_error_types_tracked_separately(self):
        """Verschiedene Fehlertypen werden separat gezählt."""
        tracker = ConnectionErrorTracker(log_interval=60)

        tracker.track_error("timeout", "Network timeout")
        tracker.track_error("modbus_exception", "Invalid register")

        status = tracker.get_status()
        assert status["active_errors"] == 2
        assert status["total_failures"] == 2

    def test_recovery_shows_multiple_error_types(self, caplog):
        """Recovery-Log zeigt die korrekte Anzahl verschiedener Fehlertypen."""
        caplog.set_level(logging.INFO, logger="huawei.errors")
        tracker = ConnectionErrorTracker(log_interval=60)

        with patch("time.time") as mock_time:
            mock_time.return_value = 1000.0
            tracker.track_error("timeout", "Network")
            tracker.track_error("modbus_exception", "Protocol")
            tracker.track_error("connection_refused", "Inverter offline")

            mock_time.return_value = 1100.0
            tracker.mark_success()

        assert "3 error types" in caplog.text

    def test_each_error_type_has_own_log_interval(self, caplog):
        """Fehlertypen haben unabhängige Log-Intervals."""
        tracker = ConnectionErrorTracker(log_interval=60)

        with patch("bridge.error_tracker.time.time", return_value=1000.0):
            assert tracker.track_error("timeout", "Error 1") is True

        caplog.clear()
        with patch("bridge.error_tracker.time.time", return_value=1010.0):
            result = tracker.track_error("modbus_exception", "Error 2")
            assert result is True
            assert len(caplog.records) == 1


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge Cases und Grenzfälle."""

    def test_inverter_offline_at_night_does_not_flood_logs(self):
        """240 Fehler über 2 Stunden erzeugen nur ~80 Log-Einträge."""
        tracker = ConnectionErrorTracker(log_interval=60)

        log_count = 0
        for i in range(240):
            with patch("bridge.error_tracker.time.time", return_value=1000.0 + i * 30):
                if tracker.track_error("timeout", "Inverter offline"):
                    log_count += 1

        assert log_count == 80

    def test_rapid_error_type_changes(self):
        """Wechselnde Fehlertypen: jeder neue Typ wird sofort geloggt, Wiederholung nicht."""
        tracker = ConnectionErrorTracker(log_interval=60)

        assert tracker.track_error("timeout", "Error 1") is True
        assert tracker.track_error("modbus_exception", "Error 2") is True
        assert tracker.track_error("timeout", "Error 3") is False

    def test_downtime_calculated_from_earliest_error(self, caplog):
        """Downtime wird ab dem ersten Fehler berechnet, nicht ab dem letzten."""
        caplog.set_level(logging.INFO, logger="huawei.errors")
        tracker = ConnectionErrorTracker(log_interval=60)

        with patch("time.time") as mock_time:
            mock_time.return_value = 1000.0
            tracker.track_error("timeout", "First error")

            mock_time.return_value = 1050.0
            tracker.track_error("modbus_exception", "Second error type")

            mock_time.return_value = 1200.0
            tracker.mark_success()

        assert "after 200s" in caplog.text


# ---------------------------------------------------------------------------
# TestStatusReporting
# ---------------------------------------------------------------------------


class TestStatusReporting:
    """get_status() für Diagnostik."""

    def test_status_empty_on_init(self):
        """Initialer Status zeigt keine Fehler."""
        status = ConnectionErrorTracker().get_status()
        assert status["active_errors"] == 0
        assert status["total_failures"] == 0
        assert status["last_success"] is None

    def test_status_reflects_current_errors(self):
        """Status spiegelt aktuelle Fehler und Typen korrekt wider."""
        tracker = ConnectionErrorTracker()

        tracker.track_error("timeout", "Error 1")
        tracker.track_error("timeout", "Error 2")
        tracker.track_error("modbus_exception", "Error 3")

        status = tracker.get_status()
        assert status["active_errors"] == 2
        assert status["total_failures"] == 3

    def test_status_updates_after_success(self):
        """Status wird nach mark_success() vollständig zurückgesetzt."""
        tracker = ConnectionErrorTracker()

        with patch("bridge.error_tracker.time.time", return_value=1000.0):
            tracker.track_error("timeout", "Error")
            tracker.mark_success()

        status = tracker.get_status()
        assert status["active_errors"] == 0
        assert status["total_failures"] == 0
        assert status["last_success"] == 1000.0
