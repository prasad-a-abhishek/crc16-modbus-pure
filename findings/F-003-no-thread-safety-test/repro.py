"""Repro for F-003 — confirms the absence of an automated thread-safety test.

The current `tests/test_crc16_modbus_pure.py` has no ThreadPoolExecutor-based
test. Running this script demonstrates the property holds in the current
implementation, but no test asserts it.

Run:
    python3 repro.py
"""

from __future__ import annotations
import concurrent.futures
from crc16_modbus_pure import crc


def main() -> int:
    data = b"123456789" * 1000  # 9 KB
    expected = crc(data)
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as ex:
        results = list(ex.map(lambda _: crc(data), range(100)))
    identical = all(r == expected for r in results)
    print(f"expected=0x{expected:04X} 100_workers={len(results)} identical={identical}")
    return 0 if identical else 1


if __name__ == "__main__":
    raise SystemExit(main())
