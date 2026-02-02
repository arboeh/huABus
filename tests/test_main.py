# tests\test_main.py

import os
import time
from unittest.mock import AsyncMock, Mock, patch

import modbus_energy_meter.main as main_module
import pytest  # type: ignore
from modbus_energy_meter.main import (
    heartbeat,
    init_logging,
    is_modbus_exception,
    main,
    main_once,
)
from modbus_energy_meter.total_increasing_filter import reset_filter


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances before each test."""
    reset_filter()
    yield
    reset_filter()


@pytest.fixture
def mock_env():
    """Mock required environment variables."""
    env_vars = {
        "HUAWEI_MODBUS_MQTT_TOPIC": "test-topic",
        "HUAWEI_MODBUS_HOST": "192.168.1.100",
        "HUAWEI_MODBUS_PORT": "502",
        "HUAWEI_SLAVE_ID": "1",
        "HUAWEI_POLL_INTERVAL": "30",
        "HUAWEI_STATUS_TIMEOUT": "180",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.mark.asyncio
async def test_main_connection_retry_on_failure(mock_env):
    """Test that main() handles connection failures gracefully."""
    with (
        patch("modbus_energy_meter.main.AsyncHuaweiSolar.create") as mock_create,
        patch("modbus_energy_meter.main.connect_mqtt"),
        patch("modbus_energy_meter.main.disconnect_mqtt"),
        patch("modbus_energy_meter.main.publish_status"),
        patch("modbus_energy_meter.main.publish_discovery_configs"),
        patch("modbus_energy_meter.main.main_once"),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        # Connection fails
        mock_create.side_effect = ConnectionRefusedError("Connection refused")

        # Main should log error and return (not crash)
        await main()

        # Verify connection was attempted
        assert mock_create.call_count == 1


@pytest.mark.asyncio
async def test_main_graceful_shutdown(mock_env):
    """Test graceful shutdown on KeyboardInterrupt."""
    with (
        patch("modbus_energy_meter.main.AsyncHuaweiSolar.create") as mock_create,
        patch("modbus_energy_meter.main.connect_mqtt"),
        patch("modbus_energy_meter.main.disconnect_mqtt") as mock_disconnect,
        patch("modbus_energy_meter.main.publish_status") as mock_status,
        patch("modbus_energy_meter.main.publish_discovery_configs"),
        patch("modbus_energy_meter.main.main_once") as mock_once,
    ):
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
async def test_main_timeout_exception_triggers_reconnect(mock_env):
    """Test that timeout exception triggers filter reset and continues."""
    with (
        patch("modbus_energy_meter.main.AsyncHuaweiSolar.create") as mock_create,
        patch("modbus_energy_meter.main.connect_mqtt"),
        patch("modbus_energy_meter.main.publish_status") as mock_status,
        patch("modbus_energy_meter.main.publish_discovery_configs"),
        patch("modbus_energy_meter.main.main_once") as mock_once,
        patch("modbus_energy_meter.main.reset_filter") as mock_reset_filter,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
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
        offline_calls = [
            call for call in mock_status.call_args_list if call[0][0] == "offline"
        ]
        assert len(offline_calls) >= 1

        # Verify sleep was called (retry delay)
        assert mock_sleep.call_count >= 1


@pytest.mark.asyncio
async def test_main_modbus_exception_handling(mock_env):
    """Test Modbus exception triggers filter reset and continues."""
    from pymodbus.exceptions import ModbusException

    with (
        patch("modbus_energy_meter.main.AsyncHuaweiSolar.create") as mock_create,
        patch("modbus_energy_meter.main.connect_mqtt"),
        patch("modbus_energy_meter.main.publish_status") as mock_status,
        patch("modbus_energy_meter.main.publish_discovery_configs"),
        patch("modbus_energy_meter.main.main_once") as mock_once,
        patch("modbus_energy_meter.main.reset_filter") as mock_reset_filter,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
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
        offline_calls = [
            call for call in mock_status.call_args_list if call[0][0] == "offline"
        ]
        assert len(offline_calls) >= 1


@pytest.mark.asyncio
async def test_main_missing_mqtt_topic():
    """Test main() exits when MQTT topic is not configured."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(SystemExit):
            await main()


@pytest.mark.asyncio
async def test_main_missing_modbus_host():
    """Test main() exits when Modbus host is not configured."""
    env = {"HUAWEI_MODBUS_MQTT_TOPIC": "test"}
    with patch.dict("os.environ", env, clear=True):
        with (
            patch("modbus_energy_meter.main.connect_mqtt"),
            pytest.raises(SystemExit),
        ):
            await main()


@pytest.mark.asyncio
async def test_main_mqtt_connection_failure(mock_env):
    """Test main() handles MQTT connection failure."""
    with (
        patch("modbus_energy_meter.main.connect_mqtt") as mock_mqtt,
        pytest.raises(SystemExit),
    ):
        mock_mqtt.side_effect = Exception("MQTT connection failed")
        await main()


def test_heartbeat_startup_no_check():
    """Test heartbeat does nothing during startup (LAST_SUCCESS == 0)."""
    # Reset LAST_SUCCESS to startup state
    main_module.LAST_SUCCESS = 0

    with patch("modbus_energy_meter.main.publish_status") as mock_status:
        heartbeat("test-topic")
        # Should not publish status during startup
        mock_status.assert_not_called()


def test_heartbeat_online_within_timeout():
    """Test heartbeat remains online when within timeout."""
    # Set LAST_SUCCESS to 50 seconds ago (within 180s timeout)
    main_module.LAST_SUCCESS = time.time() - 50

    with (
        patch("modbus_energy_meter.main.publish_status") as mock_status,
        patch.dict("os.environ", {"HUAWEI_STATUS_TIMEOUT": "180"}),
    ):
        heartbeat("test-topic")
        # Should not publish offline status
        offline_calls = [
            call for call in mock_status.call_args_list if call[0][0] == "offline"
        ]
        assert len(offline_calls) == 0


def test_heartbeat_offline_timeout_exceeded():
    """Test heartbeat publishes offline when timeout exceeded."""
    # Set LAST_SUCCESS to 200 seconds ago (exceeds 180s timeout)
    main_module.LAST_SUCCESS = time.time() - 200

    with (
        patch("modbus_energy_meter.main.publish_status") as mock_status,
        patch.dict("os.environ", {"HUAWEI_STATUS_TIMEOUT": "180"}),
    ):
        heartbeat("test-topic")
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
    import asyncio

    assert not is_modbus_exception(asyncio.TimeoutError())


@pytest.mark.asyncio
async def test_main_once_successful_cycle():
    """Test main_once executes complete cycle successfully."""
    mock_client = AsyncMock()

    with (
        patch("modbus_energy_meter.main.read_registers") as mock_read,
        patch("modbus_energy_meter.main.transform_data") as mock_transform,
        patch("modbus_energy_meter.main.publish_data") as mock_publish,
        patch("modbus_energy_meter.main.get_filter") as mock_filter,
        patch("modbus_energy_meter.main.log_cycle_summary"),
        patch.dict("os.environ", {"HUAWEI_MODBUS_MQTT_TOPIC": "test"}),
    ):
        # Setup mocks
        mock_read.return_value = {"power_active": 4500}
        mock_transform.return_value = {"power_active": 4500}
        mock_filter_instance = Mock()
        mock_filter_instance.filter.return_value = {"power_active": 4500}
        mock_filter.return_value = mock_filter_instance

        await main_once(mock_client, 1)

        # Verify complete pipeline executed
        assert mock_read.call_count == 1
        assert mock_transform.call_count == 1
        assert mock_filter_instance.filter.call_count == 1
        assert mock_publish.call_count == 1


@pytest.mark.asyncio
async def test_main_once_empty_data_handling():
    """Test main_once handles empty data gracefully."""
    mock_client = AsyncMock()

    with (
        patch("modbus_energy_meter.main.read_registers") as mock_read,
        patch("modbus_energy_meter.main.publish_data") as mock_publish,
        patch.dict("os.environ", {"HUAWEI_MODBUS_MQTT_TOPIC": "test"}),
    ):
        # Return empty data
        mock_read.return_value = {}

        await main_once(mock_client, 1)

        # Should return early without publishing
        assert mock_publish.call_count == 0


@pytest.mark.asyncio
async def test_main_once_updates_last_success():
    """Test main_once updates LAST_SUCCESS timestamp on success."""
    mock_client = AsyncMock()

    # Reset LAST_SUCCESS
    main_module.LAST_SUCCESS = 0
    before = time.time()

    with (
        patch("modbus_energy_meter.main.read_registers") as mock_read,
        patch("modbus_energy_meter.main.transform_data") as mock_transform,
        patch("modbus_energy_meter.main.publish_data"),
        patch("modbus_energy_meter.main.log_cycle_summary"),
        patch("modbus_energy_meter.main.get_filter") as mock_filter,
        patch.dict("os.environ", {"HUAWEI_MODBUS_MQTT_TOPIC": "test"}),
    ):
        mock_read.return_value = {"power_active": 4500}
        mock_transform.return_value = {"power_active": 4500}
        mock_filter_instance = Mock()
        mock_filter_instance.filter.return_value = {"power_active": 4500}
        mock_filter.return_value = mock_filter_instance

        await main_once(mock_client, 1)

        # Verify LAST_SUCCESS was updated
        assert main_module.LAST_SUCCESS > before


def test_init_logging_debug_level():
    """Test init_logging sets DEBUG level correctly."""
    import logging

    with patch.dict("os.environ", {"HUAWEI_LOG_LEVEL": "DEBUG"}):
        init_logging()
        assert logging.getLogger().level == logging.DEBUG


def test_init_logging_default_level():
    """Test init_logging defaults to INFO level."""
    import logging

    with patch.dict("os.environ", {}, clear=True):
        init_logging()
        assert logging.getLogger().level == logging.INFO


def test_init_logging_trace_level():
    """Test init_logging sets TRACE level (custom level)."""
    import logging

    with patch.dict("os.environ", {"HUAWEI_LOG_LEVEL": "TRACE"}):
        init_logging()
        # TRACE = 5
        assert logging.getLogger().level == 5


def test_init_logging_legacy_debug_env():
    """Test init_logging respects legacy HUAWEI_MODBUS_DEBUG variable."""
    import logging

    with patch.dict("os.environ", {"HUAWEI_MODBUS_DEBUG": "yes"}):
        init_logging()
        assert logging.getLogger().level == logging.DEBUG
