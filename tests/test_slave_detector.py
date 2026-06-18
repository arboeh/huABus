# tests/test_slave_detector.py

"""Tests for Auto Slave ID Detection."""

import asyncio
import logging
from unittest.mock import AsyncMock, patch

import pytest
from bridge.slave_detector import (
    INTER_ATTEMPT_DELAY,
    KNOWN_SLAVE_IDS,
    _test_slave_id,
    detect_slave_id,
)

# ---------------------------------------------------------------------------
# TestSlaveDetection
# ---------------------------------------------------------------------------


class TestSlaveDetection:
    """Hochrangige detect_slave_id()-Logik."""

    @pytest.mark.asyncio
    async def test_returns_first_working_slave_id(self):
        """Gibt die erste erfolgreiche Slave-ID zurück."""

        async def mock_test(host, port, slave_id, timeout):
            return slave_id == 1

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test):
            assert await detect_slave_id("192.168.1.100", 502) == 1

    @pytest.mark.asyncio
    async def test_tries_all_known_ids_in_order(self):
        """Alle bekannten IDs werden der Reihe nach probiert."""

        async def mock_test(host, port, slave_id, timeout):
            return slave_id == 100

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test) as mock:
            with patch("bridge.slave_detector.asyncio.sleep", new_callable=AsyncMock):
                result = await detect_slave_id("192.168.1.100", 502)

        assert result == 100
        assert mock.call_count == len(KNOWN_SLAVE_IDS)

    @pytest.mark.asyncio
    async def test_returns_none_when_all_ids_fail(self):
        """Gibt None zurück wenn alle IDs fehlschlagen."""

        async def mock_test(host, port, slave_id, timeout):
            return False

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test):
            with patch("bridge.slave_detector.asyncio.sleep", new_callable=AsyncMock):
                assert await detect_slave_id("192.168.1.100", 502) is None

    @pytest.mark.asyncio
    async def test_passes_custom_timeout_to_each_attempt(self):
        """Der übergebene timeout wird an _test_slave_id weitergegeben."""

        async def mock_test(host, port, slave_id, timeout):
            assert timeout == 10
            return slave_id == 1

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test):
            assert await detect_slave_id("192.168.1.100", 502, timeout=10) == 1

    @pytest.mark.asyncio
    async def test_no_delay_before_first_attempt(self):
        """Vor dem ersten Versuch gibt es keine Wartezeit."""
        sleep_calls = []

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)

        async def mock_test(host, port, slave_id, timeout):
            return slave_id == 1

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test):
            with patch("bridge.slave_detector.asyncio.sleep", side_effect=mock_sleep):
                await detect_slave_id("192.168.1.100", 502)

        assert sleep_calls == [], "No delay expected before first attempt"

    @pytest.mark.asyncio
    async def test_inter_attempt_delay_inserted_between_attempts(self):
        """INTER_ATTEMPT_DELAY wird zwischen allen Versuchen eingefügt (nicht davor)."""
        sleep_calls = []

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)

        async def mock_test(host, port, slave_id, timeout):
            return False

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test):
            with patch("bridge.slave_detector.asyncio.sleep", side_effect=mock_sleep):
                await detect_slave_id("192.168.1.100", 502)

        expected = [INTER_ATTEMPT_DELAY] * (len(KNOWN_SLAVE_IDS) - 1)
        assert sleep_calls == expected


# ---------------------------------------------------------------------------
# TestSlaveIdTesting
# ---------------------------------------------------------------------------


class TestSlaveIdTesting:
    """Einzelne _test_slave_id()-Aufrufe."""

    @pytest.mark.asyncio
    async def test_returns_true_on_valid_model_name(self):
        """Gibt True zurück wenn model_name gelesen werden kann."""
        mock_result = AsyncMock()
        mock_result.value = "SUN2000-6KTL-M1"
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_result

        with patch("bridge.slave_detector.AsyncHuaweiSolar.create", return_value=mock_client):
            result = await _test_slave_id("192.168.1.100", 502, 1, timeout=5)

        assert result is True
        mock_client.get.assert_called_once_with("model_name")
        mock_client.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self):
        """Gibt False zurück bei TimeoutError."""
        with patch("bridge.slave_detector.AsyncHuaweiSolar.create", side_effect=TimeoutError()):
            assert await _test_slave_id("192.168.1.100", 502, 1, timeout=1) is False

    @pytest.mark.asyncio
    async def test_returns_false_on_connection_refused(self):
        """Gibt False zurück bei ConnectionRefusedError."""
        with patch("bridge.slave_detector.AsyncHuaweiSolar.create", side_effect=ConnectionRefusedError()):
            assert await _test_slave_id("192.168.1.100", 502, 1, timeout=1) is False

    @pytest.mark.asyncio
    async def test_returns_false_on_empty_response(self):
        """Gibt False zurück wenn model_name None ist."""
        mock_result = AsyncMock()
        mock_result.value = None
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_result

        with patch("bridge.slave_detector.AsyncHuaweiSolar.create", return_value=mock_client):
            result = await _test_slave_id("192.168.1.100", 502, 1, timeout=5)

        assert result is False
        mock_client.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_called_even_on_read_error(self):
        """stop() wird auch bei Exception im get()-Aufruf aufgerufen."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Read error")

        with patch("bridge.slave_detector.AsyncHuaweiSolar.create", return_value=mock_client):
            result = await _test_slave_id("192.168.1.100", 502, 1, timeout=5)

        assert result is False
        mock_client.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_hanging_stop_does_not_block(self):
        """Hängendes stop() blockiert nicht dank wait_for-Timeout."""

        async def hanging_stop():
            await asyncio.sleep(999)

        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Read error")
        mock_client.stop = hanging_stop

        with patch("bridge.slave_detector.AsyncHuaweiSolar.create", return_value=mock_client):
            assert await _test_slave_id("192.168.1.100", 502, 1, timeout=5) is False

    @pytest.mark.asyncio
    async def test_cancelled_error_propagates(self):
        """CancelledError wird nicht geschluckt sondern weitergereicht."""
        with patch("bridge.slave_detector.AsyncHuaweiSolar.create", side_effect=asyncio.CancelledError()):
            with pytest.raises(asyncio.CancelledError):
                await _test_slave_id("192.168.1.100", 502, 1, timeout=5)


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Randfälle und Fehlerszenarien."""

    @pytest.mark.asyncio
    async def test_stops_after_first_success(self):
        """Weitere IDs werden nicht mehr getestet sobald eine funktioniert."""
        call_count = 0

        async def mock_test(host, port, slave_id, timeout):
            nonlocal call_count
            call_count += 1
            return call_count == 1

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test):
            result = await detect_slave_id("192.168.1.100", 502)

        assert result == KNOWN_SLAVE_IDS[0]
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_non_standard_port_passed_through(self):
        """Nicht-Standard-Port wird korrekt weitergegeben."""

        async def mock_test(host, port, slave_id, timeout):
            assert port == 5020
            return slave_id == 1

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test):
            assert await detect_slave_id("192.168.1.100", 5020) == 1

    @pytest.mark.asyncio
    async def test_logs_failure_summary_with_known_ids(self, caplog):
        """Bei vollständigem Fehlschlag wird eine Zusammenfassung geloggt."""
        caplog.set_level(logging.INFO)

        with patch("bridge.slave_detector.AsyncHuaweiSolar.create", side_effect=Exception("fail")):
            with patch("bridge.slave_detector.asyncio.sleep", new_callable=AsyncMock):
                result = await detect_slave_id("192.168.1.100", 502)

        assert result is None
        assert "Auto-detection failed" in caplog.text
        assert "[1, 2, 100]" in caplog.text


# ---------------------------------------------------------------------------
# TestSlaveDetector
# ---------------------------------------------------------------------------


class TestSlaveDetector:
    """SlaveDetector-Klasse (zustandsbehaftet)."""

    @pytest.mark.asyncio
    async def test_init_stores_host_and_port(self):
        from bridge.slave_detector import SlaveDetector

        detector = SlaveDetector("192.168.1.100", 5020)

        assert detector.host == "192.168.1.100"
        assert detector.port == 5020

    @pytest.mark.asyncio
    async def test_detect_delegates_to_detect_slave_id(self):
        from bridge.slave_detector import SlaveDetector

        detector = SlaveDetector("192.168.1.100", 502)

        with patch("bridge.slave_detector.detect_slave_id", new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = 1
            result = await detector.detect(timeout=10)

        assert result == 1
        mock_detect.assert_called_once_with("192.168.1.100", 502, 10)
