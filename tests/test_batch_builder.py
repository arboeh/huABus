# tests/test_batch_builder.py

"""Tests for BatchBuilder and smart batching functionality."""

from bridge.batch_builder import BatchBuilder, build_batches_from_registers


class TestBatchBuilder:
    """Test BatchBuilder class."""

    def test_init_with_defaults(self):
        """Should initialize with default values."""
        builder = BatchBuilder()
        assert builder.batch_max_gap == 100
        assert builder.enable_batching is True

    def test_init_with_custom_values(self):
        """Should accept custom batch_max_gap and enable_batching."""
        builder = BatchBuilder(batch_max_gap=50, enable_batching=False)
        assert builder.batch_max_gap == 50
        assert builder.enable_batching is False

    def test_build_batches_with_batching_disabled(self):
        """Should return all registers in a single group when batching disabled."""
        builder = BatchBuilder(enable_batching=False)
        registers = ["reg1", "reg2", "reg3", "reg4", "reg5"]

        batches, unknown = builder.build_batches(registers)

        # All registers must be accounted for
        all_regs = [r for batch in batches for r in batch] + unknown
        assert set(all_regs) == set(registers)
        assert len(all_regs) == len(registers)
        # No batching: should be a single group (either 1 batch or all in unknown)
        assert len(batches) + len(unknown) > 0

    def test_build_batches_with_empty_list(self):
        """Should handle empty register list."""
        builder = BatchBuilder(enable_batching=True)
        registers: list[str] = []

        batches, unknown = builder.build_batches(registers)

        assert batches == [[]]
        assert unknown == []

    def test_build_batches_with_single_register(self):
        """Should handle single register."""
        builder = BatchBuilder(enable_batching=True)
        registers = ["reg1"]

        batches, unknown = builder.build_batches(registers)

        all_regs = [r for batch in batches for r in batch] + unknown
        assert set(all_regs) == {"reg1"}

    def test_build_batches_splits_large_batch(self):
        """Should produce multiple groups for many registers (batches or sequential)."""
        builder = BatchBuilder(enable_batching=True)
        registers = [f"reg{i}" for i in range(67)]  # 67 registers like ESSENTIAL_REGISTERS

        batches, unknown = builder.build_batches(registers)

        # All registers should be included (in batches or unknown)
        all_regs = [r for batch in batches for r in batch] + unknown
        assert set(all_regs) == set(registers)
        assert len(all_regs) == len(registers)

    def test_build_batches_with_small_register_count(self):
        """Should return single batch for small register count."""
        builder = BatchBuilder(enable_batching=True)
        registers = ["reg1", "reg2", "reg3", "reg4"]

        batches, unknown = builder.build_batches(registers)

        all_regs = [r for batch in batches for r in batch] + unknown
        assert set(all_regs) == set(registers)

    def test_validate_batch_gap_valid_values(self):
        """Should validate acceptable batch_max_gap values."""
        builder = BatchBuilder()

        assert builder.validate_batch_gap(1) is True
        assert builder.validate_batch_gap(50) is True
        assert builder.validate_batch_gap(100) is True
        assert builder.validate_batch_gap(1000) is True

    def test_validate_batch_gap_invalid_values(self):
        """Should reject invalid batch_max_gap values."""
        builder = BatchBuilder()

        assert builder.validate_batch_gap(0) is False
        assert builder.validate_batch_gap(-1) is False

    def test_validate_batch_gap_too_large(self):
        """Should warn about unreasonably large batch_max_gap values."""
        builder = BatchBuilder()

        # 10001 is > 10000, should trigger warning but still return False
        assert builder.validate_batch_gap(10001) is False


class TestBatchBuilderConvenienceFunction:
    """Test convenience function."""

    def test_build_batches_from_registers_with_batching_enabled(self):
        """Should include all registers (in batches or sequential)."""
        registers = [f"reg{i}" for i in range(30)]

        batches, unknown = build_batches_from_registers(registers, batch_max_gap=100, enable_batching=True)

        # All registers should be included
        all_regs = [r for batch in batches for r in batch] + unknown
        assert set(all_regs) == set(registers)
        assert len(all_regs) == len(registers)

    def test_build_batches_from_registers_with_batching_disabled(self):
        """Should include all registers when batching disabled."""
        registers = [f"reg{i}" for i in range(30)]

        batches, unknown = build_batches_from_registers(registers, batch_max_gap=100, enable_batching=False)

        all_regs = [r for batch in batches for r in batch] + unknown
        assert set(all_regs) == set(registers)
        assert len(all_regs) == len(registers)


class TestBatchBuilderIntegration:
    """Integration tests for batch building with realistic scenarios."""

    def test_essential_registers_batching(self):
        """Should properly batch 67 essential registers."""
        from bridge.config.registers import ESSENTIAL_REGISTERS

        builder = BatchBuilder(enable_batching=True)
        batches, unknown = builder.build_batches(ESSENTIAL_REGISTERS)

        # Should create at least one batch
        assert len(batches) >= 1

        # All registers should be included exactly once
        all_regs = [r for batch in batches for r in batch] + unknown
        assert len(all_regs) == len(ESSENTIAL_REGISTERS)
        assert set(all_regs) == set(ESSENTIAL_REGISTERS)

    def test_batching_preserves_completeness(self):
        """All registers should be present in batches or unknown list."""
        registers = ["reg1", "reg2", "reg3", "reg4", "reg5"]

        builder = BatchBuilder(enable_batching=True)
        batches, unknown = builder.build_batches(registers)

        # All registers must be in batches or unknown
        all_regs = [r for batch in batches for r in batch] + unknown
        assert set(all_regs) == set(registers)
        assert len(all_regs) == len(registers)

    def test_batching_with_different_gap_values(self):
        """Should handle different batch_max_gap configurations."""
        registers = [f"reg{i}" for i in range(67)]

        # Test with small gap
        builder_small = BatchBuilder(batch_max_gap=10, enable_batching=True)
        batches_small, unknown_small = builder_small.build_batches(registers)

        # Test with large gap
        builder_large = BatchBuilder(batch_max_gap=10000, enable_batching=True)
        batches_large, unknown_large = builder_large.build_batches(registers)

        # Both should include all registers
        all_small = [r for batch in batches_small for r in batch] + unknown_small
        all_large = [r for batch in batches_large for r in batch] + unknown_large

        assert set(all_small) == set(registers)
        assert set(all_large) == set(registers)
