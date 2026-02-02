#!/usr/bin/env python3
"""
Update version across all project files.
Single source of truth: huawei-solar-modbus-mqtt/config.yaml
"""
import re
import sys
from pathlib import Path

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]


def get_version_from_config():
    """Read version from config.yaml"""
    config_path = Path("huawei-solar-modbus-mqtt/config.yaml")
    if not config_path.exists():
        raise FileNotFoundError(f"Could not find {config_path}")

    content = config_path.read_text(encoding="utf-8")
    match = re.search(r'^version:\s*["\']?([0-9.]+)["\']?', content, re.MULTILINE)

    if not match:
        raise ValueError("Could not extract version from config.yaml")

    return match.group(1)


def update_pyproject_toml(version):
    """Update version in pyproject.toml - only in [project] section"""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("⚠️  WARNING: pyproject.toml not found, skipping")
        return

    content = pyproject_path.read_text(encoding="utf-8")

    # Matche nur: ^version = "..." (am Zeilenanfang, kein Prefix)
    new_content = re.sub(
        r'^(version\s*=\s*")[^"]+(")',
        rf"\g<1>{version}\g<2>",
        content,
        flags=re.MULTILINE,
    )

    if content != new_content:
        pyproject_path.write_text(new_content, encoding="utf-8")
        print(f"✅ UPDATED: pyproject.toml to version {version}")
    else:
        print(f"ℹ️  INFO: pyproject.toml already at version {version}")


def update_version_py(version):
    """Update __version__.py"""
    version_file = Path("huawei-solar-modbus-mqtt/modbus_energy_meter/__version__.py")
    if not version_file.exists():
        print("⚠️  WARNING: __version__.py not found, skipping")
        return

    content = version_file.read_text(encoding="utf-8")
    new_content = re.sub(
        r'(__version__\s*=\s*")[^"]+(")',
        rf"\g<1>{version}\g<2>",
        content,
    )

    if content != new_content:
        version_file.write_text(new_content, encoding="utf-8")
        print(f"✅ UPDATED: __version__.py to version {version}")
    else:
        print(f"ℹ️  INFO: __version__.py already at version {version}")


def main():
    print("=" * 60)
    print("📦 Version Synchronization")
    print("=" * 60)
    print("📍 Source: huawei-solar-modbus-mqtt/config.yaml")
    print()

    try:
        version = get_version_from_config()
        print(f"🔍 Found version: {version}")
        print()

        update_pyproject_toml(version)
        update_version_py(version)

        print()
        print("=" * 60)
        print(f"✅ Version synchronization complete: {version}")
        print("=" * 60)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
