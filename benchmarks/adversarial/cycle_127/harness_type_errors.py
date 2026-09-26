#!/usr/bin/env python3
"""Fuzz harness for surface #1 type-error path (AC12, CWE-20).

Target: crc(data, init, xorout) input validation.

Asserts:
- TypeError raised cleanly for non-bytes-like `data`
- TypeError raised for bool `init`/`xorout` (bool is int subclass)
- TypeError raised for non-int `init`/`xorout`
- bytes subclasses (bytearray, memoryview) are ACCEPTED on canonical check value
- bool as data is REJECTED (bool is int subclass but not bytes-like)
- bytes literal is ACCEPTED on canonical check value

Usage:
    python3 harness_type_errors.py [--iters N] [--seed S]
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

# Cases that MUST raise TypeError (with the value as `data` arg).
BAD_DATA = [
    ("None", None),
    ("str", "hello"),
    ("int", 42),
    ("float", 3.14),
    ("list", [1, 2, 3]),
    ("dict", {"a": 1}),
    ("tuple", (1, 2)),
    ("set", {1, 2, 3}),
    ("bool-True-as-data", True),
    ("bool-False-as-data", False),
    ("object()", object()),
]

# Cases that MUST raise TypeError (with the value as `init` arg).
BAD_INIT = [
    ("None-init", None),
    ("str-init", "abc"),
    ("list-init", [1]),
    ("float-init", 1.0),
    ("dict-init", {1: 2}),
    ("bool-True-init", True),
    ("bool-False-init", False),
    ("bytes-init", b"\x00"),
]

# Cases that MUST raise TypeError (with the value as `xorout` arg).
BAD_XOROUT = [
    ("str-xorout", "x"),
    ("list-xorout", [0]),
    ("bool-True-xorout", True),
    ("bool-False-xorout", False),
]

# Cases that MUST be accepted (and equal 0x4B37).
ACCEPT_DATA = [
    ("bytes-literal", b"123456789"),
    ("bytearray-canonical", bytearray(b"123456789")),
    ("memoryview-canonical", memoryview(b"123456789")),
    ("empty-bytes", b""),
    ("empty-bytearray", bytearray()),
    ("empty-memoryview", memoryview(b"")),
]


def expect_typeerror(label, fn):
    try:
        result = fn()
    except TypeError as e:
        return 0, None, None
    except Exception as e:
        return 1, {
            "label": label,
            "error": f"WrongException:{type(e).__name__}",
            "msg": str(e),
            "tb": traceback.format_exc(),
        }, None
    return 1, {
        "label": label,
        "error": "NoException",
        "msg": f"function returned {result!r} instead of raising TypeError",
    }, result


def expect_accepted(label, fn, expected=0x4B37):
    try:
        result = fn()
    except Exception as e:
        return 1, {
            "label": label,
            "error": f"UnexpectedException:{type(e).__name__}",
            "msg": str(e),
            "tb": traceback.format_exc(),
        }, None
    if result != expected:
        return 1, {
            "label": label,
            "error": "Mismatch",
            "msg": f"got 0x{result:04X} expected 0x{expected:04X}",
        }, result
    return 0, None, result


def fuzz_random_type_attack(iters: int, rng: random.Random) -> tuple[int, list]:
    """Generate random objects via random helpers and feed them as data/init/xorout."""
    crashes = 0
    details = []
    factories_data = [
        lambda: None,
        lambda: rng.randint(-(2**31), 2**31),
        lambda: rng.random(),
        lambda: [rng.randint(0, 255) for _ in range(rng.randint(0, 16))],
        lambda: tuple(rng.randint(0, 255) for _ in range(rng.randint(0, 8))),
        lambda: {rng.randint(0, 255) for _ in range(rng.randint(0, 8))},
        lambda: {rng.randint(0, 255): rng.randint(0, 255) for _ in range(rng.randint(0, 4))},
        lambda: object(),
        lambda: rng.choice([True, False]),
        lambda: "x" * rng.randint(0, 64),
        lambda: b"\x00" * rng.randint(0, 8),  # valid — should NOT raise
    ]
    for i in range(iters):
        value = factories_data[rng.randrange(len(factories_data))]()
        is_bytes_like = isinstance(value, (bytes, bytearray, memoryview))
        try:
            result = crc(value)
        except TypeError:
            if is_bytes_like:
                crashes += 1
                details.append({
                    "iter": i, "error": "UnexpectedTypeError",
                    "msg": f"bytes-like rejected: {value!r}",
                })
            continue
        except Exception as e:
            crashes += 1
            details.append({
                "iter": i,
                "error": f"WrongException:{type(e).__name__}",
                "msg": f"on {value!r}: {e}",
                "tb": traceback.format_exc(),
            })
            continue
        if not is_bytes_like:
            crashes += 1
            details.append({
                "iter": i,
                "error": "NoException",
                "msg": f"non-bytes-like accepted: {value!r} -> 0x{result:04X}",
            })
        else:
            if not (0 <= result <= 0xFFFF):
                crashes += 1
                details.append({
                    "iter": i,
                    "error": "RangeError",
                    "msg": f"0x{result:X}",
                })
    return crashes, details


def main() -> int:
    p = argparse.ArgumentParser(description="crc16-modbus-pure type-error harness")
    p.add_argument("--iters", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default=str(_HERE / "fuzz" / "type_errors" / "results.json"))
    args = p.parse_args()

    rng = random.Random(args.seed)
    started = time.perf_counter()
    crashes = 0
    details: list = []

    # Hand-curated TypeError cases for `data`.
    for label, value in BAD_DATA:
        c, d, _ = expect_typeerror(f"data:{label}", lambda v=value: crc(v))
        crashes += c
        if d:
            details.append(d)

    # Hand-curated TypeError cases for `init`.
    for label, value in BAD_INIT:
        c, d, _ = expect_typeerror(
            f"init:{label}",
            lambda v=value: crc(b"123456789", init=v),
        )
        crashes += c
        if d:
            details.append(d)

    # Hand-curated TypeError cases for `xorout`.
    for label, value in BAD_XOROUT:
        c, d, _ = expect_typeerror(
            f"xorout:{label}",
            lambda v=value: crc(b"123456789", xorout=v),
        )
        crashes += c
        if d:
            details.append(d)

    # Cases that MUST be accepted.
    for label, value in ACCEPT_DATA:
        expected = 0x4B37 if value else 0x0000
        c, d, _ = expect_accepted(
            f"accept:{label}",
            lambda v=value: crc(v),
            expected=expected,
        )
        crashes += c
        if d:
            details.append(d)

    # Random fuzz pass.
    rc, rd = fuzz_random_type_attack(args.iters, rng)
    crashes += rc
    details.extend(rd)

    elapsed = time.perf_counter() - started
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump({
            "harness": "harness_type_errors.py",
            "iters": args.iters,
            "seed": args.seed,
            "crashes": crashes,
            "details": details[:50],
            "elapsed_s": round(elapsed, 4),
        }, f, indent=2)
    print(f"[type_errors] iters={args.iters} crashes={crashes} time={elapsed:.3f}s")
    return 0 if crashes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
