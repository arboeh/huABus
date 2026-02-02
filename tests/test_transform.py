# tests\test_transform.py

"""Tests for transform.py - Data transformation functions."""

import time
from unittest.mock import Mock

import pytest  # type: ignore
from modbus_energy_meter.transform import _cleanup_result, get_value, transform_data


class TestGetValue:
    """Test value extraction and filtering."""

    def test_none_passthrough(self):
        """None should pass through unchanged."""
        assert get_value(None) is None

    def test_register_value_extraction(self):
        """Extract .value from RegisterValue objects."""
        mock_register = Mock()
        mock_register.value = 4500
        assert get_value(mock_register) == 4500

    @pytest.mark.parametrize("invalid_value", [65535, 32767, -32768])
    def test_invalid_modbus_values_filtered(self, invalid_value):
        """Invalid Modbus placeholder values should become None."""
        assert get_value(invalid_value) is None

    def test_valid_numeric_passthrough(self):
        """Valid numbers should pass through unchanged."""
        assert get_value(4500) == 4500
        assert get_value(85.5) == 85.5
        assert get_value(0) == 0
        assert get_value(-100) == -100

    def test_datetime_conversion(self):
        """datetime objects should be converted to ISO format."""
        from datetime import datetime

        dt = datetime(2026, 2, 1, 18, 30, 0)
        result = get_value(dt)
        assert result == "2026-02-01T18:30:00"


class TestCleanupResult:
    """Test result cleanup and timestamp addition."""

    def test_remove_none_values(self):
        """None values should be removed from result."""
        input_data = {
            "power_active": 4500,
            "alarm1": None,
            "battery_soc": 85.5,
            "missing": None,
        }
        result = _cleanup_result(input_data)

        assert "power_active" in result
        assert "battery_soc" in result
        assert "alarm1" not in result
        assert "missing" not in result

    def test_timestamp_added(self):
        """last_update timestamp should be added."""
        input_data = {"power_active": 4500}
        before = time.time()
        result = _cleanup_result(input_data)
        after = time.time()

        assert "last_update" in result
        assert before <= result["last_update"] <= after

    def test_empty_dict(self):
        """Empty dict should get only timestamp."""
        result = _cleanup_result({})
        assert len(result) == 1
        assert "last_update" in result


class TestTransformData:
    """Test complete data transformation pipeline."""

    def test_transform_with_register_values(self, mocker):
        """Transform RegisterValue objects to MQTT format."""
        # Mock REGISTER_MAPPING
        mock_mapping = {
            "activepower": "power_active",
            "inputpower": "power_input",
        }
        mocker.patch("modbus_energy_meter.transform.REGISTER_MAPPING", mock_mapping)
        mocker.patch("modbus_energy_meter.transform.CRITICAL_DEFAULTS", {})

        # Create mock RegisterValue objects
        mock_active = Mock()
        mock_active.value = 4500
        mock_input = Mock()
        mock_input.value = 4800

        input_data = {
            "activepower": mock_active,
            "inputpower": mock_input,
        }

        result = transform_data(input_data)

        assert result["power_active"] == 4500
        assert result["power_input"] == 4800
        assert "last_update" in result

    def test_transform_filters_invalid_values(self, mocker):
        """Invalid Modbus values should be filtered out."""
        mock_mapping = {
            "activepower": "power_active",
            "alarm1": "alarm_1",
        }
        mocker.patch("modbus_energy_meter.transform.REGISTER_MAPPING", mock_mapping)
        mocker.patch("modbus_energy_meter.transform.CRITICAL_DEFAULTS", {})

        mock_active = Mock()
        mock_active.value = 4500
        mock_alarm = Mock()
        mock_alarm.value = 65535  # Invalid

        input_data = {
            "activepower": mock_active,
            "alarm1": mock_alarm,
        }

        result = transform_data(input_data)

        assert result["power_active"] == 4500
        assert "alarm_1" not in result  # Filtered out

    def test_transform_applies_critical_defaults(self, mocker):
        """Missing critical values should get defaults."""
        mock_mapping = {"activepower": "power_active"}
        mock_defaults = {"battery_power": 0}

        mocker.patch("modbus_energy_meter.transform.REGISTER_MAPPING", mock_mapping)
        mocker.patch("modbus_energy_meter.transform.CRITICAL_DEFAULTS", mock_defaults)

        mock_active = Mock()
        mock_active.value = 4500

        input_data = {"activepower": mock_active}

        result = transform_data(input_data)

        assert result["power_active"] == 4500
        assert result["battery_power"] == 0  # Default applied

    def test_transform_empty_input(self, mocker):
        """Empty input should return only timestamp."""
        mocker.patch("modbus_energy_meter.transform.REGISTER_MAPPING", {})
        mocker.patch("modbus_energy_meter.transform.CRITICAL_DEFAULTS", {})

        result = transform_data({})

        assert len(result) == 1
        assert "last_update" in result
