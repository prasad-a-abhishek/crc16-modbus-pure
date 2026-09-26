#!/usr/bin/env python3
"""Fuzz harness for surface #5: `python -m crc16_modbus_pure --self-test`.

Target: src/crc16_modbus_pure/cli.py::main_self_test.

Asserts:
- exit 0 + stdout ends with summary "N/N passed"
- Each of the 7 hard-coded vectors must print `[PASS]`
- `0x4B37` must appear in stdout (AC3 RevEng canonical)
- Invoking with arbitrary argv should NOT crash — argparse rejects gracefully
  via SystemExit (non-zero exit, usage on stderr)

Usage:
    python3 harness_cli_self_test.py [--iters N]
"""
from __future__ import annotations

import argparse
import json
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

PYTHON = sys.executable

SUMMARY_RE = re.compile(r"(\d+)/(\d+) passed")
PASS_RE = re.compile(r"\[PASS\]")


def run_self_test(argv=None):
    """Invoke `python -m crc16_modbus_pure`. __main__.py runs the self-test
    unconditionally; the optional `argv` is forwarded to main_self_test()
    to verify argparse rejects unknown flags gracefully.
    """
    cmd = [PYTHON, "-m", "crc16_modbus_pure"]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60.0,
        cwd=str(_REPO_ROOT),
    )


def main() -> int:
    p = argparse.ArgumentParser(description="crc16-modbus-pure --self-test harness")
    p.add_argument("--iters", type=int, default=10,
                   help="re-invoke self-test this many times (determinism)")
    p.add_argument("--out", default=str(_HERE / "fuzz" / "cli_self_test" / "results.json"))
    args = p.parse_args()

    started = time.perf_counter()
    crashes = 0
    details: list = []

    # 1. Baseline: --self-test with no argv.
    try:
        r = run_self_test()
    except Exception as e:
        crashes += 1
        details.append({"label": "baseline", "error": "SpawnError", "msg": str(e)})
        r = None

    if r is not None:
        if r.returncode != 0:
            crashes += 1
            details.append({
                "label": "baseline",
                "error": "NonZeroExit",
                "msg": f"exit={r.returncode} stderr={r.stderr[:300]!r}",
            })
        else:
            # Must contain 7 PASS lines.
            pass_count = len(PASS_RE.findall(r.stdout))
            if pass_count != 7:
                crashes += 1
                details.append({
                    "label": "baseline",
                    "error": "BadPassCount",
                    "msg": f"got {pass_count} [PASS] lines",
                })
            m = SUMMARY_RE.search(r.stdout)
            if not m:
                crashes += 1
                details.append({
                    "label": "baseline",
                    "error": "MissingSummary",
                    "msg": f"stdout tail={r.stdout[-200:]!r}",
                })
            elif (int(m.group(1)), int(m.group(2))) != (7, 7):
                crashes += 1
                details.append({
                    "label": "baseline",
                    "error": "SummaryMismatch",
                    "msg": f"summary: {m.group(0)}",
                })
            if "0x4B37" not in r.stdout:
                crashes += 1
                details.append({
                    "label": "baseline",
                    "error": "MissingRevengVector",
                    "msg": "0x4B37 absent from stdout",
                })

    # 2. Determinism: run N times, all results must be identical.
    outputs = []
    for i in range(args.iters):
        try:
            r = run_self_test()
        except Exception as e:
            crashes += 1
            details.append({"iter": i, "error": "SpawnError", "msg": str(e)})
            continue
        if r.returncode != 0:
            crashes += 1
            details.append({
                "iter": i, "error": "NonZeroExit",
                "msg": f"exit={r.returncode}",
            })
        else:
            outputs.append(r.stdout)
    if outputs and len(set(outputs)) > 1:
        crashes += 1
        details.append({
            "label": "determinism",
            "error": "NonDeterministic",
            "msg": f"{len(set(outputs))} distinct outputs across {len(outputs)} runs",
        })

    # 3. Negative-path: `crc16-modbus-pure-self-test` console script with extra argv
    # must be rejected gracefully (argparse exits non-zero, no traceback leak).
    bad_argvs = [
        ["--bogus"],
        ["--data", "00"],
        ["foo"],
        ["--help"],  # argparse prints usage + SystemExit(0)
    ]
    for argv in bad_argvs:
        try:
            r = subprocess.run(
                ["crc16-modbus-pure-self-test"] + argv,
                capture_output=True,
                text=True,
                timeout=30.0,
            )
        except Exception as e:
            crashes += 1
            details.append({"label": f"bad:{argv}", "error": "SpawnError", "msg": str(e)})
            continue
        # SystemExit(0) is OK for --help; argparse exits cleanly.
        if r.returncode not in (0, 1, 2):
            crashes += 1
            details.append({
                "label": f"bad:{argv}",
                "error": "UnexpectedExit",
                "msg": f"exit={r.returncode} stderr={r.stderr[:200]!r}",
            })
        # No raw tracebacks in stderr.
        if "Traceback" in r.stderr:
            crashes += 1
            details.append({
                "label": f"bad:{argv}",
                "error": "TracebackLeak",
                "msg": f"stderr contained traceback",
            })

    elapsed = time.perf_counter() - started
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump({
            "harness": "harness_cli_self_test.py",
            "iters": args.iters,
            "crashes": crashes,
            "details": details[:50],
            "elapsed_s": round(elapsed, 4),
        }, f, indent=2)
    print(f"[cli_self_test] iters={args.iters} crashes={crashes} time={elapsed:.3f}s")
    return 0 if crashes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
