# tests/test_transform.py

"""Tests for transform.py - Data transformation functions."""

import time
from datetime import datetime
from unittest.mock import Mock

import pytest
from bridge.transform import _cleanup_result, get_value, transform_data

# ---------------------------------------------------------------------------
# TestGetValue
# ---------------------------------------------------------------------------


class TestGetValue:
    """Wertextraktion und Filterung ungültiger Modbus-Werte."""

    def test_none_passes_through(self):
        """None bleibt unverändert."""
        assert get_value(None) is None

    def test_register_value_extracted(self):
        """Gibt .value eines RegisterValue-Objekts zurück."""
        mock_register = Mock()
        mock_register.value = 4500
        assert get_value(mock_register) == 4500

    @pytest.mark.parametrize("invalid_value", [65535, 32767, -32768])
    def test_invalid_modbus_placeholder_becomes_none(self, invalid_value):
        """Bekannte Modbus-Platzhalterwerte werden zu None."""
        assert get_value(invalid_value) is None

    @pytest.mark.parametrize("valid_value", [4500, 85.5, 0, -100])
    def test_valid_numeric_passes_through(self, valid_value):
        """Gültige numerische Werte werden unverändert weitergegeben."""
        assert get_value(valid_value) == valid_value

    def test_datetime_converted_to_iso_string(self):
        """datetime-Objekte werden in ISO-8601-Format konvertiert."""
        dt = datetime(2026, 2, 1, 18, 30, 0)
        assert get_value(dt) == "2026-02-01T18:30:00"


# ---------------------------------------------------------------------------
# TestCleanupResult
# ---------------------------------------------------------------------------


class TestCleanupResult:
    """Bereinigung des Result-Dicts und Timestamp-Hinzufügung."""

    def test_none_values_removed(self):
        """Keys mit None-Wert werden aus dem Ergebnis entfernt."""
        result = _cleanup_result(
            {
                "power_active": 4500,
                "alarm1": None,
                "battery_soc": 85.5,
                "missing": None,
            }
        )
        assert "power_active" in result
        assert "battery_soc" in result
        assert "alarm1" not in result
        assert "missing" not in result

    def test_last_update_timestamp_added(self):
        """last_update wird mit aktuellem Zeitstempel eingefügt."""
        before = time.time()
        result = _cleanup_result({"power_active": 4500})
        after = time.time()
        assert "last_update" in result
        assert before <= result["last_update"] <= after

    def test_empty_dict_gets_only_timestamp(self):
        """Leeres Dict enthält nach Cleanup nur den Timestamp."""
        result = _cleanup_result({})
        assert len(result) == 1
        assert "last_update" in result


# ---------------------------------------------------------------------------
# TestTransformData
# ---------------------------------------------------------------------------


class TestTransformData:
    """Vollständige Transformations-Pipeline."""

    def test_register_values_mapped_to_mqtt_keys(self, mocker):
        """RegisterValue-Objekte werden über REGISTER_MAPPING in MQTT-Keys umgewandelt."""
        mocker.patch(
            "bridge.transform.REGISTER_MAPPING",
            {
                "activepower": "power_active",
                "inputpower": "power_input",
            },
        )
        mocker.patch("bridge.transform.CRITICAL_DEFAULTS", {})

        mock_active = Mock()
        mock_active.value = 4500
        mock_input = Mock()
        mock_input.value = 4800

        result = transform_data({"activepower": mock_active, "inputpower": mock_input})

        assert result["power_active"] == 4500
        assert result["power_input"] == 4800
        assert "last_update" in result

    def test_invalid_modbus_values_excluded_from_result(self, mocker):
        """Ungültige Modbus-Werte (65535) werden nicht in das Ergebnis übernommen."""
        mocker.patch(
            "bridge.transform.REGISTER_MAPPING",
            {
                "activepower": "power_active",
                "alarm1": "alarm_1",
            },
        )
        mocker.patch("bridge.transform.CRITICAL_DEFAULTS", {})

        mock_active = Mock()
        mock_active.value = 4500
        mock_alarm = Mock()
        mock_alarm.value = 65535

        result = transform_data({"activepower": mock_active, "alarm1": mock_alarm})

        assert result["power_active"] == 4500
        assert "alarm_1" not in result

    def test_critical_defaults_applied_for_missing_keys(self, mocker):
        """Fehlende kritische Keys erhalten ihren Default-Wert."""
        mocker.patch("bridge.transform.REGISTER_MAPPING", {"activepower": "power_active"})
        mocker.patch("bridge.transform.CRITICAL_DEFAULTS", {"battery_power": 0})

        mock_active = Mock()
        mock_active.value = 4500

        result = transform_data({"activepower": mock_active})

        assert result["power_active"] == 4500
        assert result["battery_power"] == 0

    def test_empty_input_returns_only_timestamp(self, mocker):
        """Leere Eingabe ergibt ein Dict mit ausschließlich last_update."""
        mocker.patch("bridge.transform.REGISTER_MAPPING", {})
        mocker.patch("bridge.transform.CRITICAL_DEFAULTS", {})

        result = transform_data({})

        assert len(result) == 1
        assert "last_update" in result
