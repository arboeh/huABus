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
import sys
import time
from typing import Any

from huawei_solar import AsyncHuaweiSolar

from .config.registers import ESSENTIAL_REGISTERS
from .config_manager import ConfigManager
from .error_tracker import ConnectionErrorTracker
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

try:
    from pymodbus.exceptions import ModbusException
    from pymodbus.pdu import ExceptionResponse

    MODBUS_EXCEPTIONS = (ModbusException, ExceptionResponse)
except ImportError:  # pragma: no cover
    MODBUS_EXCEPTIONS = ()  # type: ignore[assignment]

# Globaler Timestamp des letzten erfolgreichen Reads
# Wird von main_once() gesetzt und von heartbeat() geprüft
# 0 = noch kein erfolgreicher Read (Startup-Phase)
LAST_SUCCESS: float = 0

TRACE = 5  # DEBUG ist 10, INFO ist 20, WARNING ist 30
logging.addLevelName(TRACE, "TRACE")


def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)


logging.Logger.trace = trace  # type: ignore[attr-defined]
logger = get_logger("huawei.main")
error_tracker = ConnectionErrorTracker(log_interval=60)


class TraceFormatter(logging.Formatter):
    """Custom formatter that correctly displays TRACE level."""

    def format(self, record):
        # Ensure TRACE level shows as "TRACE" not "DEBUG"
        if record.levelno == TRACE:
            record.levelname = "TRACE"
        return super().format(record)


def init_logging(log_level: str) -> None:
    """
    Initialisiert komplettes Logging-System.

    Konfiguriert drei Logger-Hierarchien:
    1. Root Logger - für alle eigenen Module (huawei.*)
    2. pymodbus Logger - für Modbus-Library (meist zu verbose)
    3. huawei_solar Logger - für Inverter-Library

    Args:
        log_level: Log level string (TRACE|DEBUG|INFO|WARNING|ERROR)
    """
    level = _parse_log_level(log_level)
    _setup_root_logger(level)
    _configure_pymodbus(level)
    _configure_huawei_solar(level)

    logger.info(f"📋 Logging initialized: {logging.getLevelName(level)}")

    if level <= logging.DEBUG:
        logger.debug(
            f"External loggers: "
            f"pymodbus={logging.getLevelName(logging.getLogger('pymodbus').level)}, "
            f"huawei_solar={logging.getLevelName(logging.getLogger('huawei_solar').level)}"
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
    """Konfiguriert Root Logger mit einheitlichem Format."""
    root = logging.getLogger()
    root.setLevel(level)

    # Handler clearen und neu erstellen
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # StreamHandler für stdout (Docker/Hassio Logging)
    handler = logging.StreamHandler(sys.stdout)
    formatter = TraceFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    root.addHandler(handler)


def _configure_pymodbus(level: int) -> None:
    """Konfiguriert pymodbus Logger."""
    for logger_name in ["pymodbus", "pymodbus.logging"]:
        pymodbus_logger = logging.getLogger(logger_name)
        if level == TRACE:
            pymodbus_logger.setLevel(logging.DEBUG)
        elif level == logging.DEBUG:
            pymodbus_logger.setLevel(logging.INFO)
        else:
            pymodbus_logger.setLevel(logging.WARNING)


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


def heartbeat(config: ConfigManager) -> None:
    """
    Überwacht erfolgreiche Reads und setzt Status auf offline bei Timeout.

    Args:
        config: ConfigManager instance
    """
    timeout = config.status_timeout

    if LAST_SUCCESS == 0:
        return

    offline_duration = time.time() - LAST_SUCCESS

    if offline_duration > timeout:
        if offline_duration < timeout + 5:
            error_status = error_tracker.get_status()
            logger.warning(
                f"⚠️ Inverter offline for {int(offline_duration)}s "
                f"(timeout: {timeout}s) | "
                f"Failed attempts: {error_status['total_failures']} | "
                f"Error types: {error_status['active_errors']}"
            )
        publish_status("offline", config.mqtt_topic)
    else:
        logger.debug(f"Heartbeat OK: {offline_duration:.1f}s since last success")


def log_cycle_summary(cycle_num: float, timings: dict[str, float], data: dict[str, Any]) -> None:
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
                f"└─> 🔍 Filter summary (last 20 cycles): {total_filtered} values filtered | "
                f"Details: {dict(filter_stats)}"
            )
        else:
            logger.info("└─> 🔍 Filter summary (last 20 cycles): 0 values filtered - all data valid ✓")

        get_filter().reset_stats()

    elif filter_stats and logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"🔍 Filter details: {dict(filter_stats)}")


async def read_registers(client: AsyncHuaweiSolar) -> dict[str, Any]:
    """Liest Essential Registers sequentiell vom Inverter."""
    logger.debug(f"Reading {len(ESSENTIAL_REGISTERS)} essential registers")

    start = time.time()
    data = {}
    successful = 0

    for name in ESSENTIAL_REGISTERS:
        try:
            data[name] = await client.get(name)
            successful += 1
        except Exception:
            logger.debug(f"Skipping '{name}' (not available)")

    duration = time.time() - start
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


async def main_once(client: AsyncHuaweiSolar, config: ConfigManager, cycle_num: float) -> None:
    """
    Führt einen kompletten Read-Transform-Filter-Publish Cycle aus.

    Args:
        client:     AsyncHuaweiSolar Client
        config:     ConfigManager instance
        cycle_num:  Aktuelle Cycle-Nummer
    """
    global LAST_SUCCESS

    start: float = time.time()
    logger.debug("Starting cycle")

    # === PHASE 1: Modbus Read ===
    modbus_start: float = time.time()
    try:
        data = await read_registers(client)
        modbus_duration: float = time.time() - modbus_start
    except Exception as e:
        if is_modbus_exception(e):
            logger.warning(f"⚠️ Modbus read failed after {time.time() - start:.1f}s: {e}")
        else:
            logger.error(f"❌ Read error: {e}")
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
    publish_data(mqtt_data, config.mqtt_topic)
    mqtt_duration = time.time() - mqtt_start

    LAST_SUCCESS = time.time()
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
    if cycle_duration > config.poll_interval * 0.8:
        logger.warning("⚠️ Cycle %.1fs > 80%% poll_interval (%ds)", cycle_duration, config.poll_interval)


async def determine_slave_id(config: ConfigManager) -> int:
    """
    Determine the Slave ID to use (auto-detect or manual).

    Args:
        config: ConfigManager instance

    Returns:
        Slave ID to use

    Raises:
        SystemExit: If Slave ID cannot be determined
    """
    if config.modbus_auto_detect_slave_id:
        detected_id = await detect_slave_id(
            host=config.modbus_host,
            port=config.modbus_port,
        )

        if detected_id is not None:
            return detected_id
        else:
            logger.error(
                "❌ Auto-detection failed. Please set 'modbus.auto_detect_slave_id: false' "
                "and configure 'modbus.slave_id' manually in the add-on configuration."
            )
            logger.error(
                "❌ Tested Slave IDs: %s on %s:%s",
                KNOWN_SLAVE_IDS,
                config.modbus_host,
                config.modbus_port,
            )
            sys.exit(1)

    else:
        # Manual Slave ID
        manual_slave_id = config.slave_id

        if manual_slave_id is None:
            logger.error(
                "❌ Auto-detection is disabled but no manual 'slave_id' configured. "
                "Please set 'modbus.slave_id' in the add-on configuration."
            )
            sys.exit(1)

        logger.debug(f"Using manual Slave ID: {manual_slave_id}")
        return manual_slave_id


async def main() -> None:
    """Haupt-Loop mit Error-Handling und automatischer Wiederverbindung."""
    # Load configuration
    try:
        config = ConfigManager()
    except Exception as e:
        # Logging noch nicht initialisiert, daher print()
        print(f"❌ Configuration error: {e}")
        sys.exit(1)

    # Initialize logging
    init_logging(config.log_level)

    logger.info("🚀 Huawei Solar → MQTT starting")

    # Log configuration
    config.log_config()

    # Determine Slave ID (auto-detect or manual)
    slave_id = await determine_slave_id(config)

    # === MQTT Verbindung (persistent) ===
    try:
        connect_mqtt()
        time.sleep(1)
    except Exception as e:
        logger.error(f"❌ MQTT connect failed: {e}")
        sys.exit(1)

    # Initial Status: offline
    publish_status("offline", config.mqtt_topic)

    # === Discovery publizieren ===
    try:
        publish_discovery_configs(config.mqtt_topic)
        logger.info("📢 Discovery published")
    except Exception as e:
        logger.error(f"❌ Discovery failed: {e}")

    # === Modbus Client erstellen ===
    try:
        client = await AsyncHuaweiSolar.create(
            config.modbus_host,
            config.modbus_port,
            slave_id,
        )
        logger.info(f"🔌 Connected (Slave ID: {slave_id})")
        publish_status("online", config.mqtt_topic)
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        disconnect_mqtt()
        return

    # Filter initialisieren
    get_filter()
    logger.info("🛡️ Total Increasing Filter initialized")
    logger.info(f"⏱️ Poll interval: {config.poll_interval}s")

    # === Main Loop ===
    cycle_count: float = 0
    try:
        while True:
            cycle_count += 1
            logger.debug(f"Cycle #{cycle_count}")
            cycle_start = time.time()

            try:
                await main_once(client, config, cycle_count)
                error_tracker.mark_success()
                publish_status("online", config.mqtt_topic)

                # Restliche Zeit bis zum nächsten Poll-Intervall warten
                elapsed = time.time() - cycle_start
                wait = max(0.0, config.poll_interval - elapsed)
                if wait > 0:
                    logger.debug(f"Waiting {wait:.1f}s until next cycle")
                    await asyncio.sleep(wait)

            except TimeoutError as e:
                error_tracker.track_error("timeout", str(e))
                publish_status("offline", config.mqtt_topic)
                reset_filter()
                logger.debug("Filter reset due to timeout")
                await asyncio.sleep(10)

            except ConnectionRefusedError as e:
                error_tracker.track_error("connection_refused", f"Errno {e.errno}")
                publish_status("offline", config.mqtt_topic)
                reset_filter()
                logger.debug("Filter reset due to connection error")
                await asyncio.sleep(10)

            except Exception as e:
                if MODBUS_EXCEPTIONS and isinstance(e, MODBUS_EXCEPTIONS):
                    error_tracker.track_error("modbus_exception", str(e))
                    logger.warning("⚠️ Modbus error, will retry")
                else:
                    error_type = type(e).__name__
                    if error_tracker.track_error(error_type, str(e)):
                        logger.error(f"❌ Unexpected: {error_type}", exc_info=True)

                publish_status("offline", config.mqtt_topic)
                reset_filter()
                logger.debug("Filter reset")
                await asyncio.sleep(10)

            heartbeat(config)

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("🛑 Shutdown")
        publish_status("offline", config.mqtt_topic)
        disconnect_mqtt()

    except Exception as e:
        logger.error(f"💥 Fatal: {e}", exc_info=True)
        publish_status("offline", config.mqtt_topic)
        disconnect_mqtt()
        sys.exit(1)


if __name__ == "__main__":
    """Entry-Point beim direkten Ausführen der Datei."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⌨️ Interrupted")
