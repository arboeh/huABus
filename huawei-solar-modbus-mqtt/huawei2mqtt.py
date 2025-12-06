import asyncio
import logging
import os
import sys
import time
import traceback

from huawei_solar import HuaweiSolarBridge
from huawei_solar.exceptions import DecodeError, ReadException
from dotenv import load_dotenv
from modbus_energy_meter.mqtt import (
    publish_data as mqtt_publish_data,
    publish_status,
    publish_discovery_configs,
)
from modbus_energy_meter.transform import transform_result


LAST_SUCCESS = 0  # Unix-Timestamp des letzten erfolgreichen Reads


def init():
    load_dotenv()

    loglevel = logging.INFO
    if os.environ.get("HUAWEI_MODBUS_DEBUG") == "yes":
        loglevel = logging.DEBUG

    logger = logging.getLogger()
    logger.setLevel(loglevel)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    formatter.datefmt = "%Y-%m-%dT%H:%M:%S%z"

    handler.setFormatter(formatter)
    logger.addHandler(handler)


def heartbeat(topic: str):
    """
    Überwacht, ob seit zu langer Zeit kein erfolgreicher Read war,
    und setzt dann den Status auf offline.
    """
    global LAST_SUCCESS

    timeout = int(os.environ.get("HUAWEI_STATUS_TIMEOUT", "180"))  # Sekunden

    if LAST_SUCCESS == 0:
        # Noch kein erfolgreicher Read – nichts machen
        return

    diff = time.time() - LAST_SUCCESS
    if diff > timeout:
        publish_status("offline", topic)
        logging.warning(
            "No successful data for %d seconds (%.1fs) -> status=offline",
            timeout,
            diff,
        )


async def main_once(bridge):
    """
    Ein einzelner Read-Publish-Zyklus.
    Setzt Status nur bei Erfolg auf online.
    """
    global LAST_SUCCESS

    topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
    if not topic:
        raise RuntimeError("HUAWEI_MODBUS_MQTT_TOPIC not set")

    logging.debug("Calling bridge.update()")
    
    try:
        data = await bridge.update()
    except DecodeError as e:
        logging.warning("DecodeError during bridge.update(): %s - attempting partial read", e)
        raise
    
    logging.debug("bridge.update() returned keys: %s", list(data.keys()))

    if not data:
        logging.warning("No data received from inverter")
        return

    mqtt_data = transform_result(data)

    # Daten publishen
    mqtt_publish_data(mqtt_data, topic)

    # Status nach Erfolg auf online setzen
    publish_status("online", topic)

    LAST_SUCCESS = time.time()
    logging.info("Successfully published inverter data (status=online)")


async def main():
    init()

    topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
    if not topic:
        logging.error("HUAWEI_MODBUS_MQTT_TOPIC not set – exiting")
        sys.exit(1)

    modbus_host = os.environ.get("HUAWEI_MODBUS_HOST")
    modbus_port = int(os.environ.get("HUAWEI_MODBUS_PORT", "502"))
    slave_id = int(os.environ.get("HUAWEI_MODBUS_DEVICE_ID", "1"))

    logging.info("Huawei Solar Modbus to MQTT starting")
    publish_status("offline", topic)

    # Discovery nur einmal
    try:
        publish_discovery_configs(topic)
        logging.info("MQTT Discovery configs published")
    except Exception as e:
        logging.error(f"Failed to publish MQTT Discovery configs: {e}")

    wait = int(os.environ.get("HUAWEI_POLL_INTERVAL", "60"))

    # Bridge einmalig im selben Event Loop erstellen
    try:
        bridge = await HuaweiSolarBridge.create(
            modbus_host,
            modbus_port,
            slave_id=slave_id,
        )
    except Exception as e:
        logging.error("Failed to create HuaweiSolarBridge: %s", e)
        publish_status("offline", topic)
        return

    try:
        while True:
            try:
                await main_once(bridge)
            except DecodeError as e:
                logging.error("DecodeError: %s - skipping this cycle", e)
                logging.debug("Traceback:\n%s", traceback.format_exc())
                publish_status("offline", topic)
                await asyncio.sleep(10)
            except ReadException as e:
                logging.error("ReadException: %s - connection issue", e)
                logging.debug("Traceback:\n%s", traceback.format_exc())
                publish_status("offline", topic)
                await asyncio.sleep(30)
            except Exception as e:
                logging.error("Read/publish failed (%s): %s", type(e).__name__, e)
                logging.debug("Traceback:\n%s", traceback.format_exc())
                publish_status("offline", topic)
                await asyncio.sleep(10)
            
            heartbeat(topic)
            await asyncio.sleep(wait)
            
    except asyncio.CancelledError:
        logging.info("Shutting down gracefully...")
        publish_status("offline", topic)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        logging.debug("Traceback:\n%s", traceback.format_exc())
        publish_status("offline", topic)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Interrupted by user, exiting...")
