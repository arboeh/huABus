# huawei_solar_modbus_mqtt/bridge/batch_builder.py

"""
Smart register batch grouping for optimized Modbus reads.
"""

import logging

logger = logging.getLogger("huawei.batch_builder")


class BatchBuilder:
    """Builds optimized batches of registers for reading."""

    def __init__(self, batch_max_gap: int = 100, enable_batching: bool = True):
        """Initialize batch builder."""
        self.batch_max_gap = batch_max_gap
        self.enable_batching = enable_batching

    def build_batches(self, registers: list[str]) -> list[list[str]]:
        """Build optimized batches from a list of register names."""
        if not self.enable_batching or not registers:
            return [registers]

        if len(registers) > 20:
            batch_size = 20
            return [registers[i : i + batch_size] for i in range(0, len(registers), batch_size)]

        return [registers]

    def validate_batch_gap(self, batch_max_gap: int) -> bool:
        """Validate batch_max_gap configuration."""
        if batch_max_gap < 1:
            logger.warning(f"batch_max_gap must be >= 1, got {batch_max_gap}")
            return False
        if batch_max_gap > 10000:
            logger.warning(f"batch_max_gap seems very large ({batch_max_gap}), may cause batches that are too large")
            return False
        return True


def build_batches_from_registers(
    registers: list[str],
    batch_max_gap: int = 100,
    enable_batching: bool = True,
) -> list[list[str]]:
    """Convenience function to build batches without creating a BatchBuilder."""
    builder = BatchBuilder(batch_max_gap=batch_max_gap, enable_batching=enable_batching)
    return builder.build_batches(registers)
