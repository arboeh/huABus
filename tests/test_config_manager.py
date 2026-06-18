# tests/test_config_manager.py

"""Tests for ConfigManager."""

import json
import logging

import pytest
from bridge.config_manager import ConfigManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(tmp_path, data):
    config_file = tmp_path / "options.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps(data))
    return ConfigManager(config_path=config_file)


# ---------------------------------------------------------------------------
# TestConfigManagerLoading
# ---------------------------------------------------------------------------


class TestConfigManagerLoading:
    """Tests for loading configuration from file and environment."""

    def test_load_from_file(self, tmp_path):
        """Loads all values from a flat options.json."""
        config = _make_config(
            tmp_path,
            {
                "modbus_host": "192.168.1.200",
                "modbus_port": 502,
                "modbus_auto_detect_slave_id": True,
                "slave_id": 1,
                "mqtt_host": "mqtt.example.com",
                "mqtt_port": 1883,
                "mqtt_user": "testuser",
                "mqtt_password": "testpass",
                "mqtt_topic": "test-topic",
                "log_level": "DEBUG",
                "status_timeout": 120,
                "poll_interval": 20,
                "enable_batching": True,
                "batch_max_gap": 50,
            },
        )

        assert config.modbus_host == "192.168.1.200"
        assert config.modbus_port == 502
        assert config.modbus_auto_detect_slave_id is True
        assert config.slave_id == 1
        assert config.mqtt_host == "mqtt.example.com"
        assert config.mqtt_port == 1883
        assert config.mqtt_user == "testuser"
        assert config.mqtt_password == "testpass"
        assert config.mqtt_topic == "test-topic"
        assert config.log_level == "DEBUG"
        assert config.status_timeout == 120
        assert config.poll_interval == 20
        assert config.enable_batching is True
        assert config.batch_max_gap == 50

    def test_load_from_env_when_no_file(self, monkeypatch, tmp_path):
        """Loads all values from environment variables when no file exists."""
        monkeypatch.setenv("HUAWEI_MODBUS_HOST", "10.0.0.5")
        monkeypatch.setenv("HUAWEI_MODBUS_PORT", "5020")
        monkeypatch.setenv("HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID", "false")
        monkeypatch.setenv("HUAWEI_SLAVE_ID", "2")
        monkeypatch.setenv("HUAWEI_MQTT_HOST", "mqtt.local")
        monkeypatch.setenv("HUAWEI_MQTT_PORT", "1884")
        monkeypatch.setenv("HUAWEI_MQTT_USER", "envuser")
        monkeypatch.setenv("HUAWEI_MQTT_PASSWORD", "envpass")
        monkeypatch.setenv("HUAWEI_MQTT_TOPIC", "env-topic")
        monkeypatch.setenv("HUAWEI_LOG_LEVEL", "ERROR")
        monkeypatch.setenv("HUAWEI_STATUS_TIMEOUT", "90")
        monkeypatch.setenv("HUAWEI_POLL_INTERVAL", "60")
        monkeypatch.setenv("HUAWEI_ENABLE_BATCHING", "true")
        monkeypatch.setenv("HUAWEI_BATCH_MAX_GAP", "75")

        config = ConfigManager(config_path=tmp_path / "nonexistent.json")

        assert config.modbus_host == "10.0.0.5"
        assert config.modbus_port == 5020
        assert config.modbus_auto_detect_slave_id is False
        assert config.slave_id == 2
        assert config.mqtt_host == "mqtt.local"
        assert config.mqtt_port == 1884
        assert config.mqtt_user == "envuser"
        assert config.mqtt_password == "envpass"
        assert config.mqtt_topic == "env-topic"
        assert config.log_level == "ERROR"
        assert config.status_timeout == 90
        assert config.poll_interval == 60
        assert config.enable_batching is True
        assert config.batch_max_gap == 75


# ---------------------------------------------------------------------------
# TestConfigManagerProperties
# ---------------------------------------------------------------------------


class TestConfigManagerProperties:
    """Tests for property accessors."""

    @pytest.fixture
    def config(self, tmp_path):
        return _make_config(
            tmp_path,
            {
                "modbus_host": "192.168.1.100",
                "modbus_port": 502,
                "modbus_auto_detect_slave_id": False,
                "slave_id": 5,
                "mqtt_host": "mqtt.test",
                "mqtt_port": 1883,
                "mqtt_user": "user",
                "mqtt_password": "pass",
                "mqtt_topic": "test",
                "log_level": "WARNING",
                "status_timeout": 200,
                "poll_interval": 45,
                "enable_batching": True,
                "batch_max_gap": 100,
            },
        )

    def test_modbus_properties(self, config):
        assert config.modbus_host == "192.168.1.100"
        assert config.modbus_port == 502
        assert config.modbus_auto_detect_slave_id is False
        assert config.slave_id == 5

    def test_mqtt_properties(self, config):
        assert config.mqtt_host == "mqtt.test"
        assert config.mqtt_port == 1883
        assert config.mqtt_user == "user"
        assert config.mqtt_password == "pass"
        assert config.mqtt_topic == "test"

    def test_advanced_properties(self, config):
        assert config.log_level == "WARNING"
        assert config.status_timeout == 200
        assert config.poll_interval == 45
        assert config.enable_batching is True
        assert config.batch_max_gap == 100

    def test_empty_credentials_return_none(self, tmp_path):
        """Empty username and password strings are normalized to None."""
        config = _make_config(
            tmp_path,
            {
                "modbus_host": "192.168.1.100",
                "mqtt_host": "localhost",
                "mqtt_port": 1883,
                "mqtt_user": "",
                "mqtt_password": "",
                "mqtt_topic": "test",
            },
        )
        assert config.mqtt_user is None
        assert config.mqtt_password is None


# ---------------------------------------------------------------------------
# TestConfigManagerValidation
# ---------------------------------------------------------------------------


class TestConfigManagerValidation:
    """Tests for config.validate()."""

    def test_valid_config_has_no_errors(self, tmp_path):
        config = _make_config(
            tmp_path,
            {
                "modbus_host": "192.168.1.100",
                "modbus_port": 502,
                "modbus_auto_detect_slave_id": True,
                "slave_id": 1,
                "mqtt_host": "localhost",
                "mqtt_port": 1883,
                "mqtt_topic": "test",
                "log_level": "INFO",
                "status_timeout": 180,
                "poll_interval": 30,
            },
        )
        assert config.validate() == []

    def test_empty_required_fields_produce_errors(self, tmp_path):
        config = _make_config(tmp_path, {"modbus_host": "", "mqtt_host": "", "mqtt_topic": ""})
        errors = config.validate()
        assert len(errors) >= 3
        assert "required" in " ".join(errors).lower()

    def test_invalid_port_ranges_produce_errors(self, tmp_path):
        config = _make_config(
            tmp_path,
            {
                "modbus_host": "192.168.1.100",
                "modbus_port": 99999,
                "mqtt_host": "localhost",
                "mqtt_port": 0,
                "mqtt_topic": "test",
            },
        )
        errors = config.validate()
        assert len(errors) >= 2
        assert any("modbus_port" in err for err in errors)
        assert any("mqtt_port" in err for err in errors)

    def test_invalid_log_level_produces_error(self, tmp_path):
        config = _make_config(
            tmp_path,
            {
                "modbus_host": "192.168.1.100",
                "mqtt_host": "localhost",
                "mqtt_topic": "test",
                "log_level": "INVALID",
            },
        )
        assert any("log_level" in err for err in config.validate())

    def test_invalid_batch_max_gap_produces_error(self, tmp_path):
        for value in [0, 10001]:
            config = _make_config(
                tmp_path,
                {
                    "modbus_host": "192.168.1.100",
                    "mqtt_host": "localhost",
                    "mqtt_topic": "test",
                    "batch_max_gap": value,
                },
            )
            assert any("batch_max_gap" in err for err in config.validate())


# ---------------------------------------------------------------------------
# TestConfigManagerEnvParsing
# ---------------------------------------------------------------------------


class TestConfigManagerEnvParsing:
    """Tests for ENV variable parsing helpers."""

    def test_parse_bool_true_values(self, monkeypatch):
        for val in ["true", "True", "TRUE", "yes", "YES", "1", "on", "ON"]:
            monkeypatch.setenv("TEST_BOOL", val)
            assert ConfigManager._parse_bool_env("TEST_BOOL", default=False) is True, f"Failed for: {val}"

    def test_parse_bool_false_values(self, monkeypatch):
        for val in ["false", "False", "FALSE", "no", "NO", "0", "off", "OFF"]:
            monkeypatch.setenv("TEST_BOOL", val)
            assert ConfigManager._parse_bool_env("TEST_BOOL", default=True) is False, f"Failed for: {val}"

    def test_parse_bool_uses_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("TEST_BOOL", raising=False)
        assert ConfigManager._parse_bool_env("TEST_BOOL", default=True) is True
        assert ConfigManager._parse_bool_env("TEST_BOOL", default=False) is False

    def test_parse_int_valid_value(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", "42")
        assert ConfigManager._parse_int_env("TEST_INT", default=0) == 42

    def test_parse_int_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", " 123 ")
        assert ConfigManager._parse_int_env("TEST_INT", default=0) == 123

    def test_parse_int_invalid_uses_default(self, monkeypatch, caplog):
        monkeypatch.setenv("TEST_INT", "notanumber")
        assert ConfigManager._parse_int_env("TEST_INT", default=50) == 50
        assert "Invalid integer" in caplog.text


# ---------------------------------------------------------------------------
# TestConfigManagerEdgeCases
# ---------------------------------------------------------------------------


class TestConfigManagerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_all_defaults_when_no_file_no_env(self, tmp_path, monkeypatch):
        """Uses all built-in defaults when neither file nor ENV is present."""
        for key in [
            "HUAWEI_MODBUS_HOST",
            "HUAWEI_MODBUS_PORT",
            "HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID",
            "HUAWEI_SLAVE_ID",
            "HUAWEI_MQTT_HOST",
            "HUAWEI_MQTT_PORT",
            "HUAWEI_MQTT_USER",
            "HUAWEI_MQTT_PASSWORD",
            "HUAWEI_MQTT_TOPIC",
            "HUAWEI_LOG_LEVEL",
            "HUAWEI_STATUS_TIMEOUT",
            "HUAWEI_POLL_INTERVAL",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = ConfigManager(config_path=tmp_path / "nonexistent.json")

        assert config.modbus_host == "192.168.1.100"
        assert config.modbus_port == 502
        assert config.modbus_auto_detect_slave_id is True
        assert config.slave_id == 1
        assert config.mqtt_host == "core-mosquitto"
        assert config.mqtt_port == 1883
        assert config.mqtt_topic == "huawei-solar"
        assert config.log_level == "INFO"
        assert config.status_timeout == 180
        assert config.poll_interval == 30

    def test_partial_config_fills_missing_with_defaults(self, tmp_path):
        config = _make_config(tmp_path, {"modbus_host": "192.168.1.50", "mqtt_topic": "partial-topic"})
        assert config.modbus_host == "192.168.1.50"
        assert config.mqtt_topic == "partial-topic"
        assert config.modbus_port == 502
        assert config.mqtt_host == "core-mosquitto"
        assert config.log_level == "INFO"

    def test_empty_json_uses_all_defaults(self, tmp_path):
        config = _make_config(tmp_path, {})
        assert config.modbus_host == "192.168.1.100"
        assert config.mqtt_host == "core-mosquitto"

    def test_repr_does_not_leak_password(self, tmp_path):
        config = _make_config(
            tmp_path,
            {
                "modbus_host": "192.168.1.100",
                "mqtt_host": "localhost",
                "mqtt_user": "user",
                "mqtt_password": "secret123",
                "mqtt_topic": "test",
            },
        )
        repr_str = repr(config)
        assert "secret123" not in repr_str
        assert "192.168.1.100" in repr_str
        assert "localhost" in repr_str


# ---------------------------------------------------------------------------
# TestConfigManagerLogConfig
# ---------------------------------------------------------------------------


class TestConfigManagerLogConfig:
    """Tests for config.log_config()."""

    def test_log_config_shows_all_sections(self, tmp_path, caplog):
        caplog.set_level(logging.DEBUG)
        config = _make_config(
            tmp_path,
            {
                "modbus_host": "192.168.1.100",
                "modbus_port": 502,
                "modbus_auto_detect_slave_id": False,
                "slave_id": 2,
                "mqtt_host": "mqtt.test",
                "mqtt_port": 1883,
                "mqtt_user": None,
                "mqtt_password": None,
                "mqtt_topic": "huawei",
                "log_level": "DEBUG",
                "status_timeout": 120,
                "poll_interval": 25,
            },
        )
        config.log_config()

        messages = " ".join(r.message for r in caplog.records)
        assert "192.168.1.100" in messages
        assert "502" in messages
        assert "Slave ID: 2" in messages
        assert "mqtt.test" in messages
        assert "1883" in messages
        assert "huawei" in messages
        assert "DEBUG" in messages
        assert "120" in messages
        assert "25" in messages

    def test_log_config_shows_auth_none_without_credentials(self, tmp_path, caplog):
        caplog.set_level(logging.DEBUG)
        config = _make_config(
            tmp_path,
            {
                "modbus_host": "192.168.1.100",
                "mqtt_host": "localhost",
                "mqtt_topic": "test",
                "mqtt_user": "",
                "mqtt_password": "",
            },
        )
        config.log_config()
        assert "Auth: None" in caplog.text

    def test_log_config_masks_password(self, tmp_path, caplog):
        caplog.set_level(logging.DEBUG)
        config = _make_config(
            tmp_path,
            {
                "modbus_host": "192.168.1.100",
                "mqtt_host": "localhost",
                "mqtt_topic": "test",
                "mqtt_user": "user",
                "mqtt_password": "secret123",
            },
        )
        config.log_config()
        messages = " ".join(r.message for r in caplog.records)
        assert "secret123" not in messages
        assert "***" in messages


# ---------------------------------------------------------------------------
# TestConfigManagerConsistency
# ---------------------------------------------------------------------------


class TestConfigManagerConsistency:
    """Tests for consistency between file and ENV configuration sources."""

    def test_file_and_env_produce_identical_config(self, tmp_path, monkeypatch):
        """File-loaded and ENV-loaded configs must be identical for all keys."""
        values = {
            "modbus_host": "192.168.1.50",
            "modbus_port": 5020,
            "modbus_auto_detect_slave_id": False,
            "slave_id": 42,
            "mqtt_host": "mqtt.test.local",
            "mqtt_port": 1884,
            "mqtt_user": "testuser",
            "mqtt_password": "testpass",
            "mqtt_topic": "test-prefix",
            "log_level": "DEBUG",
            "status_timeout": 120,
            "poll_interval": 45,
        }

        config_from_file = _make_config(tmp_path, values)

        for env_var, val in {
            "HUAWEI_MODBUS_HOST": "192.168.1.50",
            "HUAWEI_MODBUS_PORT": "5020",
            "HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID": "false",
            "HUAWEI_SLAVE_ID": "42",
            "HUAWEI_MQTT_HOST": "mqtt.test.local",
            "HUAWEI_MQTT_PORT": "1884",
            "HUAWEI_MQTT_USER": "testuser",
            "HUAWEI_MQTT_PASSWORD": "testpass",
            "HUAWEI_MQTT_TOPIC": "test-prefix",
            "HUAWEI_LOG_LEVEL": "DEBUG",
            "HUAWEI_STATUS_TIMEOUT": "120",
            "HUAWEI_POLL_INTERVAL": "45",
        }.items():
            monkeypatch.setenv(env_var, val)

        config_from_env = ConfigManager(config_path=tmp_path / "nonexistent.json")

        for attr in [
            "modbus_host",
            "modbus_port",
            "modbus_auto_detect_slave_id",
            "slave_id",
            "mqtt_host",
            "mqtt_port",
            "mqtt_user",
            "mqtt_password",
            "mqtt_topic",
            "log_level",
            "status_timeout",
            "poll_interval",
        ]:
            assert getattr(config_from_file, attr) == getattr(config_from_env, attr), f"Mismatch on: {attr}"

    def test_auto_detect_slave_id_boolean_logic(self, tmp_path):
        """modbus_auto_detect_slave_id is read correctly for both True and False."""
        config_true = _make_config(tmp_path / "true_case", {"modbus_auto_detect_slave_id": True, "slave_id": 1})
        assert config_true.modbus_auto_detect_slave_id is True

        config_false = _make_config(tmp_path / "false_case", {"modbus_auto_detect_slave_id": False, "slave_id": 42})
        assert config_false.modbus_auto_detect_slave_id is False
        assert config_false.slave_id == 42

    @pytest.mark.parametrize(
        "env_var,dict_key,test_value,expected",
        [
            ("HUAWEI_MODBUS_HOST", "modbus_host", "192.168.1.1", "192.168.1.1"),
            ("HUAWEI_MODBUS_PORT", "modbus_port", "5020", 5020),
            ("HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID", "modbus_auto_detect_slave_id", "false", False),
            ("HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID", "modbus_auto_detect_slave_id", "true", True),
            ("HUAWEI_SLAVE_ID", "slave_id", "42", 42),
            ("HUAWEI_MQTT_HOST", "mqtt_host", "mqtt.test", "mqtt.test"),
            ("HUAWEI_MQTT_PORT", "mqtt_port", "1884", 1884),
            ("HUAWEI_MQTT_USER", "mqtt_user", "testuser", "testuser"),
            ("HUAWEI_MQTT_PASSWORD", "mqtt_password", "testpass", "testpass"),
            ("HUAWEI_MQTT_TOPIC", "mqtt_topic", "test", "test"),
            ("HUAWEI_LOG_LEVEL", "log_level", "DEBUG", "DEBUG"),
            ("HUAWEI_STATUS_TIMEOUT", "status_timeout", "120", 120),
            ("HUAWEI_POLL_INTERVAL", "poll_interval", "45", 45),
        ],
    )
    def test_individual_env_mapping(self, monkeypatch, tmp_path, env_var, dict_key, test_value, expected):
        """Each ENV variable maps correctly to its internal config key."""
        monkeypatch.setenv(env_var, test_value)
        config = ConfigManager(config_path=tmp_path / "nonexistent.json")
        assert dict_key in config._config, f"Key '{dict_key}' not found in config"
        assert config._config[dict_key] == expected, (
            f"ENV {env_var}={test_value} -> expected {expected}, got {config._config[dict_key]}"
        )
