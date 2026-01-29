# modbus_energy_meter/total_increasing_filter.py

"""
Filter für total_increasing Sensoren zur Vermeidung falscher Counter-Resets.

Home Assistant interpretiert bei state_class: total_increasing jeden Rückgang
als Counter-Reset. Modbus-Lesefehler (Timeouts, ungültige Register-Werte) können
jedoch temporär zu 0-Werten oder Sprüngen führen, die dann falsche Resets auslösen
und die Energie-Statistiken verfälschen.

Dieser Filter arbeitet als Schutzschicht zwischen Modbus-Read und MQTT-Publishing
und verhindert, dass ungültige Werte zu Home Assistant gelangen.
"""

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("huawei.filter")


class TotalIncreasingFilter:
    """
    Filter für total_increasing Sensoren um falsche Resets zu verhindern.

    Home Assistant setzt bei state_class: total_increasing voraus, dass Werte
    niemals fallen (außer bei echten Counter-Resets). Modbus-Lesefehler können
    jedoch temporär ungültige Werte liefern, die dann falsche Resets auslösen.

    Dieser Filter:
    - Speichert letzte gültige Werte pro Sensor
    - Filtert negative Werte (unmöglich für Energie-Counter)
    - Filtert Rückgänge die größer als Toleranz sind (wahrscheinlich Lesefehler)
    - Ersetzt ungültige Werte durch letzten gültigen Wert
    - Loggt alle Filter-Aktionen für Debugging

    Beispiel:
        Modbus liefert: energy_yield_accumulated = 0 (Lesefehler)
        Filter erkennt: "Letzter Wert war 15420 kWh, 0 ist unmöglich"
        Filter ersetzt: energy_yield_accumulated = 15420 (letzter gültiger Wert)
        Home Assistant: Empfängt 15420, kein falscher Reset ausgelöst
    """

    # Sensoren die total_increasing verwenden und NIEMALS fallen dürfen
    # Diese Counter-Werte akkumulieren über die gesamte Lebensdauer und
    # sollten nur bei Hardware-Reset (neuer Inverter) auf 0 springen
    TOTAL_INCREASING_KEYS = {
        "energy_yield_accumulated",  # Solar Total Yield - Gesamtertrag seit Installation
        "energy_grid_exported",  # Grid Energy Exported - Gesamt eingespeiste Energie
        "energy_grid_accumulated",  # Grid Energy Imported - Gesamt bezogene Energie
        "battery_charge_total",  # Battery Total Charge - Gesamt geladene Energie
        "battery_discharge_total",  # Battery Total Discharge - Gesamt entladene Energie
    }

    def __init__(self, tolerance: float = 0.05, warmup_cycles: int = 3):
        """
        Initialisiert den Filter mit konfigurierbarer Toleranz.

        Args:
            tolerance: Erlaubte Toleranz für Rückgänge (0.05 = 5%)
                       Filtert nur wenn Wert um mehr als 5% fällt.
                       Kleine Toleranz verhindert False-Positives bei
                       gleichzeitigen Modbus-Reads während Counter-Updates.
            warmup_cycles: Anzahl Cycles für Warmup (default: 3)

        Hinweis:
            Eine Toleranz von 5% bedeutet:
            - Bei 10.000 kWh werden Rückgänge bis 9.500 kWh akzeptiert
            - Größere Sprünge (z.B. auf 0) werden gefiltert
            - Verhindert False-Positives bei Race-Conditions während Counter-Updates
        """
        self.tolerance = tolerance
        self._last_values: Dict[str, float] = {}  # Speichert letzte gültige Werte
        self._filter_count: Dict[str, int] = {}  # Zählt gefilterte Werte pro Sensor

        # Warmup-Periode
        self.warmup_mode = True
        self.warmup_cycles = 0
        self.warmup_required = warmup_cycles

        # First-Value Tracking
        self.suspicious_first_values: Dict[str, float] = {}

        logger.info(
            f"🛡️ TotalIncreasingFilter initialized with {self.tolerance*100:.0f}% tolerance "
            f"and {self.warmup_required}-cycle warmup period"
        )

    def filter(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtert ein komplettes Daten-Dictionary.

        Geht durch alle Werte im Dictionary und wendet should_filter()
        auf jeden total_increasing Sensor an. Gefilterte Werte werden
        durch den letzten gültigen Wert ersetzt.

        Args:
            data: Dictionary mit Sensor-Daten (MQTT-Format)

        Returns:
            Gefiltertes Dictionary (gefilterte Werte ersetzt)

        Beispiel:
            Input:  {'energy_yield_accumulated': 0, 'power_active': 4500}
            Output: {'energy_yield_accumulated': 15420.5, 'power_active': 4500}
                    # 0 wurde durch letzten gültigen Wert ersetzt
        """
        result = data.copy()

        # === WARMUP-PHASE ===
        if self.warmup_mode:
            self.warmup_cycles += 1

            for key, value in data.items():
                if key in self.TOTAL_INCREASING_KEYS and isinstance(
                    value, (int, float)
                ):
                    if key not in self._last_values:
                        if value == 0:
                            logger.warning(
                                f"⚠️ WARMUP: First value for {key} is 0 - "
                                f"marking as suspicious (cycle {self.warmup_cycles}/{self.warmup_required})"
                            )
                            self.suspicious_first_values[key] = 0
                        else:
                            logger.info(
                                f"✅ WARMUP: First value for {key}: {value:.2f} "
                                f"(cycle {self.warmup_cycles}/{self.warmup_required})"
                            )

                    self._last_values[key] = value

            if self.warmup_cycles >= self.warmup_required:
                self.warmup_mode = False
                logger.info(
                    f"✅ Filter warmup complete after {self.warmup_cycles} cycles - "
                    f"protection now ACTIVE"
                )

                if self.suspicious_first_values:
                    logger.warning(
                        f"⚠️ Suspicious zero values detected during warmup: "
                        f"{list(self.suspicious_first_values.keys())} - "
                        f"monitoring closely for next cycles"
                    )
            else:
                logger.debug(
                    f"WARMUP: Cycle {self.warmup_cycles}/{self.warmup_required} - "
                    f"storing values, no filtering yet"
                )

            return result  # Während Warmup: Unverändert durchlassen

        # === NORMAL-BETRIEB ===
        filtered_count = 0

        for key, value in data.items():
            # Nur numerische Werte prüfen
            if not isinstance(value, (int, float)):
                continue

            # Prüfen ob gefiltert werden soll
            if self.should_filter(key, value):
                # Durch letzten gültigen Wert ersetzen
                last_value = self.get_last_value(key)
                if last_value is not None:
                    result[key] = last_value
                    filtered_count += 1
                    logger.warning(
                        f"⚠️ FILTERED: {key}: {value:.2f} → {last_value:.2f} "
                        f"(drop > {self.tolerance*100:.0f}% or invalid)"
                    )
                else:
                    logger.error(
                        f"❌ Cannot filter {key}={value:.2f} - no previous valid value!"
                    )
            else:  # ✅ KORREKT: Gehört zu if self.should_filter()
                # Logge auch akzeptierte Werte (nur bei DEBUG)
                if key in self.TOTAL_INCREASING_KEYS:
                    last = self.get_last_value(key)
                    if last is not None:
                        logger.debug(f"✅ Accepted {key}: {last:.2f} → {value:.2f}")
                    else:
                        logger.debug(f"✅ First value for {key}: {value:.2f}")

        if filtered_count > 0:
            logger.info(f"🔍 Filtered {filtered_count} values in this cycle")

        return result

    def should_filter(self, key: str, value: float) -> bool:
        """
        Prüft ob ein Wert gefiltert werden soll.

        Logik:
        1. Nur definierte total_increasing Sensoren werden geprüft
        2. Negative Werte werden immer gefiltert (unmöglich für Energie-Counter)
        3. Erster Wert wird immer akzeptiert (Initialisierung)
        4. Wert >= letzter Wert → OK (normales Verhalten)
        5. Wert < letzter Wert mit Toleranz-Check:
           - Innerhalb Toleranz → akzeptieren (mögliche Race-Condition)
           - Außerhalb Toleranz → filtern (wahrscheinlich Lesefehler)

        Args:
            key: Sensor-Key aus MQTT-Daten (z.B. 'energy_yield_accumulated')
            value: Aktueller Wert vom Modbus-Read

        Returns:
            True wenn Wert gefiltert werden soll (ungültig)
            False wenn Wert OK ist und durchgelassen werden soll

        Beispiele:
            >>> filter.should_filter("energy_yield_accumulated", 15420.5)
            False  # Normaler Wert, wird durchgelassen

            >>> filter.should_filter("energy_yield_accumulated", -10)
            True  # Negativ, wird gefiltert

            >>> filter.should_filter("energy_yield_accumulated", 0)
            True  # Drop von 15420 auf 0, wird gefiltert
        """
        # Nur total_increasing Sensoren prüfen, andere durchlassen
        if key not in self.TOTAL_INCREASING_KEYS:
            return False

        # Negative Werte sind niemals erlaubt für Energie-Counter
        # Mögliche Ursachen: Modbus-Übertragungsfehler, ungültiges Register
        if value < 0:
            logger.debug(f"Filter criterion: {key}={value} is negative")
            return True

        # Ersten Wert immer akzeptieren (Initialisierung beim Start)
        if key not in self._last_values:
            logger.warning(
                f"⚠️ First value after reset for {key}: {value:.2f} "
                f"(unexpected - should have been handled in warmup)"
            )
            self._last_values[key] = value
            return False

        last_value = self._last_values[key]

        # Wenn Wert gleich oder gestiegen ist → OK (normales Verhalten)
        # Counter sollten monoton steigend sein
        if value >= last_value:
            self._last_values[key] = value

            # Recovery from suspicious zero
            if key in self.suspicious_first_values:
                logger.info(
                    f"✅ {key} recovered from suspicious zero: "
                    f"0 → {value:.2f} (normal operation resumed)"
                )
                del self.suspicious_first_values[key]

            return False

        drop_percent = (last_value - value) / last_value

        if drop_percent <= self.tolerance:
            logger.debug(
                f"Small drop for {key}: {last_value:.2f} → {value:.2f} "
                f"({drop_percent*100:.1f}% < {self.tolerance*100:.0f}%) - within tolerance"
            )
            self._last_values[key] = value
            return False

        self._filter_count[key] = self._filter_count.get(key, 0) + 1
        logger.debug(
            f"Filter criterion: {key} dropped {drop_percent*100:.1f}% "
            f"({last_value:.2f} → {value:.2f}) > {self.tolerance*100:.0f}% tolerance"
        )
        return True

    def get_last_value(self, key: str) -> Optional[float]:
        """
        Gibt letzten gültigen Wert zurück (für Ersetzung gefilterter Werte).

        Wird verwendet wenn ein Wert gefiltert wurde und durch den letzten
        gültigen Wert ersetzt werden soll, statt einfach 0 zu verwenden.

        Args:
            key: Sensor-Key

        Returns:
            Letzter gültiger Wert oder None wenn noch kein Wert vorhanden

        Beispiel:
            >>> filter.get_last_value("energy_yield_accumulated")
            15420.5  # Letzter gültiger Wert vor dem Fehler
        """
        return self._last_values.get(key)

    def get_stats(self) -> Dict[str, int]:
        """
        Gibt Statistik über gefilterte Werte zurück.

        Nützlich für Monitoring und Debugging - zeigt wie oft welche
        Sensoren gefiltert wurden. Häufige Filterungen können auf
        Modbus-Verbindungsprobleme oder Hardware-Fehler hinweisen.

        Returns:
            Dict mit Sensor-Keys und Anzahl gefilterter Werte

        Beispiel:
            >>> filter.get_stats()
            {'energy_yield_accumulated': 3, 'battery_charge_total': 1}
            # Bedeutet: 3x falscher Wert bei Solar, 1x bei Batterie
        """
        return self._filter_count.copy()

    def reset_stats(self) -> None:
        """
        Setzt die Filter-Statistik zurück.

        Behält die letzten gültigen Werte, löscht aber nur die Zähler.
        Nützlich für periodisches Reset der Statistik ohne Filter-State
        zu verlieren.
        """
        self._filter_count.clear()
        logger.debug("Filter statistics reset")

    def reset(self) -> None:
        """
        Setzt alle gespeicherten Werte und Statistiken zurück.

        Sollte aufgerufen werden bei:
        - Verbindungs-Neustart (neue Modbus-Session)
        - Bekanntem Counter-Reset (Inverter-Neustart)
        - Timeout/Fehler (alle Werte könnten ungültig sein)

        Nach Reset werden die nächsten Werte als "erste Werte" akzeptiert,
        unabhängig von vorherigen Werten.
        """
        self._last_values.clear()
        self._filter_count.clear()

        # Warmup neu starten
        self.warmup_mode = True
        self.warmup_cycles = 0

        # suspicious_first_values NICHT clearen (für Diagnose behalten)
        # Wenn du Diagnose-Historie behalten willst, ist das OK
        # Wenn du sauberen Reset willst: self.suspicious_first_values.clear()

        logger.info(
            f"Filter reset - restarting {self.warmup_required}-cycle warmup period"
        )


# Globale Instanz für das gesamte Modul (Singleton-Pattern)
# Wird beim ersten get_filter() Aufruf initialisiert
_filter_instance: Optional[TotalIncreasingFilter] = None


def get_filter(
    tolerance: Optional[float] = None, warmup_cycles: Optional[int] = None
) -> TotalIncreasingFilter:
    """
    Gibt die globale Filter-Instanz zurück (Singleton-Pattern).

    Beim ersten Aufruf wird die Instanz erstellt und konfiguriert.
    Folgende Aufrufe geben dieselbe Instanz zurück (Singleton).

    Die Toleranz kann entweder explizit übergeben oder aus der
    ENV-Variable HUAWEI_FILTER_TOLERANCE gelesen werden.

    Args:
        tolerance: Toleranz für die erste Initialisierung (optional)
                   Falls None, wird HUAWEI_FILTER_TOLERANCE ENV gelesen (default: 0.05)
        warmup_cycles: Warmup-Zyklen für die erste Initialisierung (optional)
                   Falls None, wird HUAWEI_FILTER_WARMUP ENV gelesen (default: 3)

    Returns:
        TotalIncreasingFilter Instanz (immer dieselbe)

    Beispiel:
        >>> filter = get_filter()  # Nutzt ENV oder default 0.05
        >>> filter2 = get_filter()  # Gibt dieselbe Instanz zurück
        >>> assert filter is filter2
    """
    global _filter_instance

    if _filter_instance is None:
        # Toleranz aus ENV lesen falls nicht explizit übergeben
        if tolerance is None:
            tolerance = float(os.environ.get("HUAWEI_FILTER_TOLERANCE", "0.05"))

        if warmup_cycles is None:
            warmup_cycles = int(os.environ.get("HUAWEI_FILTER_WARMUP", "3"))

        _filter_instance = TotalIncreasingFilter(
            tolerance=tolerance, warmup_cycles=warmup_cycles
        )

    return _filter_instance


def reset_filter() -> None:
    """
    Setzt die globale Filter-Instanz zurück.

    Ruft reset() auf der Singleton-Instanz auf, falls vorhanden.
    Wird typischerweise bei Verbindungsfehlern aufgerufen, um
    sicherzustellen dass nach Wiederverbindung alle Werte neu
    initialisiert werden.

    Nützlich bei:
    - Modbus-Timeouts (alte Werte könnten ungültig sein)
    - Connection-Errors (Verbindung unterbrochen)
    - Inverter-Neustart (Counter könnten resetten)

    Beispiel im Error-Handler:
        except ConnectionError:
            reset_filter()  # Alle gespeicherten Werte verwerfen
            reconnect()
    """
    global _filter_instance
    if _filter_instance is not None:
        _filter_instance.reset()
