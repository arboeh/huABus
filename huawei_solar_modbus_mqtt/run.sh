#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
# shellcheck disable=SC1008

VERSION=$(bashio::addon.version)

# Banner IMMER anzeigen
echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO: =========================================================="
echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO:  🌞 huABus v${VERSION}"
echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO:  📦 https://github.com/arboeh/huABus"
echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO: =========================================================="
echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO: >> Starting huABus - Huawei Solar Modbus MQTT Add-on..."

# Helper function for required config
get_required_config() {
    local key="$1"
    local default="${2-}" # Default ist leerer String wenn nicht angegeben
    local value

    if bashio::config.has_value "${key}"; then
        value=$(bashio::config "${key}")
    elif [ -n "${default}" ]; then
        value="${default}"
    else
        # Bei leerem default ist es optional
        value=""
    fi

    echo "${value}"
}

# Modbus Configuration
HUAWEI_MODBUS_HOST=$(get_required_config 'modbus_host')
export HUAWEI_MODBUS_HOST

HUAWEI_MODBUS_PORT=$(get_required_config 'modbus_port' '502')
export HUAWEI_MODBUS_PORT

HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID=$(get_required_config 'modbus_auto_detect_slave_id' 'true')
export HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID

HUAWEI_SLAVE_ID=$(get_required_config 'slave_id' '1')
export HUAWEI_SLAVE_ID

# MQTT Configuration - Prüfe ob mqtt_host in der Config ist
MQTT_HOST_CONFIG=$(get_required_config 'mqtt_host')

if [ -n "${MQTT_HOST_CONFIG}" ]; then
    # Custom mqtt_host aus Config
    HUAWEI_MQTT_HOST="${MQTT_HOST_CONFIG}"
    export HUAWEI_MQTT_HOST

    HUAWEI_MQTT_PORT=$(get_required_config 'mqtt_port' '1883')
    export HUAWEI_MQTT_PORT

    MQTT_SOURCE="custom"
else
    # Alles aus HA Service
    if bashio::services.available mqtt; then
        HUAWEI_MQTT_HOST=$(bashio::services mqtt "host")
        export HUAWEI_MQTT_HOST

        HUAWEI_MQTT_PORT=$(bashio::services mqtt "port")
        export HUAWEI_MQTT_PORT

        MQTT_SOURCE="HA service"
    else
        bashio::log.fatal "❌ No MQTT broker configured and HA MQTT service not available!"
        exit 1
    fi
fi

# MQTT Credentials - Prüfe ob explizite Credentials in Config gesetzt sind
MQTT_USER_CONFIG=$(get_required_config 'mqtt_user')
MQTT_PASS_CONFIG=$(get_required_config 'mqtt_password')

if [ -n "${MQTT_USER_CONFIG}" ] && [ -n "${MQTT_PASS_CONFIG}" ]; then
    # Explizite Credentials in Config verwenden
    HUAWEI_MQTT_USER="${MQTT_USER_CONFIG}"
    export HUAWEI_MQTT_USER

    HUAWEI_MQTT_PASSWORD="${MQTT_PASS_CONFIG}"
    export HUAWEI_MQTT_PASSWORD
elif bashio::services.available mqtt; then
    # Keine expliziten Credentials -> HA Service nutzen
    HUAWEI_MQTT_USER=$(bashio::services mqtt "username")
    export HUAWEI_MQTT_USER

    HUAWEI_MQTT_PASSWORD=$(bashio::services mqtt "password")
    export HUAWEI_MQTT_PASSWORD
else
    # Keine Credentials verfügbar -> no-auth Broker
    export HUAWEI_MQTT_USER=""
    export HUAWEI_MQTT_PASSWORD=""
fi

HUAWEI_MQTT_TOPIC=$(get_required_config 'mqtt_topic' 'huawei-solar')
export HUAWEI_MQTT_TOPIC

# Advanced Configuration
HUAWEI_STATUS_TIMEOUT=$(get_required_config 'status_timeout' '180')
export HUAWEI_STATUS_TIMEOUT

HUAWEI_POLL_INTERVAL=$(get_required_config 'poll_interval' '30')
export HUAWEI_POLL_INTERVAL

HUAWEI_LOG_LEVEL=$(get_required_config 'log_level' 'INFO')
export HUAWEI_LOG_LEVEL

echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO: >> Log level: ${HUAWEI_LOG_LEVEL}"

# Set bashio log level to match
case "${HUAWEI_LOG_LEVEL}" in
    TRACE)
        bashio::log.level debug # bashio doesn't have TRACE, use DEBUG
        ;;
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

# Validation
if [ -z "${HUAWEI_MODBUS_HOST}" ]; then
    bashio::log.fatal "❌ Modbus host is required but not configured!"
    exit 1
fi

if [ -z "${HUAWEI_MQTT_HOST}" ]; then
    bashio::log.fatal "❌ MQTT broker is required but not configured!"
    exit 1
fi

# Connection Summary
echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO: ----------------------------------------------------------"

# Slave ID Display Logic
if [ "${HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID}" = "true" ]; then
    echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO:  🔌 Inverter: ${HUAWEI_MODBUS_HOST}:${HUAWEI_MODBUS_PORT} (Slave ID: auto-detect)"
else
    echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO:  🔌 Inverter: ${HUAWEI_MODBUS_HOST}:${HUAWEI_MODBUS_PORT} (Slave ID: ${HUAWEI_SLAVE_ID})"
fi

echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO:  📡 MQTT: ${HUAWEI_MQTT_HOST}:${HUAWEI_MQTT_PORT} (${MQTT_SOURCE})"

# Zeige MQTT Auth Status ohne Credentials zu leaken
if [ -n "${HUAWEI_MQTT_USER}" ]; then
    echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO:  🔐 Auth: enabled (${MQTT_SOURCE})"
else
    echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO:  🔐 Auth: disabled"
fi

echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO:  📍 Topic: ${HUAWEI_MQTT_TOPIC}"
echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO:  ⏱️ Poll: ${HUAWEI_POLL_INTERVAL}s | Timeout: ${HUAWEI_STATUS_TIMEOUT}s"

echo "[$(date +'%T')] INFO: ----------------------------------------------------------"

# System Info
bashio::log.info ">> System Info"
bashio::log.info "    - Python: $(python3 --version | cut -d' ' -f2)" # Get version without "Python" prefix

# Get package versions - using pip show with fallback
HUAWEI_SOLAR_VERSION=$(pip3 show huawei-solar 2> /dev/null | grep "Version:" | awk '{print $2}')
PYMODBUS_VERSION=$(pip3 show pymodbus 2> /dev/null | grep "Version:" | awk '{print $2}')
PAHO_VERSION=$(pip3 show paho-mqtt 2> /dev/null | grep "Version:" | awk '{print $2}')

# Fallback to "unknown" if empty
HUAWEI_SOLAR_VERSION="${HUAWEI_SOLAR_VERSION:-unknown}"
PYMODBUS_VERSION="${PYMODBUS_VERSION:-unknown}"
PAHO_VERSION="${PAHO_VERSION:-unknown}"

bashio::log.info "    - huawei-solar: ${HUAWEI_SOLAR_VERSION}"
bashio::log.info "    - pymodbus: ${PYMODBUS_VERSION}"
bashio::log.info "    - paho-mqtt: ${PAHO_VERSION}"
bashio::log.info "    - Architecture: $(uname -m)"

echo "[$(date +'%T')] INFO: ----------------------------------------------------------"

# TEST MODE GUARD - Exit here when running BATS tests
if [ "${BATS_TEST_MODE:-false}" = "true" ]; then
    bashio::log.info "Test mode enabled - skipping application start"
    return 0
fi

# Dynamische Register-Zählung
if [ "${BATS_TEST_MODE:-}" != "true" ]; then
    REGISTER_COUNT=$(python3 -c "from bridge.config.registers import ESSENTIAL_REGISTERS; print(len(ESSENTIAL_REGISTERS))" 2> /dev/null || echo "58")
    echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO:  🔢 Registers: ${REGISTER_COUNT} essential"
fi

echo "[$(date +'%T')] INFO: ----------------------------------------------------------"

echo "$(date +"%Y-%m-%dT%H:%M:%S") INFO: >> Starting Python application..."

# Start Python application
cd /app || exit 1
exec python3 -u -m bridge.main
