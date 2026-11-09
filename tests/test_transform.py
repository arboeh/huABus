# tests/test_transform.py

"""Tests for transform.py - Data transformation functions."""

import time
from datetime import datetime
from unittest.mock import Mock

import pytest
from bridge.transform import _cleanup_result, derive_battery_split, derive_values, get_value, transform_data
from huawei_solar.register_definitions.base import Result
from huawei_solar.register_values import MeterStatus

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


# ---------------------------------------------------------------------------
# TestDeriveValues
# ---------------------------------------------------------------------------
# Vorzeichen-Konvention: Meter > 0 = Einspeisung, Batterie > 0 = Laden.


def _inputs(ac, grid, pv=None, **extra):
    """Baut Eingabewerte fuer derive_values()."""
    values = {"power_active": ac, "meter_power_active": grid}
    if pv is not None:
        values["power_input"] = pv
    values.update(extra)
    return values


class TestDerivePvStringPower:
    """Leistung pro PV-String: U x I."""

    def test_string_power_is_voltage_times_current(self):
        result = derive_values({"voltage_PV1": 400.0, "current_PV1": 5.0})
        assert result["power_PV1"] == 2000.0

    @pytest.mark.parametrize(
        "values",
        [
            {"voltage_PV3": None, "current_PV3": 1.0},
            {"voltage_PV3": 300.0, "current_PV3": None},
            {"voltage_PV3": 300.0},
            {},
        ],
    )
    def test_string_power_missing_without_both_inputs(self, values):
        assert "power_PV3" not in derive_values(values)

    def test_all_four_strings_derived(self):
        values = {f"{kind}_PV{n}": 10.0 for n in range(1, 5) for kind in ("voltage", "current")}
        result = derive_values(values)
        assert [result[f"power_PV{n}"] for n in range(1, 5)] == [100.0] * 4

    def test_bool_input_ignored(self):
        assert "power_PV1" not in derive_values({"voltage_PV1": True, "current_PV1": 5.0})


class TestDeriveHousePower:
    """Hausverbrauch = AC-Ausgang - Netzleistung."""

    @pytest.mark.parametrize(
        ("ac", "grid", "house"),
        [
            (3000, 1000, 2000.0),  # Einspeisung
            (0, -500, 500.0),  # Netzbezug
            (-3000, -3500, 500.0),  # Netzladen der Batterie
            (2000, -300, 2300.0),  # Batterieentladung
            (100, 300, 0.0),  # Messversatz: Untergrenze 0
        ],
    )
    def test_house_power(self, ac, grid, house):
        assert derive_values(_inputs(ac, grid))["power_house"] == house

    def test_missing_meter_gives_no_house_power(self):
        result = derive_values(_inputs(3000, None))
        assert "power_house" not in result

    def test_missing_ac_gives_no_house_power(self):
        assert "power_house" not in derive_values({"meter_power_active": 100})

    @pytest.mark.parametrize("bad", [True, "x", None])
    def test_non_numeric_meter_treated_as_missing(self, bad):
        result = derive_values(_inputs(3000, bad))
        assert not {"power_house", "ratio_autarky", "ratio_self_consumption"} & set(result)


class TestDeriveRatios:
    """Autarkie- und Eigenverbrauchsquote."""

    def test_surplus(self):
        result = derive_values(_inputs(3600, 1000, pv=4000))
        assert result["power_house"] == 2600.0
        assert result["ratio_autarky"] == 100.0
        assert result["ratio_self_consumption"] == 75.0

    def test_grid_import_only(self):
        result = derive_values(_inputs(0, -500, pv=0))
        assert result["ratio_autarky"] == 0.0

    def test_battery_discharge_autarky(self):
        assert derive_values(_inputs(2000, -300))["ratio_autarky"] == 87.0

    def test_grid_charging_clamped_to_zero(self):
        assert derive_values(_inputs(-3000, -3500))["ratio_autarky"] == 0.0

    def test_self_consumption_clamped_to_range(self):
        # Einspeisung groesser als Erzeugung (Messversatz) -> 0, nie negativ
        assert derive_values(_inputs(100, 500, pv=100))["ratio_self_consumption"] == 0.0

    def test_ratios_missing_below_threshold(self):
        result = derive_values(_inputs(20, 10, pv=30))
        assert "ratio_autarky" not in result
        assert "ratio_self_consumption" not in result

    def test_self_consumption_missing_without_pv_input(self):
        result = derive_values(_inputs(2000, -300))
        assert "ratio_self_consumption" not in result

    def test_values_rounded_to_one_decimal(self):
        """66,67 % wird auf 66,7 gerundet, nicht abgeschnitten."""
        result = derive_values(_inputs(1000, -500))  # Haus 1500, Import 500: 1000/1500
        assert result["ratio_autarky"] == 66.7
        result = derive_values(_inputs(1000, 1000, pv=3000))  # Haus 0, Export 1000: 2000/3000
        assert result["ratio_self_consumption"] == 66.7

    def test_input_not_mutated(self):
        values = _inputs(3600, 1000, pv=4000)
        snapshot = dict(values)
        derive_values(values)
        assert values == snapshot


class TestMeterStatusGate:
    """meter_status OFFLINE (0) sperrt Hausverbrauch und Quoten."""

    DERIVED = {"power_house", "ratio_autarky", "ratio_self_consumption"}

    @pytest.mark.parametrize("status", [0, 0.0, "OFFLINE", "offline", MeterStatus.OFFLINE])
    def test_offline_blocks_meter_dependent_values(self, status):
        result = derive_values(_inputs(3000, 0, pv=4000, meter_status=status))
        assert not self.DERIVED & set(result)

    @pytest.mark.parametrize("status", [1, "NORMAL", MeterStatus.NORMAL])
    def test_normal_allows_values(self, status):
        result = derive_values(_inputs(3000, 1000, pv=4000, meter_status=status))
        assert self.DERIVED <= set(result)

    def test_missing_status_does_not_block(self):
        assert self.DERIVED <= set(derive_values(_inputs(3000, 1000, pv=4000)))

    def test_offline_keeps_pv_string_power(self):
        values = _inputs(3000, 0, meter_status=0, voltage_PV1=400.0, current_PV1=5.0)
        assert derive_values(values)["power_PV1"] == 2000.0


class TestDeriveBatterySplit:
    """Batterieleistung getrennt in Laden und Entladen."""

    @pytest.mark.parametrize(
        ("power", "charge", "discharge"),
        [(1500, 1500, 0), (-800, 0, 800), (0, 0, 0)],
    )
    def test_split(self, power, charge, discharge):
        result = derive_battery_split({"battery_power": power})
        assert result == {"battery_power_charge": charge, "battery_power_discharge": discharge}

    @pytest.mark.parametrize("bad", [None, True, "x"])
    def test_non_numeric_gives_no_keys(self, bad):
        assert derive_battery_split({"battery_power": bad}) == {}

    def test_missing_key_gives_no_keys(self):
        assert derive_battery_split({}) == {}


class TestTransformDerived:
    """Abgeleitete Werte in der kompletten Pipeline."""

    @staticmethod
    def _registers(**named):
        """Echte `Result`-Objekte der huawei_solar-Bibliothek (wie von read_registers)."""
        return {name: Result(value, None) for name, value in named.items()}

    def test_round_trip_contains_derived_keys(self):
        data = self._registers(
            active_power=3600,
            input_power=4000,
            power_meter_active_power=1000,
            storage_charge_discharge_power=-200,
            meter_status=MeterStatus.NORMAL,
            pv_01_voltage=400.0,
            pv_01_current=5.0,
        )
        result = transform_data(data)

        assert result["power_PV1"] == 2000.0
        assert result["power_house"] == 2600.0
        assert result["ratio_autarky"] == 100.0
        assert result["ratio_self_consumption"] == 75.0
        assert result["battery_power_charge"] == 0
        assert result["battery_power_discharge"] == 200
        assert "last_update" in result
        assert None not in result.values()

    def test_missing_meter_does_not_fake_full_autarky(self):
        """Regression: Default meter=0 darf keine 100 % Autarkie vortaeuschen."""
        data = self._registers(active_power=3000, input_power=3500)
        result = transform_data(data)

        assert result["meter_power_active"] == 0  # CRITICAL_DEFAULT bleibt
        assert "power_house" not in result
        assert "ratio_autarky" not in result
        assert "ratio_self_consumption" not in result

    def test_missing_battery_gives_zero_split(self):
        result = transform_data(self._registers(active_power=3000))
        assert result["battery_power_charge"] == 0
        assert result["battery_power_discharge"] == 0

    def test_offline_meter_blocks_house_values(self):
        data = self._registers(
            active_power=3000,
            input_power=3500,
            power_meter_active_power=0,
            meter_status=0,
        )
        result = transform_data(data)
        assert "power_house" not in result
        assert "ratio_autarky" not in result
