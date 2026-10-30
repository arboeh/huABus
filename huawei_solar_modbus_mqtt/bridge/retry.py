# huawei_solar_modbus_mqtt/bridge/retry.py

"""
Backoff-Helfer für Verbindungsaufbau beim Start.

Wiederholt eine async Operation, bis sie ein Ergebnis liefert. Die Wartezeit
startet bei 5s, verdoppelt sich je Fehlversuch und ist auf 60s begrenzt.

Eine Operation meldet "nicht erreichbar" durch Rückgabe von ``None``.
Exceptions (inklusive ``asyncio.CancelledError``) werden nie abgefangen,
damit Konfigurationsfehler und Shutdown den Helfer sofort verlassen.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger("huawei.retry")

INITIAL_DELAY = 5.0
MAX_DELAY = 60.0
BACKOFF_FACTOR = 2.0


async def retry_with_backoff[T](
    operation: Callable[[], Awaitable[T | None]],
    description: str,
    *,
    initial_delay: float = INITIAL_DELAY,
    max_delay: float = MAX_DELAY,
    sleep: Callable[[float], Awaitable[object]] | None = None,
) -> T:
    """Run ``operation`` until it returns a value other than ``None``.

    Args:
        operation: Async callable; ``None`` means "not available yet".
        description: Name of the target for log messages (e.g. host:port).
        initial_delay: Wait after the first failed attempt in seconds.
        max_delay: Upper bound for the wait between attempts in seconds.
        sleep: Optional replacement for ``asyncio.sleep`` (tests).

    Returns:
        The first result that is not ``None``.
    """
    # asyncio.sleep is resolved at call time so a global patch also applies.
    pause = sleep if sleep is not None else asyncio.sleep
    delay = initial_delay
    attempt = 0

    while True:
        attempt += 1
        result = await operation()
        if result is not None:
            if attempt > 1:
                logger.info("✅ %s available after %d attempts", description, attempt)
            return result

        logger.warning("⏳ %s not available (attempt %d), retrying in %.0fs", description, attempt, delay)
        await pause(delay)
        delay = min(delay * BACKOFF_FACTOR, max_delay)
