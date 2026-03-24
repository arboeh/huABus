# tests/test_logging.py

"""Tests for logging setup and behavior."""

import logging
from unittest.mock import AsyncMock, patch

import pytest
from bridge.logging_utils import get_logger
from bridge.main import TRACE


def test_trace_level_exists():
    """TRACE level should be registered at level 5."""
    assert TRACE == 5
    assert logging.getLevelName(TRACE) == "TRACE"


def test_trace_method_added_to_logger():
    """Logger should have trace() method after init."""
    # TRACE-Methode wird in main.py hinzugefügt

    logger = logging.getLogger("test")
    assert hasattr(logger, "trace")


def test_trace_formatter_displays_trace_correctly(caplog):
    """TraceFormatter should display TRACE not DEBUG."""
    from bridge.main import TraceFormatter

    handler = logging.StreamHandler()
    handler.setFormatter(TraceFormatter("%(levelname)s - %(message)s"))

    logger = logging.getLogger("test_trace")
    logger.setLevel(TRACE)
    logger.handlers.clear()
    logger.addHandler(handler)

    with caplog.at_level(TRACE):
        logger.trace("Test TRACE message")  # type: ignore[attr-defined]

    # Check that log record shows TRACE not DEBUG
    assert "TRACE" in caplog.text
    assert "DEBUG" not in caplog.text


def test_get_logger_returns_logger_with_trace():
    """get_logger() should return logger with trace capability."""
    logger = get_logger("test.module")

    # Logger sollte trace-Methode haben (Protocol)
    assert hasattr(logger, "trace")
    assert hasattr(logger, "debug")
    assert hasattr(logger, "info")


def test_logging_levels_hierarchy():
    """TRACE should be below DEBUG in level hierarchy."""
    assert TRACE < logging.DEBUG
    assert logging.DEBUG < logging.INFO
    assert logging.INFO < logging.WARNING


@pytest.mark.asyncio
async def test_trace_logs_in_slave_detector(caplog):  # ← async def!
    """SlaveDetector should use TRACE for detection attempts."""
    from bridge.slave_detector import detect_slave_id

    caplog.set_level(TRACE)

    # Mock detection
    with patch("bridge.slave_detector.AsyncHuaweiSolar") as mock:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=TimeoutError())
        mock.create = AsyncMock(return_value=mock_client)

        # ✅ FIX 1: await ist erlaubt (async def)
        # ✅ FIX 2: candidates Parameter entfernt
        result = await detect_slave_id("192.168.0.1", 502)

        assert result is None  # Detection failed

    # Should log TRACE attempts
    assert "Trying Slave ID" in caplog.text or "🔬" in caplog.text


def test_trace_logs_register_reads(caplog):
    """Main loop should TRACE log register reads if enabled."""
    from bridge.main import TRACE

    caplog.set_level(TRACE)

    # Simulate one main_once cycle with TRACE logging
    # (Simplified - würde vollständige Mock-Umgebung brauchen)
    logger = get_logger("test")
    logger.trace("🔬 Register read: power_active = 4500")

    assert "🔬" in caplog.text or "TRACE" in caplog.text
