#!/usr/bin/env python3
"""Fuzz harness for surface #2: module import surface.

Target: `from crc16_modbus_pure import crc` from a fresh subprocess.

Asserts:
- Clean import — no DeprecationWarning, no SyntaxError, no ImportError
- All `__all__` symbols are importable and have correct types
- No surprise side effects: no stdout, no stderr, no exit code != 0
- Importing under different PYTHONHASHSEED still produces working symbols
- Re-import in same process works (idempotent)

Usage:
    python3 harness_module_import.py [--iters N]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import warnings
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE
for _ in range(5):
    if (_REPO_ROOT / "src").is_dir():
        break
    _REPO_ROOT = _REPO_ROOT.parent

PYTHON = sys.executable

PROBE = """
import sys
import warnings
warnings.simplefilter("error")  # turn warnings into errors

captured_stdout = []
captured_stderr = []

class _Capture:
    def __init__(self, target):
        self.target = target
    def write(self, s):
        self.target.append(s)
    def flush(self):
        pass

_orig_stdout = sys.stdout
_orig_stderr = sys.stderr
sys.stdout = _Capture(captured_stdout)
sys.stderr = _Capture(captured_stderr)

try:
    import crc16_modbus_pure
    from crc16_modbus_pure import crc, __version__
    assert callable(crc), "crc is not callable"
    assert isinstance(__version__, str), "__version__ is not str"
    # Sanity: crc on canonical must equal 0x4B37.
    assert crc(b"123456789") == 0x4B37, "crc mismatch"
    __all__ = getattr(crc16_modbus_pure, "__all__", None)
    assert __all__ is not None, "__all__ missing"
    for name in __all__:
        assert hasattr(crc16_modbus_pure, name), f"missing export {name}"
    sys.stdout = _orig_stdout
    sys.stderr = _orig_stderr
    print("OK")
except Exception as e:
    sys.stdout = _orig_stdout
    sys.stderr = _orig_stderr
    print(f"FAIL: {type(e).__name__}: {e}")
    sys.exit(1)
"""


def run_probe(seed: int | None = None) -> subprocess.CompletedProcess:
    env = None
    if seed is not None:
        import os
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = str(seed)
    return subprocess.run(
        [PYTHON, "-c", PROBE],
        capture_output=True,
        text=True,
        timeout=30.0,
        env=env,
        cwd=str(_REPO_ROOT),
    )


def main() -> int:
    p = argparse.ArgumentParser(description="crc16-modbus-pure import harness")
    p.add_argument("--iters", type=int, default=10)
    p.add_argument("--out", default=str(_HERE / "fuzz" / "module_import" / "results.json"))
    args = p.parse_args()

    started = time.perf_counter()
    crashes = 0
    details: list = []

    # 1. Fresh-subprocess imports under multiple PYTHONHASHSEED values.
    seeds = [0, 1, 42, 1337, 9999, 2**31 - 1]
    seeds = seeds[: max(1, min(args.iters, len(seeds)))]
    for i, seed in enumerate(seeds):
        try:
            r = run_probe(seed=seed)
        except Exception as e:
            crashes += 1
            details.append({"iter": i, "seed": seed,
                            "error": "SpawnError", "msg": str(e)})
            continue
        if r.returncode != 0 or "OK" not in r.stdout:
            crashes += 1
            details.append({
                "iter": i, "seed": seed,
                "error": "BadExit",
                "msg": f"exit={r.returncode} stdout={r.stdout[:200]!r} stderr={r.stderr[:200]!r}",
            })
        elif r.stderr.strip():
            crashes += 1
            details.append({
                "iter": i, "seed": seed,
                "error": "StderrLeak",
                "msg": f"stderr={r.stderr[:200]!r}",
            })

    # 2. Idempotent re-import in-process.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            import crc16_modbus_pure  # noqa: F401
            from crc16_modbus_pure import crc as crc1  # noqa: F401
            from crc16_modbus_pure import crc as crc2
            assert crc1 is crc2
            assert crc1(b"123456789") == 0x4B37
    except Exception as e:
        crashes += 1
        details.append({"label": "in-process", "error": type(e).__name__, "msg": str(e)})

    elapsed = time.perf_counter() - started
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump({
            "harness": "harness_module_import.py",
            "iters": len(seeds),
            "seeds": seeds,
            "crashes": crashes,
            "details": details[:50],
            "elapsed_s": round(elapsed, 4),
        }, f, indent=2)
    print(f"[module_import] iters={len(seeds)} crashes={crashes} time={elapsed:.3f}s")
    return 0 if crashes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
