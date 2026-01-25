# modbus_energy_meter/main.py

"""
Hauptmodul des Huawei Solar Modbus-to-MQTT Add-ons.

Dieser Service liest zyklisch Daten vom Huawei SUN2000 Inverter per Modbus TCP,
transformiert sie in MQTT-Format und publiziert sie inklusive Home Assistant
Discovery-Konfiguration.

Architektur:
    Modbus Read → Transform (mit Filter) → MQTT Publish → Repeat

Features:
    - Asynchroner Modbus-Read für bessere Performance
    - Intelligentes Error-Tracking zur Log-Spam-Vermeidung
    - total_increasing Filter gegen falsche Counter-Resets
    - Heartbeat-Monitoring mit konfigurierbarem Timeout
    - MQTT Discovery für automatische Home Assistant Integration
    - Performance-Monitoring mit Zeitmessungen
"""

import asyncio
import logging
import os
import sys
import time
from typing import Dict, Any

from huawei_solar import AsyncHuaweiSolar
from .error_tracker import ConnectionErrorTracker
from .config.registers import ESSENTIAL_REGISTERS
from .mqtt_client import (
    connect_mqtt,
    disconnect_mqtt,
    publish_status,
    publish_discovery_configs,
    publish_data,
)
from .transform import transform_data
from .total_increasing_filter import get_filter, reset_filter

try:
    from pymodbus.exceptions import ModbusException
    from pymodbus.pdu import ExceptionResponse

    MODBUS_EXCEPTIONS = (ModbusException, ExceptionResponse)
except ImportError:
    # Fallback wenn pymodbus nicht verfügbar (sollte nie passieren,
    # aber macht Code robuster bei Library-Problemen)
    MODBUS_EXCEPTIONS = ()

# Logger für dieses Modul
logger = logging.getLogger("huawei.main")

# Error Tracker instanziieren - aggregiert Fehler über 60s Intervall
# Verhindert Log-Spam bei längeren Verbindungsausfällen
error_tracker = ConnectionErrorTracker(log_interval=60)

# Globaler Timestamp des letzten erfolgreichen Reads
# Wird von main_once() gesetzt und von heartbeat() geprüft
# 0 = noch kein erfolgreicher Read (Startup-Phase)
LAST_SUCCESS = 0


def init_logging() -> None:
    """
    Initialisiert komplettes Logging-System mit ENV-Konfiguration.

    Konfiguriert drei Logger-Hierarchien:
    1. Root Logger - für alle eigenen Module (huawei.*)
    2. pymodbus Logger - für Modbus-Library (meist zu verbose)
    3. huawei_solar Logger - für Inverter-Library

    Wird einmalig beim Start aufgerufen, bevor irgendwas anderes passiert.
    """
    log_level = _parse_log_level()
    _setup_root_logger(log_level)
    _configure_pymodbus(log_level)
    _configure_huawei_solar(log_level)

    logger.info(f"Logging initialized: {logging.getLevelName(log_level)}")


def _parse_log_level() -> int:
    """
    Parsed Log-Level aus ENV-Variablen mit Fallback auf INFO.

    Unterstützt zwei Konfigurationsmethoden:
    1. HUAWEI_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR (neue Methode)
    2. HUAWEI_MODBUS_DEBUG=yes (Legacy für Abwärtskompatibilität)

    Returns:
        logging.DEBUG (10), INFO (20), WARNING (30) oder ERROR (40)

    Beispiel ENV-Konfiguration:
        HUAWEI_LOG_LEVEL=DEBUG    → Zeigt alle Details, Register-Reads, Timings
        HUAWEI_LOG_LEVEL=INFO     → Zeigt Cycle-Zusammenfassungen, Errors
        HUAWEI_LOG_LEVEL=WARNING  → Zeigt nur Warnungen und Fehler
        HUAWEI_LOG_LEVEL=ERROR    → Zeigt nur Fehler
    """
    level_str = os.environ.get("HUAWEI_LOG_LEVEL", "INFO").upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }

    # Legacy-Support: HUAWEI_MODBUS_DEBUG=yes aktiviert DEBUG-Modus
    # Wird von älteren Versionen noch verwendet
    if os.environ.get("HUAWEI_MODBUS_DEBUG") == "yes":
        return logging.DEBUG

    return level_map.get(level_str, logging.INFO)


def _setup_root_logger(level: int) -> None:
    """
    Konfiguriert Root Logger mit einheitlichem Format für Container-Umgebung.

    Format: "YYYY-MM-DD HH:MM:SS - logger.name - LEVEL - message"
    Beispiel: "2026-01-25 12:22:00 - huawei.main - INFO - Connected"

    Output geht zu stdout (nicht stderr), damit Docker/Hassio die Logs
    korrekt abfangen kann. Home Assistant Add-on Logs zeigen dann
    genau diese Ausgabe.

    Args:
        level: Logging-Level für Root Logger (alle huawei.* Logger)

    Hinweis:
        Handler werden explizit cleared, damit bei Reinitialisierung
        (z.B. Tests) keine doppelten Log-Zeilen entstehen.
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Handler clearen und neu erstellen
    # Wichtig bei Tests oder wenn init_logging() mehrfach aufgerufen wird
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # StreamHandler für stdout (Docker/Hassio Logging)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root.addHandler(handler)


def _configure_pymodbus(level: int) -> None:
    """
    Konfiguriert pymodbus Logger - standardmäßig auf ERROR beschränken.

    Problem: pymodbus ist sehr verbose und loggt bei INFO/DEBUG zu viele
    technische Details (Register-Adressen, Byte-Arrays, Protokoll-Details).

    Lösung: Standardmäßig nur ERROR-Level, außer bei explizitem DEBUG-Modus.

    Args:
        level: Haupt-Log-Level (aus HUAWEI_LOG_LEVEL)

    Beispiel bei level=INFO:
        pymodbus Logger wird auf ERROR gesetzt → keine Register-Details

    Beispiel bei level=DEBUG:
        pymodbus Logger wird auf DEBUG gesetzt → alle Modbus-Protokoll-Details
        Nützlich bei Verbindungsproblemen oder Register-Debugging
    """
    pymodbus_logger = logging.getLogger("pymodbus")
    # Immer ERROR, außer wenn Hauptlevel DEBUG ist
    pymodbus_logger.setLevel(logging.ERROR if level != logging.DEBUG else logging.DEBUG)


def _configure_huawei_solar(level: int) -> None:
    """
    Konfiguriert huawei_solar Library Logger - Tracebacks unterdrücken.

    Die huawei_solar Library loggt interne State-Änderungen und Register-Mappings.
    Bei normalem Betrieb ist das zu detailliert, nur bei Debugging relevant.

    Args:
        level: Haupt-Log-Level (aus HUAWEI_LOG_LEVEL)

    Bei INFO/WARNING/ERROR:
        huawei_solar auf ERROR → Nur echte Library-Fehler

    Bei DEBUG:
        huawei_solar auf DEBUG → Alle Library-Internals
        Zeigt z.B. wie Register-Namen zu Modbus-Adressen gemappt werden
    """
    hs_logger = logging.getLogger("huawei_solar")
    # Bei INFO nur WARNING+, bei DEBUG alles
    if level == logging.DEBUG:
        hs_logger.setLevel(logging.DEBUG)
    else:
        hs_logger.setLevel(logging.ERROR)  # Nur echte Errors


def heartbeat(topic: str) -> None:
    """
    Überwacht erfolgreiche Reads und setzt Status auf offline bei Timeout.

    Wird nach jedem Cycle aufgerufen (auch bei Fehlern) und prüft ob
    LAST_SUCCESS innerhalb des konfigurierbaren Timeouts liegt.

    Logik:
    1. LAST_SUCCESS == 0 → Startup, noch kein Check
    2. Zeit seit LAST_SUCCESS < timeout → Alles OK (nur DEBUG-Log)
    3. Zeit seit LAST_SUCCESS > timeout → Offline-Status setzen (WARNING-Log)

    Das WARNING wird nur einmal beim Übergang zu offline geloggt, nicht
    bei jedem Cycle (sonst Log-Spam).

    Args:
        topic: MQTT-Topic für Status-Publishing (z.B. "huawei-solar/status")

    ENV-Konfiguration:
        HUAWEI_STATUS_TIMEOUT: Sekunden bis Offline-Status (default: 180)

    Beispiel:
        STATUS_TIMEOUT=180, LAST_SUCCESS vor 200s
        → Log: "Inverter offline for 200s (timeout: 180s)"
        → MQTT: "huawei-solar/status" = "offline"
        → Home Assistant: binary_sensor.huawei_solar_status = OFF
    """
    global LAST_SUCCESS
    timeout = int(os.environ.get("HUAWEI_STATUS_TIMEOUT", "180"))

    # Beim ersten Start (noch kein erfolgreicher Read)
    # LAST_SUCCESS ist 0 → kein Timeout-Check möglich
    if LAST_SUCCESS == 0:
        return

    offline_duration = time.time() - LAST_SUCCESS

    if offline_duration > timeout:
        # Nur einmal loggen beim Übergang zu offline (nicht bei jedem Cycle)
        # Check: offline_duration < timeout + 5 bedeutet "gerade eben offline geworden"
        # (5s Toleranz wegen Cycle-Timing)
        if offline_duration < timeout + 5:
            # Zeige Error-Statistiken im Log (Anzahl Fehler, Fehlertypen)
            error_status = error_tracker.get_status()
            logger.warning(
                f"Inverter offline for {int(offline_duration)}s "
                f"(timeout: {timeout}s) | "
                f"Failed attempts: {error_status['total_failures']} | "
                f"Error types: {error_status['active_errors']}"
            )
        # Status auf offline setzen (wird zu MQTT publiziert)
        # Home Assistant Binary Sensor reagiert darauf
        publish_status("offline", topic)
    else:
        # Alles OK - nur DEBUG-Level für Monitoring
        logger.debug(f"Heartbeat OK: {offline_duration:.1f}s since last success")


def log_cycle_summary(
    cycle_num: int, timings: Dict[str, float], data: Dict[str, Any]
) -> None:
    """
    Loggt Cycle-Zusammenfassung - human-readable oder JSON für Monitoring-Tools.

    Zwei Output-Modi über ENV-Variable HUAWEI_LOG_FORMAT:

    1. Human-readable (default):
       "📊 Published - PV: 4500W | AC Out: 4200W | Grid: -200W | Battery: 800W"
       Gut lesbar für Menschen, inkl. Emojis

    2. JSON (HUAWEI_LOG_FORMAT=json):
       {"cycle": 42, "timestamp": 1706184000, "timings": {...}, "power": {...}}
       Strukturiert für Monitoring-Tools, Grafana, etc.

    Bei DEBUG-Level zusätzlich:
       Alle 20 Zyklen Filter-Statistik ausgeben (wie oft wurden Werte gefiltert)
       Nützlich um Modbus-Probleme zu erkennen

    Args:
        cycle_num: Aktuelle Cycle-Nummer seit Start (fortlaufend)
        timings: Dict mit Zeitmessungen {modbus, transform, mqtt, total}
        data: MQTT-Daten (für Power-Werte)

    Beispiel JSON-Output:
        {
          "cycle": 42,
          "timestamp": 1706184000.5,
          "timings": {"modbus": 2.1, "transform": 0.005, "mqtt": 0.194, "total": 2.3},
          "power": {"pv": 4500, "ac_out": 4200, "grid": -200, "battery": 800}
        }
    """
    if os.environ.get("HUAWEI_LOG_FORMAT") == "json":
        import json

        # JSON-Format für Machine-Parsing (Monitoring, Grafana)
        summary = {
            "cycle": cycle_num,
            "timestamp": time.time(),
            "timings": timings,
            "power": {
                "pv": data.get("power_input", 0),
                "ac_out": data.get("power_active", 0),
                "grid": data.get("meter_power_active", 0),
                "battery": data.get("battery_power", 0),
            },
        }
        logger.info(json.dumps(summary))
    else:
        # Filter-Statistik für aktuellen Cycle holen
        filter_stats = get_filter().get_stats()
        filter_indicator = ""

        # Wenn in diesem Cycle gefiltert wurde, Indikator hinzufügen
        if filter_stats:
            total_filtered = sum(filter_stats.values())
            filter_indicator = f" 🔍[{total_filtered} filtered]"

        # Standard human-readable log mit Emojis und Einheiten
        # Zeigt die vier wichtigsten Power-Werte im Überblick
        logger.info(
            "📊 Published - PV: %dW | AC Out: %dW | Grid: %dW | Battery: %dW%s",
            data.get("power_input", 0),
            data.get("power_active", 0),
            data.get("meter_power_active", 0),
            data.get("battery_power", 0),
            filter_indicator,
        )

        # Alle 20 Zyklen Filter-Zusammenfassung zeigen (auch wenn 0)
        if cycle_num % 20 == 0:
            total_filtered = sum(filter_stats.values()) if filter_stats else 0

            if total_filtered > 0:
                # Es wurde gefiltert → Details zeigen
                logger.info(
                    f"└─> 🔍 Filter summary (last 20 cycles): {total_filtered} values filtered | "
                    f"Details: {dict(filter_stats)}"
                )
            else:
                # Nichts gefiltert → Bestätigung dass Filter funktioniert
                logger.info(
                    "└─> 🔍 Filter summary (last 20 cycles): 0 values filtered - all data valid ✓"
                )

            # Stats für nächste Periode zurücksetzen
            get_filter().reset_stats()

        # DEBUG: Detaillierte Filter-Info bei jedem Filter-Event
        elif filter_stats and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"🔍 Filter details: {dict(filter_stats)}")


async def read_registers(client: AsyncHuaweiSolar) -> Dict[str, Any]:
    """
    Liest Essential Registers sequentiell vom Inverter via Modbus TCP.

    Liest alle in ESSENTIAL_REGISTERS (config/registers.py) definierten
    Register einzeln. Fehler bei einzelnen Registern werden gefangen,
    damit der Read weiterlaufen kann (partial success).

    Typische Read-Zeit: 2-5 Sekunden für 58 Register

    Args:
        client: AsyncHuaweiSolar Client (muss bereits verbunden sein)

    Returns:
        Dict mit erfolgreich gelesenen Register-Werten
        Format: {"activepower": RegisterValue, "inputpower": RegisterValue, ...}

    Raises:
        Exception: Bei totalem Verbindungsverlust (kein einziges Register lesbar)

    Beispiel:
        >>> data = await read_registers(client)
        >>> # Log: "Essential read: 2.1s (58/58)"
        >>> data["activepower"]  # RegisterValue Objekt von huawei_solar
        <RegisterValue: 4500 W>

    Hinweis:
        Einzelne fehlende Register (z.B. Meter bei Systemen ohne) werden
        nur im DEBUG-Log erwähnt, nicht als Fehler behandelt.
    """
    logger.debug(f"Reading {len(ESSENTIAL_REGISTERS)} essential registers")

    start = time.time()
    data = {}
    successful = 0

    # Sequentieller Read - einzelne Fehler werden gefangen
    # Alternative wäre parallel (gather), aber sequentiell ist robuster
    for name in ESSENTIAL_REGISTERS:
        try:
            # client.get() ist async und gibt RegisterValue-Objekt zurück
            data[name] = await client.get(name)
            successful += 1
        except Exception:
            # Einzelne fehlende Register nur im DEBUG-Log
            # Grund: Nicht alle Inverter haben alle Register (z.B. kein Meter)
            logger.debug(f"Failed {name}")

    duration = time.time() - start
    # INFO-Level für Performance-Monitoring
    # Beispiel: "Essential read: 2.1s (58/58)" = alle Register erfolgreich
    # Beispiel: "Essential read: 2.3s (55/58)" = 3 Register fehlen (z.B. kein Meter)
    logger.info(
        "Essential read: %.1fs (%d/%d)", duration, successful, len(ESSENTIAL_REGISTERS)
    )

    return data


def is_modbus_exception(exc: Exception) -> bool:
    """
    Prüft ob Exception eine Modbus-spezifische Exception ist.

    Wird verwendet um zwischen echten Modbus-Verbindungsfehlern
    (ModbusException, ExceptionResponse) und anderen Fehlern
    (z.B. ValueError, RuntimeError) zu unterscheiden.

    Wichtig für:
    - Korrekte Fehler-Klassifizierung im Error-Tracker
    - Unterschiedliches Logging (WARNING vs ERROR)
    - Entscheidung über Reconnect-Strategie

    Args:
        exc: Exception-Objekt das geprüft werden soll

    Returns:
        True wenn ModbusException oder ExceptionResponse
        False bei allen anderen Exception-Typen

    Beispiel:
        >>> try:
        ...     data = await read_registers(client)
        ... except Exception as e:
        ...     if is_modbus_exception(e):
        ...         logger.warning("Modbus read failed")  # Erwartbar
        ...     else:
        ...         logger.error("Unexpected error")      # Unerwartete

    Hinweis:
        Falls pymodbus nicht importiert werden konnte (MODBUS_EXCEPTIONS = ()),
        gibt diese Funktion immer False zurück (Safety-First).
    """
    if not MODBUS_EXCEPTIONS:
        return False
    return isinstance(exc, MODBUS_EXCEPTIONS)


async def main_once(client: AsyncHuaweiSolar, cycle_num: int) -> None:
    """
    Führt einen kompletten Read-Transform-Publish Cycle aus.

    Workflow:
    1. Modbus Read - Essential Registers vom Inverter lesen (2-5s)
    2. Transform - Register in MQTT-Format umwandeln (< 0.01s)
       ↳ Hier läuft auch der total_increasing Filter!
    3. MQTT Publish - Daten zum Broker senden (< 0.2s)
    4. Logging - Timings und Zusammenfassung ausgeben
    5. Performance-Check - Warnung bei zu langsamen Cycles

    Bei Erfolg: LAST_SUCCESS wird aktualisiert (für Heartbeat)
    Bei Fehler: Exception wird durchgereicht zu main() Error-Handler

    Args:
        client: AsyncHuaweiSolar Client (muss verbunden sein)
        cycle_num: Aktuelle Cycle-Nummer (fortlaufend seit Start)

    Raises:
        RuntimeError: Wenn HUAWEI_MODBUS_MQTT_TOPIC nicht gesetzt
        Exception: Bei Modbus-Read-Fehler (wird in main() gefangen)

    Globale Seiteneffekte:
        - LAST_SUCCESS wird auf current timestamp gesetzt
        - MQTT-Daten werden publiziert
        - Logs werden ausgegeben

    Performance-Beispiel:
        Modbus: 2.1s (58/58 Register)
        Transform: 0.005s (Mapping + Filter)
        MQTT: 0.194s (Publish + Wait)
        Total: 2.3s
    """
    global LAST_SUCCESS
    topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
    if not topic:
        raise RuntimeError("HUAWEI_MODBUS_MQTT_TOPIC not set")

    start = time.time()
    logger.debug("Starting cycle")

    # === PHASE 1: Modbus Read ===
    modbus_start = time.time()
    try:
        data = await read_registers(client)
        modbus_duration = time.time() - modbus_start
    except Exception as e:
        # Unterscheide zwischen Modbus-Fehler und anderen Fehlern
        # für besseres Logging
        if is_modbus_exception(e):
            # Modbus-Fehler sind "erwartbar" bei Verbindungsproblemen
            logger.warning(f"Modbus read failed after {time.time() - start:.1f}s: {e}")
        else:
            # Andere Fehler sind unerwartet und schwerwiegender
            logger.error(f"Read error: {e}")
        raise  # Exception durchreichen zu main() Error-Handler

    # Sanity-Check: Mindestens ein Register muss gelesen worden sein
    if not data:
        logger.warning("No data")
        return

    # === PHASE 2: Transform ===
    # Hier passiert:
    # 1. Register-Namen mappen (activepower → power_active)
    # 2. RegisterValue-Objekte extrahieren (value-Attribut)
    # 3. total_increasing Filter anwenden (verhindert falsche Drops)
    # 4. None-Werte entfernen
    # 5. Timestamp hinzufügen
    transform_start = time.time()
    mqtt_data = transform_data(data)
    transform_duration = time.time() - transform_start

    # === PHASE 3: MQTT Publish ===
    mqtt_start = time.time()
    publish_data(mqtt_data, topic)
    mqtt_duration = time.time() - mqtt_start

    # Erfolg markieren für Heartbeat
    LAST_SUCCESS = time.time()
    cycle_duration = time.time() - start

    # === PHASE 4: Logging ===
    timings = {
        "modbus": modbus_duration,
        "transform": transform_duration,
        "mqtt": mqtt_duration,
        "total": cycle_duration,
    }

    log_cycle_summary(cycle_num, timings, mqtt_data)

    # Debug-Details nur bei DEBUG-Level (detaillierte Zeitmessungen)
    logger.debug(
        "Cycle: %.1fs (Modbus: %.1fs, Transform: %.2fs, MQTT: %.2fs)",
        cycle_duration,
        modbus_duration,
        transform_duration,
        mqtt_duration,
    )

    # === PHASE 5: Performance-Check ===
    # Warnung wenn Cycle zu lange dauert (> 80% vom poll_interval)
    # Beispiel: poll_interval=30s, cycle=25s → 83% → WARNING
    # Grund: Nächster Cycle wird verzögert, Daten kommen nicht rechtzeitig
    poll_interval = int(os.environ.get("HUAWEI_POLL_INTERVAL", "30"))
    if cycle_duration > poll_interval * 0.8:
        logger.warning(
            "Cycle %.1fs > 80%% poll_interval (%ds)", cycle_duration, poll_interval
        )


async def main() -> None:
    """
    Haupt-Loop mit Error-Handling, automatischer Wiederverbindung und Filter-Reset.

    Lifecycle:
    1. Logging initialisieren
    2. ENV-Variablen validieren (Host, Port, Topic)
    3. MQTT verbinden (persistent über gesamte Laufzeit)
    4. Discovery publizieren (erstellt Home Assistant Entities)
    5. Modbus Client erstellen und verbinden
    6. Endlos-Loop: Cycle → Sleep → Repeat

    Error-Handling-Strategie:
    - TimeoutError → Reset Filter, 10s Pause, Retry
    - ModbusException → Reset Filter, 10s Pause, Retry
    - ConnectionRefusedError → Reset Filter, 10s Pause, Retry
    - Unbekannte Fehler → Log mit Traceback, Reset Filter, 10s Pause, Retry

    Warum Filter-Reset bei JEDEM Fehler?
    Nach Verbindungsproblemen könnten:
    - Inverter neu gestartet sein (Counter resetten)
    - Teilweise Register gelesen sein (inkonsistente Werte)
    - Alle gespeicherten Werte veraltet sein
    → Sicherer neue Filter-Session zu starten

    ENV-Variablen:
        HUAWEI_MODBUS_HOST: IP des Inverters (required)
        HUAWEI_MODBUS_PORT: Modbus Port (default: 502)
        HUAWEI_SLAVE_ID: Modbus Slave ID (default: 1, manchmal 0 oder 16)
        HUAWEI_MODBUS_MQTT_TOPIC: MQTT Basis-Topic (required)
        HUAWEI_POLL_INTERVAL: Sekunden zwischen Cycles (default: 30)

    MQTT Topics:
        {topic}: JSON mit allen Sensordaten
        {topic}/status: "online" oder "offline"
        homeassistant/sensor/{device}/*/config: Discovery-Configs

    Graceful Shutdown:
        - Bei SIGTERM (Docker Stop): Status auf offline, MQTT disconnect
        - Bei Ctrl+C (lokal): Status auf offline, MQTT disconnect
        - Bei Fatal Error: Status auf offline, MQTT disconnect, exit(1)
    """
    init_logging()

    # === ENV-Variablen Validierung ===
    # Pflichtfelder prüfen, sonst sofort abbrechen
    topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
    if not topic:
        logger.error("HUAWEI_MODBUS_MQTT_TOPIC missing")
        sys.exit(1)

    host = os.environ.get("HUAWEI_MODBUS_HOST")
    if not host:
        logger.error("HUAWEI_MODBUS_HOST missing")
        sys.exit(1)

    port = int(os.environ.get("HUAWEI_MODBUS_PORT", "502"))
    slave_id = int(os.environ.get("HUAWEI_SLAVE_ID", "1"))

    logger.info("🚀 Huawei Solar → MQTT starting")
    logger.debug(f"Host={host}:{port}, Slave={slave_id}, Topic={topic}")

    # === MQTT Verbindung (persistent) ===
    # MQTT wird einmal beim Start verbunden und bleibt für gesamte
    # Laufzeit connected. Nur Modbus reconnected bei Fehlern.
    try:
        connect_mqtt()
        import time

        # Kurze Wartezeit nach Connect für Stabilität
        # Verhindert Race-Condition bei schnellem Publish nach Connect
        time.sleep(1)
    except Exception as e:
        logger.error(f"MQTT connect failed: {e}")
        sys.exit(1)

    # Initial Status: offline (wird bei erstem erfolgreichen Read auf online gesetzt)
    # Wichtig für Home Assistant Binary Sensor
    publish_status("offline", topic)

    # === Discovery publizieren ===
    # Erstellt einmalig alle MQTT-Sensoren in Home Assistant
    # Discovery-Configs werden nur beim Start gesendet, nicht bei jedem Cycle
    try:
        publish_discovery_configs(topic)
        logger.info("✅ Discovery published")
    except Exception as e:
        # Discovery-Fehler ist nicht fatal, weitermachen
        # Sensoren können auch manuell in HA angelegt werden
        logger.error(f"Discovery failed: {e}")

    # === Modbus Client erstellen ===
    try:
        client = await AsyncHuaweiSolar.create(host, port, slave_id)
        logger.info(f"🔌 Connected (Slave ID: {slave_id})")
        publish_status("online", topic)
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        disconnect_mqtt()
        return

    # === Main Loop ===
    poll_interval = int(os.environ.get("HUAWEI_POLL_INTERVAL", "30"))
    logger.info(f"⏱️  Poll interval: {poll_interval}s")

    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            logger.debug(f"Cycle #{cycle_count}")

            try:
                # === Cycle ausführen ===
                # Enthält: Modbus Read + Transform (mit Filter!) + MQTT Publish
                await main_once(client, cycle_count)
                error_tracker.mark_success()
                publish_status("online", topic)

            except asyncio.TimeoutError as e:
                # Timeout bei Modbus-Read (Netzwerk langsam, Inverter antwortet nicht)
                error_tracker.track_error("timeout", str(e))
                publish_status("offline", topic)
                # Filter zurücksetzen weil nach Timeout alle Werte ungültig sein könnten
                reset_filter()
                logger.debug("🔄 Filter reset due to timeout")
                await asyncio.sleep(10)  # Kurze Pause vor Retry

            except (ModbusException, ExceptionResponse) as e:  # type: ignore[misc]
                # Modbus-Protokoll-Fehler (CRC-Fehler, ungültige Response, etc.)
                error_tracker.track_error("modbus_exception", str(e))
                publish_status("offline", topic)
                # Filter zurücksetzen weil Modbus-Fehler zu partiellen Reads führen können
                reset_filter()
                logger.debug("🔄 Filter reset due to Modbus exception")
                await asyncio.sleep(10)

            except ConnectionRefusedError as e:
                # Verbindung verweigert (Port zu, Firewall, Inverter aus, etc.)
                error_tracker.track_error("connection_refused", f"Errno {e.errno}")
                publish_status("offline", topic)
                # Filter zurücksetzen weil nach Reconnect Counter resetten könnten
                reset_filter()
                logger.debug("🔄 Filter reset due to connection error")
                await asyncio.sleep(10)

            except Exception as e:
                # Unbekannte/unerwartete Fehler mit vollem Traceback loggen
                error_type = type(e).__name__
                if error_tracker.track_error(error_type, str(e)):
                    # Nur beim ersten Auftreten Traceback loggen (nicht bei Wiederholung)
                    logger.error(f"Unexpected: {error_type}", exc_info=True)
                publish_status("offline", topic)
                # Filter zurücksetzen aus Vorsicht (unbekannter Fehler könnte alles sein)
                reset_filter()
                logger.debug("🔄 Filter reset due to unexpected error")
                await asyncio.sleep(10)

            # Heartbeat prüft ob Timeout überschritten (setzt ggf. offline)
            heartbeat(topic)

            # Warten bis nächster Cycle (poll_interval)
            # Cycle-Duration wird NICHT abgezogen, daher effektives Interval = poll_interval + cycle_duration
            await asyncio.sleep(poll_interval)

    except asyncio.CancelledError:
        # Graceful Shutdown durch SIGTERM (Docker Stop, Hassio Restart)
        logger.info("🛑 Shutdown")
        publish_status("offline", topic)
        disconnect_mqtt()

    except Exception as e:
        # Fatal Error - Addon muss neu starten
        # Sollte nie passieren, aber Safety-Net
        logger.error(f"💥 Fatal: {e}")
        publish_status("offline", topic)
        disconnect_mqtt()
        sys.exit(1)


if __name__ == "__main__":
    """
    Entry-Point beim direkten Ausführen der Datei.

    Startet async main() Loop und fängt KeyboardInterrupt ab
    (Ctrl+C bei lokalem Testing).
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Manueller Stop (Ctrl+C) bei lokalem Test
        logger.info("⌨️  Interrupted")
