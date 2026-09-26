#!/usr/bin/env python3
"""Fuzz harness for surface #4: `python -m crc16_modbus_pure --data HEXSTR`.

Target: src/crc16_modbus_pure/cli.py::main_compute.

Asserts:
- exit 0 + stdout contains "CRC: 0xHHHH" for valid hex input
- `crc(b"123456789")` invoked as `--data 313233343536373839` returns `0x4B37`
- Output hex is exactly 4 uppercase digits prefixed by "0x"
- Whitespace-stripped hex (e.g. "0A 1B") is accepted
- Lowercase hex is accepted
- Odd-length / non-hex input causes non-zero exit (CLI does NOT crash silently)
- Random hex strings always produce a value in [0, 0xFFFF]

Usage:
    python3 harness_cli_data.py [--iters N] [--seed S]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE
for _ in range(5):
    if (_REPO_ROOT / "src").is_dir():
        break
    _REPO_ROOT = _REPO_ROOT.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

PYTHON = sys.executable

CANONICAL = [
    ("313233343536373839", "0x4B37", "AC3 ASCII '123456789'"),
    ("00", "0x40BF", "AC1 single 0x00"),
    ("", "0x0000", "AC2 empty"),
]

OUTPUT_RE = re.compile(r"^CRC: 0x([0-9A-F]{4})$")


def run_cli(hexstr: str, timeout: float = 30.0):
    """Invoke the `crc16-modbus-pure-compute` console script with --data HEXSTR.

    Note: `python -m crc16_modbus_pure --data ...` resolves to __main__.py
    which unconditionally runs the self-test (no argv parsing), so we use the
    console-script entry point instead — that one is wired to main_compute().
    """
    return subprocess.run(
        ["crc16-modbus-pure-compute", "--data", hexstr],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def main() -> int:
    p = argparse.ArgumentParser(description="crc16-modbus-pure --data CLI harness")
    p.add_argument("--iters", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default=str(_HERE / "fuzz" / "cli_data" / "results.json"))
    args = p.parse_args()

    rng = random.Random(args.seed)
    started = time.perf_counter()
    crashes = 0
    details: list = []

    # 1. Canonical vectors via CLI.
    for hexstr, expected, label in CANONICAL:
        try:
            r = run_cli(hexstr)
        except Exception as e:
            crashes += 1
            details.append({"label": label, "error": "SpawnError", "msg": str(e)})
            continue
        last_line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        m = OUTPUT_RE.match(last_line)
        if r.returncode != 0:
            crashes += 1
            details.append({
                "label": label, "error": "NonZeroExit",
                "msg": f"exit={r.returncode} stderr={r.stderr[:200]!r}",
            })
            continue
        if not m:
            crashes += 1
            details.append({
                "label": label, "error": "BadFormat",
                "msg": f"stdout last line: {last_line!r}",
            })
            continue
        got = "0x" + m.group(1)
        if got != expected:
            crashes += 1
            details.append({
                "label": label, "error": "Mismatch",
                "msg": f"got {got} expected {expected}",
            })

    # 2. Whitespace + lowercase variants.
    variant_cases = [
        ("31 32 33 34 35 36 37 38 39", "0x4B37", "whitespace"),
        ("313233343536373839 ", "0x4B37", "trailing-space"),
        (" 313233343536373839", "0x4B37", "leading-space"),
        ("31323334353637383\n9", "0x4B37", "embedded-newline"),
        ("313233343536373839\n", "0x4B37", "trailing-newline"),
        ("abcdefab", None, "lowercase-hex"),
    ]
    for hexstr, expected, label in variant_cases:
        try:
            r = run_cli(hexstr)
        except Exception as e:
            crashes += 1
            details.append({"label": f"variant:{label}", "error": "SpawnError", "msg": str(e)})
            continue
        last_line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        m = OUTPUT_RE.match(last_line)
        if expected is not None:
            if r.returncode != 0:
                crashes += 1
                details.append({
                    "label": f"variant:{label}", "error": "NonZeroExit",
                    "msg": f"exit={r.returncode} stderr={r.stderr[:200]!r}",
                })
                continue
            if not m or ("0x" + m.group(1)) != expected:
                crashes += 1
                details.append({
                    "label": f"variant:{label}", "error": "Mismatch",
                    "msg": f"stdout={last_line!r} expected={expected}",
                })
        else:
            # lowercase-hex: just verify it succeeds and output matches 0x[0-9A-F]{4}
            if r.returncode != 0:
                crashes += 1
                details.append({
                    "label": f"variant:{label}", "error": "NonZeroExit",
                    "msg": f"exit={r.returncode} stderr={r.stderr[:200]!r}",
                })
            elif not m:
                crashes += 1
                details.append({
                    "label": f"variant:{label}", "error": "BadFormat",
                    "msg": f"stdout={last_line!r}",
                })

    # 3. Negative-path: odd-length and non-hex must reject (non-zero exit).
    # NOTE: empty string is intentionally accepted — bytes.fromhex("") returns
    # b"" which crc() processes to 0x0000 (AC2). So empty is NOT a neg-path case.
    neg_cases = ["0", "zz", "0x41", "12g", "f"]
    for bad in neg_cases:
        try:
            r = run_cli(bad)
        except subprocess.TimeoutExpired:
            crashes += 1
            details.append({"label": f"neg:{bad!r}", "error": "Timeout"})
            continue
        except Exception as e:
            crashes += 1
            details.append({"label": f"neg:{bad!r}", "error": "SpawnError", "msg": str(e)})
            continue
        if r.returncode == 0:
            crashes += 1
            details.append({
                "label": f"neg:{bad!r}", "error": "AcceptedBadInput",
                "msg": f"exit=0 stdout={r.stdout[:80]!r}",
            })

    # 4. Random fuzz — every random input must produce a valid 16-bit hex output.
    for i in range(args.iters):
        length = rng.randint(0, 256) * 2
        hexstr = "".join(rng.choice("0123456789abcdef") for _ in range(length))
        try:
            r = run_cli(hexstr, timeout=30.0)
        except subprocess.TimeoutExpired:
            crashes += 1
            details.append({"iter": i, "error": "Timeout"})
            continue
        except Exception as e:
            crashes += 1
            details.append({"iter": i, "error": "SpawnError", "msg": str(e)})
            continue
        if r.returncode != 0:
            crashes += 1
            details.append({
                "iter": i, "error": "NonZeroExit",
                "msg": f"len={length} stderr={r.stderr[:200]!r}",
            })
            continue
        last_line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        m = OUTPUT_RE.match(last_line)
        if not m:
            crashes += 1
            details.append({
                "iter": i, "error": "BadFormat",
                "msg": f"stdout={last_line!r}",
            })

    elapsed = time.perf_counter() - started
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump({
            "harness": "harness_cli_data.py",
            "iters": args.iters,
            "seed": args.seed,
            "crashes": crashes,
            "details": details[:50],
            "elapsed_s": round(elapsed, 4),
        }, f, indent=2)
    print(f"[cli_data] iters={args.iters} crashes={crashes} time={elapsed:.3f}s")
    return 0 if crashes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
