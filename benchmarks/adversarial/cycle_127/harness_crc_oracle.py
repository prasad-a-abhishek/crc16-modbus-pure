#!/usr/bin/env python3
"""Fuzz harness for surface #1 differential oracle vs crcmod (CWE-682 / AC11).

Target: crc(data) byte-exact match against crcmod.mkCrcFun reference.

If crcmod is not importable, the harness SKIPS gracefully (prints SKIPPED,
returns 0) — per the task brief. This is the documented graceful-skip path.

Asserts (when crcmod IS available):
- Byte-exact match on canonical check vectors (0x4B37, 0x40BF, 0x64BF, 0x4574)
- Byte-exact match on N random inputs of length 1..1024
- 100/100 random match rate (no oracle mismatches)

Usage:
    python3 harness_crc_oracle.py [--iters N] [--seed S]
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

try:
    import crcmod  # type: ignore
    _HAS_CRCMOD = True
except Exception:
    crcmod = None
    _HAS_CRCMOD = False


def get_reference():
    """Return crcmod's reference function for CRC-16/MODBUS, or None if unavailable."""
    if not _HAS_CRCMOD:
        return None
    return crcmod.mkCrcFun(0x18005, initCrc=0xFFFF, xorOut=0x0000, rev=True)  # type: ignore[union-attr]


CANONICAL = [
    (b"123456789", 0x4B37, "AC3 RevEng"),
    (bytes([0x00]), 0x40BF, "AC1 single 0x00"),
    (bytes([0x01]), 0x807E, "single 0x01"),
    (bytes([0xFF]), 0x00FF, "single 0xFF"),
    (bytes(range(10)), 0x4574, "0x00..0x09"),
    (b"\x00" * 256, 0x64BF, "AC7 256 zeros"),
]


def main() -> int:
    p = argparse.ArgumentParser(description="crcmod-oracle harness for crc16-modbus-pure")
    p.add_argument("--iters", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default=str(_HERE / "fuzz" / "crc_oracle" / "results.json"))
    args = p.parse_args()

    started = time.perf_counter()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ref = get_reference()
    if ref is None:
        msg = {
            "harness": "harness_crc_oracle.py",
            "skipped": True,
            "reason": "crcmod not installed",
            "crashes": 0,
            "oracle_mismatches": 0,
            "elapsed_s": round(time.perf_counter() - started, 4),
        }
        with out_path.open("w") as f:
            json.dump(msg, f, indent=2)
        print(f"[crc_oracle] SKIPPED (crcmod not installed) time={msg['elapsed_s']:.3f}s")
        return 0

    rng = random.Random(args.seed)
    crashes = 0
    oracle_mismatches = 0
    details: list = []

    # 1. Canonical vectors.
    for data, expected, label in CANONICAL:
        try:
            ours = crc(data)
            theirs = ref(data)
        except Exception as e:
            crashes += 1
            details.append({"label": label, "error": type(e).__name__, "msg": str(e)})
            continue
        if ours != theirs:
            oracle_mismatches += 1
            details.append({
                "label": label,
                "error": "OracleMismatch",
                "msg": f"ours=0x{ours:04X} crcmod=0x{theirs:04X} expected=0x{expected:04X}",
            })

    # 2. Random inputs of length 1..1024.
    for i in range(args.iters):
        length = rng.randint(1, 1024)
        data = bytes(rng.randint(0, 255) for _ in range(length))
        try:
            ours = crc(data)
            theirs = ref(data)
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
                "msg": f"ours=0x{ours:04X} crcmod=0x{theirs:04X}",
            })

    elapsed = time.perf_counter() - started
    with out_path.open("w") as f:
        json.dump({
            "harness": "harness_crc_oracle.py",
            "skipped": False,
            "iters": args.iters,
            "seed": args.seed,
            "crashes": crashes,
            "oracle_mismatches": oracle_mismatches,
            "details": details[:50],
            "elapsed_s": round(elapsed, 4),
        }, f, indent=2)
    print(f"[crc_oracle] iters={args.iters} crashes={crashes} oracle_mismatches={oracle_mismatches} time={elapsed:.3f}s")
    return 0 if crashes == 0 and oracle_mismatches == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
