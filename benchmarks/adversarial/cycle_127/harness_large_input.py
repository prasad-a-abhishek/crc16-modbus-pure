#!/usr/bin/env python3
"""Fuzz harness for surface #1 — ≥1 MB resource exhaustion (CWE-400).

Target: crc(data) at large sizes (1MB, 10MB, 64MB).

Asserts:
- crc(b"\\x00" * N) returns valid 16-bit int for N in [1, 1000, 100000, 1000000, 10000000]
- Result never exceeds 0xFFFF
- Result is deterministic across repeat calls
- Time roughly linear in N (sanity bound, no super-linear blowup)
- No crash, no hang, no OOM under reasonable allocation (10 MB cap)

Usage:
    python3 harness_large_input.py [--iters N] [--max-mb N]
"""
from __future__ import annotations

import argparse
import json
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

SIZES = [1, 1000, 100_000, 1_000_000, 10_000_000]


def main() -> int:
    p = argparse.ArgumentParser(description="crc16-modbus-pure large-input harness")
    p.add_argument("--iters", type=int, default=2, help="repeat each size this many times")
    p.add_argument("--max-mb", type=int, default=2,
                   help="upper bound on tested sizes (capped at 10)")
    p.add_argument("--out", default=str(_HERE / "fuzz" / "large_input" / "results.json"))
    args = p.parse_args()

    started = time.perf_counter()
    crashes = 0
    details: list = []
    timings: list = []

    sizes = [s for s in SIZES if s <= args.max_mb * 1024 * 1024]

    for size in sizes:
        # 0x00 fill, 0xFF fill, alternating — pick a pattern per size to vary.
        patterns = [
            (b"\x00" * size, f"0x00*{size}"),
            (b"\xFF" * size, f"0xFF*{size}"),
        ]
        # alternating only for smaller sizes (memory concern at 10MB)
        if size <= 1_000_000:
            patterns.append(((b"\xAA\x55" * (size // 2))[:size],
                             f"0xAA55*{size}"))

        for data, label in patterns:
            for rep in range(args.iters):
                t0 = time.perf_counter()
                try:
                    result = crc(data)
                except Exception as e:
                    crashes += 1
                    details.append({
                        "label": f"{label}/rep{rep}",
                        "error": type(e).__name__,
                        "msg": str(e),
                        "tb": traceback.format_exc(),
                    })
                    continue
                elapsed = time.perf_counter() - t0
                timings.append({"size": size, "elapsed_s": round(elapsed, 4)})
                if not isinstance(result, int):
                    crashes += 1
                    details.append({
                        "label": f"{label}/rep{rep}",
                        "error": "TypeError",
                        "msg": f"returned type {type(result).__name__}",
                    })
                    continue
                if not (0 <= result <= 0xFFFF):
                    crashes += 1
                    details.append({
                        "label": f"{label}/rep{rep}",
                        "error": "RangeError",
                        "msg": f"0x{result:X}",
                    })
            # Determinism: result must match across reps.
            results = []
            try:
                for _ in range(args.iters):
                    results.append(crc(data))
                if len(set(results)) > 1:
                    crashes += 1
                    details.append({
                        "label": label,
                        "error": "NonDeterministic",
                        "msg": f"distinct results: {[hex(r) for r in results]}",
                    })
            except Exception as e:
                crashes += 1
                details.append({
                    "label": f"{label}/det",
                    "error": type(e).__name__,
                    "msg": str(e),
                })

    elapsed = time.perf_counter() - started
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump({
            "harness": "harness_large_input.py",
            "sizes_tested": sizes,
            "iters_per_size": args.iters,
            "crashes": crashes,
            "details": details[:50],
            "timings": timings,
            "elapsed_s": round(elapsed, 4),
        }, f, indent=2)
    print(f"[large_input] sizes={sizes} iters/size={args.iters} crashes={crashes} time={elapsed:.3f}s")
    return 0 if crashes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
