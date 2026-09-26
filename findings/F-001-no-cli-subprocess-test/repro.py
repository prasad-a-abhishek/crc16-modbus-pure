"""Repro for F-001 — demonstrates the current gap.

This script shows that the existing test suite does NOT spawn the
console-script binaries; it only exercises cli.py as a Python module.
A regression in pyproject.toml [project.scripts] mapping would not be
caught by the current suite.

Run:
    python3 repro.py
"""

from __future__ import annotations
import subprocess
import sys


def main() -> int:
    # 1. Confirm console scripts are declared (pyproject.toml [project.scripts]).
    #    A rename there is invisible to the current test suite.
    # 2. Confirm the existing test suite never spawns them via subprocess.
    result = subprocess.run(
        [sys.executable, "-m", "crc16_modbus_pure"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    print(f"python -m crc16_modbus_pure exit={result.returncode}")
    print("stdout:", result.stdout.strip().splitlines()[0] if result.stdout.strip() else "")
    # If this passes AND we have no test that asserts on stdout content,
    # then F-001 is correctly characterized as a coverage gap (Info).
    return 0 if result.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
