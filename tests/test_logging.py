# tests/test_logging.py

"""Tests for logging setup and behavior."""

import logging
from unittest.mock import AsyncMock, patch

import pytest
from bridge.logging_utils import get_logger
from bridge.main import TRACE

# ---------------------------------------------------------------------------
# TestTraceLevelRegistration
# ---------------------------------------------------------------------------


class TestTraceLevelRegistration:
    """Registrierung und Hierarchie des TRACE-Levels."""

    def test_trace_level_value_is_five(self):
        """TRACE ist auf Level 5 registriert."""
        assert TRACE == 5
        assert logging.getLevelName(TRACE) == "TRACE"

    def test_trace_is_below_debug_in_hierarchy(self):
        """TRACE liegt unterhalb von DEBUG in der Level-Hierarchie."""
        assert TRACE < logging.DEBUG
        assert logging.DEBUG < logging.INFO
        assert logging.INFO < logging.WARNING

    def test_trace_method_added_to_logger(self):
        """Logger-Instanzen haben nach dem Setup eine trace()-Methode."""
        assert hasattr(logging.getLogger("test"), "trace")


# ---------------------------------------------------------------------------
# TestTraceFormatter
# ---------------------------------------------------------------------------


class TestTraceFormatter:
    """Ausgabe des TraceFormatters."""

    def test_formatter_displays_trace_not_debug(self, caplog):
        """TraceFormatter gibt 'TRACE' aus, nicht 'DEBUG'."""
        from bridge.main import TraceFormatter

        handler = logging.StreamHandler()
        handler.setFormatter(TraceFormatter("%(levelname)s - %(message)s"))

        logger = logging.getLogger("test_trace_formatter")
        logger.setLevel(TRACE)
        logger.handlers.clear()
        logger.addHandler(handler)

        with caplog.at_level(TRACE):
            logger.trace("Test TRACE message")  # type: ignore[attr-defined]

        assert "TRACE" in caplog.text
        assert "DEBUG" not in caplog.text


# ---------------------------------------------------------------------------
# TestGetLogger
# ---------------------------------------------------------------------------


class TestGetLogger:
    """Verhalten von get_logger()."""

    def test_returns_logger_with_trace_method(self):
        """get_logger() liefert einen Logger mit trace()-Methode."""
        logger = get_logger("test.module")
        assert hasattr(logger, "trace")

    def test_returns_logger_with_standard_methods(self):
        """get_logger() liefert einen Logger mit allen Standard-Methoden."""
        logger = get_logger("test.module")
        for method in ("debug", "info", "warning", "error", "critical"):
            assert hasattr(logger, method)

    def test_trace_method_logs_at_trace_level(self, caplog):
        """trace()-Methode schreibt tatsächlich auf Level 5."""
        logger = get_logger("test.trace")
        with caplog.at_level(5, logger="test.trace"):
            logger.trace("trace message")
        assert "trace message" in caplog.text


# ---------------------------------------------------------------------------
# TestTraceLoggingBehavior
# ---------------------------------------------------------------------------


class TestTraceLoggingBehavior:
    """TRACE-Logging in verschiedenen Modulen."""

    @pytest.mark.asyncio
    async def test_slave_detector_logs_trace_attempts(self, caplog):
        """SlaveDetector loggt TRACE-Nachrichten bei Erkennungsversuchen."""
        from bridge.slave_detector import detect_slave_id

        caplog.set_level(TRACE)

        with patch("bridge.slave_detector.create_tcp_client") as mock:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=TimeoutError())
            mock_client.connect = AsyncMock()
            mock_client.disconnect = AsyncMock()
            mock.return_value = mock_client

            result = await detect_slave_id("192.168.0.1", 502)

        assert result is None
        assert "Trying Slave ID" in caplog.text or "🔬" in caplog.text

    def test_trace_logs_register_reads(self, caplog):
        """TRACE-Level zeigt Register-Read-Nachrichten."""
        caplog.set_level(TRACE)
        logger = get_logger("test")
        logger.trace("🔬 Register read: power_active = 4500")
        assert "🔬" in caplog.text or "TRACE" in caplog.text
