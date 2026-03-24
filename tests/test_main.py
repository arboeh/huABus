# tests/test_main.py

"""Tests for Main."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import bridge.main as main_module
import pytest
from bridge.main import (
    determine_slave_id,
    heartbeat,
    init_logging,
    is_modbus_exception,
    main,
    main_once,
)
from bridge.total_increasing_filter import reset_filter


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances before each test."""
    reset_filter()
    yield
    reset_filter()


@pytest.fixture
def mock_config_file(tmp_path):
    """Create a temporary config file with test data."""
    import json

    config_file = tmp_path / "options.json"
    config_data = {
        "modbus": {
            "host": "192.168.0.246",
            "port": 502,
            "auto_detect_slave_id": False,
            "slave_id": 1,
        },
        "mqtt": {
            "broker": "192.168.0.140",
            "port": 1883,
            "username": None,
            "password": None,
            "topic_prefix": "test-topic",
            "discovery": True,
        },
        "advanced": {
            "log_level": "INFO",
            "status_timeout": 180,
            "poll_interval": 30,
        },
    }

    config_file.write_text(json.dumps(config_data))
    return config_file


@pytest.mark.asyncio
async def test_main_connection_retry_on_failure():
    """Test that main handles connection failures gracefully."""
    with (
        patch("bridge.main.ConfigManager") as mock_config_class,
        patch("bridge.main.detect_slave_id") as mock_detect,
        patch("bridge.main.AsyncHuaweiSolar.create") as mock_create,
        patch("bridge.main.connect_mqtt"),
        patch("bridge.main.disconnect_mqtt") as mock_disconnect,
        patch("bridge.main.publish_status"),
        patch("bridge.main.publish_discovery_configs"),
    ):
        # Mock config
        mock_config = Mock()
        mock_config.modbus_host = "192.168.0.246"
        mock_config.modbus_port = 502
        mock_config.modbus_auto_detect_slave_id = True  # Auto-detect
        mock_config.mqtt_broker = "192.168.0.140"
        mock_config.mqtt_port = 1883
        mock_config.mqtt_topic = "test-topic"
        mock_config.log_level = "INFO"
        mock_config.status_timeout = 180
        mock_config.poll_interval = 30
        mock_config.log_config = Mock()
        mock_config_class.return_value = mock_config

        # Auto-detect erfolgreich
        mock_detect.return_value = 1

        # Connection fails
        mock_create.side_effect = ConnectionRefusedError("Connection refused")

        await main()

        # Main sollte disconnect_mqtt aufrufen bei Connection-Fehler
        mock_disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_determine_slave_id_manual_mode():
    """Should use manual Slave ID when auto-detect disabled."""
    mock_config = Mock()
    mock_config.modbus_auto_detect_slave_id = False
    mock_config.slave_id = 42

    # Kein patch nötig - detect_slave_id wird nicht aufgerufen
    result = await determine_slave_id(mock_config)

    assert result == 42


@pytest.mark.asyncio
async def test_main_graceful_shutdown():
    """Test graceful shutdown on KeyboardInterrupt."""
    with (
        patch("bridge.main.ConfigManager") as mock_config_class,
        patch("bridge.main.AsyncHuaweiSolar.create") as mock_create,
        patch("bridge.main.connect_mqtt"),
        patch("bridge.main.disconnect_mqtt") as mock_disconnect,
        patch("bridge.main.publish_status") as mock_status,
        patch("bridge.main.publish_discovery_configs"),
        patch("bridge.main.main_once") as mock_once,
    ):
        # Mock ConfigManager
        mock_config = Mock()
        mock_config.modbus_host = "192.168.0.246"
        mock_config.modbus_port = 502
        mock_config.auto_detect_slave_id = False
        mock_config.slave_id = 1
        mock_config.mqtt_broker = "192.168.0.140"
        mock_config.mqtt_port = 1883
        mock_config.mqtt_topic = "test-topic"
        mock_config.log_level = "INFO"
        mock_config.status_timeout = 180
        mock_config.poll_interval = 30
        mock_config.log_config = Mock()
        mock_config_class.return_value = mock_config

        mock_client = AsyncMock()
        mock_create.return_value = mock_client

        # Simulate KeyboardInterrupt during main loop
        mock_once.side_effect = KeyboardInterrupt()

        # Main should exit gracefully via asyncio.CancelledError handler
        try:
            await main()
        except KeyboardInterrupt:
            pass

        # Verify disconnect was called
        assert mock_disconnect.call_count >= 1

        # Verify status was set to offline
        assert any(call[0][0] == "offline" for call in mock_status.call_args_list)


@pytest.mark.asyncio
async def test_main_timeout_exception_triggers_reconnect():
    """Test that timeout exception triggers filter reset and continues."""
    with (
        patch("bridge.main.ConfigManager") as mock_config_class,
        patch("bridge.main.AsyncHuaweiSolar.create") as mock_create,
        patch("bridge.main.connect_mqtt"),
        patch("bridge.main.publish_status") as mock_status,
        patch("bridge.main.publish_discovery_configs"),
        patch("bridge.main.main_once") as mock_once,
        patch("bridge.main.reset_filter") as mock_reset_filter,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        # Mock ConfigManager
        mock_config = Mock()
        mock_config.modbus_host = "192.168.0.246"
        mock_config.modbus_port = 502
        mock_config.auto_detect_slave_id = False
        mock_config.slave_id = 1
        mock_config.mqtt_broker = "192.168.0.140"
        mock_config.mqtt_port = 1883
        mock_config.mqtt_topic = "test-topic"
        mock_config.log_level = "INFO"
        mock_config.status_timeout = 180
        mock_config.poll_interval = 30
        mock_config.log_config = Mock()
        mock_config_class.return_value = mock_config

        mock_client = AsyncMock()
        mock_create.return_value = mock_client

        # First cycle times out, second cycle stops
        mock_once.side_effect = [
            TimeoutError("Connection timeout"),
            KeyboardInterrupt(),
        ]

        try:
            await main()
        except KeyboardInterrupt:
            pass

        # Verify filter was reset after timeout
        assert mock_reset_filter.call_count >= 1

        # Verify status was published as offline after timeout
        offline_calls = [call for call in mock_status.call_args_list if call[0][0] == "offline"]
        assert len(offline_calls) >= 1

        # Verify sleep was called (retry delay)
        assert mock_sleep.call_count >= 1


@pytest.mark.asyncio
async def test_main_modbus_exception_handling():
    """Test Modbus exception triggers filter reset and continues."""
    from pymodbus.exceptions import ModbusException

    with (
        patch("bridge.main.ConfigManager") as mock_config_class,
        patch("bridge.main.AsyncHuaweiSolar.create") as mock_create,
        patch("bridge.main.connect_mqtt"),
        patch("bridge.main.publish_status") as mock_status,
        patch("bridge.main.publish_discovery_configs"),
        patch("bridge.main.main_once") as mock_once,
        patch("bridge.main.reset_filter") as mock_reset_filter,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        # Mock ConfigManager
        mock_config = Mock()
        mock_config.modbus_host = "192.168.0.246"
        mock_config.modbus_port = 502
        mock_config.auto_detect_slave_id = False
        mock_config.slave_id = 1
        mock_config.mqtt_broker = "192.168.0.140"
        mock_config.mqtt_port = 1883
        mock_config.mqtt_topic = "test-topic"
        mock_config.log_level = "INFO"
        mock_config.status_timeout = 180
        mock_config.poll_interval = 30
        mock_config.log_config = Mock()
        mock_config_class.return_value = mock_config

        mock_client = AsyncMock()
        mock_create.return_value = mock_client

        # ModbusException then stop
        mock_once.side_effect = [
            ModbusException("Modbus read error"),
            KeyboardInterrupt(),
        ]

        try:
            await main()
        except KeyboardInterrupt:
            pass

        # Verify filter was reset
        assert mock_reset_filter.call_count >= 1

        # Verify offline status
        offline_calls = [call for call in mock_status.call_args_list if call[0][0] == "offline"]
        assert len(offline_calls) >= 1


@pytest.mark.asyncio
async def test_main_mqtt_connection_failure():
    """Test main() handles MQTT connection failure."""
    with (
        patch("bridge.main.ConfigManager") as mock_config_class,
        patch("bridge.main.connect_mqtt") as mock_mqtt,
        pytest.raises(SystemExit),
    ):
        # Vollständig gemockter ConfigManager
        mock_config = Mock()
        mock_config.log_level = "INFO"
        mock_config.modbus_host = "192.168.0.246"
        mock_config.modbus_port = 502
        mock_config.auto_detect_slave_id = False
        mock_config.slave_id = 1
        mock_config.mqtt_broker = "192.168.0.140"
        mock_config.mqtt_port = 1883
        mock_config.mqtt_username = None
        mock_config.mqtt_password = None
        mock_config.mqtt_topic = "test-topic"
        mock_config.status_timeout = 180
        mock_config.poll_interval = 30
        mock_config.log_config = Mock()  # ← Wichtig!
        mock_config_class.return_value = mock_config

        mock_mqtt.side_effect = Exception("MQTT connection failed")
        await main()


def test_heartbeat_startup_no_check():
    """Test heartbeat does nothing during startup (LAST_SUCCESS == 0)."""
    # Reset LAST_SUCCESS to startup state
    main_module.LAST_SUCCESS = 0

    mock_config = Mock()
    mock_config.mqtt_topic = "test-topic"
    mock_config.status_timeout = 180

    with patch("bridge.main.publish_status") as mock_status:
        heartbeat(mock_config)
        # Should not publish status during startup
        mock_status.assert_not_called()


def test_heartbeat_online_within_timeout():
    """Test heartbeat remains online when within timeout."""
    # Set LAST_SUCCESS to 50 seconds ago (within 180s timeout)
    main_module.LAST_SUCCESS = time.time() - 50

    mock_config = Mock()
    mock_config.mqtt_topic = "test-topic"
    mock_config.status_timeout = 180

    with patch("bridge.main.publish_status") as mock_status:
        heartbeat(mock_config)
        # Should not publish offline status
        offline_calls = [call for call in mock_status.call_args_list if call[0][0] == "offline"]
        assert len(offline_calls) == 0


def test_heartbeat_offline_timeout_exceeded():
    """Test heartbeat publishes offline when timeout exceeded."""
    # Set LAST_SUCCESS to 200 seconds ago (exceeds 180s timeout)
    main_module.LAST_SUCCESS = time.time() - 200

    mock_config = Mock()
    mock_config.mqtt_topic = "test-topic"
    mock_config.status_timeout = 180

    with patch("bridge.main.publish_status") as mock_status:
        heartbeat(mock_config)
        # Should publish offline status
        mock_status.assert_called_with("offline", "test-topic")


def test_is_modbus_exception_true():
    """Test is_modbus_exception returns True for ModbusException."""
    from pymodbus.exceptions import ModbusException

    assert is_modbus_exception(ModbusException("test error"))


def test_is_modbus_exception_false_for_generic_exception():
    """Test is_modbus_exception returns False for generic exceptions."""
    assert not is_modbus_exception(ValueError("test error"))


def test_is_modbus_exception_false_for_timeout():
    """Test is_modbus_exception returns False for timeout errors."""

    assert not is_modbus_exception(TimeoutError())


@pytest.mark.asyncio
async def test_main_once_successful_cycle():
    """Test main_once executes complete cycle successfully."""
    mock_client = AsyncMock()
    mock_config = Mock()
    mock_config.mqtt_topic = "test-topic"
    mock_config.poll_interval = 30

    with (
        patch("bridge.main.read_registers") as mock_read,
        patch("bridge.main.transform_data") as mock_transform,
        patch("bridge.main.publish_data") as mock_publish,
        patch("bridge.main.get_filter") as mock_filter,
        patch("bridge.main.log_cycle_summary"),
    ):
        # Setup mocks
        mock_read.return_value = {"power_active": 4500}
        mock_transform.return_value = {"power_active": 4500}
        mock_filter_instance = Mock()
        mock_filter_instance.filter.return_value = {"power_active": 4500}
        mock_filter.return_value = mock_filter_instance

        await main_once(mock_client, mock_config, 1)

        # Verify complete pipeline executed
        assert mock_read.call_count == 1
        assert mock_transform.call_count == 1
        assert mock_filter_instance.filter.call_count == 1
        assert mock_publish.call_count == 1


@pytest.mark.asyncio
async def test_main_once_empty_data_handling():
    """Test main_once handles empty data gracefully."""
    mock_client = AsyncMock()
    mock_config = Mock()
    mock_config.mqtt_topic = "test-topic"
    mock_config.poll_interval = 30

    with (
        patch("bridge.main.read_registers") as mock_read,
        patch("bridge.main.publish_data") as mock_publish,
    ):
        # Return empty data
        mock_read.return_value = {}

        await main_once(mock_client, mock_config, 1)

        # Should return early without publishing
        assert mock_publish.call_count == 0


@pytest.mark.asyncio
async def test_main_once_updates_last_success():
    """Test main_once updates LAST_SUCCESS timestamp on success."""
    mock_client = AsyncMock()
    mock_config = Mock()
    mock_config.mqtt_topic = "test-topic"
    mock_config.poll_interval = 30

    # Reset LAST_SUCCESS
    main_module.LAST_SUCCESS = 0
    before = time.time()

    # Small pause to ensure before < after
    await asyncio.sleep(0.01)

    with (
        patch("bridge.main.read_registers") as mock_read,
        patch("bridge.main.transform_data") as mock_transform,
        patch("bridge.main.publish_data"),
        patch("bridge.main.log_cycle_summary"),
        patch("bridge.main.get_filter") as mock_filter,
    ):
        mock_read.return_value = {"power_active": 4500}
        mock_transform.return_value = {"power_active": 4500}
        mock_filter_instance = Mock()
        mock_filter_instance.filter.return_value = {"power_active": 4500}
        mock_filter.return_value = mock_filter_instance

        await main_once(mock_client, mock_config, 1)

        # Verify LAST_SUCCESS was updated
        assert main_module.LAST_SUCCESS >= before
        assert main_module.LAST_SUCCESS <= time.time()


def test_init_logging_debug_level():
    """Test init_logging sets DEBUG level correctly."""
    import logging

    init_logging("DEBUG")
    assert logging.getLogger().level == logging.DEBUG


def test_init_logging_default_level():
    """Test init_logging defaults to INFO level."""
    import logging

    init_logging("INFO")
    assert logging.getLogger().level == logging.INFO


def test_init_logging_trace_level():
    """Test init_logging sets TRACE level (custom level)."""
    import logging

    init_logging("TRACE")
    # TRACE = 5
    assert logging.getLogger().level == 5


@pytest.mark.asyncio
async def test_determine_slave_id_auto_detect_success():
    """Should auto-detect Slave ID successfully."""
    mock_config = Mock()
    mock_config.auto_detect_slave_id = True
    mock_config.modbus_host = "192.168.1.100"
    mock_config.modbus_port = 502

    with patch("bridge.main.detect_slave_id") as mock_detect:
        mock_detect.return_value = 1

        result = await determine_slave_id(mock_config)

        assert result == 1
        mock_detect.assert_called_once_with(host="192.168.1.100", port=502)


@pytest.mark.asyncio
async def test_determine_slave_id_auto_detect_fails_exits():
    """Should exit when auto-detection fails."""
    mock_config = Mock()
    mock_config.auto_detect_slave_id = True
    mock_config.modbus_host = "192.168.1.100"
    mock_config.modbus_port = 502

    with (
        patch("bridge.main.detect_slave_id") as mock_detect,
        pytest.raises(SystemExit),
    ):
        mock_detect.return_value = None
        await determine_slave_id(mock_config)


@pytest.mark.asyncio
async def test_determine_slave_id_manual_mode_none_exits():
    """Should exit when manual mode but slave_id is None."""
    mock_config = Mock()
    mock_config.auto_detect_slave_id = False
    mock_config.slave_id = None

    with pytest.raises(SystemExit):
        await determine_slave_id(mock_config)
