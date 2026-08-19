# huawei_solar_modbus_mqtt/bridge/main.py

"""
Hauptmodul des Huawei Solar Modbus-to-MQTT Add-ons.

Dieser Service liest zyklisch Daten vom Huawei Inverter per Modbus TCP,
transformiert sie in MQTT-Format und publiziert sie inklusive Home Assistant
Discovery-Konfiguration.

Architektur:
    Modbus Read → Transform (mit Filter) → MQTT Publish → Repeat

Features:
    - Asynchroner Modbus-Read für bessere Performance
    - Intelligentes Error-Tracking zur Log-Spam-Vermeidung
    - total_increasing Filter gegen falsche Counter-Resets
    - Heartbeat-Monitoring mit konfigurierbarem Timeout
    - MQTT Discovery für automatische Home Assistant Integration
    - Performance-Monitoring mit Zeitmessungen
"""

import asyncio
import logging
import signal
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from huawei_solar import AsyncHuaweiSolarClient, RegisterName, create_tcp_client
from huawei_solar.exceptions import ConnectionException, ConnectionInterruptedException, ReadException

from .batch_builder import BatchBuilder
from .config.registers import ESSENTIAL_REGISTERS
from .config_manager import ConfigManager, ConfigurationError
from .error_tracker import ConnectionErrorTracker, ErrorType
from .logging_utils import get_logger
from .mqtt_client import (
    connect_mqtt,
    disconnect_mqtt,
    publish_data,
    publish_discovery_configs,
    publish_status,
)
from .slave_detector import KNOWN_SLAVE_IDS, detect_slave_id
from .total_increasing_filter import get_filter, reset_filter
from .transform import transform_data

MODBUS_EXCEPTIONS: tuple[type, ...] = (ReadException,)


RECOVERABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    TimeoutError,
    ConnectionRefusedError,
    ConnectionInterruptedException,
    ConnectionException,
) + MODBUS_EXCEPTIONS

# Exceptions expected during register reads -- narrowed from bare Exception
# to catch only expected read/connection failures, letting programming errors
# propagate.  AttributeError covers register names not present in the
# huawei_solar library internal register definitions.
READ_EXCEPTIONS: tuple[type[BaseException], ...] = RECOVERABLE_EXCEPTIONS + (AttributeError,)


TRACE = 5  # DEBUG ist 10, INFO ist 20, WARNING ist 30
logging.addLevelName(TRACE, "TRACE")

MODBUS_CONNECT_TIMEOUT = 15


class _TraceLogger(logging.Logger):
    """Logger subclass adding a trace() method at level 5."""

    def trace(self, message: object, *args: object, **kwargs: object) -> None:
        if self.isEnabledFor(TRACE):
            self._log(TRACE, message, args, **kwargs)  # type: ignore[arg-type]


logging.setLoggerClass(_TraceLogger)


logger = get_logger("huawei.main")
_error_tracker = ConnectionErrorTracker(log_interval=60)


def get_error_tracker() -> ConnectionErrorTracker:
    """Return the module-level error tracker instance.

    Provides read-only access to the private _error_tracker singleton
    so that callers outside this module do not need to reach into a
    private attribute directly.
    """
    return _error_tracker


def _register_sigterm_handler(loop: asyncio.AbstractEventLoop, cancel_callback: Callable[[], object]) -> None:
    if sys.platform == "win32":
        return

    try:
        loop.add_signal_handler(signal.SIGTERM, cancel_callback)
    except (NotImplementedError, RuntimeError):
        logger.debug("SIGTERM handler not registered for this event loop")


class TraceFormatter(logging.Formatter):
    """Custom formatter that correctly displays TRACE level."""

    def format(self, record):
        # Ensure TRACE level shows as "TRACE" not "DEBUG"
        if record.levelno == TRACE:
            record.levelname = "TRACE"
        return super().format(record)


@dataclass
class _BridgeState:
    """Mutable runtime state of the bridge main loop."""

    last_success: float = 0.0
    config: "ConfigManager | None" = None
    cycle_count: int = 0

    async def publish_status(self, status: str, topic: str) -> None:
        if self.config is not None:
            await publish_status(status, topic)


_state = _BridgeState()


def reset_state() -> None:
    """Wipe global bridge singletons.

    WARNING: For testing only. Resets runtime state (_state, _error_tracker)
    so tests can start from a clean baseline. Do not call in production.
    """
    global _state, _error_tracker
    _state = _BridgeState()
    _error_tracker = ConnectionErrorTracker(log_interval=60)


def init_logging(log_level: str) -> None:
    """
    Initialisiert komplettes Logging-System.

    Konfiguriert drei Logger-Hierarchien:
    1. Root Logger - für alle eigenen Module (huawei.*)
    2. tmodbus Logger - für Modbus-Library (meist zu verbose)
    3. huawei_solar Logger - für Inverter-Library

    Args:
        log_level: Log level string (TRACE|DEBUG|INFO|WARNING|ERROR)
    """
    level = _parse_log_level(log_level)
    _setup_root_logger(level)
    _configure_tmodbus(level)
    _configure_huawei_solar(level)

    logger.info("📋 Logging initialized: %s", logging.getLevelName(level))

    if level <= logging.DEBUG:
        logger.debug(
            "External loggers: tmodbus=%s, huawei_solar=%s",
            logging.getLevelName(logging.getLogger("tmodbus").level),
            logging.getLevelName(logging.getLogger("huawei_solar").level),
        )


def _parse_log_level(level_str: str) -> int:
    """
    Parse Log-Level String zu Integer.

    Args:
        level_str: Log level (TRACE|DEBUG|INFO|WARNING|ERROR)

    Returns:
        TRACE (5), DEBUG (10), INFO (20), WARNING (30) oder ERROR (40)
    """
    level_map = {
        "TRACE": TRACE,
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }

    return level_map.get(level_str.upper(), logging.INFO)


def _setup_root_logger(level: int) -> None:
    root = logging.getLogger()
    root.setLevel(level)

    # Handler clearen und neu erstellen
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()  # ← Handler auch schließen!

    handler = logging.StreamHandler(sys.stdout)
    formatter = TraceFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)


def _configure_tmodbus(level: int) -> None:
    """Konfiguriert tmodbus Logger (Modbus-Library)."""
    for logger_name in ["tmodbus", "huawei_solar.modbus_client"]:
        modbus_logger = logging.getLogger(logger_name)
        if level == TRACE:
            modbus_logger.setLevel(logging.DEBUG)
        elif level == logging.DEBUG:
            modbus_logger.setLevel(logging.INFO)
        else:
            modbus_logger.setLevel(logging.WARNING)


def _configure_huawei_solar(level: int) -> None:
    """Konfiguriert huawei_solar Library Logger."""
    for logger_name in ["huawei_solar", "huawei_solar.huawei_solar"]:
        hs_logger = logging.getLogger(logger_name)
        if level == TRACE:
            hs_logger.setLevel(logging.DEBUG)
        elif level == logging.DEBUG:
            hs_logger.setLevel(logging.INFO)
        else:
            hs_logger.setLevel(logging.WARNING)


async def heartbeat(config: ConfigManager) -> None:
    """
    Überwacht erfolgreiche Reads und setzt Status auf offline bei Timeout.

    Args:
        config: ConfigManager instance
    """
    timeout = config.status_timeout

    if _state.last_success == 0.0:
        return
    offline_duration = time.time() - _state.last_success

    if offline_duration > timeout:
        if offline_duration < timeout + 5:
            error_status = _error_tracker.get_status()
            logger.warning(
                "⚠️ Inverter offline for %ds (timeout: %ss) | Failed attempts: %s | Error types: %s",
                int(offline_duration),
                timeout,
                error_status["total_failures"],
                error_status["active_errors"],
            )
        await publish_status("offline", config.mqtt_topic)
    else:
        logger.debug("Heartbeat OK: %.1fs since last success", offline_duration)


def log_cycle_summary(cycle_num: int, _timings: dict[str, float], data: dict[str, Any]) -> None:
    """Loggt Cycle-Zusammenfassung."""
    filter_stats = get_filter().get_stats()
    filter_indicator = ""

    if filter_stats:
        total_filtered = sum(filter_stats.values())
        if total_filtered > 0:
            filter_indicator = f" 🔍[{total_filtered} filtered]"

    logger.info(
        "📊 Published - PV: %dW | AC Out: %dW | Grid: %dW | Battery: %dW%s",
        data.get("power_input", 0),
        data.get("power_active", 0),
        data.get("meter_power_active", 0),
        data.get("battery_power", 0),
        filter_indicator,
    )

    if cycle_num % 20 == 0:
        total_filtered = sum(filter_stats.values()) if filter_stats else 0

        if total_filtered > 0:
            logger.info(
                "└─> 🔍 Filter summary (last 20 cycles): %d values filtered | Details: %s",
                total_filtered,
                dict(filter_stats),
            )
        else:
            logger.info("└─> 🔍 Filter summary (last 20 cycles): 0 values filtered - all data valid ✓")

        get_filter().reset_stats()

    elif filter_stats and logger.isEnabledFor(logging.DEBUG):
        logger.debug("🔍 Filter details: %s", dict(filter_stats))


async def _read_single_register(client: AsyncHuaweiSolarClient, name: str) -> tuple[str, Any] | None:
    """Read a single register, returning (name, value) or None if unavailable.

    In read_registers(), individual registers may not exist on all inverter
    models. Catching READ_EXCEPTIONS here and returning None preserves the
    graceful-degradation behavior: unavailable registers are silently
    skipped with a DEBUG log line instead of aborting the entire read cycle.
    """
    try:
        value = await client.get(cast(RegisterName, name))
        return name, value
    except READ_EXCEPTIONS:
        logger.debug("Skipping '%s' (not available)", name)
        return None


async def read_registers(
    client: AsyncHuaweiSolarClient,
    batch_max_gap: int = 50,
    enable_batching: bool = True,
) -> dict[str, Any]:
    """Liest Essential Registers vom Inverter mit optimalem Batching.

    Args:
        client: AsyncHuaweiSolarClient Client
        batch_max_gap: Maximum address gap within a batch (for smart batching)
        enable_batching: Whether to use smart batching strategy

    Strategy:
        1. Try smart batching: group registers by address proximity
        2. Fall back to sequential mode if batching fails

    Bei DEBUG-Level werden detaillierte Timing-Informationen pro Register ausgegeben,
    um Performance-Probleme zu diagnostizieren.

    Note: Individual register reads intentionally catch expected failures
    (ReadException, TimeoutError, connection errors, AttributeError) and
    skip unavailable registers rather than propagating -- this is deliberate
    graceful degradation, because not all registers exist on every inverter
    model.  Programming errors (e.g. TypeError, ValueError) are NOT caught
    and will propagate normally.
    """

    logger.debug(
        "Reading %d essential registers (enable_batching=%s, batch_max_gap=%d)",
        len(ESSENTIAL_REGISTERS),
        enable_batching,
        batch_max_gap,
    )

    start = time.time()
    data = {}

    # === SMART BATCHING MODE (v1.10.0+) ===
    # Sort registers by Modbus address and group by proximity to reduce TCP calls
    if enable_batching and len(ESSENTIAL_REGISTERS) > 1:
        try:
            builder = BatchBuilder(batch_max_gap=batch_max_gap, enable_batching=True)
            batches, unknown_registers = builder.build_batches(ESSENTIAL_REGISTERS)

            logger.debug(
                "📦 Using smart batching: %d batches%s",
                len(batches),
                f", {len(unknown_registers)} sequential" if unknown_registers else "",
            )

            batch_start = time.time()
            batch_timings: list[tuple[int, float]] = []  # batch_num, duration

            for batch_num, batch in enumerate(batches, 1):
                batch_read_start = time.time()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "📦 Reading batch %d/%d: %d registers: %s",
                        batch_num,
                        len(batches),
                        len(batch),
                        batch,
                    )
                try:
                    values = await client.get_multiple([cast(RegisterName, n) for n in batch])
                    batch_duration = time.time() - batch_read_start
                    batch_timings.append((batch_num, batch_duration))

                    batch_data = dict(zip(batch, values, strict=True))
                    data.update(batch_data)

                    logger.debug(
                        "📦 Batch %d/%d: %d registers in %.2fs",
                        batch_num,
                        len(batches),
                        len(batch),
                        batch_duration,
                    )

                except READ_EXCEPTIONS + (ValueError,) as e:
                    # ValueError is caught here *only* as a local safety-net.
                    # The underlying tModbus PDU constructor raises
                    # ValueError("Quantity must be between 1 and 125.") when a
                    # batch's effective register quantity exceeds the Modbus
                    # FC03/FC04 hard limit of 125 registers per read.  The
                    # BatchBuilder normally prevents this via MAX_MODBUS_QUANTITY,
                    # but if a library update or configuration drift causes an
                    # oversized batch to slip through, we degrade gracefully by
                    # falling back to sequential single-register reads instead of
                    # letting a single bad batch crash the entire bridge.
                    logger.debug(
                        "⚠️ Batch %d failed (%s), falling back to sequential "
                        "(if this repeats, try reducing batch_max_gap below %d)",
                        batch_num,
                        e,
                        batch_max_gap,
                    )
                    # Fall back to sequential for this batch
                    for name in batch:
                        if (result := await _read_single_register(client, name)) is not None:
                            data[result[0]] = result[1]

            # Unknown registers (not in library) are always read sequentially
            for name in unknown_registers:
                if (result := await _read_single_register(client, name)) is not None:
                    data[result[0]] = result[1]

            total_batch_duration = time.time() - batch_start
            successful = len([v for v in data.values() if v is not None])

            logger.info(
                "📖 Essential read (smart batch): %.1fs (%d/%d, %d batches)",
                total_batch_duration,
                successful,
                len(ESSENTIAL_REGISTERS),
                len(batches),
            )

            if logger.isEnabledFor(logging.DEBUG) and batch_timings:
                batch_times = [t for _, t in batch_timings]
                logger.debug(
                    "📦 Batch timings: avg=%.2fs, min=%.2fs, max=%.2fs",
                    sum(batch_times) / len(batch_times),
                    min(batch_times),
                    max(batch_times),
                )

            return data

        except READ_EXCEPTIONS as e:
            logger.debug("⚠️ Smart batching failed (%s), falling back to sequential mode", e)
            data = {}  # Reset data, will retry sequentially

    # === SEQUENTIAL MODE (v1.9.0 behavior) ===
    successful = 0

    # Performance-Tracking für Diagnose
    register_timings: list[tuple[str, float]] = []
    slow_register_threshold = 0.2  # Sekunden - Register die länger brauchen werden gewarnt

    for name in ESSENTIAL_REGISTERS:
        register_start = time.time()
        try:
            data[name] = await client.get(cast(RegisterName, name))
            register_duration = time.time() - register_start
            register_timings.append((name, register_duration))
            successful += 1

            # Warnung bei sehr langsamen einzelnen Registern
            if register_duration > slow_register_threshold:
                logger.debug("⏱️ Slow register '%s': %.3fs", name, register_duration)

        except READ_EXCEPTIONS:
            register_duration = time.time() - register_start
            register_timings.append((name, register_duration))
            logger.debug("Skipping '%s' (not available, took %.3fs)", name, register_duration)

    duration = time.time() - start

    # Detaillierte Statistiken bei DEBUG-Level
    if logger.isEnabledFor(logging.DEBUG) and register_timings:
        timings_only = [t for _, t in register_timings]
        avg_time = sum(timings_only) / len(timings_only)
        min_time = min(timings_only)
        max_time = max(timings_only)
        sorted_timings = sorted(timings_only)
        median_time = sorted_timings[len(sorted_timings) // 2]

        logger.debug(
            "📊 Register timing stats: avg=%.3fs, min=%.3fs, max=%.3fs, median=%.3fs",
            avg_time,
            min_time,
            max_time,
            median_time,
        )

        # Top 5 langsamste Register anzeigen
        slowest = sorted(register_timings, key=lambda x: x[1], reverse=True)[:5]
        if slowest and slowest[0][1] > 0.1:  # Nur wenn wirklich langsam
            logger.debug("🐌 Slowest registers:")
            for reg_name, reg_time in slowest:
                logger.debug("   • %s: %.3fs", reg_name, reg_time)

    logger.info(
        "📖 Essential read: %.1fs (%d/%d)",
        duration,
        successful,
        len(ESSENTIAL_REGISTERS),
    )

    return data


def is_modbus_exception(exc: Exception) -> bool:
    """Prüft ob Exception eine Modbus-spezifische Exception ist."""
    if not MODBUS_EXCEPTIONS:
        return False
    return isinstance(exc, MODBUS_EXCEPTIONS)


async def main_once(client: AsyncHuaweiSolarClient, config: ConfigManager, cycle_num: int) -> None:
    """Execute a single read-transform-filter-publish cycle.

    Reads essential Modbus registers, transforms and filters the values,
    publishes them to MQTT, and updates cycle summary logging.

    Args:
        client: Connected AsyncHuaweiSolarClient Modbus client.
        config: Active configuration instance.
        cycle_num: Sequential cycle counter for logging and filtering.

     Raises:
        TimeoutError: On Modbus read timeout.
        ConnectionRefusedError: On connection failure.
        ReadException: On Modbus protocol errors.
    """
    _state.cycle_count = cycle_num
    _state.config = config

    start: float = time.time()
    logger.debug("Starting cycle")

    # === PHASE 1: Modbus Read ===
    modbus_start: float = time.time()
    try:
        data = await read_registers(
            client,
            batch_max_gap=config.batch_max_gap,
            enable_batching=config.enable_batching,
        )
        modbus_duration: float = time.time() - modbus_start
    except Exception as e:
        if is_modbus_exception(e):
            logger.warning("⚠️ Modbus read failed after %.1fs: %s", time.time() - start, e)
        else:
            logger.error("❌ Read error: %s", e)
        raise

    if not data:
        logger.warning("⚠️ No data")
        return

    # === PHASE 2: Transform ===
    transform_start: float = time.time()
    transformed = transform_data(data)
    transform_duration: float = time.time() - transform_start

    # === PHASE 3: Filter ===
    filter_start: float = time.time()
    filter_instance = get_filter()
    mqtt_data = filter_instance.filter(transformed)
    filter_duration = time.time() - filter_start

    # === PHASE 4: MQTT Publish ===
    mqtt_start: float = time.time()
    await publish_data(mqtt_data, config.mqtt_topic)
    _state.last_success = time.time()
    mqtt_duration = time.time() - mqtt_start

    cycle_duration: float = time.time() - start

    # === PHASE 5: Logging ===
    timings = {
        "modbus": modbus_duration,
        "transform": transform_duration,
        "filter": filter_duration,
        "mqtt": mqtt_duration,
        "total": cycle_duration,
    }

    log_cycle_summary(cycle_num, timings, mqtt_data)

    logger.debug(
        "Cycle: %.1fs (Modbus: %.1fs, Transform: %.3fs, Filter: %.3fs, MQTT: %.2fs)",
        cycle_duration,
        modbus_duration,
        transform_duration,
        filter_duration,
        mqtt_duration,
    )

    # === PHASE 7: Performance-Check ===
    if cycle_duration > config.poll_interval * 0.8:  # ← direkt config nutzen, nicht _state.config
        logger.warning("⚠️ Cycle %.1fs > 80%% poll_interval (%ds)", cycle_duration, config.poll_interval)


async def determine_slave_id(config: ConfigManager) -> int:
    """
    Determine the Slave ID to use (auto-detect or manual).

    Args:
        config: ConfigManager instance

    Returns:
        Slave ID to use

    Raises:
        ConfigurationError: If Slave ID cannot be determined
    """
    if config.modbus_auto_detect_slave_id:
        detected_id = await detect_slave_id(
            host=config.modbus_host,
            port=config.modbus_port,
        )

        if detected_id is not None:
            return detected_id
        else:
            raise ConfigurationError(
                "Auto-detection failed. Please set 'modbus.auto_detect_slave_id: false' "
                "and configure 'modbus.slave_id' manually in the add-on configuration. "
                f"Tested Slave IDs: {KNOWN_SLAVE_IDS} on {config.modbus_host}:{config.modbus_port}"
            )

    else:
        # Manual Slave ID
        manual_slave_id = config.slave_id

        if manual_slave_id is None:
            raise ConfigurationError(
                "Auto-detection is disabled but no manual 'slave_id' configured. "
                "Please set 'modbus.slave_id' in the add-on configuration."
            )

        logger.debug("Using manual Slave ID: %s", manual_slave_id)
        return manual_slave_id


async def setup_mqtt(config: ConfigManager) -> bool:
    """Connect to MQTT broker and wait for connection to stabilize.

    Args:
        config: Configuration instance with MQTT settings.

    Returns:
        True if MQTT connection succeeded, False otherwise.
    """
    try:
        await connect_mqtt()
        await asyncio.sleep(1)
    except (OSError, ConnectionError) as e:
        logger.error("❌ MQTT connect failed: %s", e)
        return False
    return True


async def setup_modbus(slave_id: int, config: ConfigManager) -> AsyncHuaweiSolarClient | None:
    """Create Modbus TCP connection to the inverter.

    Args:
        slave_id: Modbus slave ID to connect to.
        config: Configuration instance with connection settings.

    Returns:
        Connected AsyncHuaweiSolarClient client, or None on failure.
    """
    try:
        connection_start = time.time()
        client = create_tcp_client(
            config.modbus_host,
            config.modbus_port,
            unit_id=slave_id,
        )
        await asyncio.wait_for(client.connect(), timeout=MODBUS_CONNECT_TIMEOUT)
        connection_time = time.time() - connection_start
        logger.info(
            "🔌 Connected to %s:%s (Slave ID: %s, took %.3fs)",
            config.modbus_host,
            config.modbus_port,
            slave_id,
            connection_time,
        )
        await _state.publish_status("online", config.mqtt_topic)
        return client
    except TimeoutError:
        logger.error(
            "❌ Modbus connection to %s:%s timed out after %ds",
            config.modbus_host,
            config.modbus_port,
            MODBUS_CONNECT_TIMEOUT,
        )
        return None
    except (OSError, ConnectionError) as e:
        logger.error("❌ Connection failed: %s", e)
        return None


async def initialize_bridge(config: ConfigManager) -> AsyncHuaweiSolarClient | None:
    """Initialize MQTT, discovery, and Modbus connection.

    Args:
        config: Configuration instance.

    Returns:
        Connected AsyncHuaweiSolarClient client, or None if initialization failed.
    """
    logger.info("🚀 Huawei Solar → MQTT starting")
    config.log_config()

    slave_id = await determine_slave_id(config)

    mqtt_connected = await setup_mqtt(config)
    if not mqtt_connected:
        return None

    await publish_status("offline", config.mqtt_topic)

    try:
        await publish_discovery_configs(config.mqtt_topic)
        logger.info("📢 Discovery published")
    except Exception as e:
        logger.error("❌ Discovery failed: %s", e)

    client = await setup_modbus(slave_id, config)
    if client is None:
        await disconnect_mqtt()
        return None

    get_filter()
    logger.info("🛡️ Total Increasing Filter initialized")
    logger.info("⏱️ Poll interval: %ss", config.poll_interval)
    return client


async def _maybe_reset_on_error(e: BaseException, config: ConfigManager) -> bool:
    if isinstance(e, (TimeoutError, ConnectionInterruptedException)):
        error_type: ErrorType = "timeout" if isinstance(e, TimeoutError) else "connection_interrupted"
        _error_tracker.track_error(error_type, str(e))
        await _state.publish_status("offline", config.mqtt_topic)
        reset_filter()
        logger.debug("Filter reset due to timeout/interruption: %s", type(e).__name__)
        await asyncio.sleep(10)
        return True

    if isinstance(e, (ConnectionRefusedError, ConnectionException)):
        conn_error_type: ErrorType = (
            "connection_refused" if isinstance(e, ConnectionRefusedError) else "connection_exception"
        )
        _error_tracker.track_error(conn_error_type, str(e))
        await _state.publish_status("offline", config.mqtt_topic)
        reset_filter()
        logger.debug("Filter reset due to connection error: %s", type(e).__name__)
        await asyncio.sleep(10)
        return True

    if MODBUS_EXCEPTIONS and isinstance(e, MODBUS_EXCEPTIONS):
        _error_tracker.track_error("modbus_exception", str(e))
        await _state.publish_status("offline", config.mqtt_topic)
        reset_filter()
        logger.debug("Filter reset due to modbus exception")
        await asyncio.sleep(10)
        return True

    return False


async def run_main_cycle(client: AsyncHuaweiSolarClient, config: ConfigManager, cycle_count: int) -> None:
    cycle_start = time.time()
    logger.debug("Cycle #%d", cycle_count)

    try:
        await main_once(client, config, cycle_count)
    except KeyboardInterrupt as e:
        logger.info("🛑 Interrupted during cycle")
        raise KeyboardInterrupt from e
    except asyncio.CancelledError:
        raise
    except RECOVERABLE_EXCEPTIONS as e:
        if await _maybe_reset_on_error(e, config):
            return
        logger.error("❌ Recoverable error not handled: %s", e, exc_info=True)
        await _state.publish_status("offline", config.mqtt_topic)
        reset_filter()
        await asyncio.sleep(10)
        return

    _error_tracker.mark_success()
    await _state.publish_status("online", config.mqtt_topic)

    elapsed = time.time() - cycle_start
    wait = max(0.0, config.poll_interval - elapsed)
    if wait > 0:
        logger.debug("Waiting %.1fs until next cycle", wait)
        try:
            await asyncio.sleep(wait)
        except KeyboardInterrupt:
            logger.info("⌨️ Interrupted during wait")
            raise


async def main() -> None:
    """Haupt-Loop mit Error-Handling und automatischer Wiederverbindung."""
    loop = asyncio.get_running_loop()
    current_task = asyncio.current_task()
    if current_task is not None:
        _register_sigterm_handler(loop, current_task.cancel)

    # Load configuration
    try:
        config = ConfigManager()
    except Exception as e:
        # Logging noch nicht initialisiert, daher print()
        print(f"❌ Configuration error: {e}")
        sys.exit(1)

    # Initialize logging
    init_logging(config.log_level)
    _state.config = config

    try:
        client = await initialize_bridge(config)
    except ConfigurationError as e:
        logger.error("❌ %s", e)
        sys.exit(1)
    if client is None:
        return

    # === Main Loop ===
    cycle_count: int = 0
    try:
        while True:
            cycle_count += 1
            await run_main_cycle(client, config, cycle_count)
            await heartbeat(config)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("🛑 Shutdown")
        await _state.publish_status("offline", config.mqtt_topic)
        await disconnect_mqtt()
    except Exception as e:
        logger.error("💥 Fatal: %s", e, exc_info=True)
        await _state.publish_status("offline", config.mqtt_topic)
        await disconnect_mqtt()
        sys.exit(1)


async def _run() -> None:
    """Entry-point wrapper used by direct execution of this module."""
    await main()


if __name__ == "__main__":
    """Entry-Point beim direkten Ausführen der Datei."""
    asyncio.run(_run())
