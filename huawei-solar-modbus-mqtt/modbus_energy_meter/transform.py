# modbus_energy_meter/transform.py

"""
Transformiert Modbus-Register-Daten in MQTT-Format.

Dieser Transformations-Layer sitzt zwischen Modbus-Read und MQTT-Publishing
und führt folgende Schritte aus:

1. Register-Namen mappen (Modbus → MQTT-Keys)
   activepower → power_active, inputpower → power_input, ...

2. RegisterValue-Objekte extrahieren (huawei_solar Library)
   RegisterValue(value=4500, unit="W") → 4500

3. Ungültige Modbus-Werte filtern
   65535, 32767, -32768 → None (Modbus "keine Daten verfügbar")

4. Critical Defaults anwenden
   Fehlende Pflicht-Werte mit Defaults befüllen (z.B. battery_power=0)

5. total_increasing Filter anwenden
   Verhindert falsche Counter-Resets (siehe total_increasing_filter.py)

6. Cleanup
   None-Werte entfernen, Timestamp hinzufügen

Das Ergebnis ist ein sauberes Dict das direkt als JSON zu MQTT publiziert
werden kann und von Home Assistant verstanden wird.
"""

import logging
import time
from typing import Any, Dict

from .config.mappings import CRITICAL_DEFAULTS, REGISTER_MAPPING

logger = logging.getLogger("huawei.transform")


def transform_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transformiert Huawei Register-Daten in MQTT-Format mit Filter-Anwendung.

    Haupt-Pipeline:
    1. Register-Namen mappen (activepower → power_active)
    2. RegisterValue-Objekte extrahieren (.value Attribut)
    3. Ungültige Modbus-Werte filtern (65535 → None)
    4. Critical Defaults für fehlende Pflicht-Keys
    5. Cleanup (None entfernen, Timestamp hinzufügen)

    HINWEIS: total_increasing Filter wird jetzt in main_once() angewendet!

    Args:
        data: Dict mit Modbus-Register-Daten aus read_registers()
              Format: {"activepower": RegisterValue, "inputpower": RegisterValue, ...}

    Returns:
        Dict mit transformierten MQTT-Daten, bereit zum Publishing
        Format: {"power_active": 4500, "power_input": 4200, ...}

    Performance:
        Typisch < 5ms für 58 Register

    Beispiel Input (von read_registers):
        {
          "activepower": RegisterValue(value=4500, unit="W"),
          "inputpower": RegisterValue(value=4800, unit="W"),
          "storagestateofcapacity": RegisterValue(value=85.5, unit="%"),
          "alarm1": RegisterValue(value=65535, unit=None)  # Ungültig
        }

    Beispiel Output (für MQTT):
        {
          "power_active": 4500,
          "power_input": 4800,
          "battery_soc": 85.5,
          # alarm1 fehlt (wurde gefiltert wegen 65535)
          "last_update": 1706184000.123
        }
    """
    logger.debug(f"Transforming {len(data)} registers")
    start = time.time()

    # === PHASE 1: Register-Mapping & Value-Extraction ===
    # Iteriert über alle Mappings aus config/mappings.py
    # - register_key: Modbus-Register-Name (aus huawei_solar Library)
    # - mqtt_key: MQTT-Key-Name (für Home Assistant)
    # get_value() extrahiert .value und filtert ungültige Modbus-Werte
    result = {
        mqtt_key: get_value(data.get(register_key))
        for register_key, mqtt_key in REGISTER_MAPPING.items()
    }

    # === PHASE 2: Critical Defaults ===
    # Stellt sicher dass wichtige Keys existieren, auch wenn Modbus fehlt
    # Beispiel: battery_power=0 wenn kein Batteriewert verfügbar
    # Verhindert Template-Errors in Home Assistant
    for key, default in CRITICAL_DEFAULTS.items():
        if result.get(key) is None:
            logger.warning(f"Critical '{key}' missing, using {default}")
            result[key] = default

    # === PHASE 3: Cleanup ===
    # - Entfernt None-Werte (würden in JSON als null erscheinen)
    # - Fügt last_update Timestamp hinzu
    result = _cleanup_result(result)

    duration = time.time() - start
    logger.debug(f"Transform complete: {len(result)} values ({duration:.3f}s)")

    return result


def get_value(value):
    """
    Extrahiert Wert aus Register-Result und filtert spezielle Fälle.

    Verarbeitet drei Arten von Werten:

    1. None → None (Register nicht gelesen oder fehlt)

    2. RegisterValue-Objekte (huawei_solar Library)
       RegisterValue hat .value Attribut mit tatsächlichem Wert
       Beispiel: RegisterValue(value=4500, unit="W") → 4500

    3. Ungültige Modbus-Werte filtern
       65535, 32767, -32768 sind Modbus-Platzhalter für "keine Daten"
       Diese werden zu None konvertiert (später von cleanup entfernt)

    Args:
        value: Wert aus read_registers() - kann RegisterValue, int, float, None sein

    Returns:
        Extrahierter numerischer Wert oder None

    Beispiele:
        >>> get_value(None)
        None

        >>> get_value(RegisterValue(value=4500, unit="W"))
        4500

        >>> get_value(65535)  # Modbus "kein Wert vorhanden"
        None

        >>> get_value(4500)
        4500

    Modbus "Keine Daten"-Werte:
        65535 (0xFFFF): Unsigned 16-bit "nicht verfügbar"
        32767 (0x7FFF): Signed 16-bit Maximum (oft ungültig)
        -32768 (0x8000): Signed 16-bit Minimum (oft ungültig)

    Diese Werte werden vom Inverter gesendet wenn:
        - Register existiert, aber aktuell kein Wert verfügbar
        - Sensor nicht vorhanden (z.B. kein Optimizer an String 3)
        - Messwert außerhalb gültiger Range

    Hinweis:
        Filterung ist "silent" (kein Log) da diese Werte häufig und
        erwartbar sind (z.B. PV String 3/4 bei kleineren Anlagen).
    """
    if value is None:
        return None

    # Handle huawei_solar library objects
    # RegisterValue hat .value Attribut mit tatsächlichem Wert
    if hasattr(value, "value"):
        value = value.value

    # datetime zu ISO-String konvertieren (für JSON-Serialisierung)
    # startup_time ist datetime-Objekt, muss zu String werden
    if hasattr(value, "isoformat"):  # datetime, date, time haben isoformat()
        return value.isoformat()

    # Filter invalid Modbus values (silent - sind häufig und erwartbar)
    # Diese Werte sind Modbus-Konvention für "keine Daten verfügbar"
    if isinstance(value, (int, float)):
        if value in (65535, 32767, -32768):
            return None

    return value


def _cleanup_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entfernt None-Werte und fügt Timestamp hinzu.

    Cleanup-Schritte:
    1. Alle Keys mit None-Werten entfernen
       Grund: JSON-Payload soll nur vorhandene Werte enthalten
       None → würde in MQTT als "key": null erscheinen

    2. last_update Timestamp hinzufügen
       Unix-Zeit in Sekunden (float mit Millisekunden)
       Nützlich für Debugging und Monitoring

    Args:
        result: Dict mit transformierten Werten (enthält evtl. None)

    Returns:
        Bereinigtes Dict ohne None-Werte, mit Timestamp

    Warum None-Werte entfernen?
    - Home Assistant Templates würden "dict object has no attribute" Error werfen
    - JSON-Payload wird kleiner (weniger MQTT-Traffic)
    - Nur vorhandene Werte sollen in HA aktualisiert werden
    - value_template mit | default(0) fängt fehlende Keys ab (siehe sensors_mqtt.py)

    Beispiel:
        Input: {"power_active": 4500, "alarm1": None, "battery_soc": 85.5}
        Output: {"power_active": 4500, "battery_soc": 85.5, "last_update": 1706184000.123}

    Hinweis:
        last_update wird auch in mqtt_client.publish_data() nochmal gesetzt,
        aber mit int(time.time()). Hier float für höhere Präzision bei Debugging.
    """
    # Dictionary Comprehension: Nur Keys wo Value nicht None ist
    cleaned = {k: v for k, v in result.items() if v is not None}

    # Timestamp hinzufügen (Unix-Zeit in Sekunden, float mit Millisekunden)
    cleaned["last_update"] = time.time()

    return cleaned
