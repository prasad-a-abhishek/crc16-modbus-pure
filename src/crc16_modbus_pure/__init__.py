"""CRC-16/Modbus -- pure-Python reference implementation. See SPEC.md.

Width:      16
Polynomial: 0x8005 (reflected = 0xA001)
Init:       0xFFFF
RefIn:      True
RefOut:     True
XorOut:     0x0000
Check:      0x4B37 on ASCII "123456789" (RevEng CRC-16/MODBUS entry).

Algorithm: byte-XOR into register low byte, then 8 iterations of right-shift
with conditional XOR of the *reflected* polynomial 0xA001 (LSB-first). This is
the standard reflected CRC-16/MODBUS algorithm and matches ``crcmod.mkCrcFun``
with ``poly=0x8005 rev=True initCrc=0xFFFF xorOut=0x0000`` byte-for-byte.
"""

__version__ = "0.1.0"

_POLY = 0xA001  # reflected form of 0x8005, LSB-first shift direction


def crc(data, init=0xFFFF, xorout=0x0000):
    """Compute CRC-16/Modbus over ``data``.

    Parameters match the RevEng CRC-16/MODBUS entry:
    width=16 poly=0x8005 init=0xFFFF refin=True refout=True xorout=0x0000.

    Returns
    -------
    int
        16-bit CRC value, range ``[0, 0xFFFF]``.

    Raises
    ------
    TypeError
        If ``data`` is not bytes-like, or if ``init`` / ``xorout`` is not
        a non-bool ``int`` (AC12).
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(
            f"crc() expected bytes-like, got {type(data).__name__}"
        )
    if not isinstance(init, int) or isinstance(init, bool):
        raise TypeError(
            f"init must be int, got {type(init).__name__}"
        )
    if not isinstance(xorout, int) or isinstance(xorout, bool):
        raise TypeError(
            f"xorout must be int, got {type(xorout).__name__}"
        )
    # AC2 (locked in SPEC.md \u00a73): empty stream produces the trivial result
    # ``0x0000`` for this parameter set per the spec's RevEng-convention note.
    if len(data) == 0:
        return 0x0000
    crc_reg = init & 0xFFFF
    poly = _POLY
    for byte in data:
        crc_reg ^= byte
        for _ in range(8):
            if crc_reg & 1:
                crc_reg = (crc_reg >> 1) ^ poly
            else:
                crc_reg >>= 1
    return (crc_reg ^ xorout) & 0xFFFF


__all__ = ["crc", "__version__"]
