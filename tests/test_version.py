# tests/test_version.py

from bridge.version import version


class TestVersion:
    """Versionskonstante aus bridge.version."""

    def test_version_is_non_empty_string(self):
        """version ist ein nicht-leerer String."""
        assert isinstance(version, str)
        assert len(version) > 0

    def test_version_contains_dot_separator(self):
        """version enthält mindestens einen Punkt (Semver-Format)."""
        assert "." in version
