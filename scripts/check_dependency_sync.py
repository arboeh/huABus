# scripts/check_dependency_sync.py

"""
Pre-commit hook to verify that the pinned Docker requirements.txt satisfies
the dependency ranges declared in pyproject.toml.
"""

import re
import sys
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

SCRIPT_DIR = Path(__file__).parent
PYPROJECT = SCRIPT_DIR / "../pyproject.toml"
REQUIREMENTS = SCRIPT_DIR / "../huawei_solar_modbus_mqtt/requirements.txt"

PIN_PATTERN = re.compile(r"^([A-Za-z0-9._-]+)==([^\s;]+)")

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]


def read_declared() -> list[Requirement]:
    """Read runtime dependencies from pyproject.toml"""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return [Requirement(dep) for dep in data["project"]["dependencies"]]


def read_pinned() -> dict[str, str]:
    """Read name==version pins from requirements.txt"""
    pinned: dict[str, str] = {}
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        match = PIN_PATTERN.match(line)
        if match:
            pinned[canonicalize_name(match.group(1))] = match.group(2)
    return pinned


def main() -> int:
    declared = read_declared()
    pinned = read_pinned()

    print("Checking dependency consistency...")
    errors = []
    for req in declared:
        name = canonicalize_name(req.name)
        version = pinned.get(name)
        shown = version or "NOT PINNED"
        print(f"   {req.name}: requirements.txt {shown} | pyproject.toml {req.specifier}")
        if version is None:
            errors.append(f"{req.name} missing in requirements.txt")
        elif not req.specifier.contains(version, prereleases=True):
            errors.append(f"{req.name}=={version} violates '{req.specifier}'")

    if errors:
        print()
        print("ERROR: Dependency mismatch detected!")
        for error in errors:
            print(f"   - {error}")
        print(
            "Run: uv lock --upgrade && uv export --no-dev --no-hashes "
            "--no-emit-project -o huawei_solar_modbus_mqtt/requirements.txt"
        )
        return 1

    print("OK: Pinned dependencies satisfy pyproject.toml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
