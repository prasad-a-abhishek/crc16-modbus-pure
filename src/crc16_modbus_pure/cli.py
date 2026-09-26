"""CRC-16/Modbus CLI (argparse). Stdout only, no file IO."""

import argparse
import sys

from . import __version__, crc


def _print_result(label, value):
    sys.stdout.write(f"{label}: 0x{value:04X}\n")


def _parse_hex_data(hex_string):
    """Parse a hex string into bytes. Accepts spaces and even-length hex digits."""
    cleaned = "".join(hex_string.split())
    if len(cleaned) % 2 != 0:
        raise ValueError(f"hex data must have even length, got {len(cleaned)}")
    try:
        return bytes.fromhex(cleaned)
    except ValueError as e:
        raise ValueError(f"invalid hex input: {e}") from e


def main_compute(argv=None):
    parser = argparse.ArgumentParser(
        prog="crc16-modbus-pure-compute",
        description="Compute CRC-16/Modbus over a hex byte string.",
    )
    parser.add_argument(
        "--data",
        required=True,
        help="hex bytes to checksum, e.g. '313233343536373839' for ASCII '123456789'",
    )
    args = parser.parse_args(argv)
    data = _parse_hex_data(args.data)
    result = crc(data)
    _print_result("CRC", result)
    return 0


def main_self_test(argv=None):
    parser = argparse.ArgumentParser(
        prog="crc16-modbus-pure-self-test",
        description="Print all known-good CRC-16/MODBUS vectors with PASS markers.",
    )
    parser.parse_args(argv)
    vectors = [
        (b"", 0x0000, "AC2 empty-stream trivial result (spec-locked)"),
        (bytes([0x00]), 0x40BF, "AC1 single-byte canonical vector"),
        (b"\x01", 0x807E, "single-byte 0x01 (crcmod-confirmed)"),
        (b"\xff", 0x00FF, "single-byte 0xFF (crcmod-confirmed)"),
        (bytes(range(10)), 0x4574, "bytes 0x00..0x09 (crcmod-confirmed)"),
        (b"\x00" * 256, 0x64BF, "AC7 256-byte zero run (crcmod-confirmed)"),
        (b"123456789", 0x4B37, "AC3 RevEng check value"),
    ]
    failures = 0
    for data, expected, label in vectors:
        actual = crc(data)
        status = "PASS" if actual == expected else "FAIL"
        if actual != expected:
            failures += 1
        sys.stdout.write(
            f"[{status}] {label}: "
            f"crc({len(data)}B) = 0x{actual:04X} (expected 0x{expected:04X})\n"
        )
    sys.stdout.write(f"\ncrc16-modbus-pure v{__version__} self-test: {len(vectors) - failures}/{len(vectors)} passed\n")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main_compute())
