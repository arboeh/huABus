# huawei_solar_modbus_mqtt/bridge/batch_builder.py

"""
Smart register batch grouping for optimized Modbus reads.

Modbus function code 3 (Read Holding Registers) and function code 4
(Read Input Registers) allow a maximum of 125 registers per request.
Each batch produced by this module must therefore stay within that
limit when measured as the address span from the first register's
start address to the last register's end address.
"""

import logging
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from huawei_solar.register_definitions.base import RegisterDefinition

logger = logging.getLogger("huawei.batch_builder")

MAX_MODBUS_QUANTITY = 125


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

        Additionally enforces the hard Modbus FC03/FC04 limit of at most
        ``MAX_MODBUS_QUANTITY`` (125) registers per single read request: a batch
        whose address span would exceed 125 registers is split so no individual
        get_multiple() call requests more than 125 registers.

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

        # Group by address proximity: new batch when gap > batch_max_gap.
        # Also enforce the hard Modbus limit: the address span of any single
        # batch (last register end address - first register start address)
        # must not exceed MAX_MODBUS_QUANTITY (125) registers, otherwise the
        # underlying tModbus PDU constructor raises
        # ValueError("Quantity must be between 1 and 125.").
        batches: list[list[str]] = []
        current_batch: list[str] = []
        prev_end: int | None = None
        batch_start_address: int | None = None

        for name, reg in known:
            reg_end = reg.register + reg.length

            # Split on large address gap
            if prev_end is not None and (reg.register - prev_end) > self.batch_max_gap:
                batches.append(current_batch)
                current_batch = []
                batch_start_address = None

            # Split on Modbus quantity limit
            if batch_start_address is not None:
                span = reg_end - batch_start_address
                if span > MAX_MODBUS_QUANTITY:
                    batches.append(current_batch)
                    current_batch = []
                    batch_start_address = reg.register

            if not current_batch:
                batch_start_address = reg.register

            current_batch.append(name)
            prev_end = reg_end

        if current_batch:
            batches.append(current_batch)

        # DEBUG: log each batch's composition so the register span /
        # effective Modbus quantity can be verified at runtime.
        if logger.isEnabledFor(logging.DEBUG):
            for idx, batch in enumerate(batches, 1):
                first_reg = huawei_registers[batch[0]]
                last_reg = huawei_registers[batch[-1]]
                span = (last_reg.register + last_reg.length) - first_reg.register
                logger.debug(
                    "BatchBuilder batch %d/%d: addr %d-%d, span=%d, names=%s",
                    idx,
                    len(batches),
                    first_reg.register,
                    last_reg.register + last_reg.length,
                    span,
                    batch,
                )

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
