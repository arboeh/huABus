# tests/test_config_manager.py

"""Tests for ConfigManager."""

import json

import pytest
from bridge.config_manager import ConfigManager


class TestConfigManagerLoading:
    """Test configuration loading from different sources."""

    def test_load_from_file_flat_structure(self, tmp_path):
        """Should load flat config from options.json."""
        config_file = tmp_path / "options.json"
        config_data = {
            # Modbus (flat)
            "modbus_host": "192.168.1.200",
            "modbus_port": 502,
            "modbus_auto_detect_slave_id": True,
            "slave_id": 1,
            # MQTT (flat)
            "mqtt_host": "mqtt.example.com",
            "mqtt_port": 1883,
            "mqtt_user": "testuser",
            "mqtt_password": "testpass",
            "mqtt_topic": "test-topic",
            # Advanced (flat)
            "log_level": "DEBUG",
            "status_timeout": 120,
            "poll_interval": 20,
        }
        config_file.write_text(json.dumps(config_data))

        config = ConfigManager(config_path=config_file)

        # Modbus
        assert config.modbus_host == "192.168.1.200"
        assert config.modbus_port == 502
        assert config.modbus_auto_detect_slave_id is True
        assert config.slave_id == 1

        # MQTT
        assert config.mqtt_host == "mqtt.example.com"
        assert config.mqtt_port == 1883
        assert config.mqtt_user == "testuser"
        assert config.mqtt_password == "testpass"
        assert config.mqtt_topic == "test-topic"

        # Advanced
        assert config.log_level == "DEBUG"
        assert config.status_timeout == 120
        assert config.poll_interval == 20

    def test_load_from_env_when_no_file(self, monkeypatch, tmp_path):
        """Should load from ENV when options.json doesn't exist."""
        config_file = tmp_path / "nonexistent.json"

        # Modbus
        monkeypatch.setenv("HUAWEI_MODBUS_HOST", "10.0.0.5")
        monkeypatch.setenv("HUAWEI_MODBUS_PORT", "5020")
        monkeypatch.setenv("HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID", "false")
        monkeypatch.setenv("HUAWEI_SLAVE_ID", "2")

        # MQTT
        monkeypatch.setenv("HUAWEI_MQTT_HOST", "mqtt.local")
        monkeypatch.setenv("HUAWEI_MQTT_PORT", "1884")
        monkeypatch.setenv("HUAWEI_MQTT_USER", "envuser")
        monkeypatch.setenv("HUAWEI_MQTT_PASSWORD", "envpass")
        monkeypatch.setenv("HUAWEI_MQTT_TOPIC", "env-topic")

        # Advanced
        monkeypatch.setenv("HUAWEI_LOG_LEVEL", "ERROR")
        monkeypatch.setenv("HUAWEI_STATUS_TIMEOUT", "90")
        monkeypatch.setenv("HUAWEI_POLL_INTERVAL", "60")

        config = ConfigManager(config_path=config_file)

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


class TestConfigManagerProperties:
    """Test property accessors."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create a ConfigManager with test data."""
        config_file = tmp_path / "options.json"
        config_data = {
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
        }
        config_file.write_text(json.dumps(config_data))
        return ConfigManager(config_path=config_file)

    def test_modbus_properties(self, config):
        """Test modbus property accessors."""
        assert config.modbus_host == "192.168.1.100"
        assert config.modbus_port == 502
        assert config.modbus_auto_detect_slave_id is False
        assert config.slave_id == 5

    def test_mqtt_properties(self, config):
        """Test MQTT property accessors."""
        assert config.mqtt_host == "mqtt.test"
        assert config.mqtt_port == 1883
        assert config.mqtt_user == "user"
        assert config.mqtt_password == "pass"
        assert config.mqtt_topic == "test"

    def test_advanced_properties(self, config):
        """Test advanced property accessors."""
        assert config.log_level == "WARNING"
        assert config.status_timeout == 200
        assert config.poll_interval == 45

    def test_mqtt_user_returns_none_for_empty_string(self, tmp_path):
        """Should return None for empty username."""
        config_file = tmp_path / "options.json"
        config_data = {
            "modbus_host": "192.168.1.100",
            "modbus_port": 502,
            "modbus_auto_detect_slave_id": True,
            "slave_id": 1,
            "mqtt_host": "localhost",
            "mqtt_port": 1883,
            "mqtt_user": "",  # Empty string
            "mqtt_password": "",  # Empty string
            "mqtt_topic": "test",
            "log_level": "INFO",
            "status_timeout": 180,
            "poll_interval": 30,
        }
        config_file.write_text(json.dumps(config_data))
        config = ConfigManager(config_path=config_file)

        assert config.mqtt_user is None
        assert config.mqtt_password is None


class TestConfigManagerValidation:
    """Test configuration validation."""

    def test_validate_valid_config(self, tmp_path):
        """Should validate a correct config without errors."""
        config_file = tmp_path / "options.json"
        config_data = {
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
        }
        config_file.write_text(json.dumps(config_data))
        config = ConfigManager(config_path=config_file)

        errors = config.validate()
        assert len(errors) == 0

    def test_validate_missing_required_fields(self, tmp_path):
        """Should detect empty required fields."""
        config_file = tmp_path / "options.json"
        config_data = {
            "modbus_host": "",  # LEER statt fehlend!
            "mqtt_host": "",  # LEER!
            "mqtt_topic": "",  # LEER!
        }
        config_file.write_text(json.dumps(config_data))
        config = ConfigManager(config_path=config_file)

        errors = config.validate()
        assert len(errors) >= 3  # Mindestens 3 Fehler

        # Prüfe dass die Errors zu leeren Strings gehören
        error_text = " ".join(errors)
        assert "required" in error_text.lower()

    def test_validate_invalid_port_ranges(self, tmp_path):
        """Should detect invalid port numbers."""
        config_file = tmp_path / "options.json"
        config_data = {
            "modbus_host": "192.168.1.100",
            "modbus_port": 99999,  # Invalid!
            "mqtt_host": "localhost",
            "mqtt_port": 0,  # Invalid!
            "mqtt_topic": "test",
        }
        config_file.write_text(json.dumps(config_data))
        config = ConfigManager(config_path=config_file)

        errors = config.validate()
        assert len(errors) >= 2
        assert any("modbus_port" in err for err in errors)
        assert any("mqtt_port" in err for err in errors)

    def test_validate_invalid_log_level(self, tmp_path):
        """Should detect invalid log level."""
        config_file = tmp_path / "options.json"
        config_data = {
            "modbus_host": "192.168.1.100",
            "mqtt_host": "localhost",
            "mqtt_topic": "test",
            "log_level": "INVALID",  # Not in list!
        }
        config_file.write_text(json.dumps(config_data))
        config = ConfigManager(config_path=config_file)

        errors = config.validate()
        assert any("log_level" in err for err in errors)


class TestConfigManagerEnvParsing:
    """Test environment variable parsing helpers."""

    def test_parse_bool_env_true_values(self, monkeypatch):
        """Should parse various true values."""
        for true_val in ["true", "True", "TRUE", "yes", "YES", "1", "on", "ON"]:
            monkeypatch.setenv("TEST_BOOL", true_val)
            result = ConfigManager._parse_bool_env("TEST_BOOL", default=False)
            assert result is True, f"Failed for value {true_val}"

    def test_parse_bool_env_false_values(self, monkeypatch):
        """Should parse various false values."""
        for false_val in ["false", "False", "FALSE", "no", "NO", "0", "off", "OFF"]:
            monkeypatch.setenv("TEST_BOOL", false_val)
            result = ConfigManager._parse_bool_env("TEST_BOOL", default=True)
            assert result is False, f"Failed for value {false_val}"

    def test_parse_bool_env_uses_default(self, monkeypatch):
        """Should use default when ENV not set."""
        monkeypatch.delenv("TEST_BOOL", raising=False)
        assert ConfigManager._parse_bool_env("TEST_BOOL", default=True) is True
        assert ConfigManager._parse_bool_env("TEST_BOOL", default=False) is False

    def test_parse_int_env_valid_value(self, monkeypatch):
        """Should parse valid integer."""
        monkeypatch.setenv("TEST_INT", "42")
        assert ConfigManager._parse_int_env("TEST_INT", default=0) == 42

    def test_parse_int_env_strips_whitespace(self, monkeypatch):
        """Should strip whitespace."""
        monkeypatch.setenv("TEST_INT", " 123 ")
        assert ConfigManager._parse_int_env("TEST_INT", default=0) == 123

    def test_parse_int_env_invalid_value_uses_default(self, monkeypatch, caplog):
        """Should use default for invalid integer."""
        monkeypatch.setenv("TEST_INT", "notanumber")
        result = ConfigManager._parse_int_env("TEST_INT", default=50)
        assert result == 50
        assert "Invalid integer" in caplog.text


class TestConfigManagerEdgeCases:
    """Test edge cases and error handling."""

    def test_default_config_when_no_file_no_env(self, tmp_path, monkeypatch):
        """Should use all defaults when no file and no ENV."""
        config_file = tmp_path / "nonexistent.json"

        # Clear all relevant ENV vars
        for key in [
            # Modbus
            "HUAWEI_MODBUS_HOST",
            "HUAWEI_MODBUS_PORT",
            "HUAWEI_MODBUS_AUTO_DETECT_SLAVE_ID",
            "HUAWEI_SLAVE_ID",
            # MQTT
            "HUAWEI_MQTT_HOST",
            "HUAWEI_MQTT_PORT",
            "HUAWEI_MQTT_USER",
            "HUAWEI_MQTT_PASSWORD",
            "HUAWEI_MQTT_TOPIC",
            # Advanced
            "HUAWEI_LOG_LEVEL",
            "HUAWEI_STATUS_TIMEOUT",
            "HUAWEI_POLL_INTERVAL",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = ConfigManager(config_path=config_file)

        # All defaults
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

    def test_partial_config_uses_defaults(self, tmp_path):
        """Should use defaults for missing keys."""
        config_file = tmp_path / "options.json"
        partial_config = {
            "modbus_host": "192.168.1.50",
            "mqtt_topic": "partial-topic",
        }
        config_file.write_text(json.dumps(partial_config))
        config = ConfigManager(config_path=config_file)

        # Provided values
        assert config.modbus_host == "192.168.1.50"
        assert config.mqtt_topic == "partial-topic"

        # Defaults
        assert config.modbus_port == 502
        assert config.mqtt_host == "core-mosquitto"
        assert config.log_level == "INFO"

    def test_empty_config_file(self, tmp_path):
        """Should handle empty config file."""
        config_file = tmp_path / "options.json"
        config_file.write_text("{}")
        config = ConfigManager(config_path=config_file)

        # Should use all defaults
        assert config.modbus_host == "192.168.1.100"
        assert config.mqtt_host == "core-mosquitto"

    def test_repr_does_not_leak_password(self, tmp_path):
        """repr() should not contain password."""
        config_file = tmp_path / "options.json"
        config_data = {
            "modbus_host": "192.168.1.100",
            "mqtt_host": "localhost",
            "mqtt_user": "user",
            "mqtt_password": "secret123",
            "mqtt_topic": "test",
        }
        config_file.write_text(json.dumps(config_data))
        config = ConfigManager(config_path=config_file)

        repr_str = repr(config)
        assert "secret123" not in repr_str
        assert "192.168.1.100" in repr_str
        assert "localhost" in repr_str


class TestConfigManagerLogConfig:
    """Test configuration logging."""

    def test_log_config_shows_all_sections(self, tmp_path, caplog):
        """Should log all configuration sections."""
        import logging

        caplog.set_level(logging.DEBUG)

        config_file = tmp_path / "options.json"
        config_data = {
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
        }
        config_file.write_text(json.dumps(config_data))
        config = ConfigManager(config_path=config_file)

        config.log_config()

        # Präzise: Nur die Nachrichten der Records
        messages = [record.message for record in caplog.records]

        # Modbus section
        assert "192.168.1.100" in " ".join(messages)
        assert "502" in " ".join(messages)
        assert "Slave ID: 2" in " ".join(messages)

        # MQTT section
        assert "mqtt.test" in " ".join(messages)
        assert "1883" in " ".join(messages)
        assert "huawei" in " ".join(messages)

        # Advanced section
        assert "DEBUG" in " ".join(messages)
        assert "120" in " ".join(messages)
        assert "25" in " ".join(messages)

    def test_log_config_shows_auth_none_when_no_credentials(self, tmp_path, caplog):
        """Should show 'Auth: None' when no username/password."""
        import logging

        caplog.set_level(logging.DEBUG)

        config_file = tmp_path / "options.json"
        config_data = {
            "modbus_host": "192.168.1.100",
            "mqtt_host": "localhost",
            "mqtt_topic": "test",
            "mqtt_user": "",  # Empty = None
            "mqtt_password": "",
        }
        config_file.write_text(json.dumps(config_data))
        config = ConfigManager(config_path=config_file)

        config.log_config()

        assert "Auth: None" in caplog.text


class TestConfigManagerConsistency:
    """Test consistency between different configuration sources."""

    def test_env_and_file_produce_same_result(self, tmp_path, monkeypatch):
        """ENV variables should map to same keys as options.json.

        This test ensures that the mapping between ENV variable names
        and dictionary keys is consistent, preventing bugs where
        config from file works but config from ENV doesn't.
        """
        # Test-Werte
        test_values = {
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

        # 1. Config aus options.json laden
        config_file = tmp_path / "options.json"
        config_file.write_text(json.dumps(test_values))
        config_from_file = ConfigManager(config_path=config_file)

        # 2. Config aus ENV laden
        env_mapping = {
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
        }

        for key, value in env_mapping.items():
            monkeypatch.setenv(key, value)

        config_from_env = ConfigManager(config_path=tmp_path / "nonexistent.json")

        # 3. Beide müssen identisch sein!
        assert config_from_file.modbus_host == config_from_env.modbus_host
        assert config_from_file.modbus_port == config_from_env.modbus_port
        assert config_from_file.modbus_auto_detect_slave_id == config_from_env.modbus_auto_detect_slave_id
        assert config_from_file.slave_id == config_from_env.slave_id
        assert config_from_file.mqtt_host == config_from_env.mqtt_host
        assert config_from_file.mqtt_port == config_from_env.mqtt_port
        assert config_from_file.mqtt_user == config_from_env.mqtt_user
        assert config_from_file.mqtt_password == config_from_env.mqtt_password
        assert config_from_file.mqtt_topic == config_from_env.mqtt_topic
        assert config_from_file.log_level == config_from_env.log_level
        assert config_from_file.status_timeout == config_from_env.status_timeout
        assert config_from_file.poll_interval == config_from_env.poll_interval

    def test_modbus_auto_detect_slave_id_boolean_logic(self, tmp_path):
        """Specifically test that modbus_auto_detect_slave_id works correctly.

        This was the original bug - auto_detect was always True regardless
        of configuration due to incorrect ENV variable name mapping.
        """
        # Test 1: auto_detect = True (default)
        config_file_true = tmp_path / "options_true.json"
        config_file_true.write_text(json.dumps({"modbus_auto_detect_slave_id": True, "slave_id": 1}))
        config_true = ConfigManager(config_path=config_file_true)
        assert config_true.modbus_auto_detect_slave_id is True

        # Test 2: auto_detect = False (manual slave ID)
        config_file_false = tmp_path / "options_false.json"
        config_file_false.write_text(json.dumps({"modbus_auto_detect_slave_id": False, "slave_id": 42}))
        config_false = ConfigManager(config_path=config_file_false)
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
        """Test each ENV variable individually maps to correct dict key.

        This parametrized test validates every single ENV→dict mapping,
        making it impossible for inconsistencies to slip through.
        """
        # Setze nur diese eine ENV-Variable
        monkeypatch.setenv(env_var, test_value)

        config = ConfigManager(config_path=tmp_path / "nonexistent.json")

        # Prüfe dass der dict_key im internen Config existiert
        assert dict_key in config._config, f"Key '{dict_key}' not found in config"

        # Prüfe dass der Wert korrekt gemappt wurde
        actual = config._config[dict_key]
        assert actual == expected, f"ENV {env_var}={test_value} → expected {expected}, got {actual}"
