# tests/conftest.py

"""Pytest Configuration and shared fixtures."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

# Füge den huawei_solar_modbus_mqtt Ordner hinzu
addon_path = Path(__file__).parent.parent / "huawei_solar_modbus_mqtt"
sys.path.insert(0, str(addon_path))

from bridge.total_increasing_filter import reset_filter  # noqa: E402

# ---------------------------------------------------------------------------
# Autouse: Filter-Singleton vor/nach jedem Test zurücksetzen
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances before each test."""
    reset_filter()
    yield
    reset_filter()


# ---------------------------------------------------------------------------
# Config-Mock – deckt alle Tests in test_main.py und test_log_cycle_summary.py ab
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config():
    config = Mock()
    config.log_level = "INFO"
    config.modbus_host = "192.168.1.100"
    config.modbus_port = 502
    config.modbus_auto_detect_slave_id = False
    config.slave_id = 1
    config.mqtt_host = "localhost"
    config.mqtt_port = 1883
    config.mqtt_topic = "huawei-solar"
    config.mqtt_user = None
    config.mqtt_password = None
    config.poll_interval = 30
    config.status_timeout = 180
    config.enable_batching = True
    config.batch_max_gap = 50
    return config


@pytest.fixture
def mock_client():
    """AsyncMock für AsyncHuaweiSolar Client."""
    return AsyncMock()


# ---------------------------------------------------------------------------
# Config-Datei (tmp_path-basiert) für ConfigManager-Integrationstests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config_file(tmp_path):
    """Create a temporary config file with test data."""
    config_data = {
        "modbus": {
            "host": "192.0.2.100",
            "port": 502,
            "auto_detect_slave_id": False,
            "slave_id": 1,
        },
        "mqtt": {
            "broker": "192.0.2.1",
            "port": 1883,
            "username": None,
            "password": None,
            "topic_prefix": "test-topic",
            "discovery": True,
        },
        "advanced": {
            "log_level": "INFO",
            "status_timeout": 180,
            "poll_interval": 30,
        },
    }
    config_file = tmp_path / "options.json"
    config_file.write_text(json.dumps(config_data))
    return config_file
