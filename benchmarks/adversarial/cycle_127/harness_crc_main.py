#!/usr/bin/env python3
"""Fuzz harness for surface #1: crc(data) — random + stress inputs.

Target: src/crc16_modbus_pure/__init__.py::crc (line 22).

Asserts (per SURFACES.md surface #1 + VULN_AUDIT CWE-682/CWE-190/CWE-125):
- crc(b"")          == 0x0000                (AC2)
- crc(b"123456789") == 0x4B37                (AC3, RevEng canonical)
- crc(bytes([0x00])) == 0x40BF               (AC1)
- result is int in [0, 0xFFFF] for every input
- result is deterministic on repeat calls

Iteration modes (--mode):
  random    length 0..10000 random bytes          (default if no seed)
  stress    1MB all-0x00, 1MB all-0xFF, alternating
  subclass  bytes subclasses (bytearray, memoryview) at canonical check value

Usage:
    python3 harness_crc_main.py [--iters N] [--mode random|stress|subclass] [--seed S]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import traceback
from pathlib import Path

# Make the package importable when run from anywhere.
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE
for _ in range(5):
    if (_REPO_ROOT / "src").is_dir():
        break
    _REPO_ROOT = _REPO_ROOT.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from crc16_modbus_pure import crc  # noqa: E402

CANONICAL_VECTORS = [
    (b"", 0x0000, "AC2 empty"),
    (b"123456789", 0x4B37, "AC3 RevEng"),
    (bytes([0x00]), 0x40BF, "AC1 single 0x00"),
    (bytes([0x01]), 0x807E, "single 0x01"),
    (bytes([0xFF]), 0x00FF, "single 0xFF"),
    (bytes(range(10)), 0x4574, "0x00..0x09"),
    (b"\x00" * 256, 0x64BF, "AC7 256 zeros"),
]


def check_vector(data, expected, label):
    actual = crc(data)
    if not isinstance(actual, int):
        return f"{label}: type {type(actual).__name__} (expected int)"
    if not (0 <= actual <= 0xFFFF):
        return f"{label}: out-of-range 0x{actual:X}"
    if actual != expected:
        return f"{label}: got 0x{actual:04X} expected 0x{expected:04X}"
    return None


def fuzz_random(iters: int, rng: random.Random) -> tuple[int, list]:
    crashes = 0
    details = []
    for i in range(iters):
        length = rng.randint(0, 10000)
        data = bytes(rng.randint(0, 255) for _ in range(length))
        try:
            result = crc(data)
        except Exception as e:
            crashes += 1
            details.append({
                "iter": i, "length": length,
                "error": type(e).__name__, "msg": str(e),
                "tb": traceback.format_exc(),
            })
            continue
        if not isinstance(result, int):
            crashes += 1
            details.append({
                "iter": i, "length": length,
                "error": "TypeError", "msg": f"return type {type(result).__name__}",
            })
            continue
        if not (0 <= result <= 0xFFFF):
            crashes += 1
            details.append({
                "iter": i, "length": length,
                "error": "RangeError",
                "msg": f"result 0x{result:X} out of [0,0xFFFF]",
            })
    return crashes, details


def fuzz_stress() -> tuple[int, list]:
    """1MB all-0x00, 1MB all-0xFF, 1MB alternating, plus determinism."""
    crashes = 0
    details = []
    stresses = [
        (b"\x00" * (1024 * 1024), "1MB all-0x00"),
        (b"\xFF" * (1024 * 1024), "1MB all-0xFF"),
        (b"\xAA\x55" * (512 * 1024), "1MB alternating"),
    ]
    for data, label in stresses:
        try:
            r1 = crc(data)
            r2 = crc(data)
        except Exception as e:
            crashes += 1
            details.append({"label": label, "error": type(e).__name__, "msg": str(e)})
            continue
        if r1 != r2:
            crashes += 1
            details.append({"label": label, "error": "NonDeterministic",
                            "msg": f"r1=0x{r1:04X} r2=0x{r2:04X}"})
            continue
        if not (0 <= r1 <= 0xFFFF):
            crashes += 1
            details.append({"label": label, "error": "RangeError",
                            "msg": f"0x{r1:X}"})
    return crashes, details


def fuzz_subclass() -> tuple[int, list]:
    """Accept bytes subclasses (bytearray, memoryview) on canonical check value."""
    crashes = 0
    details = []
    for data, expected, label in CANONICAL_VECTORS:
        for factory, name in [(lambda d: bytearray(d), "bytearray"),
                              (lambda d: memoryview(d).cast("B"), "memoryview")]:
            wrapped = factory(data)
            try:
                actual = crc(wrapped)
            except Exception as e:
                crashes += 1
                details.append({"label": f"{label}/{name}",
                                "error": type(e).__name__,
                                "msg": str(e)})
                continue
            if actual != expected:
                crashes += 1
                details.append({
                    "label": f"{label}/{name}",
                    "error": "Mismatch",
                    "msg": f"got 0x{actual:04X} expected 0x{expected:04X}",
                })
    return crashes, details


def main() -> int:
    p = argparse.ArgumentParser(description="crc16-modbus-pure fuzz harness (surface #1)")
    p.add_argument("--iters", type=int, default=100, help="random-mode iterations")
    p.add_argument("--mode", choices=["random", "stress", "subclass", "all"],
                   default="all")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default=str(_HERE / "fuzz" / "crc_main" / "results.json"))
    args = p.parse_args()

    rng = random.Random(args.seed)
    started = time.perf_counter()
    crashes = 0
    details: list = []

    # Canonical vectors run first regardless of mode.
    for data, expected, label in CANONICAL_VECTORS:
        err = check_vector(data, expected, label)
        if err is not None:
            crashes += 1
            details.append({"label": label, "error": "CanonicalFail", "msg": err})

    modes = ["random", "stress", "subclass"] if args.mode == "all" else [args.mode]
    for mode in modes:
        if mode == "random":
            c, d = fuzz_random(args.iters, rng)
        elif mode == "stress":
            c, d = fuzz_stress()
        elif mode == "subclass":
            c, d = fuzz_subclass()
        else:
            continue
        crashes += c
        details.extend(d)

    elapsed = time.perf_counter() - started
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump({
            "harness": "harness_crc_main.py",
            "mode": args.mode,
            "iters": args.iters,
            "seed": args.seed,
            "crashes": crashes,
            "details": details[:50],  # cap detail dump
            "elapsed_s": round(elapsed, 4),
        }, f, indent=2)
    print(f"[crc_main] iters={args.iters} crashes={crashes} time={elapsed:.3f}s")
    return 0 if crashes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
