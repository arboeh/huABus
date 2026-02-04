# bridge/total_increasing_filter.py

"""
Vereinfachter Filter für total_increasing Sensoren.

Schützt Energy Counter vor falschen Resets durch:
- Negative Werte → Filtern
- Drops auf 0 → Filtern
- Rückgänge → Filtern
- Fehlende Keys → Mit letztem Wert füllen
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("huawei.filter")


class TotalIncreasingFilter:
    """Vereinfachter Filter - keine Warmup, keine Toleranz-Config."""

    # Keys die NIEMALS fallen dürfen
    TOTAL_INCREASING_KEYS = [
        "energy_yield_accumulated",
        "energy_grid_exported",
        "energy_grid_accumulated",
        "battery_charge_total",
        "battery_discharge_total",
    ]

    def __init__(self):
        """Initialisiert den Filter - simpel!"""
        self._last_values: Dict[str, float] = {}
        self._filter_stats: Dict[str, int] = {}

    def filter(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtert Daten und füllt fehlende Keys.

        Args:
            data: Sensor-Daten aus transform.py

        Returns:
            Gefiltertes Dictionary
        """
        result = data.copy()
        filtered_count = 0
        missing_count = 0

        # ALLE total_increasing Keys prüfen (auch fehlende!)
        for key in self.TOTAL_INCREASING_KEYS:
            # 1. Key fehlt komplett? → Auffüllen mit letztem Wert
            if key not in data:
                last = self._last_values.get(key)
                if last is not None:
                    result[key] = last
                    missing_count += 1
                    logger.warning(f"MISSING: {key} filled with {last:.2f}")
                continue  # Nächster Key

            # 2. Key ist da → Prüfen ob filtern
            value = data[key]

            if not isinstance(value, (int, float)):
                continue

            if self._should_filter(key, value):
                last = self._last_values.get(key)
                if last is not None:
                    result[key] = last
                    filtered_count += 1
                    self._filter_stats[key] = self._filter_stats.get(key, 0) + 1
                    logger.warning(f"FILTERED: {key} {value:.2f} → {last:.2f}")
                else:
                    # Kein last_value vorhanden (z.B. erster Wert ist negativ)
                    # → Key komplett aus result entfernen!
                    del result[key]
                    # Optional: Als "gefiltert" zählen
                    filtered_count += 1
                    self._filter_stats[key] = self._filter_stats.get(key, 0) + 1
            else:
                # Wert ist OK → Speichern
                self._last_values[key] = value

        # Zusammenfassung
        if filtered_count > 0 or missing_count > 0:
            logger.info(f"Filter: {filtered_count} filtered, {missing_count} missing")

        return result

    def _should_filter(self, key: str, value: float) -> bool:
        """
        Prüft ob Wert gefiltert werden muss.

        Filtert wenn:
        - Negativ (unmöglich für Energy Counter)
        - Drop auf 0 von Wert > 0 (Modbus-Fehler)
        - Rückgang (Counter können nur steigen)

        Args:
            key: Sensor-Key
            value: Aktueller Wert

        Returns:
            True = Filtern, False = OK
        """
        # Nicht unser Key?
        if key not in self.TOTAL_INCREASING_KEYS:
            return False

        # Negativ? → IMMER filtern
        if value < 0:
            return True

        last = self._last_values.get(key)

        # Erster Wert? → Akzeptieren (Speichern passiert in filter()!)
        if last is None:
            return False  # ← KEIN self._last_values[key] = value hier!

        # Drop auf 0? → Filtern (außer letzter war auch 0)
        if value == 0 and last > 0:
            return True

        # Gefallen? → Filtern (Counter steigen nur!)
        if value < last:
            return True

        # Alles OK
        return False

    def get_stats(self) -> Dict[str, int]:
        """Gibt Filter-Statistik zurück."""
        return self._filter_stats.copy()

    def reset_stats(self):
        """Setzt Statistik zurück (behält last_values)."""
        self._filter_stats.clear()

    def reset(self):
        """Kompletter Reset - bei Connection-Fehler."""
        self._last_values.clear()
        self._filter_stats.clear()
        logger.info("Filter reset")


# Singleton-Instanz
_filter_instance: Optional[TotalIncreasingFilter] = None


def get_filter() -> TotalIncreasingFilter:
    """Gibt Singleton-Instanz zurück."""
    global _filter_instance
    if _filter_instance is None:
        _filter_instance = TotalIncreasingFilter()
    return _filter_instance


def reset_filter():
    """Setzt Singleton zurück (löscht Instanz komplett)."""
    global _filter_instance
    if _filter_instance is not None:
        _filter_instance.reset()
        _filter_instance = None
