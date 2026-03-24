# huawei_solar_modbus_mqtt/bridge/logging_utils.py

"""Logging utilities with TRACE support."""

import logging
from typing import Protocol, runtime_checkable


@runtime_checkable
class LoggerWithTrace(Protocol):
    """Protocol for Logger with TRACE method."""

    def trace(self, message: str, *args, **kwargs) -> None:
        """Log message at TRACE level."""
        ...

    # Standard logging methods - Namen MÜSSEN identisch mit logging.Logger sein!
    def debug(self, message: str, *args, **kwargs) -> None: ...
    def info(self, message: str, *args, **kwargs) -> None: ...
    def warning(self, message: str, *args, **kwargs) -> None: ...
    def error(self, message: str, *args, **kwargs) -> None: ...
    def critical(self, message: str, *args, **kwargs) -> None: ...
    def log(self, level: int, message: str, *args, **kwargs) -> None: ...

    # Diese Methode heißt offiziell isEnabledFor (nicht is_enabled_for)!
    def isEnabledFor(self, level: int) -> bool: ...  # noqa: N802
    def setLevel(self, level: int) -> None: ...  # noqa: N802


def get_logger(name: str) -> LoggerWithTrace:
    """
    Get a logger instance with TRACE support.

    The returned logger has all standard logging methods plus trace().
    Type checkers will recognize the trace() method.

    Args:
        name: Logger name (e.g. "huawei.main")

    Returns:
        Logger instance typed as LoggerWithTrace

    Example:
        >>> logger = get_logger("huawei.main")
        >>> logger.trace("🔬 Test message")  # Type-safe!
        >>> logger.info("📋 Info message")  # All standard methods work
    """
    # Logger wird zur Laufzeit um trace() erweitert (in main.py)
    # Type-Checker sieht LoggerWithTrace Protocol
    return logging.getLogger(name)  # type: ignore[return-value]
