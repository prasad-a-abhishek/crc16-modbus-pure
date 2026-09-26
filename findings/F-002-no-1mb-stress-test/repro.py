"""Repro for F-002 — confirms the existing test suite has no 1 MB stress test,
while the fuzzer harness `fuzz/large_input` does empirically bound it.

Run:
    python3 repro.py
"""

from __future__ import annotations
import time
from crc16_modbus_pure import crc


def main() -> int:
    data = bytes(range(256)) * 4096  # 1 MB
    t0 = time.perf_counter()
    result = crc(data)
    elapsed = time.perf_counter() - t0
    in_range = 0 <= result <= 0xFFFF
    fast_enough = elapsed < 5.0
    print(f"result=0x{result:04X} elapsed={elapsed:.3f}s "
          f"in_range={in_range} fast_enough={fast_enough}")
    return 0 if (in_range and fast_enough) else 1


if __name__ == "__main__":
    raise SystemExit(main())
