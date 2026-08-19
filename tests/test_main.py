# tests/test_main.py

"""Tests for bridge.main."""

import asyncio
import importlib
import logging
import sys
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import bridge.main as main_module
import pytest
from bridge.config_manager import ConfigurationError
from bridge.main import (
    RECOVERABLE_EXCEPTIONS,
    _run,
    determine_slave_id,
    heartbeat,
    init_logging,
    is_modbus_exception,
    log_cycle_summary,
    main,
    main_once,
    read_registers,
    reset_state,
    run_main_cycle,
    setup_modbus,
)
from huawei_solar.exceptions import ReadException

# ---------------------------------------------------------------------------
# Module-level test data for log_cycle_summary tests
# ---------------------------------------------------------------------------

TIMINGS = {
    "modbus": 1.2,
    "transform": 0.003,
    "filter": 0.001,
    "mqtt": 0.05,
    "total": 1.3,
}

DATA = {
    "power_input": 4800,
    "power_active": 4500,
    "meter_power_active": -200,
    "battery_power": 300,
}


@pytest.fixture(autouse=True)
def reset_main_state():
    reset_state()
    yield
    reset_state()


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for the main() entry point."""

    @pytest.fixture(autouse=True)
    def patch_sigterm_handler(self):
        with patch("bridge.main._register_sigterm_handler"):
            yield

    def test_reset_state_recreates_runtime_singletons(self):
        """reset_state() isolates runtime state between tests."""
        old_state = main_module._state
        old_tracker = main_module._error_tracker
        main_module._state.last_success = 123.0
        main_module._error_tracker.track_error("timeout", "error")

        reset_state()

        assert main_module._state is not old_state
        assert main_module._error_tracker is not old_tracker
        assert main_module._state.last_success == 0.0
        assert main_module._state.config is None
        assert main_module._state.cycle_count == 0

    @pytest.mark.asyncio
    async def test_registers_sigterm_handler_for_current_task(self, mock_config, mock_client):
        """main() registers SIGTERM cancellation on the running event loop."""
        with (
            patch("bridge.main.ConfigManager", return_value=mock_config),
            patch("bridge.main.create_tcp_client", return_value=mock_client),
            patch("bridge.main.connect_mqtt", new_callable=AsyncMock),
            patch("bridge.main.disconnect_mqtt", new_callable=AsyncMock),
            patch("bridge.main.publish_status", new_callable=AsyncMock),
            patch("bridge.main.publish_discovery_configs", new_callable=AsyncMock),
            patch("bridge.main.main_once", side_effect=KeyboardInterrupt()),
            patch("bridge.main._register_sigterm_handler") as mock_register,
        ):
            await main()

        loop = asyncio.get_running_loop()
        current_task = asyncio.current_task()
        assert current_task is not None
        mock_register.assert_called_once_with(loop, current_task.cancel)

    @pytest.mark.asyncio
    async def test_run_wrapper_awaits_main(self):
        """The direct-entry wrapper delegates exactly to main()."""
        with patch("bridge.main.main", new_callable=AsyncMock) as mock_main:
            await _run()

        mock_main.assert_awaited_once()

    def test_bridge_package_entrypoint_uses_run_wrapper(self):
        """`python -m bridge` delegates to the same _run() wrapper."""
        module_name = "bridge.__main__"
        sys.modules.pop(module_name, None)

        with patch("asyncio.run") as mock_run:
            importlib.import_module(module_name)

        coro = mock_run.call_args.args[0]
        assert coro.cr_code.co_name == "_run"
        coro.close()

    @pytest.mark.asyncio
    async def test_connection_retry_on_failure(self, mock_config):
        """main() calls disconnect_mqtt exactly once on Modbus connection failure."""
        mock_config.modbus_auto_detect_slave_id = True  # override für diesen Test

        with (
            patch("bridge.main.ConfigManager", return_value=mock_config),
            patch("bridge.main.detect_slave_id", return_value=1),
            patch("bridge.main.create_tcp_client", side_effect=ConnectionRefusedError()),
            patch("bridge.main.connect_mqtt", new_callable=AsyncMock),
            patch("bridge.main.disconnect_mqtt", new_callable=AsyncMock) as mock_disconnect,
            patch("bridge.main.publish_status", new_callable=AsyncMock),
            patch("bridge.main.publish_discovery_configs", new_callable=AsyncMock),
        ):
            await main()

        mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, mock_config, mock_client):
        """main() shuts down gracefully on KeyboardInterrupt."""
        with (
            patch("bridge.main.ConfigManager", return_value=mock_config),
            patch("bridge.main.create_tcp_client", return_value=mock_client),
            patch("bridge.main.connect_mqtt", new_callable=AsyncMock),
            patch("bridge.main.disconnect_mqtt", new_callable=AsyncMock) as mock_disconnect,
            patch("bridge.main.publish_status", new_callable=AsyncMock) as mock_status,
            patch("bridge.main.publish_discovery_configs", new_callable=AsyncMock),
            patch("bridge.main.main_once", side_effect=KeyboardInterrupt()),
        ):
            try:
                await main()
            except KeyboardInterrupt:
                pass

            assert mock_disconnect.call_count >= 1
            assert any(call[0][0] == "offline" for call in mock_status.call_args_list)

    @pytest.mark.asyncio
    async def test_sigterm_triggers_graceful_shutdown(self, mock_config, mock_client):
        """SIGTERM cancels the main loop and disconnects cleanly."""

        with (
            patch("bridge.main.ConfigManager", return_value=mock_config),
            patch("bridge.main.create_tcp_client", return_value=mock_client),
            patch("bridge.main.connect_mqtt", new_callable=AsyncMock),
            patch("bridge.main.disconnect_mqtt", new_callable=AsyncMock) as mock_disconnect,
            patch("bridge.main.publish_status", new_callable=AsyncMock) as mock_status,
            patch("bridge.main.publish_discovery_configs", new_callable=AsyncMock),
            patch("bridge.main.main_once", side_effect=asyncio.CancelledError()),
        ):
            await main()

        assert mock_disconnect.call_count >= 1
        assert any(call[0][0] == "offline" for call in mock_status.call_args_list)

    @pytest.mark.asyncio
    async def test_timeout_triggers_filter_reset(self, mock_config, mock_client):
        """TimeoutError triggers filter reset and retry."""
        with (
            patch("bridge.main.ConfigManager", return_value=mock_config),
            patch("bridge.main.create_tcp_client", return_value=mock_client),
            patch("bridge.main.connect_mqtt", new_callable=AsyncMock),
            patch("bridge.main.publish_status", new_callable=AsyncMock) as mock_status,
            patch("bridge.main.publish_discovery_configs", new_callable=AsyncMock),
            patch("bridge.main.main_once", side_effect=[TimeoutError(), KeyboardInterrupt()]),
            patch("bridge.main.reset_filter") as mock_reset_filter,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            try:
                await main()
            except KeyboardInterrupt:
                pass

            assert mock_reset_filter.call_count >= 1
            assert any(call[0][0] == "offline" for call in mock_status.call_args_list)

    @pytest.mark.asyncio
    async def test_modbus_exception_triggers_filter_reset(self, mock_config, mock_client):
        """ReadException triggers filter reset and retry."""
        from huawei_solar.exceptions import ReadException

        with (
            patch("bridge.main.ConfigManager", return_value=mock_config),
            patch("bridge.main.create_tcp_client", return_value=mock_client),
            patch("bridge.main.connect_mqtt", new_callable=AsyncMock),
            patch("bridge.main.publish_status", new_callable=AsyncMock) as mock_status,
            patch("bridge.main.publish_discovery_configs", new_callable=AsyncMock),
            patch("bridge.main.main_once", side_effect=[ReadException("error"), KeyboardInterrupt()]),
            patch("bridge.main.reset_filter") as mock_reset_filter,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            try:
                await main()
            except KeyboardInterrupt:
                pass

            assert mock_reset_filter.call_count >= 1
            assert any(call[0][0] == "offline" for call in mock_status.call_args_list)

    @pytest.mark.asyncio
    async def test_loop_waits_poll_interval(self, mock_config, mock_client):
        """main() waits the remaining poll interval after a successful cycle."""
        with (
            patch("bridge.main.ConfigManager", return_value=mock_config),
            patch("bridge.main.create_tcp_client", return_value=mock_client),
            patch("bridge.main.connect_mqtt", new_callable=AsyncMock),
            patch("bridge.main.disconnect_mqtt", new_callable=AsyncMock),
            patch("bridge.main.publish_status", new_callable=AsyncMock),
            patch("bridge.main.publish_discovery_configs", new_callable=AsyncMock),
            patch("bridge.main._error_tracker"),
            patch("bridge.main.main_once", side_effect=[None, KeyboardInterrupt()]),
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            try:
                await main()
            except KeyboardInterrupt:
                pass

            sleep_args = [call[0][0] for call in mock_sleep.call_args_list]
            assert any(arg > 0 for arg in sleep_args)

    @pytest.mark.asyncio
    async def test_mqtt_connection_failure_exits(self, mock_config):
        """main() returns cleanly (no ConfigurationError) on MQTT connection failure."""
        with (
            patch("bridge.main.ConfigManager", return_value=mock_config),
            patch("bridge.main.detect_slave_id", return_value=1),
            patch("bridge.main.connect_mqtt", new_callable=AsyncMock, side_effect=ConnectionError("MQTT failed")),
            patch("bridge.main.disconnect_mqtt", new_callable=AsyncMock) as mock_disconnect,
            patch("bridge.main.publish_status", new_callable=AsyncMock),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await main()

        mock_disconnect.assert_not_called()


# ---------------------------------------------------------------------------
# TestDetermineSlaveId
# ---------------------------------------------------------------------------


class TestDetermineSlaveId:
    """Tests for determine_slave_id()."""

    @pytest.mark.asyncio
    async def test_manual_mode_returns_configured_id(self):
        config = Mock(modbus_auto_detect_slave_id=False, slave_id=42)
        assert await determine_slave_id(config) == 42

    @pytest.mark.asyncio
    async def test_manual_mode_none_exits(self):
        config = Mock(modbus_auto_detect_slave_id=False, slave_id=None)
        with pytest.raises(ConfigurationError):
            await determine_slave_id(config)

    @pytest.mark.asyncio
    async def test_auto_detect_success(self):
        config = Mock(modbus_auto_detect_slave_id=True, modbus_host="192.168.1.100", modbus_port=502)
        with patch("bridge.main.detect_slave_id", return_value=1) as mock_detect:
            result = await determine_slave_id(config)
        assert result == 1
        mock_detect.assert_called_once_with(host="192.168.1.100", port=502)

    @pytest.mark.asyncio
    async def test_auto_detect_failure_exits(self):
        config = Mock(modbus_auto_detect_slave_id=True, modbus_host="192.168.1.100", modbus_port=502)
        with (
            patch("bridge.main.detect_slave_id", return_value=None),
            pytest.raises(ConfigurationError),
        ):
            await determine_slave_id(config)


# ---------------------------------------------------------------------------
# TestHeartbeat
# ---------------------------------------------------------------------------


class TestHeartbeat:
    """Tests for heartbeat()."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        """Stellt _state nach jedem Test zurück auf Startup-Werte."""
        main_module._state.last_success = 0.0
        yield
        main_module._state.last_success = 0.0

    @pytest.mark.asyncio
    async def test_startup_no_check(self):
        """Does nothing during startup (_state.last_success == 0)."""
        main_module._state.last_success = 0.0
        config = Mock(mqtt_topic="test-topic", status_timeout=180)
        with patch("bridge.main.publish_status", new_callable=AsyncMock) as mock_status:
            await heartbeat(config)
            mock_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_online_within_timeout(self):
        """Does not publish offline when within timeout."""
        main_module._state.last_success = time.time() - 50
        config = Mock(mqtt_topic="test-topic", status_timeout=180)
        with patch("bridge.main.publish_status", new_callable=AsyncMock) as mock_status:
            await heartbeat(config)
            assert not any(call[0][0] == "offline" for call in mock_status.call_args_list)

    @pytest.mark.asyncio
    async def test_offline_when_timeout_exceeded(self):
        """Publishes offline when timeout is exceeded."""
        main_module._state.last_success = time.time() - 200
        config = Mock(mqtt_topic="test-topic", status_timeout=180)
        with patch("bridge.main.publish_status", new_callable=AsyncMock) as mock_status:
            await heartbeat(config)
            mock_status.assert_called_with("offline", "test-topic")


# ---------------------------------------------------------------------------
# TestIsModbusException
# ---------------------------------------------------------------------------


class TestIsModbusException:
    """Tests for is_modbus_exception()."""

    def test_returns_true_for_modbus_exception(self):
        from huawei_solar.exceptions import ReadException

        assert is_modbus_exception(ReadException("error"))

    def test_returns_false_for_value_error(self):
        assert not is_modbus_exception(ValueError("error"))

    def test_returns_false_for_timeout(self):
        assert not is_modbus_exception(TimeoutError())

    def test_returns_false_when_modbus_exceptions_empty(self):
        with patch("bridge.main.MODBUS_EXCEPTIONS", ()):
            assert not is_modbus_exception(ValueError("any"))
            assert not is_modbus_exception(Exception("test"))


# ---------------------------------------------------------------------------
# TestSetupModbus
# ---------------------------------------------------------------------------


class TestSetupModbus:
    """Tests for setup_modbus() — connection creation and timeout handling."""

    @pytest.mark.asyncio
    async def test_successful_connection(self, mock_config):
        """Returns a connected client on success."""
        mock_client = AsyncMock()
        with patch("bridge.main.create_tcp_client", return_value=mock_client):
            result = await setup_modbus(1, mock_config)

        assert result is mock_client

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self, mock_config, caplog):
        """TimeoutError from create() returns None and logs the timeout."""
        with (
            patch("bridge.main.create_tcp_client", side_effect=TimeoutError()),
            patch("bridge.main._state.publish_status", new_callable=AsyncMock),
        ):
            result = await setup_modbus(1, mock_config)

        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_logs_host_and_port(self, mock_config, caplog):
        """Timeout error message includes host, port, and timeout value."""
        with (
            patch("bridge.main.create_tcp_client", side_effect=TimeoutError()),
            patch("bridge.main._state.publish_status", new_callable=AsyncMock),
        ):
            await setup_modbus(1, mock_config)

        assert "timed out" in caplog.text
        assert mock_config.modbus_host in caplog.text

    @pytest.mark.asyncio
    async def test_connection_refused_returns_none(self, mock_config):
        """ConnectionRefusedError from create() returns None."""
        with patch("bridge.main.create_tcp_client", side_effect=ConnectionRefusedError()):
            result = await setup_modbus(1, mock_config)

        assert result is None


# ---------------------------------------------------------------------------
# TestRunMainCycleExceptionHandling
# ---------------------------------------------------------------------------


class TestRunMainCycleExceptionHandling:
    """Tests for run_main_cycle() error recovery and propagation."""

    @pytest.mark.asyncio
    async def test_cancelled_error_propagates(self, mock_client, mock_config):
        """asyncio.CancelledError propagates without filter reset."""
        with (
            patch("bridge.main.main_once", side_effect=asyncio.CancelledError()),
            patch("bridge.main._maybe_reset_on_error") as mock_maybe_reset,
            patch("bridge.main.reset_filter") as mock_reset_filter,
        ):
            with pytest.raises(asyncio.CancelledError):
                await run_main_cycle(mock_client, mock_config, 1)

        mock_maybe_reset.assert_not_called()
        mock_reset_filter.assert_not_called()

    @pytest.mark.asyncio
    async def test_unexpected_exception_propagates(self, mock_client, mock_config):
        """Non-recoverable exceptions propagate to caller (fail-fast)."""
        with patch("bridge.main.main_once", side_effect=ValueError("unexpected")):
            with pytest.raises(ValueError):
                await run_main_cycle(mock_client, mock_config, 1)

    @pytest.mark.asyncio
    async def test_timeout_triggers_filter_reset_in_cycle(self, mock_client, mock_config):
        """TimeoutError in main_once triggers filter reset via _maybe_reset_on_error."""
        with (
            patch("bridge.main._maybe_reset_on_error", return_value=True) as mock_maybe,
            patch("bridge.main.main_once", side_effect=TimeoutError()),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await run_main_cycle(mock_client, mock_config, 1)

        mock_maybe.assert_called_once()


# ---------------------------------------------------------------------------
# TestRecoverableExceptionsSanitized
# ---------------------------------------------------------------------------


class TestRecoverableExceptionsSanitized:
    """RECOVERABLE_EXCEPTIONS contains only real exception classes."""

    def test_all_entries_are_baseclasses(self):
        """Every class in RECOVERABLE_EXCEPTIONS is a BaseException subclass."""
        assert isinstance(RECOVERABLE_EXCEPTIONS, tuple)
        for exc in RECOVERABLE_EXCEPTIONS:
            assert isinstance(exc, type)
            assert issubclass(exc, BaseException)

    def test_includes_standard_recoverable(self):
        assert TimeoutError in RECOVERABLE_EXCEPTIONS
        assert ConnectionRefusedError in RECOVERABLE_EXCEPTIONS

    def test_includes_huawei_solar_exceptions(self):
        from bridge.main import MODBUS_EXCEPTIONS
        from huawei_solar.exceptions import ConnectionException, ConnectionInterruptedException, ReadException

        assert ConnectionInterruptedException in RECOVERABLE_EXCEPTIONS
        assert ConnectionException in RECOVERABLE_EXCEPTIONS
        assert ReadException in MODBUS_EXCEPTIONS

    def test_only_real_exceptions_included(self):
        """RECOVERABLE_EXCEPTIONS never includes non-BaseException classes."""
        import bridge.main as main_module

        for exc in main_module.RECOVERABLE_EXCEPTIONS:
            assert isinstance(exc, type)
            assert issubclass(exc, BaseException)


# ---------------------------------------------------------------------------
# TestMainOnce
# ---------------------------------------------------------------------------


class TestMainOnce:
    """Tests for main_once()."""

    @pytest.mark.asyncio
    async def test_successful_cycle_runs_full_pipeline(self, mock_client, mock_config):
        """Executes read -> transform -> filter -> publish in sequence."""
        with (
            patch("bridge.main.read_registers", return_value={"power_active": 4500}) as mock_read,
            patch("bridge.main.transform_data", return_value={"power_active": 4500}) as mock_transform,
            patch("bridge.main.publish_data", new_callable=AsyncMock) as mock_publish,
            patch("bridge.main.log_cycle_summary"),
            patch("bridge.main.get_filter") as mock_get_filter,
        ):
            mock_filter = Mock()
            mock_filter.filter.return_value = {"power_active": 4500}
            mock_get_filter.return_value = mock_filter

            await main_once(mock_client, mock_config, 1)

            assert mock_read.call_count == 1
            assert mock_transform.call_count == 1
            assert mock_filter.filter.call_count == 1
            assert mock_publish.call_count == 1

    @pytest.mark.asyncio
    async def test_empty_data_skips_publish(self, mock_client, mock_config):
        """Returns early without publishing when read returns empty data."""
        with (
            patch("bridge.main.read_registers", return_value={}),
            patch("bridge.main.publish_data", new_callable=AsyncMock) as mock_publish,
        ):
            await main_once(mock_client, mock_config, 1)
            assert mock_publish.call_count == 0

    @pytest.mark.asyncio
    async def test_updates_last_success_timestamp(self, mock_client, mock_config):
        """Updates _state.last_success timestamp on success."""
        main_module._state.last_success = 0.0
        before = time.time()
        await asyncio.sleep(0.01)

        with (
            patch("bridge.main.read_registers", return_value={"power_active": 4500}),
            patch("bridge.main.transform_data", return_value={"power_active": 4500}),
            patch("bridge.main.publish_data", new_callable=AsyncMock),
            patch("bridge.main.log_cycle_summary"),
            patch("bridge.main.get_filter") as mock_get_filter,
        ):
            mock_filter = Mock()
            mock_filter.filter.return_value = {"power_active": 4500}
            mock_get_filter.return_value = mock_filter

            await main_once(mock_client, mock_config, 1)

            assert main_module._state.last_success >= before
            assert main_module._state.last_success <= time.time()

    @pytest.mark.asyncio
    async def test_failed_cycle_does_not_update_last_success_timestamp(self, mock_client, mock_config):
        """Does not refresh heartbeat when a cycle fails before MQTT publish."""
        previous_success = time.time() - 300
        main_module._state.last_success = previous_success

        with patch("bridge.main.read_registers", side_effect=TimeoutError("timeout")):
            with pytest.raises(TimeoutError):
                await main_once(mock_client, mock_config, 1)

        assert main_module._state.last_success == previous_success


# ---------------------------------------------------------------------------
# TestInitLogging
# ---------------------------------------------------------------------------


class TestInitLogging:
    """Tests for init_logging()."""

    def test_debug_level(self):
        init_logging("DEBUG")
        assert logging.getLogger().level == logging.DEBUG

    def test_info_level(self):
        init_logging("INFO")
        assert logging.getLogger().level == logging.INFO

    def test_trace_level(self):
        init_logging("TRACE")
        assert logging.getLogger().level == 5


# ---------------------------------------------------------------------------
# TestReadRegisters
# ---------------------------------------------------------------------------


class TestReadRegisters:
    """Tests for read_registers()."""

    @pytest.mark.asyncio
    async def test_smart_batching_reads_all_registers(self, mock_client):
        """Smart batching returns all register values."""
        mock_client.get_multiple.return_value = [100, 200, 300]
        with (
            patch("bridge.main.ESSENTIAL_REGISTERS", ["reg1", "reg2", "reg3"]),
            patch("bridge.batch_builder._get_huawei_registers", return_value=None),
        ):
            result = await read_registers(mock_client, enable_batching=True)
        assert result == {"reg1": 100, "reg2": 200, "reg3": 300}
        assert mock_client.get_multiple.called

    @pytest.mark.asyncio
    async def test_batch_mode_returns_all_including_none(self, mock_client):
        """Batch mode returns None for unavailable registers."""
        mock_client.get_multiple.return_value = [100, 200, 300, None]
        with (
            patch("bridge.main.ESSENTIAL_REGISTERS", ["reg1", "reg2", "reg3", "reg4"]),
            patch("bridge.batch_builder._get_huawei_registers", return_value=None),
        ):
            result = await read_registers(mock_client)
        assert result == {"reg1": 100, "reg2": 200, "reg3": 300, "reg4": None}

    @pytest.mark.asyncio
    async def test_batch_failure_falls_back_to_sequential(self, mock_client):
        """Falls back to sequential reads when batch call fails."""
        mock_client.get_multiple.side_effect = ReadException("Did not recognize register names")
        mock_client.get = AsyncMock(side_effect=lambda name: {"reg1": 100, "reg2": 200, "reg3": 300}[name])
        with (
            patch("bridge.main.ESSENTIAL_REGISTERS", ["reg1", "reg2", "reg3"]),
            patch("bridge.batch_builder._get_huawei_registers", return_value=None),
        ):
            result = await read_registers(mock_client)
        assert result == {"reg1": 100, "reg2": 200, "reg3": 300}

    @pytest.mark.asyncio
    async def test_batch_quantity_value_error_falls_back_to_sequential(self, mock_client):
        """ValueError from get_multiple (oversized Modbus batch) falls back to sequential reads."""
        mock_client.get_multiple.side_effect = ValueError("Quantity must be between 1 and 125.")
        mock_client.get = AsyncMock(side_effect=lambda name: {"reg1": 100, "reg2": 200, "reg3": 300}[name])
        with (
            patch("bridge.main.ESSENTIAL_REGISTERS", ["reg1", "reg2", "reg3"]),
            patch("bridge.batch_builder._get_huawei_registers", return_value=None),
        ):
            result = await read_registers(mock_client)
        assert result == {"reg1": 100, "reg2": 200, "reg3": 300}
        assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_programming_error_in_build_batches_propagates(self, mock_client):
        """Test that non-READ_EXCEPTIONS propagate."""
        with (
            patch(
                "bridge.batch_builder.BatchBuilder.build_batches",
                side_effect=TypeError("Unexpected register structure"),
            ),
            patch("bridge.main.ESSENTIAL_REGISTERS", ["reg1", "reg2", "reg3"]),
        ):
            with pytest.raises(TypeError, match="Unexpected register structure"):
                await read_registers(mock_client)

    @pytest.mark.asyncio
    async def test_batching_disabled_uses_sequential(self, mock_client):
        """Disabling batching reads each register sequentially."""
        mock_client.get = AsyncMock(side_effect=lambda name: {"reg1": 100, "reg2": 200, "reg3": 300}[name])
        with patch("bridge.main.ESSENTIAL_REGISTERS", ["reg1", "reg2", "reg3"]):
            result = await read_registers(mock_client, enable_batching=False)
        mock_client.get_multiple.assert_not_called()
        assert mock_client.get.call_count == 3
        assert result == {"reg1": 100, "reg2": 200, "reg3": 300}

    @pytest.mark.asyncio
    async def test_smart_batching_with_custom_gap(self, mock_client):
        """Smart batching with custom gap reads all registers."""
        mock_client.get_multiple.return_value = [100, 200, 300, 400]
        with (
            patch("bridge.main.ESSENTIAL_REGISTERS", ["reg1", "reg2", "reg3", "reg4"]),
            patch("bridge.batch_builder._get_huawei_registers", return_value=None),
        ):
            result = await read_registers(mock_client, enable_batching=True, batch_max_gap=100)
        assert len(result) == 4
        assert mock_client.get_multiple.called


# ---------------------------------------------------------------------------
# TestLogCycleSummaryBasicInfoLog
# ---------------------------------------------------------------------------


class TestLogCycleSummaryBasicInfoLog:
    """Tests for the always-present info log line."""

    def test_contains_all_power_values(self, caplog):
        caplog.set_level(logging.INFO)
        log_cycle_summary(1, TIMINGS, DATA)
        assert "4800" in caplog.text
        assert "4500" in caplog.text
        assert "-200" in caplog.text
        assert "300" in caplog.text

    def test_contains_published_prefix(self, caplog):
        caplog.set_level(logging.INFO)
        log_cycle_summary(1, TIMINGS, DATA)
        assert "Published" in caplog.text

    def test_missing_data_keys_default_to_zero(self, caplog):
        caplog.set_level(logging.INFO)
        log_cycle_summary(1, TIMINGS, {})
        assert "Published" in caplog.text


# ---------------------------------------------------------------------------
# TestLogCycleSummaryFilterIndicator
# ---------------------------------------------------------------------------


class TestLogCycleSummaryFilterIndicator:
    """Tests for the filter indicator in the info log."""

    def test_no_indicator_when_no_stats(self, caplog):
        caplog.set_level(logging.INFO)
        log_cycle_summary(1, TIMINGS, DATA)
        assert "filtered" not in caplog.text

    def test_indicator_shown_when_values_filtered(self, caplog):
        caplog.set_level(logging.INFO)
        mock_filter = MagicMock()
        mock_filter.get_stats.return_value = {"energy_grid_exported": 2, "battery_charge_total": 1}
        with patch("bridge.main.get_filter", return_value=mock_filter):
            log_cycle_summary(1, TIMINGS, DATA)
        assert "3 filtered" in caplog.text

    def test_indicator_shows_correct_total(self, caplog):
        caplog.set_level(logging.INFO)
        mock_filter = MagicMock()
        mock_filter.get_stats.return_value = {
            "energy_grid_exported": 5,
            "energy_yield_accumulated": 3,
            "battery_charge_total": 2,
        }
        with patch("bridge.main.get_filter", return_value=mock_filter):
            log_cycle_summary(1, TIMINGS, DATA)
        assert "10 filtered" in caplog.text

    def test_no_indicator_when_all_counts_zero(self, caplog):
        caplog.set_level(logging.INFO)
        mock_filter = MagicMock()
        mock_filter.get_stats.return_value = {"energy_grid_exported": 0}
        with patch("bridge.main.get_filter", return_value=mock_filter):
            log_cycle_summary(1, TIMINGS, DATA)
        assert "filtered" not in caplog.text


# ---------------------------------------------------------------------------
# TestLogCycleSummaryCycle20
# ---------------------------------------------------------------------------


class TestLogCycleSummaryCycle20:
    """Tests for the every-20-cycles summary log."""

    def test_no_summary_on_non_20_cycle(self, caplog):
        caplog.set_level(logging.INFO)
        for cycle in [1, 19, 21, 39]:
            caplog.clear()
            log_cycle_summary(cycle, TIMINGS, DATA)
            assert "Filter summary" not in caplog.text

    def test_summary_on_cycle_20(self, caplog):
        caplog.set_level(logging.INFO)
        log_cycle_summary(20, TIMINGS, DATA)
        assert "Filter summary (last 20 cycles)" in caplog.text

    def test_summary_on_multiples_of_20(self, caplog):
        caplog.set_level(logging.INFO)
        for cycle in [40, 60, 80, 100]:
            caplog.clear()
            log_cycle_summary(cycle, TIMINGS, DATA)
            assert "Filter summary (last 20 cycles)" in caplog.text

    def test_summary_with_filtered_values(self, caplog):
        caplog.set_level(logging.INFO)
        mock_filter = MagicMock()
        mock_filter.get_stats.return_value = {"energy_grid_exported": 3, "battery_charge_total": 1}
        with patch("bridge.main.get_filter", return_value=mock_filter):
            log_cycle_summary(20, TIMINGS, DATA)
        assert "4 values filtered" in caplog.text
        assert "energy_grid_exported" in caplog.text
        assert "battery_charge_total" in caplog.text

    def test_summary_without_filtered_values(self, caplog):
        caplog.set_level(logging.INFO)
        mock_filter = MagicMock()
        mock_filter.get_stats.return_value = {}
        with patch("bridge.main.get_filter", return_value=mock_filter):
            log_cycle_summary(20, TIMINGS, DATA)
        assert "0 values filtered" in caplog.text
        assert "all data valid" in caplog.text

    def test_summary_calls_reset_stats(self, caplog):
        caplog.set_level(logging.INFO)
        mock_filter = MagicMock()
        mock_filter.get_stats.return_value = {}
        with patch("bridge.main.get_filter", return_value=mock_filter):
            log_cycle_summary(20, TIMINGS, DATA)
        mock_filter.reset_stats.assert_called_once()

    def test_non_20_cycle_does_not_call_reset_stats(self, caplog):
        caplog.set_level(logging.INFO)
        mock_filter = MagicMock()
        mock_filter.get_stats.return_value = {}
        with patch("bridge.main.get_filter", return_value=mock_filter):
            log_cycle_summary(1, TIMINGS, DATA)
        mock_filter.reset_stats.assert_not_called()


# ---------------------------------------------------------------------------
# TestLogCycleSummaryDebugBranch
# ---------------------------------------------------------------------------


class TestLogCycleSummaryDebugBranch:
    """Tests for the DEBUG-level filter detail log outside cycle 20."""

    def test_debug_details_logged_when_stats_active(self, caplog):
        caplog.set_level(logging.DEBUG)
        mock_filter = MagicMock()
        mock_filter.get_stats.return_value = {"energy_grid_exported": 1}
        with patch("bridge.main.get_filter", return_value=mock_filter):
            log_cycle_summary(1, TIMINGS, DATA)
        assert "Filter details" in caplog.text
        assert "energy_grid_exported" in caplog.text

    def test_no_debug_details_when_no_stats(self, caplog):
        caplog.set_level(logging.DEBUG)
        mock_filter = MagicMock()
        mock_filter.get_stats.return_value = {}
        with patch("bridge.main.get_filter", return_value=mock_filter):
            log_cycle_summary(1, TIMINGS, DATA)
        assert "Filter details" not in caplog.text

    def test_no_debug_details_on_cycle_20(self, caplog):
        caplog.set_level(logging.DEBUG)
        mock_filter = MagicMock()
        mock_filter.get_stats.return_value = {"energy_grid_exported": 1}
        with patch("bridge.main.get_filter", return_value=mock_filter):
            log_cycle_summary(20, TIMINGS, DATA)
        assert "Filter summary" in caplog.text
        assert "Filter details" not in caplog.text

    def test_no_debug_details_at_info_level(self, caplog):
        caplog.set_level(logging.INFO)
        mock_filter = MagicMock()
        mock_filter.get_stats.return_value = {"energy_grid_exported": 2}
        with patch("bridge.main.get_filter", return_value=mock_filter):
            log_cycle_summary(1, TIMINGS, DATA)
        assert "Filter details" not in caplog.text

    def test_get_error_tracker_returns_module_singleton(self):
        """get_error_tracker returns the private _error_tracker singleton."""
        assert main_module.get_error_tracker() is main_module._error_tracker

    def test_get_error_tracker_reflects_reset_state(self):
        """After reset_state the accessor yields the new instance."""
        old_tracker = main_module.get_error_tracker()
        reset_state()
        new_tracker = main_module.get_error_tracker()
        assert new_tracker is not old_tracker
        assert new_tracker is main_module._error_tracker
