#!/usr/bin/env python3
"""Fuzz harness: cross-cycle determinism + bit-order independence (CWE-1339).

Target: crc(data) repeated-call stability + comparison against a bitwise
reference impl transcribed from the SPEC.md §1 algorithm description.

Asserts:
- crc(data) == crc(data) for the same input across 1000 calls (deterministic)
- A bitwise reference impl (matching the documented reflected algorithm)
  produces byte-exact results across N inputs (algorithm fidelity check)

Usage:
    python3 harness_cross_cycle.py [--iters N] [--seed S]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
import traceback
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE
for _ in range(5):
    if (_REPO_ROOT / "src").is_dir():
        break
    _REPO_ROOT = _REPO_ROOT.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from crc16_modbus_pure import crc  # noqa: E402


def crc_reference(data: bytes, init: int = 0xFFFF, xorout: int = 0x0000) -> int:
    """Independent bitwise reference for CRC-16/MODBUS, transcribed from SPEC §1.

    This is INTENTIONALLY written differently from the package implementation
    so it can detect algorithm-transcription bugs (wrong polynomial, wrong
    shift direction, missing XOR). Both implementations MUST agree.
    """
    POLY = 0xA001  # reflected form of 0x8005
    if len(data) == 0:
        return 0x0000
    reg = init & 0xFFFF
    for byte in data:
        reg ^= byte
        # 8 reflected shifts: low bit => shift right + XOR poly; else shift right.
        for _ in range(8):
            if reg & 0x0001:
                reg = (reg >> 1) ^ POLY
            else:
                reg = reg >> 1
    return (reg ^ xorout) & 0xFFFF


CANONICAL = [
    (b"", 0x0000, "AC2 empty"),
    (b"123456789", 0x4B37, "AC3 RevEng"),
    (bytes([0x00]), 0x40BF, "AC1 single 0x00"),
    (b"\x00" * 256, 0x64BF, "AC7 256 zeros"),
    (bytes(range(256)), None, "0x00..0xFF"),
]


def main() -> int:
    p = argparse.ArgumentParser(description="crc16-modbus-pure cross-cycle/determinism harness")
    p.add_argument("--iters", type=int, default=100)
    p.add_argument("--det-iters", type=int, default=1000,
                   help="repeat same input this many times for determinism check")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default=str(_HERE / "fuzz" / "cross_cycle" / "results.json"))
    args = p.parse_args()

    rng = random.Random(args.seed)
    started = time.perf_counter()
    crashes = 0
    oracle_mismatches = 0
    details: list = []

    # 1. Determinism: run crc(data) N times for one input, expect identical results.
    det_input = b"123456789"
    det_results = []
    try:
        for _ in range(args.det_iters):
            det_results.append(crc(det_input))
    except Exception as e:
        crashes += 1
        details.append({"label": "determinism", "error": type(e).__name__,
                        "msg": str(e),
                        "tb": traceback.format_exc()})
    if det_results and len(set(det_results)) > 1:
        crashes += 1
        details.append({
            "label": "determinism",
            "error": "NonDeterministic",
            "msg": f"distinct results: {[hex(r) for r in set(det_results)]}",
        })

    # 2. Reference impl cross-check on canonical vectors.
    for data, expected, label in CANONICAL:
        try:
            ours = crc(data)
            theirs = crc_reference(data)
        except Exception as e:
            crashes += 1
            details.append({"label": label, "error": type(e).__name__,
                            "msg": str(e),
                            "tb": traceback.format_exc()})
            continue
        if ours != theirs:
            oracle_mismatches += 1
            details.append({
                "label": label, "error": "OracleMismatch",
                "msg": f"ours=0x{ours:04X} ref=0x{theirs:04X}",
            })
        if expected is not None and ours != expected:
            oracle_mismatches += 1
            details.append({
                "label": label, "error": "RevEngMismatch",
                "msg": f"ours=0x{ours:04X} expected=0x{expected:04X}",
            })

    # 3. Reference impl cross-check on N random inputs of length 1..4096.
    for i in range(args.iters):
        length = rng.randint(1, 4096)
        data = bytes(rng.randint(0, 255) for _ in range(length))
        try:
            ours = crc(data)
            theirs = crc_reference(data)
        except Exception as e:
            crashes += 1
            details.append({"iter": i, "length": length,
                            "error": type(e).__name__,
                            "msg": str(e),
                            "tb": traceback.format_exc()})
            continue
        if ours != theirs:
            oracle_mismatches += 1
            details.append({
                "iter": i, "length": length,
                "error": "OracleMismatch",
                "msg": f"ours=0x{ours:04X} ref=0x{theirs:04X}",
            })

    elapsed = time.perf_counter() - started
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump({
            "harness": "harness_cross_cycle.py",
            "iters": args.iters,
            "det_iters": args.det_iters,
            "seed": args.seed,
            "crashes": crashes,
            "oracle_mismatches": oracle_mismatches,
            "details": details[:50],
            "elapsed_s": round(elapsed, 4),
        }, f, indent=2)
    print(f"[cross_cycle] iters={args.iters} det_iters={args.det_iters} crashes={crashes} oracle_mismatches={oracle_mismatches} time={elapsed:.3f}s")
    return 0 if crashes == 0 and oracle_mismatches == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
