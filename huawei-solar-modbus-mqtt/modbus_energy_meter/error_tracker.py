# modbus_energy_meter/error_tracker.py
import logging
import time
from typing import Optional, Dict

logger = logging.getLogger("huawei.errors")


class ConnectionErrorTracker:
    """Tracks and aggregates connection errors to reduce log spam."""

    def __init__(self, log_interval: int = 60):
        self.log_interval = log_interval
        self.errors: Dict[str, Dict] = {}
        self.last_success_time: Optional[float] = None

    def track_error(self, error_type: str, details: str = "") -> bool:
        """
        Track an error occurrence.
        Returns True if error should be logged (first occurrence or interval expired).
        """
        now = time.time()

        if error_type not in self.errors:
            # First occurrence of this error type
            self.errors[error_type] = {
                "first_seen": now,
                "last_logged": now,
                "count": 1,
                "details": details,
            }
            logger.error(f"Connection error: {error_type} - {details}")
            return True

        # Update existing error
        error_info = self.errors[error_type]
        error_info["count"] += 1

        # Log again if interval expired
        if now - error_info["last_logged"] > self.log_interval:
            duration = now - error_info["first_seen"]
            logger.warning(
                f"Still failing: {error_type} "
                f"({error_info['count']} attempts in {int(duration)}s)"
            )
            error_info["last_logged"] = now
            return True

        return False

    def mark_success(self) -> None:
        """Mark successful connection, log recovery if there were errors."""
        if self.errors:
            total_errors = sum(e["count"] for e in self.errors.values())
            first_error = min(e["first_seen"] for e in self.errors.values())
            downtime = time.time() - first_error
            logger.info(
                f"Connection restored after {int(downtime)}s "
                f"({total_errors} failed attempts, {len(self.errors)} error types)"
            )
            self.errors.clear()

        self.last_success_time = time.time()

    def get_status(self) -> Dict:
        """Get current error status for diagnostics."""
        return {
            "active_errors": len(self.errors),
            "total_failures": sum(e["count"] for e in self.errors.values()),
            "last_success": self.last_success_time,
        }
