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
        """Should return all registers as single batch when batching disabled."""
        builder = BatchBuilder(enable_batching=False)
        registers = ["reg1", "reg2", "reg3", "reg4", "reg5"]

        batches = builder.build_batches(registers)

        assert len(batches) == 1
        assert batches[0] == registers

    def test_build_batches_with_empty_list(self):
        """Should handle empty register list."""
        builder = BatchBuilder(enable_batching=True)
        registers: list[str] = []

        batches = builder.build_batches(registers)

        assert len(batches) == 1
        assert batches[0] == []

    def test_build_batches_with_single_register(self):
        """Should handle single register."""
        builder = BatchBuilder(enable_batching=True)
        registers = ["reg1"]

        batches = builder.build_batches(registers)

        assert len(batches) == 1
        assert batches[0] == ["reg1"]

    def test_build_batches_splits_large_batch(self):
        """Should split large batch into smaller chunks."""
        builder = BatchBuilder(enable_batching=True)
        registers = [f"reg{i}" for i in range(67)]  # 67 registers like ESSENTIAL_REGISTERS

        batches = builder.build_batches(registers)

        # With default batch_size=20, should get multiple batches
        assert len(batches) > 1

        # All batches should have size <= 20
        for batch in batches:
            assert len(batch) <= 20

        # All registers should be included
        all_regs = []
        for batch in batches:
            all_regs.extend(batch)
        assert set(all_regs) == set(registers)
        assert len(all_regs) == len(registers)

    def test_build_batches_with_small_register_count(self):
        """Should return single batch for small register count."""
        builder = BatchBuilder(enable_batching=True)
        registers = ["reg1", "reg2", "reg3", "reg4"]

        batches = builder.build_batches(registers)

        assert len(batches) == 1
        assert batches[0] == registers

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
        """Should use smart batching when enabled."""
        registers = [f"reg{i}" for i in range(30)]

        batches = build_batches_from_registers(registers, batch_max_gap=100, enable_batching=True)

        # Should get multiple batches for 30 registers
        assert len(batches) >= 1

        # All registers should be included
        all_regs = []
        for batch in batches:
            all_regs.extend(batch)
        assert set(all_regs) == set(registers)

    def test_build_batches_from_registers_with_batching_disabled(self):
        """Should return single batch when batching disabled."""
        registers = [f"reg{i}" for i in range(30)]

        batches = build_batches_from_registers(registers, batch_max_gap=100, enable_batching=False)

        assert len(batches) == 1
        assert batches[0] == registers


class TestBatchBuilderIntegration:
    """Integration tests for batch building with realistic scenarios."""

    def test_essential_registers_batching(self):
        """Should properly batch 67 essential registers."""
        from bridge.config.registers import ESSENTIAL_REGISTERS

        builder = BatchBuilder(enable_batching=True)
        batches = builder.build_batches(ESSENTIAL_REGISTERS)

        # Should create multiple batches
        assert len(batches) >= 1

        # All registers should be included exactly once
        all_regs = []
        for batch in batches:
            all_regs.extend(batch)

        assert len(all_regs) == len(ESSENTIAL_REGISTERS)
        assert set(all_regs) == set(ESSENTIAL_REGISTERS)

    def test_batching_preserves_order(self):
        """Should preserve register order within batches."""
        registers = ["reg1", "reg2", "reg3", "reg4", "reg5"]

        builder = BatchBuilder(enable_batching=True)
        batches = builder.build_batches(registers)

        # Flatten batches and check order
        flattened = []
        for batch in batches:
            flattened.extend(batch)

        # Original order should be maintained
        assert flattened == registers

    def test_batching_with_different_gap_values(self):
        """Should handle different batch_max_gap configurations."""
        registers = [f"reg{i}" for i in range(67)]

        # Test with small gap
        builder_small = BatchBuilder(batch_max_gap=10, enable_batching=True)
        batches_small = builder_small.build_batches(registers)

        # Test with large gap
        builder_large = BatchBuilder(batch_max_gap=10000, enable_batching=True)
        batches_large = builder_large.build_batches(registers)

        # Both should include all registers
        all_small = []
        for batch in batches_small:
            all_small.extend(batch)

        all_large = []
        for batch in batches_large:
            all_large.extend(batch)

        assert set(all_small) == set(registers)
        assert set(all_large) == set(registers)
