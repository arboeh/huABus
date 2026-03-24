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


class TestSlaveDetection:
    """Test auto Slave ID detection."""

    @pytest.mark.asyncio
    async def test_detect_slave_id_finds_first_working(self):
        """Test detection finds first working Slave ID (1)."""

        async def mock_test(host, port, slave_id, timeout):
            return slave_id == 1

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test):
            result = await detect_slave_id("192.168.1.100", 502)

            assert result == 1

    @pytest.mark.asyncio
    async def test_detect_slave_id_tries_all_ids(self):
        """Test detection tries all known IDs in order."""

        async def mock_test(host, port, slave_id, timeout):
            return slave_id == 100

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test) as mock:
            # Patch sleep so the test doesn't actually wait
            with patch("bridge.slave_detector.asyncio.sleep", new_callable=AsyncMock):
                result = await detect_slave_id("192.168.1.100", 502)

                assert result == 100
                assert mock.call_count == len(KNOWN_SLAVE_IDS)

    @pytest.mark.asyncio
    async def test_detect_slave_id_returns_none_on_failure(self):
        """Test detection returns None if all IDs fail."""

        async def mock_test(host, port, slave_id, timeout):
            return False

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test):
            with patch("bridge.slave_detector.asyncio.sleep", new_callable=AsyncMock):
                result = await detect_slave_id("192.168.1.100", 502)

                assert result is None

    @pytest.mark.asyncio
    async def test_detect_slave_id_uses_custom_timeout(self):
        """Test detection passes custom timeout to each attempt."""

        async def mock_test(host, port, slave_id, timeout):
            assert timeout == 10
            return slave_id == 1

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test):
            result = await detect_slave_id("192.168.1.100", 502, timeout=10)

            assert result == 1

    @pytest.mark.asyncio
    async def test_detect_slave_id_no_delay_before_first_attempt(self):
        """Test that no delay is inserted before the very first attempt."""

        sleep_calls = []

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)

        async def mock_test(host, port, slave_id, timeout):
            return slave_id == 1  # First ID succeeds immediately

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test):
            with patch("bridge.slave_detector.asyncio.sleep", side_effect=mock_sleep):
                await detect_slave_id("192.168.1.100", 502)

                assert sleep_calls == [], "No delay expected before first attempt"

    @pytest.mark.asyncio
    async def test_detect_slave_id_delay_between_attempts(self):
        """Test that INTER_ATTEMPT_DELAY is inserted between attempts."""

        sleep_calls = []

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)

        async def mock_test(host, port, slave_id, timeout):
            return False  # All fail → all delays triggered

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test):
            with patch("bridge.slave_detector.asyncio.sleep", side_effect=mock_sleep):
                await detect_slave_id("192.168.1.100", 502)

                # Delay before attempt 2 and 3, but NOT before attempt 1
                expected_delays = [INTER_ATTEMPT_DELAY] * (len(KNOWN_SLAVE_IDS) - 1)
                assert sleep_calls == expected_delays


class TestSlaveIdTesting:
    """Test individual Slave ID testing."""

    @pytest.mark.asyncio
    async def test_test_slave_id_success(self):
        """Test successful Slave ID test."""

        mock_result = AsyncMock()
        mock_result.value = "SUN2000-6KTL-M1"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_result

        with patch("bridge.slave_detector.AsyncHuaweiSolar.create") as mock_create:
            mock_create.return_value = mock_client

            result = await _test_slave_id("192.168.1.100", 502, 1, timeout=5)

            assert result is True
            mock_create.assert_called_once()
            mock_client.get.assert_called_once_with("model_name")
            mock_client.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_slave_id_timeout(self):
        """Test Slave ID test handles timeout."""

        with patch("bridge.slave_detector.AsyncHuaweiSolar.create") as mock_create:
            mock_create.side_effect = TimeoutError("Connection timeout")

            result = await _test_slave_id("192.168.1.100", 502, 1, timeout=1)

            assert result is False

    @pytest.mark.asyncio
    async def test_test_slave_id_connection_refused(self):
        """Test Slave ID test handles connection refused."""

        with patch("bridge.slave_detector.AsyncHuaweiSolar.create") as mock_create:
            mock_create.side_effect = ConnectionRefusedError("Connection refused")

            result = await _test_slave_id("192.168.1.100", 502, 1, timeout=1)

            assert result is False

    @pytest.mark.asyncio
    async def test_test_slave_id_empty_response(self):
        """Test Slave ID test handles empty response."""

        mock_result = AsyncMock()
        mock_result.value = None

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_result

        with patch("bridge.slave_detector.AsyncHuaweiSolar.create") as mock_create:
            mock_create.return_value = mock_client

            result = await _test_slave_id("192.168.1.100", 502, 1, timeout=5)

            assert result is False
            mock_client.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_slave_id_cleanup_on_error(self):
        """Test cleanup happens even on error."""

        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Read error")

        with patch("bridge.slave_detector.AsyncHuaweiSolar.create") as mock_create:
            mock_create.return_value = mock_client

            result = await _test_slave_id("192.168.1.100", 502, 1, timeout=5)

            assert result is False
            mock_client.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_slave_id_stop_timeout_does_not_block(self):
        """Test that a hanging stop() does not block indefinitely."""

        async def hanging_stop():
            await asyncio.sleep(999)  # Simulates a client that never closes cleanly

        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Read error")
        mock_client.stop = hanging_stop

        with patch("bridge.slave_detector.AsyncHuaweiSolar.create") as mock_create:
            mock_create.return_value = mock_client

            # Should complete quickly despite hanging stop(), due to wait_for timeout
            result = await _test_slave_id("192.168.1.100", 502, 1, timeout=5)

            assert result is False

    @pytest.mark.asyncio
    async def test_test_slave_id_cancelled_error_propagates(self):
        """Test that CancelledError is re-raised and not swallowed."""

        with patch("bridge.slave_detector.AsyncHuaweiSolar.create") as mock_create:
            mock_create.side_effect = asyncio.CancelledError()

            with pytest.raises(asyncio.CancelledError):
                await _test_slave_id("192.168.1.100", 502, 1, timeout=5)


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_detect_stops_after_first_success(self):
        """Test detection stops after finding working ID."""

        call_count = 0

        async def mock_test(host, port, slave_id, timeout):
            nonlocal call_count
            call_count += 1
            return call_count == 1  # First call succeeds

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test):
            result = await detect_slave_id("192.168.1.100", 502)

            assert result == KNOWN_SLAVE_IDS[0]
            assert call_count == 1

    @pytest.mark.asyncio
    async def test_detect_with_different_port(self):
        """Test detection with non-standard port."""

        async def mock_test(host, port, slave_id, timeout):
            assert port == 5020
            return slave_id == 1

        with patch("bridge.slave_detector._test_slave_id", side_effect=mock_test):
            result = await detect_slave_id("192.168.1.100", 5020)

            assert result == 1

    @pytest.mark.asyncio
    async def test_detect_logs_attempts(self, caplog):
        """Test detection logs each attempt."""
        caplog.set_level(logging.INFO)

        with patch("bridge.slave_detector.AsyncHuaweiSolar.create") as mock_create:
            mock_create.side_effect = Exception("Connection failed")

            with patch("bridge.slave_detector.asyncio.sleep", new_callable=AsyncMock):
                result = await detect_slave_id("192.168.1.100", 502)

                assert result is None
                assert "Auto-detection failed" in caplog.text
                assert "[1, 2, 100]" in caplog.text


class TestSlaveDetector:
    """Test stateful SlaveDetector class."""

    @pytest.mark.asyncio
    async def test_detector_init(self):
        """Test SlaveDetector initializes with correct attributes."""
        from bridge.slave_detector import SlaveDetector

        detector = SlaveDetector("192.168.1.100", 5020)

        assert detector.host == "192.168.1.100"
        assert detector.port == 5020

    @pytest.mark.asyncio
    async def test_detector_detect_delegates(self):
        """Test SlaveDetector.detect() delegates to detect_slave_id."""
        from bridge.slave_detector import SlaveDetector

        detector = SlaveDetector("192.168.1.100", 502)

        with patch("bridge.slave_detector.detect_slave_id", new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = 1
            result = await detector.detect(timeout=10)

            assert result == 1
            mock_detect.assert_called_once_with("192.168.1.100", 502, 10)
