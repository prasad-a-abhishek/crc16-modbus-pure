# crc16-modbus-pure — Attack Surface Enumeration (cycle_127/adversary/01)

**Scope:** every public callable + module-level entry point in `crc16-modbus-pure` v0.1.0.
**Method:** static read of `src/crc16_modbus_pure/__init__.py` (67 lines), `cli.py` (71 lines), `__main__.py` (8 lines). Verified by `cat` line counts above.
**Date:** 2026-09-26

---

## Surface #1 — `crc(data, init=0xFFFF, xorout=0x0000)` (top-level public API)

- **Entry point:** `src/crc16_modbus_pure/__init__.py:22`
- **Signature:** `def crc(data, init=0xFFFF, xorout=0x0000) -> int`
- **Input domain:**
  - `data`: must be `bytes`, `bytearray`, or `memoryview` (validated by `isinstance(data, (bytes, bytearray, memoryview))` at line 39).
  - `init`: any `int` excluding `bool` (line 43-46).
  - `xorout`: any `int` excluding `bool` (line 47-50).
- **Output range:** 16-bit unsigned `int` ∈ `[0, 0xFFFF]` (guaranteed by `& 0xFFFF` mask at line 64).
- **Adversarial inputs (must raise `TypeError`):** `None`, `str`, `int`, `list`, `tuple`, `dict`, `set`, `float`, `bool` (as data), `True`/`False` (as `init`/`xorout`).
- **Accepted bytes-like subclasses:** `bytes`, `bytearray`, `memoryview` — each iterates byte-by-byte.
- **Edge cases covered by tests:**
  - `crc(b"") == 0x0000` (AC2 — empty stream short-circuit at line 53-54).
  - `crc(b"123456789") == 0x4B37` (AC3 — RevEng canonical check value).
  - `crc(bytes([0x00])) == 0x40BF` (AC1 — single-byte RevEng vector).
  - `crc(b"\x00" * 256) == 0x64BF` (AC7 — 256-byte zero run, verified against crcmod).
  - `crc(b"\xff" * 65536) == ?` (AC8 — large refin verification, returns valid 16-bit).
  - `crc(b"a" * 1024)` (length sweep coverage).
  - `crc(b"The quick brown fox jumps over the lazy dog" * 10)` (representative real-world ASCII).
- **Algorithm path:** byte-XOR into low register → 8 iterations of right-shift with conditional XOR of reflected poly `0xA001` → final XOR with `xorout` → 16-bit mask.

## Surface #2 — Module import surface (`from crc16_modbus_pure import crc`)

- **Entry point:** `src/crc16_modbus_pure/__init__.py:1-15` (module docstring) + line 67 (`__all__`).
- **Public symbols:** `crc`, `__version__` only (per `__all__ = ["crc", "__version__"]`).
- **Module-level state:** `_POLY = 0xA001` (private constant), `__version__ = "0.1.0"`.
- **Side effects on import:** none (no `print`, no `os.environ` reads, no I/O, no global mutation). Verified by reading the full module — only assignments + function definitions.
- **Surface risk:** import-time attacks are N/A because there is no import-time code beyond the docstring and constant assignments.

## Surface #3 — `python3 -m crc16_modbus_pure --self-test` entrypoint

- **Entry point:** `src/crc16_modbus_pure/__main__.py:8` (calls `sys.exit(main_self_test())`).
- **Wiring:** `__main__.py` unconditionally calls `main_self_test()` with no argv parsing — argv must be empty when invoked via `-m`.
- **Subroutine:** `src/crc16_modbus_pure/cli.py:41-67` — `main_self_test(argv=None)`.
- **argv handling:** `parser.parse_args(argv)` accepts `None` (default → `sys.argv[1:]`); the parser declares NO arguments, so any extra argv triggers `SystemExit` via argparse.
- **Output:** 7 PASS/FAIL lines + 1 summary line to stdout.
- **Exit codes:** `0` if all 7 vectors pass, `1` otherwise.
- **Adversarial inputs:** passing any argv element causes argparse to print usage and exit non-zero (no command injection risk — argparse is a safe sink).

## Surface #4 — `crc16-modbus-pure-compute` console script (argparse `--data`)

- **Entry point:** `src/crc16_modbus_pure/cli.py:24-38` — `main_compute(argv=None)`.
- **Wired via:** `pyproject.toml [project.scripts]` → `crc16_modbus_pure.cli:main_compute`.
- **Argv interface:** single required `--data HEXSTR` flag (line 29-33).
- **Processing pipeline:**
  1. `_parse_hex_data(args.data)` (line 13-21): strips whitespace via `str.split()`, enforces even length, calls `bytes.fromhex(cleaned)`.
  2. `crc(data)` (line 36): byte-exact CRC computation.
  3. `_print_result("CRC", result)` (line 9-10): writes `CRC: 0xHHHH\n` via `sys.stdout.write` (no `print` race).
- **Adversarial inputs to `_parse_hex_data`:**
  - Odd-length hex string → `ValueError` ("hex data must have even length").
  - Non-hex characters (e.g. `'zz'`, `'0x41'`) → `ValueError` ("invalid hex input: ...").
  - Empty string after strip → even length (0) → `bytes.fromhex("")` returns `b""` → `crc(b"") == 0x0000` (AC2).
- **Exit codes:** `0` on success, non-zero via uncaught `ValueError`/`SystemExit` on bad input.

## Surface #5 — `crc16-modbus-pure-self-test` console script

- **Entry point:** `src/crc16_modbus_pure/cli.py:41-67` — `main_self_test(argv=None)`.
- **Wired via:** `pyproject.toml [project.scripts]` → `crc16_modbus_pure.cli:main_self_test`.
- **Argv interface:** no arguments accepted (parser has zero `add_argument` calls).
- **Hard-coded test vectors (line 47-55):**
  1. `b""` → `0x0000` (AC2)
  2. `bytes([0x00])` → `0x40BF` (AC1)
  3. `b"\x01"` → `0x807E`
  4. `b"\xff"` → `0x00FF`
  5. `bytes(range(10))` → `0x4574`
  6. `b"\x00" * 256` → `0x64BF` (AC7)
  7. `b"123456789"` → `0x4B37` (AC3)
- **Output:** one `[PASS]`/`[FAIL]` line per vector + one summary `crc16-modbus-pure v0.1.0 self-test: 7/7 passed`.
- **Adversarial inputs:** none — argv parsing rejects unknown flags via argparse.

## Surface #6 — `_parse_hex_data(hex_string)` internal helper

- **Entry point:** `src/crc16_modbus_pure/cli.py:13-21`.
- **Signature:** `def _parse_hex_data(hex_string) -> bytes`.
- **Input domain:** any `str` (Python `str.split()` works on `str`; passing `bytes` would raise `AttributeError` — not a documented surface but worth noting).
- **Processing:**
  1. `cleaned = "".join(hex_string.split())` — strips all whitespace (spaces, tabs, newlines).
  2. `len(cleaned) % 2 != 0` → `ValueError`.
  3. `bytes.fromhex(cleaned)` — may raise `ValueError` (non-hex chars) or `TypeError` (non-string input). Caught and re-raised as `ValueError` with `from e`.
- **Risk:** explicit `from e` preserves traceback chain (good practice).

## Surface #7 — `_print_result(label, value)` internal helper

- **Entry point:** `src/crc16_modbus_pure/cli.py:9-10`.
- **Signature:** `def _print_result(label, value) -> None`.
- **Behavior:** `sys.stdout.write(f"{label}: 0x{value:04X}\n")` — formats `value` as 4-digit uppercase hex with `0x` prefix.
- **Risk:** `value` is always the return of `crc()` (already masked to `[0, 0xFFFF]`), so the format is bounded. If a future caller passes a negative number, `{value:04X}` would crash with `ValueError: Unknown format code 'X' for object of type 'int'` for negative values — but the surface is internal and not exposed.

---

## Surface count: 7

(within the 4–7 target band from the task brief)
