# huawei_solar_modbus_mqtt/bridge/batch_builder.py

"""
Smart register batch grouping for optimized Modbus reads.
"""

import logging
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from huawei_solar.register_definitions.base import RegisterDefinition

logger = logging.getLogger("huawei.batch_builder")


def _get_huawei_registers() -> "dict[str, RegisterDefinition] | None":
    """Try to import the huawei_solar REGISTERS dict. Returns None if unavailable."""
    try:
        from huawei_solar.registers import REGISTERS

        return cast(dict, REGISTERS)
    except ImportError:
        return None


class BatchBuilder:
    """Builds optimized batches of registers for reading.

    Sorts registers by their Modbus address and groups them by address proximity,
    so each batch can be read with a single get_multiple() call.
    """

    def __init__(self, batch_max_gap: int = 50, enable_batching: bool = True):
        """Initialize batch builder."""
        self.batch_max_gap = batch_max_gap
        self.enable_batching = enable_batching

    def build_batches(self, registers: list[str]) -> tuple[list[list[str]], list[str]]:
        """Build address-sorted batches from register names.

        Sorts registers by Modbus address and groups by proximity so each batch
        satisfies the get_multiple() monotonically-increasing-address requirement.

        Returns:
            (batches, unknown): batches to read with get_multiple(),
                                unknown = registers not in the library (read sequentially)
        """
        if not registers:
            return [[]], []

        huawei_registers = _get_huawei_registers()

        if huawei_registers is None:
            # Library not available: fall back to simple position-based splitting
            if not self.enable_batching:
                return [list(registers)], []
            batch_size = 20
            return [registers[i : i + batch_size] for i in range(0, len(registers), batch_size)], []

        # Separate known (in library) from unknown registers
        known = [(name, huawei_registers[name]) for name in registers if name in huawei_registers]
        unknown = [name for name in registers if name not in huawei_registers]

        if not known:
            return [], unknown

        # Sort by Modbus address (required by get_multiple)
        known.sort(key=lambda x: x[1].register)

        if not self.enable_batching:
            return [[name for name, _ in known]], unknown

        # Group by address proximity: new batch when gap > batch_max_gap
        batches: list[list[str]] = []
        current_batch: list[str] = []
        prev_end: int | None = None

        for name, reg in known:
            if prev_end is not None:
                gap = reg.register - prev_end
                if gap > self.batch_max_gap:
                    batches.append(current_batch)
                    current_batch = []
            current_batch.append(name)
            prev_end = reg.register + reg.length

        if current_batch:
            batches.append(current_batch)

        return batches, unknown

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
    batch_max_gap: int = 50,
    enable_batching: bool = True,
) -> tuple[list[list[str]], list[str]]:
    """Convenience function to build batches without creating a BatchBuilder."""
    builder = BatchBuilder(batch_max_gap=batch_max_gap, enable_batching=enable_batching)
    return builder.build_batches(registers)
