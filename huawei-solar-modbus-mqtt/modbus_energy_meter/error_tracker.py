# modbus_energy_meter/error_tracker.py

"""
Connection Error Tracker für intelligentes Fehler-Logging.

Dieses Modul implementiert einen intelligenten Error-Tracker der Verbindungsfehler
aggregiert und Log-Spam vermeidet. Statt bei jedem fehlgeschlagenen Cycle denselben
Fehler zu loggen, werden Fehler nach Typ gruppiert und nur in konfigurierbaren
Intervallen ausgegeben.

Problem ohne Tracker:
    Bei einem 10-minütigen Inverter-Ausfall mit 30s Poll-Interval würden 20
    identische Error-Logs entstehen, die das Log überschwemmen und wichtige
    andere Meldungen überdecken.

Lösung mit Tracker:
    - Ersten Fehler eines Typs sofort loggen (ERROR-Level)
    - Wiederholte Fehler nur intern zählen (kein Log)
    - Alle X Sekunden aggregiertes Update (WARNING-Level mit Statistik)
    - Bei Recovery einmalige Zusammenfassung (INFO-Level mit Downtime)

Features:
    - Fehler-Aggregation nach Typ (timeout, modbus_exception, connection_refused, ...)
    - Konfigurierbare Log-Intervalle (default: 60s)
    - Downtime-Tracking (Zeit zwischen erstem Fehler und Recovery)
    - Fehler-Statistiken (Anzahl Versuche, Fehlertypen)
    - Recovery-Logging mit Zusammenfassung

Verwendung:
    >>> tracker = ConnectionErrorTracker(log_interval=60)
    >>>
    >>> # In Error-Handler:
    >>> if tracker.track_error("timeout", str(exc)):
    >>>     # Fehler wurde geloggt (erster Auftritt oder Interval abgelaufen)
    >>>     pass
    >>>
    >>> # Nach erfolgreichem Cycle:
    >>> tracker.mark_success()  # Loggt Recovery falls es Fehler gab
    >>>
    >>> # Für Diagnostik:
    >>> status = tracker.get_status()
    >>> print(f"Active errors: {status['active_errors']}")

Beispiel-Log-Sequenz:
    [10:00:00] ERROR - Connection error: timeout - Connection timeout
    [10:01:00] WARNING - Still failing: timeout (2 attempts in 60s)
    [10:02:00] WARNING - Still failing: timeout (4 attempts in 120s)
    [10:03:00] INFO - Connection restored after 180s (6 failed attempts, 1 error types)
"""

import logging
import time
from typing import Dict, Optional

logger = logging.getLogger("huawei.errors")


class ConnectionErrorTracker:
    """
    Trackt und aggregiert Verbindungsfehler um Log-Spam zu reduzieren.

    Problem ohne Tracker:
    Bei Verbindungsproblemen würde jeder Poll-Cycle (z.B. alle 30s) denselben
    Fehler loggen → Log wird unübersichtlich und wichtige Meldungen gehen unter.

    Lösung mit Tracker:
    - Ersten Fehler eines Typs sofort loggen
    - Wiederholte Fehler nur aggregiert alle X Sekunden loggen
    - Bei Recovery einmalig Zusammenfassung loggen (Downtime, Fehleranzahl)

    Beispiel:
        Bei 10-minütigem Ausfall mit 30s Poll-Interval würden ohne Tracker
        20 identische Error-Logs entstehen. Mit Tracker: 1x beim Start,
        1-2x während (je nach log_interval), 1x bei Recovery.
    """

    def __init__(self, log_interval: int = 60):
        """
        Initialisiert den Error-Tracker.

        Args:
            log_interval: Mindestabstand in Sekunden zwischen wiederholten
                         Logs desselben Fehlertyps. Standard: 60s bedeutet
                         maximal 1 Log pro Minute für denselben Fehler.

        Beispiel:
            >>> tracker = ConnectionErrorTracker(log_interval=60)
            >>> # Fehler 1: wird geloggt
            >>> tracker.track_error("timeout", "Connection timeout")
            >>> # Fehler 2 nach 10s: wird NICHT geloggt (< 60s)
            >>> # Fehler 3 nach 70s: wird geloggt (> 60s)
        """
        self.log_interval = log_interval

        # Dict mit Fehler-Informationen pro error_type
        # Structure: {
        #   "timeout": {
        #     "first_seen": 1706184000.0,      # Timestamp erstes Auftreten
        #     "last_logged": 1706184000.0,     # Timestamp letztes Logging
        #     "count": 5,                      # Anzahl Wiederholungen
        #     "details": "Connection timeout"  # Fehlerdetails
        #   }
        # }
        self.errors: Dict[str, Dict] = {}

        # Timestamp des letzten erfolgreichen Cycles (für Downtime-Berechnung)
        self.last_success_time: Optional[float] = None

    def track_error(self, error_type: str, details: str = "") -> bool:
        """
        Trackt ein Fehler-Auftreten und entscheidet ob geloggt werden soll.

        Logik:
        1. Erster Fehler eines Typs → Sofort loggen (ERROR-Level)
        2. Wiederholter Fehler innerhalb log_interval → Nicht loggen (nur zählen)
        3. Wiederholter Fehler nach log_interval → Aggregiert loggen (WARNING-Level)

        Args:
            error_type: Typ des Fehlers (z.B. "timeout", "modbus_exception")
                       Wird als Key für Aggregation verwendet
            details: Optionale Details zum Fehler (z.B. Exception-Message)

        Returns:
            True wenn Fehler geloggt wurde (erster Auftritt oder Interval abgelaufen)
            False wenn Fehler nur intern gezählt wurde (Log-Spam-Vermeidung)

        Beispiel:
            >>> tracker = ConnectionErrorTracker(log_interval=60)
            >>> # Erster Timeout → True, wird geloggt
            >>> tracker.track_error("timeout", "No response")
            True  # Log: "Connection error: timeout - No response"

            >>> # 10 Sekunden später, gleicher Fehler → False, wird NICHT geloggt
            >>> time.sleep(10)
            >>> tracker.track_error("timeout", "No response")
            False  # Nur interner Counter erhöht

            >>> # 65 Sekunden später → True, wird aggregiert geloggt
            >>> time.sleep(55)
            >>> tracker.track_error("timeout", "No response")
            True  # Log: "Still failing: timeout (3 attempts in 65s)"
        """
        now = time.time()

        if error_type not in self.errors:
            # Erster Auftritt dieses Fehlertyps
            # → Neue Error-Info erstellen und sofort loggen
            self.errors[error_type] = {
                "first_seen": now,  # Timestamp für Downtime-Berechnung
                "last_logged": now,  # Timestamp für log_interval Check
                "count": 1,  # Zähler initialisieren
                "details": details,  # Details speichern
            }
            # Erster Fehler ist wichtig → ERROR-Level
            logger.error(f"Connection error: {error_type} - {details}")
            return True

        # Fehlertyp existiert bereits → Update
        error_info = self.errors[error_type]
        error_info["count"] += 1  # Zähler erhöhen

        # Prüfen ob log_interval abgelaufen ist
        # Beispiel: last_logged=10:00:00, now=10:01:30, interval=60
        # → 90s vergangen, > 60s → loggen
        if now - error_info["last_logged"] > self.log_interval:
            # Interval abgelaufen → Aggregiertes Update loggen
            duration = now - error_info["first_seen"]
            # WARNING statt ERROR (wir wissen bereits dass es ein Problem gibt)
            logger.warning(
                f"Still failing: {error_type} "
                f"({error_info['count']} attempts in {int(duration)}s)"
            )
            error_info["last_logged"] = now  # Timestamp aktualisieren
            return True

        # Innerhalb log_interval → Nicht loggen (nur gezählt)
        return False

    def mark_success(self) -> None:
        """
        Markiert erfolgreiche Verbindung und loggt Recovery-Info.

        Wird nach jedem erfolgreichen Cycle aufgerufen. Wenn vorher Fehler
        aufgetreten waren, wird eine Zusammenfassung geloggt (Downtime,
        Anzahl Fehler-Versuche, Anzahl verschiedener Fehlertypen).

        Danach wird der Error-State zurückgesetzt für den nächsten Fehlerfall.

        Beispiel:
            Bei 5-minütiger Downtime mit 3 verschiedenen Fehlertypen und
            insgesamt 15 fehlgeschlagenen Versuchen:

            Log: "Connection restored after 300s (15 failed attempts, 3 error types)"

        Dies ist wertvoll für:
        - Monitoring (wie lange war System offline?)
        - Debugging (wie viele Versuche wurden gemacht?)
        - Statistik (wie stabil ist die Verbindung?)
        """
        if self.errors:
            # Es gab Fehler → Recovery-Info loggen

            # Gesamtanzahl aller fehlgeschlagenen Versuche über alle Fehlertypen
            # Beispiel: {"timeout": {"count": 10}, "modbus_exception": {"count": 5}}
            # → total_errors = 15
            total_errors = sum(e["count"] for e in self.errors.values())

            # Frühester Fehlerzeitpunkt = Start der Downtime
            # Beispiel: {"timeout": {"first_seen": 100}, "connection": {"first_seen": 120}}
            # → first_error = 100
            first_error = min(e["first_seen"] for e in self.errors.values())

            # Downtime = Zeit zwischen erstem Fehler und jetzt
            downtime = time.time() - first_error

            # INFO-Level, da Recovery eine positive Nachricht ist
            logger.info(
                f"Connection restored after {int(downtime)}s "
                f"({total_errors} failed attempts, {len(self.errors)} error types)"
            )

            # Error-State zurücksetzen für nächsten Fehlerfall
            # Dictionary leeren = alle Error-Infos verwerfen
            self.errors.clear()

        # Erfolgs-Timestamp aktualisieren (für Statistik/Monitoring)
        self.last_success_time = time.time()

    def get_status(self) -> Dict:
        """
        Gibt aktuellen Error-Status für Diagnostik zurück.

        Nützlich für:
        - Heartbeat-Logging (zeigt Error-Info bei Offline-Status)
        - Health-Checks (externe Monitoring-Tools)
        - Debug-Ausgaben (aktueller Fehlerzustand)

        Returns:
            Dict mit drei Keys:
            - active_errors: Anzahl verschiedener aktiver Fehlertypen
            - total_failures: Gesamtanzahl fehlgeschlagener Versuche
            - last_success: Timestamp des letzten erfolgreichen Cycles (oder None)

        Beispiel:
            >>> tracker.get_status()
            {
                'active_errors': 2,           # 2 verschiedene Fehlertypen aktiv
                'total_failures': 15,         # Insgesamt 15 fehlgeschlagene Versuche
                'last_success': 1706184000.0  # Letzter Erfolg vor 5 Minuten
            }

        Verwendung in main.py:
            ```python
            error_status = error_tracker.get_status()
            logger.warning(
                f"Inverter offline | "
                f"Failed attempts: {error_status['total_failures']} | "
                f"Error types: {error_status['active_errors']}"
            )
            ```
        """
        return {
            # Anzahl unterschiedlicher Fehlertypen (len von errors Dict)
            "active_errors": len(self.errors),
            # Summe aller counts über alle Fehlertypen
            # sum([5, 3, 7]) = 15 fehlgeschlagene Versuche total
            "total_failures": sum(e["count"] for e in self.errors.values()),
            # Timestamp oder None (None = noch kein erfolgreicher Cycle)
            "last_success": self.last_success_time,
        }
