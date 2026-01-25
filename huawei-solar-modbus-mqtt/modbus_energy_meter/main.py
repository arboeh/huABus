# modbus_energy_meter/main.py
import asyncio
import logging
import os
import sys
import time
from typing import Dict, Any

from huawei_solar import AsyncHuaweiSolar  # type: ignore
from .error_tracker import ConnectionErrorTracker

try:
    from pymodbus.exceptions import ModbusException  # type: ignore
    from pymodbus.pdu import ExceptionResponse  # type: ignore

    MODBUS_EXCEPTIONS = (ModbusException, ExceptionResponse)
except ImportError:
    # Fallback wenn pymodbus nicht verfügbar
    MODBUS_EXCEPTIONS = ()

from .config.registers import ESSENTIAL_REGISTERS
from .mqtt_client import (
    connect_mqtt,
    disconnect_mqtt,
    publish_status,
    publish_discovery_configs,
    publish_data,
)
from .transform import transform_data

# Logger
logger = logging.getLogger("huawei.main")

# Error Tracker
error_tracker = ConnectionErrorTracker(log_interval=60)

LAST_SUCCESS = 0


def init_logging() -> None:
    """Initialisiert Logging mit ENV-Konfiguration."""
    log_level = _parse_log_level()
    _setup_root_logger(log_level)
    _configure_pymodbus(log_level)
    _configure_huawei_solar(log_level)

    logger.info(f"Logging initialized: {logging.getLevelName(log_level)}")


def _parse_log_level() -> int:
    """Parse HUAWEI_LOG_LEVEL oder Fallback."""
    level_str = os.environ.get("HUAWEI_LOG_LEVEL", "INFO").upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }

    if os.environ.get("HUAWEI_MODBUS_DEBUG") == "yes":
        return logging.DEBUG

    return level_map.get(level_str, logging.INFO)


def _setup_root_logger(level: int) -> None:
    """Konfiguriert Root Logger mit einheitlichem Format."""
    root = logging.getLogger()
    root.setLevel(level)

    # Handler clearen und neu erstellen
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root.addHandler(handler)


def _configure_pymodbus(level: int) -> None:
    """Pymodbus Logging konfigurieren - nur Errors zeigen."""
    pymodbus_logger = logging.getLogger("pymodbus")
    # Immer ERROR, außer bei DEBUG
    pymodbus_logger.setLevel(logging.ERROR if level != logging.DEBUG else logging.DEBUG)


def _configure_huawei_solar(level: int) -> None:
    """Huawei Solar Logging - Tracebacks unterdrücken."""
    hs_logger = logging.getLogger("huawei_solar")
    # Bei INFO nur WARNING+, bei DEBUG alles
    if level == logging.DEBUG:
        hs_logger.setLevel(logging.DEBUG)
    else:
        hs_logger.setLevel(logging.ERROR)  # Nur echte Errors


def heartbeat(topic: str) -> None:
    """Überwacht erfolgreiche Reads und setzt Status."""
    global LAST_SUCCESS
    timeout = int(os.environ.get("HUAWEI_STATUS_TIMEOUT", "180"))

    if LAST_SUCCESS == 0:
        return

    offline_duration = time.time() - LAST_SUCCESS

    if offline_duration > timeout:
        # Nur einmal loggen beim Übergang zu offline
        if offline_duration < timeout + 5:
            error_status = error_tracker.get_status()
            logger.warning(
                f"Inverter offline for {int(offline_duration)}s "
                f"(timeout: {timeout}s) | "
                f"Failed attempts: {error_status['total_failures']} | "
                f"Error types: {error_status['active_errors']}"
            )
        publish_status("offline", topic)
    else:
        logger.debug(f"Heartbeat OK: {offline_duration:.1f}s since last success")


def log_cycle_summary(
    cycle_num: int, timings: Dict[str, float], data: Dict[str, Any]
) -> None:
    """Log cycle summary - can be JSON for machine parsing."""

    if os.environ.get("HUAWEI_LOG_FORMAT") == "json":
        import json

        summary = {
            "cycle": cycle_num,
            "timestamp": time.time(),
            "timings": timings,
            "power": {
                "pv": data.get("power_input", 0),
                "ac_out": data.get("power_active", 0),
                "grid": data.get("meter_power_active", 0),
                "battery": data.get("battery_power", 0),
            },
        }
        logger.info(json.dumps(summary))
    else:
        # Standard human-readable log
        logger.info(
            "📊 Published - PV: %dW | AC Out: %dW | Grid: %dW | Battery: %dW",
            data.get("power_input", 0),
            data.get("power_active", 0),
            data.get("meter_power_active", 0),
            data.get("battery_power", 0),
        )


async def read_registers(client: AsyncHuaweiSolar) -> Dict[str, Any]:
    """Liest Essential Registers sequentiell."""
    logger.debug(f"Reading {len(ESSENTIAL_REGISTERS)} essential registers")

    start = time.time()
    data = {}
    successful = 0

    for name in ESSENTIAL_REGISTERS:
        try:
            data[name] = await client.get(name)
            successful += 1
        except Exception:
            logger.debug(f"Failed {name}")

    duration = time.time() - start
    logger.info(
        "Essential read: %.1fs (%d/%d)", duration, successful, len(ESSENTIAL_REGISTERS)
    )

    return data


def is_modbus_exception(exc: Exception) -> bool:
    """Check if exception is a Modbus-related error."""
    if not MODBUS_EXCEPTIONS:
        return False
    return isinstance(exc, MODBUS_EXCEPTIONS)


async def main_once(client: AsyncHuaweiSolar, cycle_num: int) -> None:
    """Read essential registers and publish."""
    global LAST_SUCCESS
    topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
    if not topic:
        raise RuntimeError("HUAWEI_MODBUS_MQTT_TOPIC not set")

    start = time.time()
    logger.debug("Starting cycle")

    # Modbus Read
    modbus_start = time.time()
    try:
        data = await read_registers(client)
        modbus_duration = time.time() - modbus_start
    except Exception as e:
        # Check if it's a Modbus exception
        if is_modbus_exception(e):
            logger.warning(f"Modbus read failed after {time.time() - start:.1f}s: {e}")
        else:
            logger.error(f"Read error: {e}")
        raise

    if not data:
        logger.warning("No data")
        return

    # Transform & Publish
    transform_start = time.time()
    mqtt_data = transform_data(data)
    transform_duration = time.time() - transform_start

    mqtt_start = time.time()
    publish_data(mqtt_data, topic)
    mqtt_duration = time.time() - mqtt_start

    LAST_SUCCESS = time.time()
    cycle_duration = time.time() - start

    # Timings Dict für log_cycle_summary
    timings = {
        "modbus": modbus_duration,
        "transform": transform_duration,
        "mqtt": mqtt_duration,
        "total": cycle_duration,
    }

    log_cycle_summary(cycle_num, timings, mqtt_data)

    # Debug-Details nur bei DEBUG-Level
    logger.debug(
        "Cycle: %.1fs (Modbus: %.1fs, Transform: %.2fs, MQTT: %.2fs)",
        cycle_duration,
        modbus_duration,
        transform_duration,
        mqtt_duration,
    )

    # Performance Warning
    poll_interval = int(os.environ.get("HUAWEI_POLL_INTERVAL", "30"))
    if cycle_duration > poll_interval * 0.8:
        logger.warning(
            "Cycle %.1fs > 80%% poll_interval (%ds)", cycle_duration, poll_interval
        )


async def main() -> None:
    """Haupt-Loop mit Error-Handling."""
    init_logging()

    # Check topic
    topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
    if not topic:
        logger.error("HUAWEI_MODBUS_MQTT_TOPIC missing")
        sys.exit(1)

    # Check host
    host = os.environ.get("HUAWEI_MODBUS_HOST")
    if not host:
        logger.error("HUAWEI_MODBUS_HOST missing")
        sys.exit(1)

    port = int(os.environ.get("HUAWEI_MODBUS_PORT", "502"))
    slave_id = int(os.environ.get("HUAWEI_SLAVE_ID", "1"))

    logger.info("Huawei Solar → MQTT starting")
    logger.debug(f"Host={host}:{port}, Slave={slave_id}, Topic={topic}")

    # MQTT einmal verbinden (persistent)
    try:
        connect_mqtt()
        import time

        time.sleep(1)
    except Exception as e:
        logger.error(f"MQTT connect failed: {e}")
        sys.exit(1)

    publish_status("offline", topic)

    # Discovery
    try:
        publish_discovery_configs(topic)
        logger.info("Discovery published")
    except Exception as e:
        logger.error(f"Discovery failed: {e}")

    # Client
    try:
        client = await AsyncHuaweiSolar.create(host, port, slave_id)
        logger.info(f"Connected (Slave ID: {slave_id})")
        publish_status("online", topic)
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        disconnect_mqtt()
        return

    # Main Loop
    poll_interval = int(os.environ.get("HUAWEI_POLL_INTERVAL", "30"))
    logger.info(f"Poll interval: {poll_interval}s")

    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            logger.debug(f"Cycle #{cycle_count}")

            try:
                await main_once(client, cycle_count)
                error_tracker.mark_success()
                publish_status("online", topic)
            except asyncio.TimeoutError as e:
                error_tracker.track_error("timeout", str(e))
                publish_status("offline", topic)
                await asyncio.sleep(10)
            except (ModbusException, ExceptionResponse) as e:  # type: ignore[misc]
                error_tracker.track_error("modbus_exception", str(e))
                publish_status("offline", topic)
                await asyncio.sleep(10)
            except ConnectionRefusedError as e:
                error_tracker.track_error("connection_refused", f"Errno {e.errno}")
                publish_status("offline", topic)
                await asyncio.sleep(10)
            except Exception as e:
                # Nur unbekannte Fehler mit Traceback
                error_type = type(e).__name__
                if error_tracker.track_error(error_type, str(e)):
                    logger.error(f"Unexpected: {error_type}", exc_info=True)
                publish_status("offline", topic)
                await asyncio.sleep(10)

            heartbeat(topic)
            await asyncio.sleep(poll_interval)

    except asyncio.CancelledError:
        logger.info("Shutdown")
        publish_status("offline", topic)
        disconnect_mqtt()
    except Exception as e:
        logger.error(f"Fatal: {e}")
        publish_status("offline", topic)
        disconnect_mqtt()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")
