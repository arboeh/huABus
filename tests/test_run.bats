#!/usr/bin/env bats

# tests/test_run.bats - Tests für run.sh

setup() {

    # ===== TEST MODE MUSS GANZ OBEN STEHEN =====
    export BATS_TEST_MODE=true
    # ===========================================

    # Testdaten vorbereiten
    export TEST_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

    # Mock ALLE bashio functions
    bashio::addon.version() {
        echo "1.0.0"
    }

    bashio::config() {
        case "$1" in
        "modbus_host") echo "192.168.1.100" ;;
        "modbus_port") echo "502" ;;
        "modbus_auto_detect_slave_id") echo "true" ;;
        "slave_id") echo "1" ;;
        "mqtt_host") echo "core-mosquitto" ;;
        "mqtt_port") echo "1883" ;;
        "mqtt_user") echo "" ;;
        "mqtt_password") echo "" ;;
        "mqtt_topic") echo "huawei-solar" ;;
        "log_level") echo "INFO" ;;
        "status_timeout") echo "180" ;;
        "poll_interval") echo "30" ;;
        *) echo "${2:-}" ;;
        esac
    }

    bashio::config.has_value() {
        case "$1" in
        "modbus_host" | "modbus_port" | "modbus_auto_detect_slave_id" | "slave_id" | "mqtt_topic" | "log_level" | "status_timeout" | "poll_interval")
            return 0
            ;;
        *)
            return 1
            ;;
        esac
    }

    bashio::services.available() {
        [ "$1" = "mqtt" ]
    }

    bashio::services() {
        case "$2" in
        "host") echo "core-mosquitto" ;;
        "port") echo "1883" ;;
        "username") echo "homeassistant" ;;
        "password") echo "secret" ;;
        esac
    }

    bashio::log.fatal() {
        echo "FATAL: $*" >&2
        exit 1
    }

    bashio::log.warning() {
        echo "WARNING: $*" >&2
    }

    bashio::log.info() {
        echo "INFO: $*"
    }

    bashio::log.level() {
        return 0
    }

    # Export alle Mock-Funktionen
    export -f bashio::addon.version
    export -f bashio::config
    export -f bashio::config.has_value
    export -f bashio::services.available
    export -f bashio::services
    export -f bashio::log.fatal
    export -f bashio::log.warning
    export -f bashio::log.info
    export -f bashio::log.level
}

teardown() {
    unset BATS_TEST_MODE
    unset HUAWEI_MODBUS_HOST
    unset HUAWEI_MODBUS_PORT
    unset HUAWEI_MQTT_HOST
    unset HUAWEI_MQTT_PORT
    unset HUAWEI_MQTT_USER
    unset HUAWEI_MQTT_PASSWORD
    unset HUAWEI_MQTT_TOPIC
    unset HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID
    unset HUAWEI_SLAVE_ID
    unset HUAWEI_STATUS_TIMEOUT
    unset HUAWEI_POLL_INTERVAL
    unset HUAWEI_LOG_LEVEL
}

@test "get_required_config returns value when config exists" {
    run bash -c "
        export BATS_TEST_MODE=true
        $(declare -f bashio::addon.version bashio::config bashio::config.has_value bashio::services.available bashio::services bashio::log.fatal bashio::log.warning bashio::log.info bashio::log.level)
        source huawei_solar_modbus_mqtt/run.sh && get_required_config 'modbus_host'
    "
    [ "$status" -eq 0 ]
    [[ "$output" =~ "192.168.1.100" ]]
}

@test "get_required_config uses default when provided" {
    run bash -c "
        export BATS_TEST_MODE=true
        $(declare -f bashio::addon.version bashio::config bashio::config.has_value bashio::services.available bashio::services bashio::log.fatal bashio::log.warning bashio::log.info bashio::log.level)
        source huawei_solar_modbus_mqtt/run.sh && get_required_config 'modbus_port' '502'
    "
    [ "$status" -eq 0 ]
    [[ "$output" =~ "502" ]]
}

@test "MQTT broker from custom config with HA auth" {
    bashio::config.has_value() {
        case "$1" in
        modbus_host | modbus_port | mqtt_host) return 0 ;;
        *) return 1 ;;
        esac
    }
    bashio::config() {
        case "$1" in
        mqtt_host) echo 'mqtt.custom.local' ;;
        modbus_host) echo '192.168.1.100' ;;
        modbus_port) echo '502' ;;
        modbus_auto_detect_slave_id) echo 'true' ;;
        slave_id) echo '1' ;;
        mqtt_port) echo '1883' ;;
        mqtt_user) echo '' ;;     # Leer!
        mqtt_password) echo '' ;; # Leer!
        mqtt_topic) echo 'huawei-solar' ;;
        log_level) echo 'INFO' ;;
        status_timeout) echo '180' ;;
        poll_interval) echo '30' ;;
        *) echo '' ;;
        esac
    }
    export -f bashio::config.has_value
    export -f bashio::config

    source huawei_solar_modbus_mqtt/run.sh >/dev/null 2>&1

    [ "$HUAWEI_MQTT_HOST" = "mqtt.custom.local" ]
    [ "$HUAWEI_MQTT_USER" = "homeassistant" ] # Aus HA Service
    [ "$HUAWEI_MQTT_PASSWORD" = "secret" ]    # Aus HA Service
}

@test "MQTT broker from custom config with explicit auth" {
    bashio::config.has_value() {
        case "$1" in
        modbus_host | modbus_port | mqtt_host | mqtt_user | mqtt_password) return 0 ;;
        *) return 1 ;;
        esac
    }
    bashio::config() {
        case "$1" in
        mqtt_host) echo 'mqtt.custom.local' ;;
        mqtt_user) echo 'custom_user' ;;
        mqtt_password) echo 'custom_pass' ;;
        modbus_host) echo '192.168.1.100' ;;
        modbus_port) echo '502' ;;
        modbus_auto_detect_slave_id) echo 'true' ;;
        slave_id) echo '1' ;;
        mqtt_port) echo '1883' ;;
        mqtt_topic) echo 'huawei-solar' ;;
        log_level) echo 'INFO' ;;
        status_timeout) echo '180' ;;
        poll_interval) echo '30' ;;
        *) echo '' ;;
        esac
    }
    export -f bashio::config.has_value
    export -f bashio::config

    source huawei_solar_modbus_mqtt/run.sh >/dev/null 2>&1

    [ "$HUAWEI_MQTT_HOST" = "mqtt.custom.local" ]
    [ "$HUAWEI_MQTT_USER" = "custom_user" ]
    [ "$HUAWEI_MQTT_PASSWORD" = "custom_pass" ]
}

@test "MQTT broker from HA service when no custom config" {
    source huawei_solar_modbus_mqtt/run.sh >/dev/null 2>&1

    [ "$HUAWEI_MQTT_HOST" = "core-mosquitto" ]
}

@test "Fatal error when no MQTT broker available" {
    bashio::config.has_value() {
        return 1
    }
    bashio::services.available() {
        return 1
    }
    export -f bashio::config.has_value
    export -f bashio::services.available

    run source huawei_solar_modbus_mqtt/run.sh

    [ "$status" -eq 1 ]
    [[ "$output" =~ "FATAL" ]]
}

@test "Environment variables are exported correctly" {
    source huawei_solar_modbus_mqtt/run.sh >/dev/null 2>&1

    [ "$HUAWEI_MODBUS_HOST" = "192.168.1.100" ]
    [ "$HUAWEI_MODBUS_PORT" = "502" ]
    [ "$HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID" = "true" ]
    [ "$HUAWEI_SLAVE_ID" = "1" ]
    [ "$HUAWEI_MQTT_TOPIC" = "huawei-solar" ]
    [ "$HUAWEI_STATUS_TIMEOUT" = "180" ]
    [ "$HUAWEI_POLL_INTERVAL" = "30" ]
    [ "$HUAWEI_LOG_LEVEL" = "INFO" ]
}

@test "Slave ID auto detect enabled" {
    source huawei_solar_modbus_mqtt/run.sh >/dev/null 2>&1

    [ "$HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID" = "true" ]
}

@test "Slave ID manual mode" {
    bashio::config() {
        case "$1" in
        modbus_auto_detect_slave_id) echo 'false' ;;
        slave_id) echo '5' ;;
        modbus_host) echo '192.168.1.100' ;;
        modbus_port) echo '502' ;;
        mqtt_topic) echo 'huawei-solar' ;;
        log_level) echo 'INFO' ;;
        status_timeout) echo '180' ;;
        poll_interval) echo '30' ;;
        *) echo '' ;;
        esac
    }
    export -f bashio::config

    source huawei_solar_modbus_mqtt/run.sh >/dev/null 2>&1

    [ "$HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID" = "false" ]
    [ "$HUAWEI_SLAVE_ID" = "5" ]
}
