# tests/test_batch_builder.py

"""Tests for BatchBuilder and smart batching functionality."""

import sys
from unittest.mock import patch

from huawei_solar_modbus_mqtt.bridge.batch_builder import (
    BatchBuilder,
    _get_huawei_registers,
    build_batches_from_registers,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_regs(batches, unknown):
    return [r for batch in batches for r in batch] + unknown


def _mock_register(address: int, length: int = 1):
    return type("MockRegister", (), {"register": address, "length": length})()


def _batch_span(batch, register_map):
    first = register_map[batch[0]]
    last = register_map[batch[-1]]
    return (last.register + last.length) - first.register


# ---------------------------------------------------------------------------
# TestBatchBuilder
# ---------------------------------------------------------------------------


class TestBatchBuilder:
    """Tests for BatchBuilder initialization and build_batches()."""

    def test_init_with_defaults(self):
        builder = BatchBuilder()
        assert builder.batch_max_gap == 50
        assert builder.enable_batching is True

    def test_init_with_custom_values(self):
        builder = BatchBuilder(batch_max_gap=25, enable_batching=False)
        assert builder.batch_max_gap == 25
        assert builder.enable_batching is False

    def test_build_batches_disabled_preserves_all_registers(self):
        registers = ["reg1", "reg2", "reg3", "reg4", "reg5"]
        batches, unknown = BatchBuilder(enable_batching=False).build_batches(registers)
        result = _all_regs(batches, unknown)
        assert set(result) == set(registers)
        assert len(result) == len(registers)

    def test_build_batches_empty_list(self):
        batches, unknown = BatchBuilder(enable_batching=True).build_batches([])
        assert batches == [[]]
        assert unknown == []

    def test_build_batches_single_register(self):
        batches, unknown = BatchBuilder(enable_batching=True).build_batches(["reg1"])
        assert set(_all_regs(batches, unknown)) == {"reg1"}

    def test_build_batches_small_register_count(self):
        registers = ["reg1", "reg2", "reg3", "reg4"]
        batches, unknown = BatchBuilder(enable_batching=True).build_batches(registers)
        assert set(_all_regs(batches, unknown)) == set(registers)

    def test_build_batches_large_register_count_preserves_all(self):
        registers = [f"reg{i}" for i in range(67)]
        batches, unknown = BatchBuilder(enable_batching=True).build_batches(registers)
        result = _all_regs(batches, unknown)
        assert set(result) == set(registers)
        assert len(result) == len(registers)

    def test_validate_batch_gap_valid_values(self):
        builder = BatchBuilder()
        for value in [1, 50, 100, 1000]:
            assert builder.validate_batch_gap(value) is True

    def test_validate_batch_gap_invalid_values(self):
        builder = BatchBuilder()
        for value in [0, -1]:
            assert builder.validate_batch_gap(value) is False

    def test_validate_batch_gap_too_large(self):
        assert BatchBuilder().validate_batch_gap(10001) is False


# ---------------------------------------------------------------------------
# TestBatchBuilderConvenienceFunction
# ---------------------------------------------------------------------------


class TestBatchBuilderConvenienceFunction:
    """Tests for build_batches_from_registers()."""

    def test_with_batching_enabled(self):
        registers = [f"reg{i}" for i in range(30)]
        batches, unknown = build_batches_from_registers(registers, batch_max_gap=100, enable_batching=True)
        result = _all_regs(batches, unknown)
        assert set(result) == set(registers)
        assert len(result) == len(registers)

    def test_with_batching_disabled(self):
        registers = [f"reg{i}" for i in range(30)]
        batches, unknown = build_batches_from_registers(registers, batch_max_gap=100, enable_batching=False)
        result = _all_regs(batches, unknown)
        assert set(result) == set(registers)
        assert len(result) == len(registers)

    def test_default_batch_max_gap_matches_batch_builder(self):
        registers = {
            "reg_a": _mock_register(10),
            "reg_b": _mock_register(62),
        }

        with patch("huawei_solar_modbus_mqtt.bridge.batch_builder._get_huawei_registers", return_value=registers):
            batches, unknown = build_batches_from_registers(["reg_a", "reg_b"])

        assert unknown == []
        assert batches == [["reg_a"], ["reg_b"]]


# ---------------------------------------------------------------------------
# TestBatchBuilderIntegration
# ---------------------------------------------------------------------------


class TestBatchBuilderIntegration:
    """Integration tests with realistic register sets."""

    def test_essential_registers_produces_at_least_one_batch(self):
        from huawei_solar_modbus_mqtt.bridge.config.registers import ESSENTIAL_REGISTERS

        batches, unknown = BatchBuilder(enable_batching=True).build_batches(ESSENTIAL_REGISTERS)
        assert len(batches) >= 1
        result = _all_regs(batches, unknown)
        assert len(result) == len(ESSENTIAL_REGISTERS)
        assert set(result) == set(ESSENTIAL_REGISTERS)

    def test_completeness_with_small_register_set(self):
        registers = ["reg1", "reg2", "reg3", "reg4", "reg5"]
        batches, unknown = BatchBuilder(enable_batching=True).build_batches(registers)
        result = _all_regs(batches, unknown)
        assert set(result) == set(registers)
        assert len(result) == len(registers)

    def test_different_gap_values_preserve_all_registers(self):
        registers = [f"reg{i}" for i in range(67)]
        for gap in [10, 10000]:
            batches, unknown = BatchBuilder(batch_max_gap=gap, enable_batching=True).build_batches(registers)
            assert set(_all_regs(batches, unknown)) == set(registers)

    def test_essential_register_batches_within_modbus_quantity_limit(self):
        """Every essential-register batch span must be <= MAX_MODBUS_QUANTITY (125).

        The Modbus protocol limits a single read-multiple-registers request
        to 125 registers. This is measured by the address span
        (last_end - first_start), not by the count of register entries.
        """
        from huawei_solar.registers import REGISTERS

        from huawei_solar_modbus_mqtt.bridge.batch_builder import MAX_MODBUS_QUANTITY
        from huawei_solar_modbus_mqtt.bridge.config.registers import ESSENTIAL_REGISTERS

        builder = BatchBuilder()
        batches, _ = builder.build_batches(ESSENTIAL_REGISTERS)
        for batch in batches:
            span = _batch_span(batch, REGISTERS)
            assert span <= MAX_MODBUS_QUANTITY, f"Batch span {span} exceeds Modbus limit {MAX_MODBUS_QUANTITY}: {batch}"

    def test_batch_splits_when_modbus_quantity_limit_would_be_exceeded(self):
        """Registers whose span exceeds 125 within one gap-group are split.

        The Modbus limit is on the address span / quantity requested, not on
        the raw count of register entries in a batch.
        """
        from huawei_solar_modbus_mqtt.bridge.batch_builder import MAX_MODBUS_QUANTITY

        # Six registers, each 1 register long, spaced 30 apart.
        # Gaps (29-30) are well within batch_max_gap=50, so without span-based
        # splitting they would all land in one batch with span 136 (> 125).
        mock_registers = {
            "r_a": _mock_register(30000),
            "r_b": _mock_register(30030),
            "r_c": _mock_register(30060),
            "r_d": _mock_register(30090),
            "r_e": _mock_register(30120),
            "r_f": _mock_register(30135),
        }
        with patch(
            "huawei_solar_modbus_mqtt.bridge.batch_builder._get_huawei_registers",
            return_value=mock_registers,
        ):
            batches, unknown = BatchBuilder(batch_max_gap=50, enable_batching=True).build_batches(
                ["r_a", "r_b", "r_c", "r_d", "r_e", "r_f"],
            )

        assert unknown == []
        assert len(batches) >= 2, "Expected split due to span exceeding 125"

        for batch in batches:
            span = _batch_span(batch, mock_registers)
            assert span <= MAX_MODBUS_QUANTITY, f"Batch span {span} exceeds {MAX_MODBUS_QUANTITY}: {batch}"

        # All registers must still be present
        result = _all_regs(batches, unknown)
        assert set(result) == {"r_a", "r_b", "r_c", "r_d", "r_e", "r_f"}
        assert len(result) == 6


# ---------------------------------------------------------------------------
# TestGetHuaweiRegisters
# ---------------------------------------------------------------------------


class TestGetHuaweiRegisters:
    """Tests for the _get_huawei_registers() helper."""

    def test_returns_registers_dict_when_available(self):
        mock_module = type(sys)("huawei_solar.registers")
        mock_module.REGISTERS = {"test_reg": "dummy"}  # type: ignore[attr-defined]  # dynamisches Mock-Modul, keine statische Typ-Info
        with patch.dict(sys.modules, {"huawei_solar.registers": mock_module}):
            assert _get_huawei_registers() == {"test_reg": "dummy"}

    def test_returns_none_when_import_fails(self):
        with patch.dict(sys.modules, {"huawei_solar.registers": None}):
            result = _get_huawei_registers()
        assert result is None


# ---------------------------------------------------------------------------
# TestBatchBuilderEdgeCases
# ---------------------------------------------------------------------------


class TestBatchBuilderEdgeCases:
    """Edge cases when huawei_solar registers are unavailable or partially known."""

    def test_fallback_to_position_batching_when_huawei_unavailable(self):
        with patch("huawei_solar_modbus_mqtt.bridge.batch_builder._get_huawei_registers", return_value=None):
            registers = [f"reg{i}" for i in range(25)]
            batches, unknown = BatchBuilder(batch_max_gap=50, enable_batching=True).build_batches(registers)
            assert set(_all_regs(batches, unknown)) == set(registers)
            assert len(batches) == 2
            assert len(batches[0]) == 20
            assert len(batches[1]) == 5

    def test_batching_disabled_with_huawei_unavailable(self):
        with patch("huawei_solar_modbus_mqtt.bridge.batch_builder._get_huawei_registers", return_value=None):
            registers = ["reg1", "reg2", "reg3"]
            batches, unknown = BatchBuilder(enable_batching=False).build_batches(registers)
            assert set(_all_regs(batches, unknown)) == set(registers)
            assert len(batches) == 1
            assert len(batches[0]) == 3

    def test_all_unknown_registers_go_to_unknown_list(self):
        mock_reg = type("R", (), {"register": 100, "length": 2})()
        with patch(
            "huawei_solar_modbus_mqtt.bridge.batch_builder._get_huawei_registers",
            return_value={"known_reg": mock_reg},
        ):
            batches, unknown = BatchBuilder(enable_batching=True).build_batches(["unknown_reg1", "unknown_reg2"])
            assert batches == []
            assert unknown == ["unknown_reg1", "unknown_reg2"]

    def test_known_and_unknown_registers_separated_correctly(self):
        mock_reg = type("R", (), {"register": 100, "length": 2})()
        with patch(
            "huawei_solar_modbus_mqtt.bridge.batch_builder._get_huawei_registers",
            return_value={"known_reg": mock_reg},
        ):
            registers = ["known_reg", "unknown_reg1", "unknown_reg2"]
            batches, unknown = BatchBuilder(enable_batching=True).build_batches(registers)
            assert "known_reg" in [r for batch in batches for r in batch]
            assert unknown == ["unknown_reg1", "unknown_reg2"]
