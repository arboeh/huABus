# modbus_energy_meter/mqtt_client.py

"""
MQTT Client Manager für Home Assistant Integration.

Verwaltet die persistente MQTT-Verbindung zum Broker und implementiert:
- Home Assistant MQTT Discovery (automatische Entity-Erstellung)
- Sensor-Daten Publishing (JSON-Payload mit allen Messwerten)
- Status Publishing (online/offline für Binary Sensor)
- Last Will Testament (LWT) für automatisches offline bei Verbindungsabbruch
- Connection State Tracking zur Vermeidung von "not connected" Errors

Die Verbindung wird einmalig beim Start erstellt und bleibt für die gesamte
Laufzeit bestehen (persistent), nur Modbus reconnected bei Fehlern.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import paho.mqtt.client as mqtt  # type: ignore

from .config.sensors_mqtt import NUMERIC_SENSORS, TEXT_SENSORS

logger = logging.getLogger("huawei.mqtt")

# Globale MQTT Client Instanz (Singleton-Pattern)
# Wird von _get_mqtt_client() erstellt und wiederverwendet
_mqtt_client: Optional[mqtt.Client] = None

# Connection State Flag - verhindert Publishing wenn nicht verbunden
# Wird von Callbacks (_on_connect, _on_disconnect) aktualisiert
_is_connected = False


def _on_connect(client, userdata, flags, rc, properties=None):
    """
    Callback wenn MQTT-Verbindung hergestellt wurde.

    Wird von paho-mqtt automatisch aufgerufen bei erfolgreicher Verbindung.
    Setzt _is_connected Flag, damit Publishing-Funktionen wissen dass
    sie sicher publizieren können.

    Args:
        client: MQTT Client Instanz
        userdata: User-definierte Daten (nicht genutzt)
        flags: Connection flags vom Broker
        rc: Return code (0 = Success)
        properties: MQTT v5 Properties (optional, für Abwärtskompatibilität)

    Return Codes (rc):
        0: Success
        1: Connection refused - incorrect protocol version
        2: Connection refused - invalid client identifier
        3: Connection refused - server unavailable
        4: Connection refused - bad username or password
        5: Connection refused - not authorized
    """
    global _is_connected
    if rc == 0:
        _is_connected = True
        logger.info("📡 MQTT connected")
    else:
        logger.error(f"MQTT connection failed: {rc}")


def _on_disconnect(client, userdata, flags, rc=0, properties=None):
    """
    Callback wenn MQTT-Verbindung getrennt wurde.

    Wird von paho-mqtt automatisch aufgerufen bei Verbindungsverlust.
    Setzt _is_connected Flag zurück, damit keine Publishing-Versuche
    mehr gemacht werden (würden fehlschlagen).

    Args:
        client: MQTT Client Instanz
        userdata: User-definierte Daten (nicht genutzt)
        flags: Disconnect flags
        rc: Return code (0 = Clean disconnect, sonst Fehler)
        properties: MQTT v5 Properties (optional)

    Unterscheidung:
        rc == 0: Sauberer Disconnect (vom Client initiiert)
        rc != 0: Unerwarteter Disconnect (Netzwerkproblem, Broker-Crash)
    """
    global _is_connected
    _is_connected = False
    if rc != 0:
        # Unerwarteter Disconnect (nicht vom Client initiiert)
        logger.warning(f"MQTT unexpected disconnect: {rc}")


def _get_mqtt_client() -> mqtt.Client:
    """
    Erstellt oder gibt existierenden MQTT Client zurück (Singleton-Pattern).

    Der Client wird nur einmal erstellt und dann wiederverwendet.
    Konfiguriert:
    - paho-mqtt 2.x API Callbacks
    - Authentifizierung (falls USER/PASSWORD gesetzt)
    - Last Will Testament (LWT) für automatisches offline bei Crash

    Last Will Testament (LWT):
        Wenn die Verbindung unerwartet abbricht (Crash, Netzwerk),
        publiziert der MQTT-Broker automatisch "{topic}/status" = "offline".
        Damit weiß Home Assistant sofort dass das Add-on nicht mehr läuft.

    Returns:
        Konfigurierter MQTT Client (noch nicht verbunden)

    ENV-Konfiguration:
        HUAWEI_MODBUS_MQTT_USER: MQTT Username (optional)
        HUAWEI_MODBUS_MQTT_PASSWORD: MQTT Password (optional)
        HUAWEI_MODBUS_MQTT_TOPIC: Basis-Topic für LWT

    Hinweis:
        Bei paho-mqtt >= 2.0 muss CallbackAPIVersion.VERSION2 angegeben
        werden, sonst sind die Callback-Signaturen falsch.
    """
    global _mqtt_client
    if _mqtt_client is not None:
        # Client existiert bereits, wiederverwenden
        return _mqtt_client

    # paho-mqtt 2.x API - VERSION2 für neue Callback-Signaturen
    # (Alte VERSION1 hätte andere Parameter-Reihenfolge)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)  # type: ignore[attr-defined]

    # Callbacks registrieren für Connection-State-Tracking
    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect

    # Optionale Authentifizierung konfigurieren
    user = os.environ.get("HUAWEI_MODBUS_MQTT_USER")
    password = os.environ.get("HUAWEI_MODBUS_MQTT_PASSWORD")

    if user and password:
        client.username_pw_set(user, password)
        logger.debug(f"MQTT auth configured for {user}")

    # Last Will Testament (LWT) konfigurieren
    # Wird vom Broker automatisch publiziert bei unerwartetem Disconnect
    topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
    if topic:
        # QoS=1: Mindestens einmal zugestellt
        # retain=True: Letzter Wert bleibt gespeichert (wichtig für Status)
        client.will_set(f"{topic}/status", "offline", qos=1, retain=True)
        logger.debug(f"LWT set: {topic}/status")

    # Client speichern für Wiederverwendung (Singleton)
    _mqtt_client = client
    return client


def connect_mqtt() -> None:
    """
    Verbindet MQTT Client einmalig beim Start (persistent).

    Workflow:
    1. Client holen/erstellen (_get_mqtt_client)
    2. Zu Broker verbinden (client.connect)
    3. Background-Loop starten (client.loop_start)
    4. Warten bis _is_connected True ist (max 10s)
    5. Zusätzliche 300ms Stabilisierung

    Die Verbindung bleibt für die gesamte Laufzeit bestehen.
    Bei Netzwerkproblemen reconnected paho-mqtt automatisch.

    Raises:
        RuntimeError: Wenn MQTT Broker nicht konfiguriert
        ConnectionError: Wenn Verbindung nach 10s Timeout nicht steht

    ENV-Konfiguration:
        HUAWEI_MODBUS_MQTT_BROKER: IP/Hostname des MQTT Brokers (required)
        HUAWEI_MODBUS_MQTT_PORT: MQTT Port (default: 1883)

    Beispiel:
        >>> connect_mqtt()
        # Log: "Connecting MQTT to 192.168.1.2:1883"
        # Log: "MQTT connected"
        # Log: "MQTT connection stable"

    Hinweis:
        client.loop_start() startet Background-Thread für MQTT-Kommunikation.
        Dieser läuft parallel zu asyncio Event-Loop (kein Konflikt).
    """
    global _is_connected

    client = _get_mqtt_client()

    broker = os.environ.get("HUAWEI_MODBUS_MQTT_BROKER")
    port = int(os.environ.get("HUAWEI_MODBUS_MQTT_PORT", "1883"))

    if not broker:
        logger.error("MQTT broker not configured")
        raise RuntimeError("MQTT broker not configured")

    logger.debug(f"Connecting MQTT to {broker}:{port}")
    # Keepalive: 60s (Broker erwartet Ping alle 60s)
    client.connect(broker, port, 60)
    # Background-Loop starten (eigener Thread für MQTT-Kommunikation)
    client.loop_start()

    # Warte bis _is_connected True ist (wird von _on_connect gesetzt)
    # Polling alle 100ms, max 10 Sekunden
    timeout = 10
    waited = 0
    while not _is_connected and waited < timeout:
        time.sleep(0.1)
        waited += 0.1

    if not _is_connected:
        # Timeout - Verbindung steht nicht
        client.loop_stop()
        raise ConnectionError(f"MQTT connection timeout after {timeout}s")

    # Zusätzliche Stabilisierungszeit (verhindert Race-Conditions)
    # 300ms geben dem Broker Zeit für interne Initialisierung
    time.sleep(0.3)
    logger.debug("MQTT connection stable")


def disconnect_mqtt() -> None:
    """
    Trennt MQTT Client beim Shutdown sauber.

    Workflow:
    1. Status auf "offline" publizieren (sauberes Goodbye)
    2. Background-Loop stoppen (client.loop_stop)
    3. Verbindung trennen (client.disconnect)
    4. Globale Variablen zurücksetzen

    Wird aufgerufen bei:
    - Graceful Shutdown (SIGTERM von Docker/Hassio)
    - Fatal Error (vor sys.exit)
    - KeyboardInterrupt (Ctrl+C bei lokalem Test)

    Wichtig:
        Status "offline" wird mit retain=True publiziert, damit
        Home Assistant den Status auch nach Reconnect noch sieht.
    """
    global _mqtt_client, _is_connected
    if _mqtt_client is None:
        # Noch nicht verbunden, nichts zu tun
        return

    try:
        # Abschiedsgruß: Status auf offline setzen
        topic = os.environ.get("HUAWEI_MODBUS_MQTT_TOPIC")
        if topic and _is_connected:
            result = _mqtt_client.publish(
                f"{topic}/status", "offline", qos=1, retain=True
            )
            # Warten bis publiziert (max 1s)
            result.wait_for_publish(timeout=1.0)
        # Background-Loop stoppen (beendet MQTT-Thread)
        _mqtt_client.loop_stop()
        # Verbindung sauber trennen
        _mqtt_client.disconnect()
        logger.info("MQTT disconnected")
    except Exception as e:
        # Fehler beim Disconnect nicht fatal (wir beenden eh)
        logger.error(f"MQTT disconnect error: {e}")
    finally:
        # Globals zurücksetzen für sauberen State
        _mqtt_client = None
        _is_connected = False


def _build_sensor_config(
    sensor: Dict[str, Any], base_topic: str, device_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Erstellt MQTT Discovery Config für einzelnen Sensor.

    MQTT Discovery ist Home Assistants Protokoll zur automatischen
    Entity-Erstellung. Durch Publishing einer JSON-Config zu einem
    speziellen Topic erstellt HA automatisch den Sensor.

    Discovery-Topic-Format:
        homeassistant/sensor/{device}/{entity}/config

    Config-Keys (Auswahl):
        name: Anzeigename in HA
        unique_id: Eindeutige ID (für Entity Registry)
        state_topic: Topic wo Werte publiziert werden
        value_template: Jinja2 Template zum Extrahieren des Wertes
        availability_topic: Topic für online/offline Status
        device: Geräteinformationen (für Device-Gruppierung)
        unit_of_measurement: Einheit (kWh, W, °C, ...)
        device_class: HA Device Class (energy, power, temperature, ...)
        state_class: State Class (measurement, total, total_increasing)

    Args:
        sensor: Sensor-Definition aus sensors_mqtt.py
        base_topic: MQTT Basis-Topic (z.B. "huawei-solar")
        device_config: Device-Informationen für Gruppierung in HA

    Returns:
        Dict mit vollständiger MQTT Discovery Config

    Beispiel:
        >>> sensor = {
        ...     "name": "Solar Power",
        ...     "key": "power_input",
        ...     "unit_of_measurement": "W",
        ...     "device_class": "power"
        ... }
        >>> config = _build_sensor_config(sensor, "huawei-solar", device_config)
        >>> config["state_topic"]
        "huawei-solar"
        >>> config["value_template"]
        "{{ value_json.power_input }}"
    """
    # Basis-Config (Pflichtfelder)
    config = {
        "name": sensor["name"],
        "unique_id": f"huawei_solar_{sensor['key']}",
        "state_topic": base_topic,
        # value_template: Extrahiert Wert aus JSON-Payload
        # Default: {{ value_json.key_name }}
        # Custom: {{ value_json.key_name | default(0) }} (aus sensors_mqtt.py)
        "value_template": sensor.get(
            "value_template",
            f"{{{{ value_json.{sensor['key']} }}}}",
        ),
        "availability_topic": f"{base_topic}/status",
        "payload_available": "online",
        "payload_not_available": "offline",
        "device": device_config,
    }

    # Optional: Weitere Config-Keys falls vorhanden
    # Diese Keys werden 1:1 von sensors_mqtt.py übernommen
    for key in [
        "unit_of_measurement",  # Einheit (kWh, W, V, A, ...)
        "device_class",  # HA Device Class (energy, power, voltage, ...)
        "state_class",  # State Class (measurement, total, total_increasing)
        "icon",  # MDI Icon (mdi:solar-power, mdi:battery, ...)
        "entity_category",  # Kategorie (diagnostic, config, None)
    ]:
        if key in sensor:
            config[key] = sensor[key]

    # Optional: Sensor standardmäßig deaktivieren (enabled=False in sensors_mqtt.py)
    # Nutzer kann in HA UI manuell aktivieren (für diagnostische Sensoren)
    if sensor.get("enabled", True) is False:
        config["enabled_by_default"] = False

    return config


def _load_numeric_sensors() -> List[Dict[str, Any]]:
    """
    Lädt numerische Sensor-Definitionen aus sensors_mqtt.py.

    Numerische Sensoren haben unit_of_measurement und oft device_class.
    Beispiele: Leistung (W), Energie (kWh), Spannung (V), Temperatur (°C)

    Returns:
        Liste mit Sensor-Definitionen für numerische Werte

    Siehe:
        config/sensors_mqtt.py -> NUMERIC_SENSORS
    """
    return NUMERIC_SENSORS


def _load_text_sensors() -> List[Dict[str, Any]]:
    """
    Lädt Text-Sensor-Definitionen aus sensors_mqtt.py.

    Text-Sensoren haben keine unit_of_measurement, nur String-Werte.
    Beispiele: Modellname, Seriennummer, Status-Strings

    Returns:
        Liste mit Sensor-Definitionen für Text-Werte

    Siehe:
        config/sensors_mqtt.py -> TEXT_SENSORS
    """
    return TEXT_SENSORS


def _publish_sensor_configs(
    client: mqtt.Client,
    base_topic: str,
    sensors: List[Dict[str, Any]],
    device_config: Dict[str, Any],
) -> int:
    """
    Publiziert MQTT Discovery Configs für Liste von Sensoren.

    Für jeden Sensor:
    1. Discovery-Config erstellen (_build_sensor_config)
    2. Zu Discovery-Topic publizieren (mit QoS=1, retain=True)
    3. Auf Publish-Bestätigung warten (max 1s)

    QoS=1: Mindestens einmal zugestellt (wichtig für Discovery)
    retain=True: Config bleibt gespeichert, auch nach Broker-Neustart

    Args:
        client: MQTT Client Instanz
        base_topic: MQTT Basis-Topic (z.B. "huawei-solar")
        sensors: Liste mit Sensor-Definitionen
        device_config: Device-Info für HA Gruppierung

    Returns:
        Anzahl publizierter Sensoren

    Discovery-Topic-Format:
        homeassistant/sensor/huawei_solar/{sensor_key}/config

    Beispiel:
        homeassistant/sensor/huawei_solar/power_input/config
        → Erstellt sensor.solar_power in Home Assistant
    """
    count = 0
    for sensor in sensors:
        # Config für diesen Sensor erstellen
        config = _build_sensor_config(sensor, base_topic, device_config)
        # Discovery-Topic: homeassistant/sensor/{device}/{entity}/config
        topic = f"homeassistant/sensor/huawei_solar/{sensor['key']}/config"
        # Config als JSON publizieren (QoS=1, retain=True)
        result = client.publish(topic, json.dumps(config), qos=1, retain=True)
        # Auf Publish-Bestätigung warten (verhindert Race-Conditions)
        result.wait_for_publish(timeout=1.0)
        count += 1
    return count


def publish_discovery_configs(base_topic: str) -> None:
    """
    Publiziert alle MQTT Discovery Configs (einmalig beim Start).

    Erstellt in Home Assistant:
    - Alle numerischen Sensoren (Leistung, Energie, Spannung, ...)
    - Alle Text-Sensoren (Modellname, Status, ...)
    - Binary Sensor für Connectivity-Status (online/offline)

    Die Discovery-Configs werden nur beim Start publiziert, nicht
    bei jedem Cycle. Home Assistant speichert sie in der Entity Registry.

    Device-Gruppierung:
        Alle Sensoren werden in HA unter einem Device gruppiert:
        "Huawei Solar Inverter" mit Identifier "huawei_solar_modbus"

    Args:
        base_topic: MQTT Basis-Topic (z.B. "huawei-solar")

    Beispiel:
        >>> publish_discovery_configs("huawei-solar")
        # Log: "Publishing MQTT Discovery"
        # Log: "Published 45 numeric sensors"
        # Log: "Published 8 text sensors"
        # Log: "Discovery complete: 54 entities"
        # → Home Assistant hat jetzt 54 neue Entities unter einem Device

    Hinweis:
        Wenn MQTT nicht verbunden ist, wird Discovery übersprungen
        (kann später manuell mit HA MQTT Reload nachgeholt werden).
    """
    if not _is_connected:
        logger.warning("MQTT not connected, skipping discovery")
        return

    logger.info("🔍 Publishing MQTT Discovery")
    client = _get_mqtt_client()

    # Device-Config für HA Gruppierung
    # Alle Sensoren erscheinen unter diesem Device in HA UI
    device_config = {
        "identifiers": ["huawei_solar_modbus"],  # Eindeutige Device-ID
        "name": "Huawei Solar Inverter",  # Anzeigename
        "model": "SUN2000",  # Modell
        "manufacturer": "Huawei",  # Hersteller
    }

    # Numerische Sensoren publizieren (Leistung, Energie, ...)
    sensors = _load_numeric_sensors()
    count = _publish_sensor_configs(client, base_topic, sensors, device_config)
    logger.debug(f"Published {count} numeric sensors")

    # Text-Sensoren publizieren (Modellname, Status, ...)
    text_sensors = _load_text_sensors()
    text_count = _publish_sensor_configs(
        client, base_topic, text_sensors, device_config
    )
    logger.debug(f"Published {text_count} text sensors")

    # Binary Sensor für Connectivity-Status
    _publish_status_sensor(client, base_topic, device_config)

    logger.info(f"✅ Discovery complete: {count + text_count + 1} entities")


def _publish_status_sensor(
    client: mqtt.Client, base_topic: str, device_config: Dict[str, Any]
) -> None:
    """
    Publiziert Binary Sensor für Connectivity-Status (online/offline).

    Erstellt in Home Assistant:
        binary_sensor.huawei_solar_status
        - ON wenn "{base_topic}/status" = "online"
        - OFF wenn "{base_topic}/status" = "offline"
        - Device Class: connectivity

    Dieser Sensor zeigt im HA Dashboard ob das Add-on läuft und
    Daten vom Inverter empfängt.

    Args:
        client: MQTT Client Instanz
        base_topic: MQTT Basis-Topic (z.B. "huawei-solar")
        device_config: Device-Info für HA Gruppierung

    Discovery-Topic:
        homeassistant/binary_sensor/huawei_solar/status/config

    State-Topic:
        {base_topic}/status (z.B. "huawei-solar/status")

    Verwendung in HA:
        - Automationen: Benachrichtigung bei offline
        - Dashboard: Status-Anzeige
        - Lovelace-Card: Conditional auf Status
    """
    config = {
        "name": "Huawei Solar Status",
        "unique_id": "huawei_solar_status",
        "state_topic": f"{base_topic}/status",
        "payload_on": "online",  # Sensor ist ON wenn "online"
        "payload_off": "offline",  # Sensor ist OFF wenn "offline"
        "device_class": "connectivity",  # Icon/Styling für Connectivity
        "device": device_config,
    }
    # Discovery-Config publizieren
    result = client.publish(
        "homeassistant/binary_sensor/huawei_solar/status/config",
        json.dumps(config),
        qos=1,
        retain=True,
    )
    result.wait_for_publish(timeout=1.0)


def publish_data(data: Dict[str, Any], topic: str) -> None:
    """
    Publiziert Sensor-Daten zu MQTT (wird jeden Cycle aufgerufen).

    Daten-Format:
        JSON mit allen Sensor-Werten + last_update Timestamp

    Beispiel-Payload:
        {
          "power_input": 4500,
          "power_active": 4200,
          "meter_power_active": -200,
          "battery_power": 800,
          "battery_soc": 85.5,
          "energy_yield_day": 25.3,
          ...
          "last_update": 1706184000
        }

    QoS=1: Mindestens einmal zugestellt (wichtig für Statistiken)
    retain=True: Letzter Wert bleibt gespeichert (für Sensor-Init nach HA-Restart)

    Args:
        data: Dict mit allen Sensor-Werten (aus transform.py)
        topic: MQTT Topic (z.B. "huawei-solar")

    Raises:
        ConnectionError: Wenn MQTT nicht verbunden
        Exception: Bei Publish-Fehler (wird in main.py gefangen)

    Beispiel:
        >>> publish_data({"power_input": 4500, "battery_soc": 85.5}, "huawei-solar")
        # Log: "Publishing: Solar=4500W, Grid=N/AW, Battery=800W"
        # Log: "Data published: 48 keys"
        # → MQTT: huawei-solar = {"power_input": 4500, ...}
        # → HA: Alle Sensoren aktualisieren sich
    """
    if not _is_connected:
        logger.warning("MQTT not connected, cannot publish data")
        raise ConnectionError("MQTT not connected")

    client = _get_mqtt_client()
    # Timestamp hinzufügen (Unix-Zeit in Sekunden)
    data["last_update"] = int(time.time())

    # DEBUG: Zeige wichtigste Werte im Log
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Publishing: Solar={data.get('power_active', 'N/A')}W, "
            f"Grid={data.get('meter_power_active', 'N/A')}W, "
            f"Battery={data.get('battery_power', 'N/A')}W"
        )

    try:
        # JSON-Payload publizieren (QoS=1, retain=True)
        result = client.publish(topic, json.dumps(data), qos=1, retain=True)
        # Auf Publish-Bestätigung warten (max 2s)
        # Verhindert dass Daten verloren gehen bei schnellen Cycles
        result.wait_for_publish(timeout=2.0)
        logger.debug(f"Data published: {len(data)} keys")
    except Exception as e:
        # Publish-Fehler durchreichen zu main.py (dort Error-Handling)
        logger.error(f"MQTT publish failed: {e}")
        raise


def publish_status(status: str, topic: str) -> None:
    """
    Publiziert online/offline Status zu MQTT.

    Wird aufgerufen:
    - Nach jedem erfolgreichen Cycle → "online"
    - Bei Fehler im Cycle → "offline"
    - Bei Heartbeat-Timeout → "offline"
    - Beim Start → "offline" (initial)
    - Vor Shutdown → "offline" (cleanup)

    Status-Topic:
        {base_topic}/status (z.B. "huawei-solar/status")

    Auswirkung:
        - binary_sensor.huawei_solar_status ändert sich (ON/OFF)
        - Alle anderen Sensoren zeigen "unavailable" bei offline
        - Automationen können auf Status-Änderung reagieren

    Args:
        status: "online" oder "offline"
        topic: MQTT Basis-Topic (z.B. "huawei-solar")

    Beispiel:
        >>> publish_status("online", "huawei-solar")
        # Log: "Status: 'online' → huawei-solar/status"
        # → HA: binary_sensor.huawei_solar_status = ON
        # → HA: Alle Sensoren available

        >>> publish_status("offline", "huawei-solar")
        # Log: "Status: 'offline' → huawei-solar/status"
        # → HA: binary_sensor.huawei_solar_status = OFF
        # → HA: Alle Sensoren unavailable

    Hinweis:
        Wenn MQTT nicht verbunden, wird Status-Update übersprungen
        (nur DEBUG-Log, kein Error - ist erwartbar bei Disconnect).
    """
    if not _is_connected:
        # Nicht verbunden - Status-Update übersprungen (nicht fatal)
        logger.debug(f"MQTT not connected, cannot publish status '{status}'")
        return

    client = _get_mqtt_client()
    status_topic = f"{topic}/status"

    try:
        # Status publizieren (QoS=1, retain=True)
        # retain=True wichtig damit Status nach Broker-Restart noch da ist
        result = client.publish(status_topic, status, qos=1, retain=True)
        result.wait_for_publish(timeout=1.0)
        logger.debug(f"Status: '{status}' → {status_topic}")
    except Exception as e:
        # Status-Publish-Fehler nicht fatal (wird weiter versucht)
        logger.error(f"Status publish failed: {e}")
