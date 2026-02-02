# tests\test_mqtt_client.py

"""Tests für MQTT Client Manager."""

import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from modbus_energy_meter.mqtt_client import (
    _build_sensor_config,
    _get_mqtt_client,
    _on_connect,
    _on_disconnect,
    connect_mqtt,
    disconnect_mqtt,
    publish_data,
    publish_discovery_configs,
    publish_status,
)


@pytest.fixture
def mock_mqtt_client():
    """Mock MQTT Client für Tests."""
    with patch("modbus_energy_meter.mqtt_client.mqtt.Client") as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        # Mock publish result
        publish_result = MagicMock()
        publish_result.wait_for_publish = MagicMock()
        client_instance.publish.return_value = publish_result
        yield client_instance


@pytest.fixture
def mqtt_env_vars(monkeypatch):
    """Setze MQTT Environment-Variablen für Tests."""
    monkeypatch.setenv("HUAWEI_MODBUS_MQTT_BROKER", "localhost")
    monkeypatch.setenv("HUAWEI_MODBUS_MQTT_PORT", "1883")
    monkeypatch.setenv("HUAWEI_MODBUS_MQTT_TOPIC", "test/huawei")
    monkeypatch.setenv("HUAWEI_MODBUS_MQTT_USER", "testuser")
    monkeypatch.setenv("HUAWEI_MODBUS_MQTT_PASSWORD", "testpass")


@pytest.fixture(autouse=True)
def reset_mqtt_globals():
    """Reset globale MQTT Variablen vor jedem Test."""
    import modbus_energy_meter.mqtt_client as mqtt_module

    mqtt_module._mqtt_client = None
    mqtt_module._is_connected = False
    yield
    mqtt_module._mqtt_client = None
    mqtt_module._is_connected = False


class TestCallbacks:
    """Test MQTT Callback-Funktionen."""

    def test_on_connect_success(self):
        """Test erfolgreichen Connect-Callback."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        _on_connect(None, None, None, 0)
        assert mqtt_module._is_connected is True

    def test_on_connect_failure(self):
        """Test fehlerhaften Connect-Callback."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        _on_connect(None, None, None, 5)  # rc=5 = not authorized
        assert mqtt_module._is_connected is False

    def test_on_disconnect_clean(self):
        """Test sauberen Disconnect."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        mqtt_module._is_connected = True

        _on_disconnect(None, None, None, 0)  # rc=0 = clean
        assert mqtt_module._is_connected is False

    def test_on_disconnect_unexpected(self):
        """Test unerwarteten Disconnect."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        mqtt_module._is_connected = True

        _on_disconnect(None, None, None, 1)  # rc=1 = unexpected
        assert mqtt_module._is_connected is False


class TestClientCreation:
    """Test MQTT Client Erstellung."""

    def test_get_mqtt_client_creates_new(self, mock_mqtt_client, mqtt_env_vars):
        """Test dass Client neu erstellt wird."""
        with patch("modbus_energy_meter.mqtt_client.mqtt.Client") as mock_client:
            mock_client.return_value = mock_mqtt_client
            client = _get_mqtt_client()

            assert client is not None
            mock_client.assert_called_once()

    def test_get_mqtt_client_singleton(self, mock_mqtt_client, mqtt_env_vars):
        """Test dass Client nur einmal erstellt wird (Singleton)."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        with patch("modbus_energy_meter.mqtt_client.mqtt.Client") as mock_client:
            mock_client.return_value = mock_mqtt_client
            mqtt_module._mqtt_client = mock_mqtt_client

            client = _get_mqtt_client()

            # Client wurde nicht neu erstellt
            mock_client.assert_not_called()
            assert client is mock_mqtt_client

    def test_get_mqtt_client_with_auth(self, mock_mqtt_client, mqtt_env_vars):
        """Test Client-Erstellung mit Authentifizierung."""
        with patch("modbus_energy_meter.mqtt_client.mqtt.Client") as mock_client:
            mock_client.return_value = mock_mqtt_client
            _get_mqtt_client()

            mock_mqtt_client.username_pw_set.assert_called_once_with(
                "testuser", "testpass"
            )

    def test_get_mqtt_client_with_lwt(self, mock_mqtt_client, mqtt_env_vars):
        """Test Client-Erstellung mit Last Will Testament."""
        with patch("modbus_energy_meter.mqtt_client.mqtt.Client") as mock_client:
            mock_client.return_value = mock_mqtt_client
            _get_mqtt_client()

            mock_mqtt_client.will_set.assert_called_once_with(
                "test/huawei/status", "offline", qos=1, retain=True
            )


class TestConnect:
    """Test MQTT Verbindungsaufbau."""

    def test_connect_mqtt_success(self, mock_mqtt_client, mqtt_env_vars):
        """Test erfolgreiche MQTT Verbindung."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        with patch("modbus_energy_meter.mqtt_client.mqtt.Client") as mock_client:
            mock_client.return_value = mock_mqtt_client

            # Simuliere erfolgreichen Connect
            def set_connected(*args):
                mqtt_module._is_connected = True

            mock_mqtt_client.connect.side_effect = set_connected

            connect_mqtt()

            mock_mqtt_client.connect.assert_called_once_with("localhost", 1883, 60)
            mock_mqtt_client.loop_start.assert_called_once()

    def test_connect_mqtt_no_broker(self, mock_mqtt_client, monkeypatch):
        """Test Connect ohne konfigurierten Broker."""
        monkeypatch.delenv("HUAWEI_MODBUS_MQTT_BROKER", raising=False)

        with pytest.raises(RuntimeError, match="MQTT broker not configured"):
            connect_mqtt()

    def test_connect_mqtt_timeout(self, mock_mqtt_client, mqtt_env_vars):
        """Test Connect-Timeout."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        with patch("modbus_energy_meter.mqtt_client.mqtt.Client") as mock_client:
            mock_client.return_value = mock_mqtt_client
            # _is_connected bleibt False (simuliert Timeout)
            mqtt_module._is_connected = False

            with patch("modbus_energy_meter.mqtt_client.time.sleep"):
                with pytest.raises(ConnectionError, match="MQTT connection timeout"):
                    connect_mqtt()


class TestDisconnect:
    """Test MQTT Trennung."""

    def test_disconnect_mqtt_when_connected(self, mock_mqtt_client, mqtt_env_vars):
        """Test saubere Trennung."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        mqtt_module._mqtt_client = mock_mqtt_client
        mqtt_module._is_connected = True

        disconnect_mqtt()

        mock_mqtt_client.publish.assert_called_once()
        mock_mqtt_client.loop_stop.assert_called_once()
        mock_mqtt_client.disconnect.assert_called_once()
        assert mqtt_module._mqtt_client is None
        assert mqtt_module._is_connected is False

    def test_disconnect_mqtt_when_not_connected(self):
        """Test Disconnect wenn nicht verbunden."""
        # Sollte keine Exception werfen
        disconnect_mqtt()


class TestSensorConfig:
    """Test Sensor-Konfiguration."""

    def test_build_sensor_config_basic(self):
        """Test Basis Sensor-Config."""
        sensor = {
            "name": "Test Sensor",
            "key": "test_key",
        }
        device_config = {"identifiers": ["test_device"]}

        config = _build_sensor_config(sensor, "test/topic", device_config)

        assert config["name"] == "Test Sensor"
        assert config["unique_id"] == "huawei_solar_test_key"
        assert config["state_topic"] == "test/topic"
        assert "{{ value_json.test_key }}" in config["value_template"]

    def test_build_sensor_config_with_unit(self):
        """Test Sensor-Config mit Einheit."""
        sensor = {
            "name": "Power",
            "key": "power",
            "unit_of_measurement": "W",
            "device_class": "power",
        }
        device_config = {"identifiers": ["test_device"]}

        config = _build_sensor_config(sensor, "test/topic", device_config)

        assert config["unit_of_measurement"] == "W"
        assert config["device_class"] == "power"

    def test_build_sensor_config_disabled(self):
        """Test Sensor-Config mit enabled=False."""
        sensor = {
            "name": "Diagnostic",
            "key": "diag",
            "enabled": False,
        }
        device_config = {"identifiers": ["test_device"]}

        config = _build_sensor_config(sensor, "test/topic", device_config)

        assert config["enabled_by_default"] is False


class TestPublishing:
    """Test MQTT Publishing."""

    def test_publish_data_success(self, mock_mqtt_client, mqtt_env_vars):
        """Test erfolgreiches Daten-Publishing."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        mqtt_module._mqtt_client = mock_mqtt_client
        mqtt_module._is_connected = True

        data = {"power_input": 4500, "battery_soc": 85.5}
        publish_data(data, "test/topic")

        # Prüfe dass publish aufgerufen wurde
        mock_mqtt_client.publish.assert_called_once()
        call_args = mock_mqtt_client.publish.call_args

        assert call_args[0][0] == "test/topic"
        payload = json.loads(call_args[0][1])
        assert payload["power_input"] == 4500
        assert payload["battery_soc"] == 85.5
        assert "last_update" in payload

    def test_publish_data_not_connected(self):
        """Test Publishing wenn nicht verbunden."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        mqtt_module._is_connected = False

        with pytest.raises(ConnectionError, match="MQTT not connected"):
            publish_data({"test": 123}, "test/topic")

    def test_publish_status_online(self, mock_mqtt_client, mqtt_env_vars):
        """Test Status-Publishing (online)."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        mqtt_module._mqtt_client = mock_mqtt_client
        mqtt_module._is_connected = True

        publish_status("online", "test/topic")

        mock_mqtt_client.publish.assert_called_once_with(
            "test/topic/status", "online", qos=1, retain=True
        )

    def test_publish_status_not_connected(self, mock_mqtt_client):
        """Test Status-Publishing wenn nicht verbunden."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        mqtt_module._is_connected = False

        # Sollte keine Exception werfen, nur Warning loggen
        publish_status("online", "test/topic")
        mock_mqtt_client.publish.assert_not_called()

    def test_publish_data_publish_exception(self, mock_mqtt_client, mqtt_env_vars):
        import modbus_energy_meter.mqtt_client as mqtt_module

        mqtt_module._mqtt_client = mock_mqtt_client
        mqtt_module._is_connected = True

        mock_mqtt_client.publish.side_effect = Exception("Test error")

        with pytest.raises(Exception, match="Test error"):
            publish_data({"test": 123}, "test/topic")

    def test_publish_status_publish_exception(
        self, mock_mqtt_client, mqtt_env_vars, caplog
    ):
        """Test Exception-Handling bei Status-Publish-Fehler."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        mqtt_module._mqtt_client = mock_mqtt_client
        mqtt_module._is_connected = True

        # Mock publish wirft Exception
        mock_mqtt_client.publish.side_effect = Exception("Network timeout")

        # Exception wird gefangen und geloggt (nicht geworfen)
        publish_status("online", "test/topic")

        # Prüfe dass Error geloggt wurde
        assert "Status publish failed" in caplog.text
        assert "Network timeout" in caplog.text

    def test_publish_data_with_debug_logging(
        self, mock_mqtt_client, mqtt_env_vars, caplog
    ):
        """Test Debug-Logging bei publish_data."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        mqtt_module._mqtt_client = mock_mqtt_client
        mqtt_module._is_connected = True

        # DEBUG-Level aktivieren
        caplog.set_level(logging.DEBUG, logger="huawei.mqtt")

        data = {"power_active": 4500, "meter_power_active": -200, "battery_power": 800}

        publish_data(data, "test/topic")

        # Prüfe dass DEBUG-Log ausgegeben wurde
        assert "Publishing: Solar=4500W" in caplog.text
        assert "Grid=-200W" in caplog.text
        assert "Battery=800W" in caplog.text


class TestDiscovery:
    """Test MQTT Discovery."""

    def test_publish_discovery_configs(self, mock_mqtt_client, mqtt_env_vars):
        """Test Discovery-Config Publishing."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        mqtt_module._mqtt_client = mock_mqtt_client
        mqtt_module._is_connected = True

        with patch(
            "modbus_energy_meter.mqtt_client._load_numeric_sensors"
        ) as mock_numeric:
            with patch(
                "modbus_energy_meter.mqtt_client._load_text_sensors"
            ) as mock_text:
                mock_numeric.return_value = [{"name": "Test", "key": "test"}]
                mock_text.return_value = []

                publish_discovery_configs("test/topic")

                # Mindestens 2 Publishes: 1 Sensor + 1 Binary Sensor
                assert mock_mqtt_client.publish.call_count >= 2

    def test_publish_discovery_not_connected(self, mock_mqtt_client):
        """Test Discovery wenn nicht verbunden."""
        import modbus_energy_meter.mqtt_client as mqtt_module

        mqtt_module._is_connected = False

        publish_discovery_configs("test/topic")

        # Sollte nichts publizieren
        mock_mqtt_client.publish.assert_not_called()
