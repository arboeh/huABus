# tests/test_retry.py

"""Tests für den Backoff-Helfer."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from bridge.retry import retry_with_backoff


def _operation(results):
    """Async operation returning the given results one by one."""
    iterator = iter(results)

    async def operation():
        return next(iterator)

    return operation


class TestRetryWithBackoff:
    """retry_with_backoff(): Wartefolge, Abbruch, Rückgabewerte."""

    @pytest.mark.asyncio
    async def test_returns_immediately_without_sleep(self):
        sleep = AsyncMock()

        result = await retry_with_backoff(_operation(["ok"]), "target", sleep=sleep)

        assert result == "ok"
        sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_backoff_doubles_until_maximum(self):
        sleep = AsyncMock()
        operation = _operation([None] * 6 + ["ok"])

        result = await retry_with_backoff(operation, "target", sleep=sleep)

        assert result == "ok"
        assert [call.args[0] for call in sleep.call_args_list] == [5, 10, 20, 40, 60, 60]

    @pytest.mark.asyncio
    async def test_custom_delays(self):
        sleep = AsyncMock()

        await retry_with_backoff(
            _operation([None, None, None, "ok"]),
            "target",
            initial_delay=1.0,
            max_delay=3.0,
            sleep=sleep,
        )

        assert [call.args[0] for call in sleep.call_args_list] == [1, 2, 3]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("value", [0, False, ""])
    async def test_falsy_result_counts_as_success(self, value):
        """Only None means 'retry' (slave ID 0 is valid)."""
        sleep = AsyncMock()

        result = await retry_with_backoff(_operation([value]), "target", sleep=sleep)

        assert result == value
        sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolves_asyncio_sleep_at_call_time(self):
        """A global asyncio.sleep patch applies (no real waiting in tests)."""
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await retry_with_backoff(_operation([None, "ok"]), "target")

        mock_sleep.assert_awaited_once_with(5.0)

    @pytest.mark.asyncio
    async def test_cancel_during_sleep_propagates(self):
        sleep = AsyncMock(side_effect=asyncio.CancelledError())

        with pytest.raises(asyncio.CancelledError):
            await retry_with_backoff(_operation([None, "ok"]), "target", sleep=sleep)

    @pytest.mark.asyncio
    async def test_cancel_inside_operation_propagates(self):
        async def operation():
            raise asyncio.CancelledError

        sleep = AsyncMock()

        with pytest.raises(asyncio.CancelledError):
            await retry_with_backoff(operation, "target", sleep=sleep)

        sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_operation_exception_is_not_retried(self):
        async def operation():
            raise ValueError("configuration")

        sleep = AsyncMock()

        with pytest.raises(ValueError, match="configuration"):
            await retry_with_backoff(operation, "target", sleep=sleep)

        sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_attempt_and_target(self, caplog):
        caplog.set_level("INFO", logger="huawei.retry")

        await retry_with_backoff(_operation([None, None, "ok"]), "MQTT broker x:1883", sleep=AsyncMock())

        assert "MQTT broker x:1883 not available (attempt 2)" in caplog.text
        assert "available after 3 attempts" in caplog.text
