# huawei_solar_modbus_mqtt/bridge/transform.py

"""
Transformiert Modbus-Register-Daten in MQTT-Format.

Dieser Transformations-Layer sitzt zwischen Modbus-Read und MQTT-Publishing
und führt folgende Schritte aus:

1. Register-Namen mappen (Modbus → MQTT-Keys)
   activepower → power_active, inputpower → power_input, ...

2. Result-Objekte extrahieren (huawei_solar Library, Felder value, unit)
   Result(value=4500, unit="W") → 4500

3. Ungültige Modbus-Werte filtern
   65535, 32767, -32768 → None (Modbus "keine Daten verfügbar")

4. Abgeleitete Werte berechnen (vor den Critical Defaults!)
   power_PV1..4, power_house, ratio_autarky, ratio_self_consumption.
   Fehlt eine Eingangsgröße (z.B. der Meter), fehlt auch der abgeleitete Wert.
   Würde nach den Defaults gerechnet, läge meter=0 an und die Autarkie
   bei 100 %.

5. Critical Defaults anwenden
   Fehlende Pflicht-Werte mit Defaults befüllen (z.B. battery_power=0)

6. Batterie-Aufteilung (nach den Critical Defaults)
   battery_power_charge / battery_power_discharge. Ohne Batterie ist
   battery_power per Default 0, beide Werte sind dann 0.

7. total_increasing Filter anwenden
   Verhindert falsche Counter-Resets (siehe total_increasing_filter.py)

8. Cleanup
   None-Werte entfernen, Timestamp hinzufügen

Vorzeichen-Konvention (Huawei, live gegengeprüft):
    meter_power_active > 0 = Einspeisung, < 0 = Netzbezug
    battery_power      > 0 = Laden,       < 0 = Entladen

Das Ergebnis ist ein sauberes Dict das direkt als JSON zu MQTT publiziert
werden kann und von Home Assistant verstanden wird.
"""

import logging
import time
from typing import Any

from .config.mappings import CRITICAL_DEFAULTS, REGISTER_MAPPING

logger = logging.getLogger("huawei.transform")

# Zielkey, Spannungskey, Stromkey je PV-String
PV_STRING_POWER_KEYS: tuple[tuple[str, str, str], ...] = tuple(
    (f"power_PV{n}", f"voltage_PV{n}", f"current_PV{n}") for n in range(1, 5)
)

# Unterhalb dieser Basisleistung ist eine Quote Rauschen und wird nicht berechnet
MIN_RATIO_BASE_POWER_W = 50.0

# meter_status: MeterStatus.OFFLINE == 0 (huawei_solar)
METER_STATUS_OFFLINE = 0

# Quoten in Prozent (0 bis PERCENT_MAX), gerundet auf VALUE_DECIMALS Nachkommastellen
PERCENT_MAX = 100.0
VALUE_DECIMALS = 1

# Keys, die transform_data() aus anderen Werten berechnet (kein Modbus-Register)
DERIVED_KEYS: frozenset[str] = frozenset(
    {power_key for power_key, _, _ in PV_STRING_POWER_KEYS}
    | {"power_house", "ratio_autarky", "ratio_self_consumption", "battery_power_charge", "battery_power_discharge"}
)


def transform_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Transformiert Huawei Register-Daten in MQTT-Format mit Filter-Anwendung.

    Ablauf: siehe Modul-Docstring (Schritte 1-8).

    HINWEIS: total_increasing Filter wird jetzt in main_once() angewendet!

    Args:
        data: Dict mit Modbus-Register-Daten aus read_registers()
              Format: {"activepower": Result, "inputpower": Result, ...}

    Returns:
        Dict mit transformierten MQTT-Daten, bereit zum Publishing
        Format: {"power_active": 4500, "power_input": 4200, ...}

    Performance:
        Typisch < 5ms für 58 Register

    Beispiel Input (von read_registers):
        {
          "activepower": Result(value=4500, unit="W"),
          "inputpower": Result(value=4800, unit="W"),
          "storagestateofcapacity": Result(value=85.5, unit="%"),
          "alarm1": Result(value=65535, unit=None)  # Ungültig
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
    result = {mqtt_key: get_value(data.get(register_key)) for register_key, mqtt_key in REGISTER_MAPPING.items()}

    # === PHASE 1b: Abgeleitete Werte ===
    # MUSS vor den Critical Defaults laufen: fehlt der Meter, soll kein
    # Hausverbrauch/keine Quote entstehen (meter=0 würde 100 % Autarkie vortäuschen).
    result.update(derive_values(result))

    # === PHASE 2: Critical Defaults ===
    # Stellt sicher dass wichtige Keys existieren, auch wenn Modbus fehlt
    # Beispiel: battery_power=0 wenn kein Batteriewert verfügbar
    # Verhindert Template-Errors in Home Assistant
    for key, default in CRITICAL_DEFAULTS.items():
        if result.get(key) is None:
            logger.warning(f"⚠️ Critical '{key}' missing, using {default}")
            result[key] = default

    # === PHASE 2b: Batterie-Aufteilung ===
    # Nach den Defaults: ohne Batterie sind Laden und Entladen 0 (wie battery_power)
    result.update(derive_battery_split(result))

    # === PHASE 3: Cleanup ===
    # - Entfernt None-Werte (würden in JSON als null erscheinen)
    # - Fügt last_update Timestamp hinzu
    result = _cleanup_result(result)

    duration = time.time() - start
    logger.debug(f"Transform complete: {len(result)} values ({duration:.3f}s)")

    return result


def _number(key: str, value: Any) -> float | None:
    """Gibt value als float zurück, wenn es eine echte Zahl ist (kein bool, str).

    None gilt als "fehlt" und wird still übergangen. Falsch typisierte Werte
    werden auf debug mit dem Key-Namen protokolliert.
    """
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        logger.debug("Wert für '%s' ignoriert, keine Zahl: %r", key, value)
        return None
    return float(value)


def _clamp_percent(value: float) -> float:
    """Begrenzt auf 0 bis PERCENT_MAX und rundet auf VALUE_DECIMALS Nachkommastellen."""
    return round(min(max(value, 0.0), PERCENT_MAX), VALUE_DECIMALS)


def _is_meter_offline(status: Any) -> bool:
    """True nur bei ausdrücklichem OFFLINE (0 bzw. Text "offline").

    Fehlt der Status oder hat er einen anderen Wert, gilt der Meter nicht als
    offline, damit Anlagen ohne dieses Register ihre Werte behalten.
    meter_status kommt als MeterStatus-IntEnum (int-Unterklasse) oder als int.
    """
    if isinstance(status, str):
        return status.strip().lower() == "offline"
    return _number("meter_status", status) == METER_STATUS_OFFLINE


def _derive_pv_string_power(values: dict[str, Any]) -> dict[str, float]:
    """Leistung pro PV-String (U x I), nur wenn Spannung und Strom vorliegen."""
    derived: dict[str, float] = {}
    for power_key, voltage_key, current_key in PV_STRING_POWER_KEYS:
        voltage = _number(voltage_key, values.get(voltage_key))
        current = _number(current_key, values.get(current_key))
        if voltage is not None and current is not None:
            derived[power_key] = round(voltage * current, VALUE_DECIMALS)
    return derived


def _derive_ratios(house: float, grid_power: float, pv_power: float | None) -> dict[str, float]:
    """Autarkie- und Eigenverbrauchsquote, nur ab MIN_RATIO_BASE_POWER_W Basisleistung.

    - ratio_autarky: Anteil des Verbrauchs ohne Netzbezug (Basis: Hausverbrauch)
    - ratio_self_consumption: Anteil der PV-Erzeugung, der nicht eingespeist wird
    """
    ratios: dict[str, float] = {}
    if house >= MIN_RATIO_BASE_POWER_W:
        grid_import = max(0.0, -grid_power)
        ratios["ratio_autarky"] = _clamp_percent((house - grid_import) / house * PERCENT_MAX)
    if pv_power is not None and pv_power >= MIN_RATIO_BASE_POWER_W:
        grid_export = max(0.0, grid_power)
        ratios["ratio_self_consumption"] = _clamp_percent((pv_power - grid_export) / pv_power * PERCENT_MAX)
    return ratios


def _derive_house_values(values: dict[str, Any]) -> dict[str, float]:
    """Hausverbrauch und Quoten aus AC-Ausgang, Netzleistung und PV-Leistung.

    Vorzeichen: Meter > 0 = Einspeisung, < 0 = Netzbezug.

    - power_house = power_active - meter_power_active (min. 0). power_active
      enthält Batterie und Wandlungsverluste bereits.

    Ohne Meter-Messwert oder bei meter_status OFFLINE entsteht nichts.
    """
    if _is_meter_offline(values.get("meter_status")):
        return {}

    ac_power = _number("power_active", values.get("power_active"))
    grid_power = _number("meter_power_active", values.get("meter_power_active"))
    if ac_power is None or grid_power is None:
        return {}

    house = max(0.0, ac_power - grid_power)
    pv_power = _number("power_input", values.get("power_input"))
    return {"power_house": round(house, VALUE_DECIMALS), **_derive_ratios(house, grid_power, pv_power)}


def derive_values(values: dict[str, Any]) -> dict[str, float]:
    """Berechnet abgeleitete Werte aus den gemappten MQTT-Werten (ohne Modbus-Reads).

    Muss vor den Critical Defaults aufgerufen werden (siehe transform_data).

    Args:
        values: Gemappte MQTT-Werte (Keys wie ``power_active``), wird nicht verändert.

    Returns:
        Neues Dict nur mit den berechenbaren Keys: ``power_PV1..4``,
        ``power_house``, ``ratio_autarky``, ``ratio_self_consumption``.
    """
    return {**_derive_pv_string_power(values), **_derive_house_values(values)}


def derive_battery_split(values: dict[str, Any]) -> dict[str, float]:
    """Teilt battery_power (> 0 = Laden, < 0 = Entladen) in zwei positive Werte.

    Returns:
        ``battery_power_charge`` und ``battery_power_discharge``, leer wenn
        battery_power keine Zahl ist.
    """
    battery_power = _number("battery_power", values.get("battery_power"))
    if battery_power is None:
        return {}
    return {
        "battery_power_charge": max(0.0, battery_power),
        "battery_power_discharge": max(0.0, -battery_power),
    }


def get_value(value):
    """
    Extrahiert Wert aus Register-Result und filtert spezielle Fälle.

    Verarbeitet drei Arten von Werten:

    1. None → None (Register nicht gelesen oder fehlt)

    2. Result-Objekte (huawei_solar Library)
       Result hat .value Attribut mit tatsächlichem Wert
       Beispiel: Result(value=4500, unit="W") → 4500

    3. Ungültige Modbus-Werte filtern
       65535, 32767, -32768 sind Modbus-Platzhalter für "keine Daten"
       Diese werden zu None konvertiert (später von cleanup entfernt)

    Args:
        value: Wert aus read_registers() - kann Result, int, float, None sein

    Returns:
        Extrahierter numerischer Wert oder None

    Beispiele:
        >>> get_value(None)
        None

        >>> get_value(Result(value=4500, unit="W"))
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
    # Result hat .value Attribut mit tatsächlichem Wert
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


def _cleanup_result(result: dict[str, Any]) -> dict[str, Any]:
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
