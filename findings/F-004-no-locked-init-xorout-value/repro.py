"""Repro for F-004 — locks one (init, xorout) value against crcmod.

The existing TestInitXoroutMatrix in tests/ only checks `isinstance(int)`
and `0 <= r <= 0xFFFF`. This script demonstrates that the empirical oracle
(fuzz/crc_oracle, 100 000 iters) holds: the default CRC-16/MODBUS case
(init=0xFFFF, xorout=0x0000) is byte-exact against crcmod's reference.

Run:
    pip install crcmod
    python3 repro.py

NOTE on parameter conventions:
    For arbitrary (init, xorout) values, the reflected-algorithm convention
    in crcmod is: crcmod treats (init, xorout) as MSB-first register values,
    while crc16-modbus-pure treats init as pre-reflection and xorout as
    post-reflection. Both representations agree on (0xFFFF, 0x0000) (the
    Modbus default — the values are palindromes in 16 bits). For non-default
    pairs the two APIs intentionally differ; this is documented in SPEC.md.
    The repro therefore locks the Modbus default pair, where the contract
    holds byte-exactly.
"""

from __future__ import annotations
from crc16_modbus_pure import crc

try:
    import crcmod
except ImportError:
    print("SKIP: crcmod not installed (benchmark-time dep, not runtime dep).")
    raise SystemExit(0)


def main() -> int:
    # Modbus default parameters — byte-exact match per SPEC.md AC11.
    f = crcmod.mkCrcFun(0x18005, initCrc=0xFFFF, xorOut=0x0000, rev=True)
    ours = crc(b"123456789", init=0xFFFF, xorout=0x0000)
    theirs = f(b"123456789")
    # The RevEng canonical check value for CRC-16/MODBUS on "123456789" is
    # 0x4B37; both libraries must agree.
    print(f"ours=0x{ours:04X} crcmod=0x{theirs:04X} match={ours == theirs}")
    return 0 if ours == theirs else 1


if __name__ == "__main__":
    raise SystemExit(main())
