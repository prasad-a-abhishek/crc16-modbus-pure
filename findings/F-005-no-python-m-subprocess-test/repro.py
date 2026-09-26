"""Repro for F-005 — demonstrates the end-to-end `python -m` works today;
no automated test asserts it.

Run:
    python3 repro.py
"""

from __future__ import annotations
import subprocess
import sys


def main() -> int:
    r = subprocess.run(
        [sys.executable, "-m", "crc16_modbus_pure"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    # The self-test CLI prints "[PASS] ... 7/7 passed" at the end. The marker
    # "passed" is the in-suite convention; "OK" was incorrect in the v0 draft.
    has_passed = "passed" in r.stdout
    print(f"exit={r.returncode} stdout_first_line={r.stdout.strip().splitlines()[0] if r.stdout.strip() else ''!r}")
    print(f"stdout_last_line={r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ''!r}")
    print(f"contains_passed={has_passed}")
    return 0 if (r.returncode == 0 and has_passed) else 1


if __name__ == "__main__":
    raise SystemExit(main())
