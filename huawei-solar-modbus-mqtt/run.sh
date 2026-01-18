#!/usr/bin/with-contenv bashio

VERSION=$(bashio::addon.version)

# Banner IMMER anzeigen
echo "[$(date +'%T')] INFO: =================================================================="
echo "[$(date +'%T')] INFO:  🌞 Huawei Solar Modbus MQTT v${VERSION}"
echo "[$(date +'%T')] INFO:  📦 https://github.com/arboeh/homeassistant-huawei-solar-addon"
echo "[$(date +'%T')] INFO: =================================================================="
echo "[$(date +'%T')] INFO: >> Starting Huawei Solar Modbus MQTT Add-on..."
echo "[$(date +'%T')] INFO: >> Log level: $(bashio::config 'log_level')"

# Modbus Configuration
export HUAWEI_MODBUS_HOST=$(bashio::config 'modbus_host')
export HUAWEI_MODBUS_PORT=$(bashio::config 'modbus_port')
export HUAWEI_SLAVE_ID=$(bashio::config 'slave_id')

# MQTT Topic & Intervals
export HUAWEI_MODBUS_MQTT_TOPIC=$(bashio::config 'mqtt_topic')
export HUAWEI_STATUS_TIMEOUT=$(bashio::config 'status_timeout')
export HUAWEI_POLL_INTERVAL=$(bashio::config 'poll_interval')

# Log Level Configuration
export HUAWEI_LOG_LEVEL=$(bashio::config 'log_level')

# Set bashio log level to match
case "${HUAWEI_LOG_LEVEL}" in
DEBUG)
	bashio::log.level debug
	;;
WARNING)
	bashio::log.level warning
	;;
ERROR)
	bashio::log.level error
	;;
*)
	bashio::log.level info
	;;
esac

# MQTT Broker (Custom or HA Service) - nur für Export, kein echo
if bashio::config.has_value 'mqtt_host' && [ -n "$(bashio::config 'mqtt_host')" ]; then
	export HUAWEI_MODBUS_MQTT_BROKER=$(bashio::config 'mqtt_host')
	MQTT_SOURCE="custom"
else
	export HUAWEI_MODBUS_MQTT_BROKER=$(bashio::services mqtt "host")
	MQTT_SOURCE="HA service"
fi

# MQTT Port
if bashio::config.has_value 'mqtt_port' && [ -n "$(bashio::config 'mqtt_port')" ]; then
	export HUAWEI_MODBUS_MQTT_PORT=$(bashio::config 'mqtt_port')
else
	export HUAWEI_MODBUS_MQTT_PORT=$(bashio::services mqtt "port")
fi

# MQTT User
if bashio::config.has_value 'mqtt_user' && [ -n "$(bashio::config 'mqtt_user')" ]; then
	export HUAWEI_MODBUS_MQTT_USER=$(bashio::config 'mqtt_user')
	MQTT_AUTH="custom"
else
	export HUAWEI_MODBUS_MQTT_USER=$(bashio::services mqtt "username")
	MQTT_AUTH="HA service"
fi

# MQTT Password
if bashio::config.has_value 'mqtt_password' && [ -n "$(bashio::config 'mqtt_password')" ]; then
	export HUAWEI_MODBUS_MQTT_PASSWORD=$(bashio::config 'mqtt_password')
else
	export HUAWEI_MODBUS_MQTT_PASSWORD=$(bashio::services mqtt "password")
fi

# Connection Summary - IMMER anzeigen (nur hier, nicht vorher!)
echo "[$(date +'%T')] INFO: ------------------------------------------------------------------"
echo "[$(date +'%T')] INFO:  🔌 Inverter: ${HUAWEI_MODBUS_HOST}:${HUAWEI_MODBUS_PORT} (Slave ID: ${HUAWEI_SLAVE_ID})"
echo "[$(date +'%T')] INFO:  📡 MQTT: ${HUAWEI_MODBUS_MQTT_BROKER}:${HUAWEI_MODBUS_MQTT_PORT} (${MQTT_SOURCE})"

# Zeige MQTT Auth Status (ohne Credentials zu leaken)
if [ -n "${HUAWEI_MODBUS_MQTT_USER}" ]; then
	echo "[$(date +'%T')] INFO:  🔐 Auth: enabled (${MQTT_AUTH})"
else
	echo "[$(date +'%T')] INFO:  🔐 Auth: disabled"
fi

echo "[$(date +'%T')] INFO:  📍 Topic: ${HUAWEI_MODBUS_MQTT_TOPIC}"
echo "[$(date +'%T')] INFO:  ⏱️  Poll: ${HUAWEI_POLL_INTERVAL}s | Timeout: ${HUAWEI_STATUS_TIMEOUT}s"

# Registerzähler
REGISTER_COUNT=58
echo "[$(date +'%T')] INFO:  📊 Registers: ${REGISTER_COUNT} essential"

echo "[$(date +'%T')] INFO: ------------------------------------------------------------------"

# System Info
bashio::log.info ">> System Info:"
bashio::log.info "   - Python: $(python3 --version | cut -d' ' -f2)"

# Get package versions - using pip show with fallback
HUAWEI_SOLAR_VERSION=$(pip3 show huawei-solar 2>/dev/null | grep '^Version:' | awk '{print $2}')
PYMODBUS_VERSION=$(pip3 show pymodbus 2>/dev/null | grep '^Version:' | awk '{print $2}')
PAHO_VERSION=$(pip3 show paho-mqtt 2>/dev/null | grep '^Version:' | awk '{print $2}')

# Fallback to "unknown" if empty
HUAWEI_SOLAR_VERSION=${HUAWEI_SOLAR_VERSION:-unknown}
PYMODBUS_VERSION=${PYMODBUS_VERSION:-unknown}
PAHO_VERSION=${PAHO_VERSION:-unknown}

bashio::log.info "   - huawei-solar: ${HUAWEI_SOLAR_VERSION}"
bashio::log.info "   - pymodbus: ${PYMODBUS_VERSION}"
bashio::log.info "   - paho-mqtt: ${PAHO_VERSION}"
bashio::log.info "   - Architecture: $(uname -m)"

echo "[$(date +'%T')] INFO: >> Starting Python application..."

# Start Python application
cd /app || exit 1
exec python3 -u -m modbus_energy_meter.main
