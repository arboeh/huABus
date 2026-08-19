# tests/test_register_validation.py

"""Validation tests for register names, mappings, and sensor definitions."""


class TestRegisterNamesValid:
    """Verify register names are recognized by the huawei_solar library."""

    def test_all_essential_registers_exist_in_library(self):
        from huawei_solar.registers import REGISTERS

        from huawei_solar_modbus_mqtt.bridge.config.registers import ESSENTIAL_REGISTERS

        missing = [n for n in ESSENTIAL_REGISTERS if n not in REGISTERS]
        assert not missing, f"Not in library: {missing}"

    def test_no_underscore_soc_register_names(self):
        from huawei_solar_modbus_mqtt.bridge.config.registers import ESSENTIAL_REGISTERS

        invalid = [r for r in ESSENTIAL_REGISTERS if r.endswith("_soc")]
        assert not invalid, f"Use _state_of_capacity: {invalid}"


class TestRegisterMappingsConsistent:
    """Verify REGISTER_MAPPING keys match ESSENTIAL_REGISTERS."""

    def test_mapping_keys_match_essential_registers(self):
        from huawei_solar_modbus_mqtt.bridge.config.mappings import REGISTER_MAPPING
        from huawei_solar_modbus_mqtt.bridge.config.registers import ESSENTIAL_REGISTERS

        reg_set = set(ESSENTIAL_REGISTERS)
        map_set = set(REGISTER_MAPPING.keys())
        assert reg_set == map_set, f"Mismatch: {reg_set ^ map_set}"


class TestSensorsConsistent:
    """Verify sensor definitions match REGISTER_MAPPING values."""

    def test_sensor_keys_match_mapping_values(self):
        from huawei_solar_modbus_mqtt.bridge.config.mappings import REGISTER_MAPPING
        from huawei_solar_modbus_mqtt.bridge.config.sensors_mqtt import NUMERIC_SENSORS, TEXT_SENSORS

        sensor_keys = {s["key"] for s in NUMERIC_SENSORS + TEXT_SENSORS if s.get("key")}
        mqtt_keys = set(REGISTER_MAPPING.values())
        unmatched = sensor_keys - mqtt_keys
        assert unmatched.issubset({"status"}), f"Unmatched: {unmatched}"

    def test_battery_unit3_sensor_removed(self):
        from huawei_solar_modbus_mqtt.bridge.config.sensors_mqtt import NUMERIC_SENSORS, TEXT_SENSORS

        all_keys = {s["key"] for s in NUMERIC_SENSORS + TEXT_SENSORS if s.get("key")}
        assert "battery_unit3_soc" not in all_keys

    def test_battery_unit1_and_unit2_sensors_present(self):
        from huawei_solar_modbus_mqtt.bridge.config.sensors_mqtt import NUMERIC_SENSORS, TEXT_SENSORS

        all_keys = {s["key"] for s in NUMERIC_SENSORS + TEXT_SENSORS if s.get("key")}
        assert "battery_unit1_soc" in all_keys
        assert "battery_unit2_soc" in all_keys
