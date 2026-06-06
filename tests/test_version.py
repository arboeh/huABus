from huawei_solar_modbus_mqtt.bridge.version import version


class TestVersion:
    def test_version_constant(self):
        assert isinstance(version, str)
        assert len(version) > 0
        assert "." in version
