# tests/test_mqtt_client.py

"""Tests für MQTT Client Manager."""

import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from bridge.mqtt_client import (
    _build_sensor_config,
    _get_mqtt_client,
    _load_numeric_sensors,
    _load_text_sensors,
    _on_connect,
    _on_disconnect,
    connect_mqtt,
    disconnect_mqtt,
    publish_data,
    publish_discovery_configs,
    publish_status,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_mqtt_client():
    with patch("bridge.mqtt_client.mqtt.Client") as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        publish_result = MagicMock()
        publish_result.wait_for_publish = MagicMock()
        client_instance.publish.return_value = publish_result
        yield client_instance


@pytest.fixture
def mqtt_env_vars(monkeypatch):
    monkeypatch.setenv("HUAWEI_MQTT_HOST", "localhost")
    monkeypatch.setenv("HUAWEI_MQTT_PORT", "1883")
    monkeypatch.setenv("HUAWEI_MQTT_TOPIC", "test/huawei")
    monkeypatch.setenv("HUAWEI_MQTT_USER", "testuser")
    monkeypatch.setenv("HUAWEI_MQTT_PASSWORD", "testpass")


@pytest.fixture(autouse=True)
def reset_mqtt_globals():
    import bridge.mqtt_client as mqtt_module

    mqtt_module._mqtt_client = None
    mqtt_module._is_connected = False
    yield
    mqtt_module._mqtt_client = None
    mqtt_module._is_connected = False


# ---------------------------------------------------------------------------
# TestCallbacks
# ---------------------------------------------------------------------------


class TestCallbacks:
    """MQTT Callback-Funktionen."""

    def test_on_connect_success_sets_connected(self):
        import bridge.mqtt_client as mqtt_module

        _on_connect(None, None, None, 0)
        assert mqtt_module._is_connected is True

    def test_on_connect_failure_leaves_disconnected(self):
        import bridge.mqtt_client as mqtt_module

        _on_connect(None, None, None, 5)
        assert mqtt_module._is_connected is False

    def test_on_disconnect_clears_connected_flag(self):
        import bridge.mqtt_client as mqtt_module

        mqtt_module._is_connected = True
        _on_disconnect(None, None, None, 0)
        assert mqtt_module._is_connected is False

    def test_on_disconnect_unexpected_also_clears_flag(self):
        import bridge.mqtt_client as mqtt_module

        mqtt_module._is_connected = True
        _on_disconnect(None, None, None, 1)
        assert mqtt_module._is_connected is False


# ---------------------------------------------------------------------------
# TestClientCreation
# ---------------------------------------------------------------------------


class TestClientCreation:
    """MQTT Client Erstellung und Singleton-Verhalten."""

    def test_get_mqtt_client_creates_new_instance(self, mock_mqtt_client, mqtt_env_vars):
        with patch("bridge.mqtt_client.mqtt.Client") as mock_client:
            mock_client.return_value = mock_mqtt_client
            client = _get_mqtt_client()
            assert client is not None
            mock_client.assert_called_once()

    def test_get_mqtt_client_returns_existing_singleton(self, mock_mqtt_client, mqtt_env_vars):
        import bridge.mqtt_client as mqtt_module

        with patch("bridge.mqtt_client.mqtt.Client") as mock_client:
            mock_client.return_value = mock_mqtt_client
            mqtt_module._mqtt_client = mock_mqtt_client
            client = _get_mqtt_client()
            mock_client.assert_not_called()
            assert client is mock_mqtt_client

    def test_get_mqtt_client_sets_auth_credentials(self, mock_mqtt_client, mqtt_env_vars):
        with patch("bridge.mqtt_client.mqtt.Client") as mock_client:
            mock_client.return_value = mock_mqtt_client
            _get_mqtt_client()
            mock_mqtt_client.username_pw_set.assert_called_once_with("testuser", "testpass")

    def test_get_mqtt_client_sets_last_will(self, mock_mqtt_client, mqtt_env_vars):
        with patch("bridge.mqtt_client.mqtt.Client") as mock_client:
            mock_client.return_value = mock_mqtt_client
            _get_mqtt_client()
            mock_mqtt_client.will_set.assert_called_once_with("test/huawei/status", "offline", qos=1, retain=True)


# ---------------------------------------------------------------------------
# TestConnect
# ---------------------------------------------------------------------------


class TestConnect:
    """MQTT Verbindungsaufbau."""

    def test_connect_mqtt_calls_connect_and_loop_start(self, mock_mqtt_client, mqtt_env_vars):
        import bridge.mqtt_client as mqtt_module

        with patch("bridge.mqtt_client.mqtt.Client") as mock_client:
            mock_client.return_value = mock_mqtt_client

            def set_connected(*args):
                mqtt_module._is_connected = True

            mock_mqtt_client.connect.side_effect = set_connected
            connect_mqtt()

            mock_mqtt_client.connect.assert_called_once_with("localhost", 1883, 60)
            mock_mqtt_client.loop_start.assert_called_once()

    def test_connect_mqtt_raises_without_broker(self, mock_mqtt_client, monkeypatch):
        monkeypatch.delenv("HUAWEI_MQTT_HOST", raising=False)
        with pytest.raises(RuntimeError, match="MQTT broker not configured"):
            connect_mqtt()

    def test_connect_mqtt_raises_on_timeout(self, mock_mqtt_client, mqtt_env_vars):
        import bridge.mqtt_client as mqtt_module

        with patch("bridge.mqtt_client.mqtt.Client") as mock_client:
            mock_client.return_value = mock_mqtt_client
            mqtt_module._is_connected = False
            with patch("bridge.mqtt_client.time.sleep"):
                with pytest.raises(ConnectionError, match="MQTT connection timeout"):
                    connect_mqtt()


# ---------------------------------------------------------------------------
# TestDisconnect
# ---------------------------------------------------------------------------


class TestDisconnect:
    """MQTT Trennung."""

    def test_disconnect_when_connected_publishes_and_cleans_up(self, mock_mqtt_client, mqtt_env_vars):
        import bridge.mqtt_client as mqtt_module

        mqtt_module._mqtt_client = mock_mqtt_client
        mqtt_module._is_connected = True

        disconnect_mqtt()

        mock_mqtt_client.publish.assert_called_once()
        mock_mqtt_client.loop_stop.assert_called_once()
        mock_mqtt_client.disconnect.assert_called_once()
        assert mqtt_module._mqtt_client is None
        assert mqtt_module._is_connected is False

    def test_disconnect_when_not_connected_is_safe(self):
        disconnect_mqtt()  # Should not raise


# ---------------------------------------------------------------------------
# TestSensorConfig
# ---------------------------------------------------------------------------


class TestSensorConfig:
    """Sensor-Konfiguration für MQTT Discovery."""

    def test_basic_sensor_config(self):
        device_config = {"identifiers": ["test_device"]}
        config = _build_sensor_config(
            {"name": "Test Sensor", "key": "test_key"},
            "test/topic",
            device_config,
        )
        assert config["name"] == "Test Sensor"
        assert config["unique_id"] == "huawei_solar_test_key"
        assert config["state_topic"] == "test/topic"
        assert "{{ value_json.test_key }}" in config["value_template"]

    def test_sensor_config_with_unit_and_device_class(self):
        device_config = {"identifiers": ["test_device"]}
        config = _build_sensor_config(
            {"name": "Power", "key": "power", "unit_of_measurement": "W", "device_class": "power"},
            "test/topic",
            device_config,
        )
        assert config["unit_of_measurement"] == "W"
        assert config["device_class"] == "power"

    def test_sensor_config_disabled_by_default(self):
        device_config = {"identifiers": ["test_device"]}
        config = _build_sensor_config(
            {"name": "Diagnostic", "key": "diag", "enabled": False},
            "test/topic",
            device_config,
        )
        assert config["enabled_by_default"] is False


# ---------------------------------------------------------------------------
# TestPublishing
# ---------------------------------------------------------------------------


class TestPublishing:
    """MQTT Publishing von Daten und Status."""

    def test_publish_data_sends_correct_payload(self, mock_mqtt_client, mqtt_env_vars):
        import bridge.mqtt_client as mqtt_module

        mqtt_module._mqtt_client = mock_mqtt_client
        mqtt_module._is_connected = True

        publish_data({"power_input": 4500, "battery_soc": 85.5}, "test/topic")

        mock_mqtt_client.publish.assert_called_once()
        call_args = mock_mqtt_client.publish.call_args
        assert call_args[0][0] == "test/topic"
        payload = json.loads(call_args[0][1])
        assert payload["power_input"] == 4500
        assert payload["battery_soc"] == 85.5
        assert "last_update" in payload

    def test_publish_data_raises_when_not_connected(self):
        import bridge.mqtt_client as mqtt_module

        mqtt_module._is_connected = False
        with pytest.raises(ConnectionError, match="MQTT not connected"):
            publish_data({"test": 123}, "test/topic")

    def test_publish_data_propagates_exception(self, mock_mqtt_client, mqtt_env_vars):
        import bridge.mqtt_client as mqtt_module

        mqtt_module._mqtt_client = mock_mqtt_client
        mqtt_module._is_connected = True
        mock_mqtt_client.publish.side_effect = Exception("Test error")
        with pytest.raises(Exception, match="Test error"):
            publish_data({"test": 123}, "test/topic")

    def test_publish_data_logs_debug_info(self, mock_mqtt_client, mqtt_env_vars, caplog):
        import bridge.mqtt_client as mqtt_module

        mqtt_module._mqtt_client = mock_mqtt_client
        mqtt_module._is_connected = True
        caplog.set_level(logging.DEBUG, logger="huawei.mqtt")

        publish_data(
            {"power_active": 4500, "meter_power_active": -200, "battery_power": 800},
            "test/topic",
        )

        assert "Publishing: Solar=4500W" in caplog.text
        assert "Grid=-200W" in caplog.text
        assert "Battery=800W" in caplog.text

    def test_publish_status_online(self, mock_mqtt_client, mqtt_env_vars):
        import bridge.mqtt_client as mqtt_module

        mqtt_module._mqtt_client = mock_mqtt_client
        mqtt_module._is_connected = True

        publish_status("online", "test/topic")

        mock_mqtt_client.publish.assert_called_once_with("test/topic/status", "online", qos=1, retain=True)

    def test_publish_status_skips_when_not_connected(self, mock_mqtt_client):
        import bridge.mqtt_client as mqtt_module

        mqtt_module._is_connected = False
        publish_status("online", "test/topic")
        mock_mqtt_client.publish.assert_not_called()

    def test_publish_status_logs_exception_without_raising(self, mock_mqtt_client, mqtt_env_vars, caplog):
        import bridge.mqtt_client as mqtt_module

        mqtt_module._mqtt_client = mock_mqtt_client
        mqtt_module._is_connected = True
        mock_mqtt_client.publish.side_effect = Exception("Network timeout")

        publish_status("online", "test/topic")

        assert "Status publish failed" in caplog.text
        assert "Network timeout" in caplog.text


# ---------------------------------------------------------------------------
# TestDiscovery
# ---------------------------------------------------------------------------


class TestDiscovery:
    """MQTT Discovery Config Publishing."""

    def test_publish_discovery_configs_publishes_sensors(self, mock_mqtt_client, mqtt_env_vars):
        import bridge.mqtt_client as mqtt_module

        mqtt_module._mqtt_client = mock_mqtt_client
        mqtt_module._is_connected = True

        with patch("bridge.mqtt_client._load_numeric_sensors", return_value=[{"name": "Test", "key": "test"}]):
            with patch("bridge.mqtt_client._load_text_sensors", return_value=[]):
                publish_discovery_configs("test/topic")
                assert mock_mqtt_client.publish.call_count >= 2

    def test_publish_discovery_skips_when_not_connected(self, mock_mqtt_client):
        import bridge.mqtt_client as mqtt_module

        mqtt_module._is_connected = False
        publish_discovery_configs("test/topic")
        mock_mqtt_client.publish.assert_not_called()


# ---------------------------------------------------------------------------
# TestSensorLoaders
# ---------------------------------------------------------------------------


class TestSensorLoaders:
    """Sensor-Listen-Loader."""

    def test_load_numeric_sensors_returns_list(self):
        assert isinstance(_load_numeric_sensors(), list)

    def test_load_text_sensors_returns_list(self):
        assert isinstance(_load_text_sensors(), list)
