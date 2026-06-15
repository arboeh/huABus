# scripts/update_version.py

"""
Update version across all project files.
Single source of truth: huawei_solar_modbus_mqtt/config.yaml
"""

import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]


def get_version_from_config():
    """Read version from config.yaml"""
    config_path = SCRIPT_DIR / "../huawei_solar_modbus_mqtt/config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Could not find {config_path}")

    content = config_path.read_text(encoding="utf-8")
    match = re.search(r'^version:\s*["\']?([0-9.]+)["\']?', content, re.MULTILINE)

    if not match:
        raise ValueError("Could not extract version from config.yaml")

    return match.group(1)


def update_version_py(version):
    """Update version.py"""
    version_file = SCRIPT_DIR / "../huawei_solar_modbus_mqtt/bridge/version.py"
    if not version_file.exists():
        print("⚠️ WARNING: version.py not found, skipping")
        return

    content = version_file.read_text(encoding="utf-8")
    new_content = re.sub(
        r'(version\s*=\s*")[^"]+(")',
        rf"\g<1>{re.escape(version)}\g<2>",
        content,
    )

    if content != new_content:
        version_file.write_text(new_content, encoding="utf-8")
        print(f"✅ UPDATED: version.py to version {version}")
    else:
        print(f"ℹ️  INFO: version.py already at version {version}")


def update_requirements():
    """Generate requirements.txt from pyproject.toml via uv."""
    output_path = SCRIPT_DIR / "../huawei_solar_modbus_mqtt/requirements.txt"
    try:
        subprocess.run(
            [
                "uv",
                "export",
                "--no-dev",
                "--no-hashes",
                "--no-emit-project",
                "-o",
                str(output_path),
            ],
            check=True,
            cwd=SCRIPT_DIR / "..",
        )
        print("✅ UPDATED: requirements.txt")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"uv export failed: {e}") from e
    except FileNotFoundError as e:
        raise RuntimeError("uv not found - is it installed?") from e


def main():
    print("=" * 60)
    print("📦 Version Synchronization")
    print("=" * 60)
    print("📍 Source: huawei_solar_modbus_mqtt/config.yaml")
    print()

    try:
        version = get_version_from_config()
        print(f"🔍 Found version: {version}")
        print()

        update_version_py(version)
        update_requirements()

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
