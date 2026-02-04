#!/usr/bin/env python3
"""
Pre-commit hook to verify version consistency across files.
"""

import re
import sys
from pathlib import Path

# Fix encoding for Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def get_version_from_config():
    """Read version from config.yaml"""
    config_path = Path("huawei_solar_modbus_mqtt/config.yaml")
    if not config_path.exists():
        return None

    content = config_path.read_text(encoding="utf-8")
    match = re.search(r'^version:\s*["\']?([0-9.]+)["\']?', content, re.MULTILINE)
    return match.group(1) if match else None


def get_version_from_pyproject():
    """Read version from pyproject.toml"""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        return None

    content = pyproject_path.read_text(encoding="utf-8")

    # Statische Version: version = "1.7.3"
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if match:
        return match.group(1)

    # Dynamische Version: attr = "bridge.__version__.__version__"
    # → Verwende __version__.py als Source of Truth
    match = re.search(r'attr\s*=\s*"bridge\.__version__\.__version__"', content)
    if match:
        return get_version_from_version_py()  # Nutze die gleiche Version

    return None


def get_version_from_version_py():
    """Read version from __version__.py"""
    version_file = Path("huawei_solar_modbus_mqtt/bridge/__version__.py")
    if not version_file.exists():
        return None

    content = version_file.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else None


def main():
    config_version = get_version_from_config()
    pyproject_version = get_version_from_pyproject()
    version_py = get_version_from_version_py()

    print("Checking version consistency...")
    print(f"   config.yaml:     {config_version or 'NOT FOUND'}")
    print(f"   pyproject.toml:  {pyproject_version or 'NOT FOUND'}")
    print(f"   __version__.py:  {version_py or 'NOT FOUND'}")

    versions = [v for v in [config_version, pyproject_version, version_py] if v]

    if not versions:
        print("WARNING: No version files found")
        return 0

    if len(set(versions)) > 1:
        print()
        print("ERROR: Version mismatch detected!")
        print("Run: python update_version.py")
        return 1

    print("OK: All versions are synchronized")
    return 0


if __name__ == "__main__":
    sys.exit(main())
