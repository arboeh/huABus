import asyncio
import logging
import os
import sys
import time

from huawei_solar import HuaweiSolarBridge
from dotenv import load_dotenv
from modbus_energy_meter.mqtt import publish_data as mqtt_publish_data, publish_status, publish_discovery_configs
from modbus_energy_meter.transform import transform_result


def init():
    load_dotenv()

    loglevel = logging.INFO
    if os.environ.get('HUAWEI_MODBUS_DEBUG') == 'yes':
        loglevel = logging.DEBUG

    logger = logging.getLogger()
    logger.setLevel(loglevel)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    formatter.datefmt = '%Y-%m-%dT%H:%M:%S%z'

    handler.setFormatter(formatter)
    logger.addHandler(handler)


async def main():
    topic = os.environ.get('HUAWEI_MODBUS_MQTT_TOPIC')
    modbus_slave_id = int(os.environ.get('HUAWEI_MODBUS_DEVICE_ID', '1'))

    try:
        bridge = await HuaweiSolarBridge.create(
            os.environ.get('HUAWEI_MODBUS_HOST'),
            int(os.environ.get('HUAWEI_MODBUS_PORT', '502')),
            slave_id=modbus_slave_id,
        )

        logging.info(
            f"Successfully connected to inverter at {os.environ.get('HUAWEI_MODBUS_HOST')}")

        data = await bridge.update()
        mqtt_data = transform_result(data)

        mqtt_publish_data(mqtt_data, topic)
        publish_status('online', topic)

        logging.info("Successfully published data to MQTT")

    except Exception as e:
        logging.error(f"Error querying inverter or publishing to MQTT: {e}")
        publish_status('offline', topic)
        raise


if __name__ == "__main__":
    init()

    topic = os.environ.get('HUAWEI_MODBUS_MQTT_TOPIC')

    logging.info("Huawei Solar Modbus to MQTT started")

    # Publish MQTT Discovery configs once at startup
    try:
        publish_discovery_configs(topic)
        logging.info("MQTT Discovery configs published")
    except Exception as e:
        logging.error(f"Failed to publish MQTT Discovery configs: {e}")

    # Publish initial online status
    publish_status('online', topic)

    last_run = 0
    wait = 60

    try:
        while True:
            if last_run > 0 and (time.time() - last_run < wait):
                sleep_time = max(2, int(wait - (time.time() - last_run)))
                logging.debug(f"Sleeping for {sleep_time} seconds")
                time.sleep(sleep_time)

            last_run = time.time()

            try:
                asyncio.run(main())
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                # Continue running even after errors
                time.sleep(10)

    except KeyboardInterrupt:
        logging.info("Shutting down gracefully...")
        publish_status('offline', topic)
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        publish_status('offline', topic)
        sys.exit(1)
