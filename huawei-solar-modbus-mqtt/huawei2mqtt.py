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


LAST_SUCCESS = 0


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


def heartbeat(topic):
    global LAST_SUCCESS
    timeout = int(os.environ.get("HUAWEI_STATUS_TIMEOUT", "180"))
    if LAST_SUCCESS == 0:
        return
    diff = time.time() - LAST_SUCCESS
    if diff > timeout:
        publish_status("offline", topic)
        logging.warning("No successful data for %d seconds -> status=offline", timeout)


async def main_once(bridge):
    global LAST_SUCCESS
    topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
    if not topic:
        raise RuntimeError("HUAWEI_MODBUS_MQTT_TOPIC not set")

    logging.debug("Calling bridge.update()")

    try:
        data = await bridge.update()
    except DecodeError as e:
        logging.warning("DecodeError during bridge.update(): %s", e)
        raise

    logging.debug("bridge.update() returned keys: %s", list(data.keys()))

    if not data:
        logging.warning("No data received from inverter")
        return

    mqtt_data = transform_result(data)
    mqtt_publish_data(mqtt_data, topic)
    publish_status("online", topic)
    LAST_SUCCESS = time.time()
    logging.info("Successfully published inverter data")


async def main():
    init()

    topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
    if not topic:
        logging.error("HUAWEI_MODBUS_MQTT_TOPIC not set")
        sys.exit(1)

    modbus_host = os.environ.get("HUAWEI_MODBUS_HOST")
    modbus_port = int(os.environ.get("HUAWEI_MODBUS_PORT", "502"))
    slave_id = int(os.environ.get("HUAWEI_MODBUS_DEVICE_ID", "1"))

    logging.info("Huawei Solar Modbus to MQTT starting")
    publish_status("offline", topic)

    try:
        publish_discovery_configs(topic)
        logging.info("MQTT Discovery configs published")
    except Exception as e:
        logging.error("Failed to publish MQTT Discovery configs: %s", e)

    wait = int(os.environ.get("HUAWEI_POLL_INTERVAL", "60"))
    update_lock = asyncio.Lock()

    try:
        bridge = await HuaweiSolarBridge.create(modbus_host, modbus_port, slave_id, update_lock)
        logging.info("HuaweiSolarBridge created successfully")
    except Exception as e:
        logging.error("Failed to create HuaweiSolarBridge: %s", e)
        logging.debug("Error details: %s", str(e))
        publish_status("offline", topic)
        return

    try:
        while True:
            try:
                await main_once(bridge)
            except DecodeError as e:
                logging.error("DecodeError: %s", e)
                publish_status("offline", topic)
                await asyncio.sleep(10)
            except ReadException as e:
                logging.error("ReadException: %s", e)
                publish_status("offline", topic)
                await asyncio.sleep(30)
            except Exception as e:
                logging.error("Read/publish failed: %s", e)
                publish_status("offline", topic)
                await asyncio.sleep(10)

            heartbeat(topic)
            await asyncio.sleep(wait)

    except asyncio.CancelledError:
        logging.info("Shutting down gracefully")
        publish_status("offline", topic)
    except Exception as e:
        logging.error("Fatal error: %s", e)
        publish_status("offline", topic)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
