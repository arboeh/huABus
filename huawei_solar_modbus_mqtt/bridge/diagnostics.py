# huawei_solar_modbus_mqtt/bridge/diagnostics.py

"""
Diagnose-Werte der Bridge selbst (nicht des Wechselrichters).

Liefert die Werte für die Diagnose-Entities ``bridge_errors``,
``bridge_cycle_duration``, ``bridge_uptime`` und ``bridge_batch_mode``.
Die Funktion ist rein (kein Modbus, kein MQTT, keine globalen Zugriffe), damit
sie ohne Infrastruktur testbar ist. main.py mischt das Ergebnis nach dem
total_increasing Filter in den Payload.

Zeitbasis: time.monotonic() für Dauer und Uptime (unabhängig von Uhrsprüngen).

Hinweis: Die Diagnose-Werte werden nur in erfolgreichen Zyklen veröffentlicht.
Während einer Störung steht der Status auf "offline"; den neuen Fehlerzähler
sieht man erst nach der Wiederherstellung.
"""

import time
from typing import Literal, TypedDict

from .error_tracker import ConnectionErrorTracker

# batch:      Smart Batching, alle Batches erfolgreich
# fallback:   mindestens ein Batch (oder der ganze Batch-Pfad) fiel auf Einzelreads zurück
# sequential: Einzelreads (enable_batching=false oder noch kein Read)
BatchMode = Literal["batch", "fallback", "sequential"]


class BridgeDiagnostics(TypedDict):
    """Payload-Werte der Bridge-Diagnose. Typ-Quelle für BRIDGE_KEYS."""

    bridge_errors: int
    bridge_cycle_duration: float
    bridge_uptime: int
    bridge_batch_mode: BatchMode


# Alle Keys aus BridgeDiagnostics (Tests und Ausnahmeliste im Register-Test)
BRIDGE_KEYS: frozenset[str] = frozenset(BridgeDiagnostics.__annotations__)


def build_bridge_diagnostics(
    tracker: ConnectionErrorTracker,
    *,
    start_time: float,
    cycle_duration: float,
    batch_mode: BatchMode,
    now: float | None = None,
) -> BridgeDiagnostics:
    """Baut die Diagnose-Werte der Bridge.

    Args:
        tracker: Error-Tracker; ``lifetime_failures`` liefert die Fehleranzahl.
        start_time: Monotonic-Zeit des Prozessstarts (time.monotonic()).
        cycle_duration: Dauer der aktuellen Verarbeitung in Sekunden
            (Modbus + Transform + Filter, ohne MQTT-Publish).
        batch_mode: Aktueller Lesemodus.
        now: Aktuelle Monotonic-Zeit (für Tests injizierbar, Default time.monotonic()).

    Returns:
        ``bridge_errors`` (int), ``bridge_cycle_duration`` (float, s),
        ``bridge_uptime`` (int, s) und ``bridge_batch_mode`` (str).
    """
    current = time.monotonic() if now is None else now
    return {
        "bridge_errors": tracker.lifetime_failures,
        "bridge_cycle_duration": round(max(cycle_duration, 0.0), 2),
        "bridge_uptime": int(max(current - start_time, 0.0)),
        "bridge_batch_mode": batch_mode,
    }
