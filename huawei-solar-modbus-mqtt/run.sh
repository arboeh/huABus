#!/usr/bin/with-contenv bashio

bashio::log.info "🚀 Starte Huawei Solar Modbus to MQTT Addon..."

# Read config from Home Assistant
export HUAWEI_MODBUS_HOST=$(bashio::config 'modbus_host')
export HUAWEI_MODBUS_PORT=$(bashio::config 'modbus_port')
export HUAWEI_MODBUS_DEVICE_ID=$(bashio::config 'modbus_device_id')
export HUAWEI_MODBUS_MQTT_TOPIC=$(bashio::config 'mqtt_topic')
export HUAWEI_STATUS_TIMEOUT=$(bashio::config 'status_timeout')
export HUAWEI_POLL_INTERVAL=$(bashio::config 'poll_interval')
export HUAWEI_LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "Log level set to: ${HUAWEI_LOG_LEVEL}"

# MQTT Config from Home Assistant Supervisor
if bashio::config.has_value 'mqtt_host'; then
    export HUAWEI_MODBUS_MQTT_BROKER=$(bashio::config 'mqtt_host')
    bashio::log.info "Using custom MQTT broker: ${HUAWEI_MODBUS_MQTT_BROKER}"
else
    export HUAWEI_MODBUS_MQTT_BROKER=$(bashio::services mqtt "host")
    bashio::log.info "Using Home Assistant MQTT broker: ${HUAWEI_MODBUS_MQTT_BROKER}"
fi

if bashio::config.has_value 'mqtt_port'; then
    export HUAWEI_MODBUS_MQTT_PORT=$(bashio::config 'mqtt_port')
else
    export HUAWEI_MODBUS_MQTT_PORT=$(bashio::services mqtt "port")
fi

if bashio::config.has_value 'mqtt_user'; then
    export HUAWEI_MODBUS_MQTT_USER=$(bashio::config 'mqtt_user')
else
    export HUAWEI_MODBUS_MQTT_USER=$(bashio::services mqtt "username")
fi

if bashio::config.has_value 'mqtt_password'; then
    export HUAWEI_MODBUS_MQTT_PASSWORD=$(bashio::config 'mqtt_password')
else
    export HUAWEI_MODBUS_MQTT_PASSWORD=$(bashio::services mqtt "password")
fi

# Debug Mode + Log-Level Kompatibilität
if bashio::config.true 'debug'; then
    export HUAWEI_MODBUS_DEBUG="yes"
    export HUAWEI_LOG_LEVEL="DEBUG"  # ← v1.0.6: Überschreibt log_level
    bashio::log.level "debug"
    bashio::log.debug "Debug mode enabled (legacy flag)"
else
    export HUAWEI_MODBUS_DEBUG="no"
fi

bashio::log.info "Connecting to inverter at ${HUAWEI_MODBUS_HOST}:${HUAWEI_MODBUS_PORT}"
bashio::log.info "Modbus Slave ID: ${HUAWEI_MODBUS_DEVICE_ID}"
bashio::log.info "MQTT Topic: ${HUAWEI_MODBUS_MQTT_TOPIC}"
bashio::log.info "Poll interval: ${HUAWEI_POLL_INTERVAL}s"

# 🚀 Start application - GENAU WIE ES FRÜHER FUNKTIONIERT HAT!
python3 -u /app/huawei2mqtt.py
