# tests\test_error_tracker.py

"""
Tests für Connection Error Tracker - Korrigierte Version
"""

import logging
from unittest.mock import patch

from modbus_energy_meter.error_tracker import ConnectionErrorTracker


class TestBasicErrorTracking:
    """Test grundlegende Fehler-Tracking-Funktionalität."""

    def test_first_error_is_logged(self, caplog):
        """
        Szenario: Erster Verbindungsfehler tritt auf.
        Erwartung: Fehler wird sofort geloggt (ERROR-Level).
        """
        tracker = ConnectionErrorTracker(log_interval=60)

        result = tracker.track_error("timeout", "Connection timed out")

        assert result is True  # Fehler wurde geloggt
        assert "Connection error: timeout" in caplog.text
        assert "ERROR" in caplog.text

    def test_repeated_error_within_interval_not_logged(self, caplog):
        """
        Szenario: Gleicher Fehler tritt nach 10s wieder auf (< 60s Interval).
        Erwartung: Fehler wird NICHT nochmal geloggt (Log-Spam-Prevention).
        Fachlich: Verhindert 20 identische Logs bei 10-minütigem Ausfall.
        """
        tracker = ConnectionErrorTracker(log_interval=60)

        # Erster Fehler
        caplog.clear()
        tracker.track_error("timeout", "Connection timed out")
        assert len(caplog.records) == 1  # 1 Log-Eintrag

        # Gleicher Fehler nach 10s (simuliert durch sofortigen zweiten Call)
        caplog.clear()
        result = tracker.track_error("timeout", "Connection timed out")

        assert result is False  # Fehler wurde NICHT geloggt
        assert len(caplog.records) == 0  # Kein neuer Log-Eintrag

        # Aber Counter wurde erhöht
        status = tracker.get_status()
        assert status["total_failures"] == 2

    def test_repeated_error_after_interval_is_logged(self, caplog):
        """
        Szenario: Fehler tritt nach 65s wieder auf (> 60s Interval).
        Erwartung: Aggregiertes Update wird geloggt (WARNING-Level).
        Fachlich: Zeigt an dass Problem weiterhin besteht.
        """
        tracker = ConnectionErrorTracker(log_interval=60)

        # Erster Fehler
        with patch("modbus_energy_meter.error_tracker.time.time", return_value=1000.0):
            tracker.track_error("timeout", "Connection timed out")

        # Zweiter Fehler nach 10s (wird nicht geloggt)
        with patch("modbus_energy_meter.error_tracker.time.time", return_value=1010.0):
            tracker.track_error("timeout", "Connection timed out")

        # Dritter Fehler nach 65s (wird geloggt)
        caplog.clear()
        with patch("modbus_energy_meter.error_tracker.time.time", return_value=1065.0):
            result = tracker.track_error("timeout", "Connection timed out")

        assert result is True  # Fehler wurde geloggt
        assert "Still failing: timeout" in caplog.text
        assert "3 attempts" in caplog.text  # 3 Versuche gezählt
        assert "WARNING" in caplog.text  # WARNING-Level (nicht ERROR)


class TestRecoveryScenarios:
    """Test Recovery-Logging und Downtime-Berechnung."""

    def test_recovery_logs_downtime_and_stats(self, caplog):
        """
        Szenario: Nach 5 Minuten Ausfall (10 Fehler) wird Verbindung wiederhergestellt.
        Erwartung: Recovery-Log mit Downtime, Fehleranzahl und Fehlertypen.
        Fachlich: Wichtig für Monitoring - wie lange war System offline?
        """
        caplog.set_level(logging.INFO, logger="huawei.errors")
        tracker = ConnectionErrorTracker(log_interval=60)

        # PATCH das time module selbst
        with patch("time.time") as mock_time:
            # Erster Fehler bei t=1000
            mock_time.return_value = 1000.0
            tracker.track_error("timeout", "Connection timed out")

            # 9 weitere Fehler (simuliert 5 Minuten mit 30s Poll-Interval)
            for i in range(1, 10):
                mock_time.return_value = 1000.0 + i * 30
                tracker.track_error("timeout", "Connection timed out")

            # Recovery nach 5 Minuten (300s)
            mock_time.return_value = 1300.0
            tracker.mark_success()

        # Jetzt prüfen
        assert "Connection restored" in caplog.text
        assert "after 300s" in caplog.text
        assert "10 failed attempts" in caplog.text
        assert "1 error types" in caplog.text

    def test_recovery_resets_error_state(self, caplog):
        """
        Szenario: Nach Recovery tritt neuer Fehler auf.
        Erwartung: Error-State wurde zurückgesetzt, neuer Fehler wird wieder geloggt.
        Fachlich: Verhindert dass alte Fehler neue Fehler beeinflussen.
        """
        caplog.set_level(logging.INFO, logger="huawei.errors")
        tracker = ConnectionErrorTracker(log_interval=60)

        # Fehler + Recovery
        tracker.track_error("timeout", "Error 1")
        tracker.mark_success()

        # Status sollte zurückgesetzt sein
        status = tracker.get_status()
        assert status["active_errors"] == 0
        assert status["total_failures"] == 0

        # Neuer Fehler sollte wieder als "erster" geloggt werden
        result = tracker.track_error("connection_refused", "Error 2")
        assert result is True  # Wird geloggt (neuer Fehlertyp)

    def test_no_recovery_log_if_no_errors(self, caplog):
        """
        Szenario: mark_success() ohne vorherige Fehler.
        Erwartung: Kein Recovery-Log (war ja nichts kaputt).
        Fachlich: Vermeidet sinnlose "Connection restored" Logs bei stabilem Betrieb.
        """
        caplog.set_level(logging.INFO, logger="huawei.errors")
        tracker = ConnectionErrorTracker(log_interval=60)

        caplog.clear()
        tracker.mark_success()

        # Kein Log-Eintrag, da keine Fehler vorhanden waren
        assert len(caplog.records) == 0


class TestMultipleErrorTypes:
    """Test Aggregation verschiedener Fehlertypen."""

    def test_different_error_types_tracked_separately(self):
        """
        Szenario: Timeout-Fehler UND Modbus-Exception treten auf.
        Erwartung: Beide werden separat gezählt und geloggt.
        Fachlich: Zeigt verschiedene Fehlerursachen (Netzwerk vs. Protokoll).
        """
        tracker = ConnectionErrorTracker(log_interval=60)

        tracker.track_error("timeout", "Network timeout")
        tracker.track_error("modbus_exception", "Invalid register")

        status = tracker.get_status()
        assert status["active_errors"] == 2  # 2 verschiedene Fehlertypen
        assert status["total_failures"] == 2  # Insgesamt 2 Fehler

    def test_recovery_shows_multiple_error_types(self, caplog):
        """
        Szenario: 3 verschiedene Fehlertypen während Downtime.
        Erwartung: Recovery-Log zeigt "3 error types".
        Fachlich: Hilft bei Diagnose - war es nur Netzwerk oder mehrere Probleme?
        """
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
        """
        Szenario: Timeout alle 10s, Modbus-Exception alle 10s.
        Erwartung: Beide werden unabhängig voneinander nach ihrem Interval geloggt.
        Fachlich: Ein Fehlertyp blockiert nicht das Logging anderer Typen.
        """
        tracker = ConnectionErrorTracker(log_interval=60)

        # Erster Timeout bei t=1000
        with patch("modbus_energy_meter.error_tracker.time.time", return_value=1000.0):
            result1 = tracker.track_error("timeout", "Error 1")
            assert result1 is True  # Geloggt

        # Erste Modbus-Exception bei t=1010 (anderer Typ!)
        caplog.clear()
        with patch("modbus_energy_meter.error_tracker.time.time", return_value=1010.0):
            result2 = tracker.track_error("modbus_exception", "Error 2")
            assert result2 is True  # Auch geloggt (neuer Typ)
            assert len(caplog.records) == 1


class TestEdgeCases:
    """Test Edge Cases und Grenzfälle."""

    def test_inverter_offline_at_night_normal_operation(self):
        """
        Szenario: Inverter ist nachts 2 Stunden offline (240 Fehler bei 30s Poll).
        Erwartung: Nur ~80 Logs (erster + alle 90s real time), nicht 240 Logs.
        Fachlich: Nachts offline ist NORMAL, sollte Log nicht fluten.
        """
        tracker = ConnectionErrorTracker(log_interval=60)

        # Simuliere 240 Fehler über 2 Stunden (30s Interval)
        log_count = 0
        for i in range(240):
            with patch(
                "modbus_energy_meter.error_tracker.time.time",
                return_value=1000.0 + i * 30,
            ):
                if tracker.track_error("timeout", "Inverter offline"):
                    log_count += 1

        # Bei 30s Poll und 60s interval:
        # Erster Call (i=0): geloggt
        # Nach 60s (i=2): geloggt
        # Nach 120s (i=4): geloggt
        # ...
        # 240 Calls * 30s = 7200s
        # Logs alle 90s (3 calls): 7200s / 90s = 80 Logs
        assert log_count == 80  # Exakt: 1 + (240-1)/3 = 1 + 79.67 ≈ 80

    def test_rapid_error_changes(self):
        """
        Szenario: Fehlertyp wechselt ständig (timeout → modbus → timeout → modbus).
        Erwartung: Jeder Wechsel wird als "neuer erster Fehler" behandelt.
        Fachlich: Instabile Verbindung mit wechselnden Fehlerursachen.
        """
        tracker = ConnectionErrorTracker(log_interval=60)

        result1 = tracker.track_error("timeout", "Error 1")
        result2 = tracker.track_error("modbus_exception", "Error 2")
        result3 = tracker.track_error("timeout", "Error 3")  # Wieder timeout

        assert result1 is True  # Erster timeout geloggt
        assert result2 is True  # Erster modbus geloggt
        assert result3 is False  # Zweiter timeout NICHT geloggt (< interval)

    def test_downtime_calculation_uses_earliest_error(self, caplog):
        """
        Szenario: Timeout bei t=1000, dann Modbus-Error bei t=1050, Recovery bei t=1200.
        Erwartung: Downtime = 200s (ab erstem Timeout), nicht 150s (ab Modbus-Error).
        Fachlich: Downtime = Zeitraum ALLER Probleme, nicht nur letzter Fehler.
        """
        caplog.set_level(logging.INFO, logger="huawei.errors")
        tracker = ConnectionErrorTracker(log_interval=60)

        with patch("time.time") as mock_time:
            mock_time.return_value = 1000.0
            tracker.track_error("timeout", "First error")

            mock_time.return_value = 1050.0
            tracker.track_error("modbus_exception", "Second error type")

            mock_time.return_value = 1200.0
            tracker.mark_success()

        assert "after 200s" in caplog.text  # Nicht 150s!


class TestStatusReporting:
    """Test get_status() für Diagnostik."""

    def test_status_empty_on_init(self):
        """Initialer Status zeigt keine Fehler."""
        tracker = ConnectionErrorTracker()
        status = tracker.get_status()

        assert status["active_errors"] == 0
        assert status["total_failures"] == 0
        assert status["last_success"] is None

    def test_status_shows_current_error_state(self):
        """Status spiegelt aktuelle Fehler wider."""
        tracker = ConnectionErrorTracker()

        tracker.track_error("timeout", "Error 1")
        tracker.track_error("timeout", "Error 2")
        tracker.track_error("modbus_exception", "Error 3")

        status = tracker.get_status()
        assert status["active_errors"] == 2  # 2 Typen
        assert status["total_failures"] == 3  # 3 Fehler

    def test_status_updates_after_success(self):
        """Status wird nach mark_success() aktualisiert."""
        tracker = ConnectionErrorTracker()

        with patch("modbus_energy_meter.error_tracker.time.time", return_value=1000.0):
            tracker.track_error("timeout", "Error")
            tracker.mark_success()

        status = tracker.get_status()
        assert status["active_errors"] == 0  # Zurückgesetzt
        assert status["total_failures"] == 0  # Zurückgesetzt
        assert status["last_success"] == 1000.0  # Timestamp gesetzt
