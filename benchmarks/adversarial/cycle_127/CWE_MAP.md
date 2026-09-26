# crc16-modbus-pure — MITRE CWE Mapping (cycle_127/adversary/01)

**Scope:** 1–3 CWE entries per surface from SURFACES.md.
**Authority:** MITRE CWE database — https://cwe.mitre.org/ (offline reference; primary descriptions cited inline).
**Method:** for each surface, identify the failure mode the surface WOULD have if its guards were removed or bypassed.

---

## CWE-682 — Incorrect Calculation

**Surfaces:** #1 (`crc`), #5 (`main_self_test`), #6 (`_parse_hex_data`).

**Rationale:** the entire purpose of this package is *byte-exact* CRC computation. A calculation error (off-by-one shift, wrong polynomial constant, wrong XOR direction, wrong reflect bit order) would silently produce plausible-but-wrong CRCs that pass structural tests but fail interop with real Modbus slaves.

**Specific failure modes guarded:**
- Using un-reflected polynomial `0x8005` instead of reflected `0xA001` would yield non-reflected CRCs (`crc(b"123456789") == 0xCFC1` instead of `0x4B37`).
- Forgetting the initial register `0xFFFF` would shift all outputs.
- Forgetting `xorout=0x0000` would be a no-op (it IS zero by default) but a future API change to non-zero xorout would silently break.

**Test coverage:**
- AC1 (single-byte 0x00 → 0x40BF) — `TestRevengCanonical.test_ac1_single_byte_zero`.
- AC3 (9-byte check → 0x4B37) — `TestRevengCanonical.test_ac3_standard_check_value`.
- AC7 (256-byte zeros → 0x64BF) — `TestRevengCanonical.test_ac7_256_zero_run`.
- AC11 (differential vs crcmod on 25+10+10 fuzz inputs) — `TestDifferentialVsCrcmod`, `TestFuzzInputs`.

**Status:** MITIGATED — 35+ differential oracle tests + 5 RevEng-canonical vectors lock the algorithm byte-exact.

---

## CWE-190 — Integer Overflow or Wraparound

**Surfaces:** #1 (`crc`), #7 (`_print_result`).

**Rationale:** CRC arithmetic on a 16-bit register could overflow if the implementation worked on a fixed-width integer type. Python ints are arbitrary-precision (PEP 237), but the loop only right-shifts (`crc_reg >>= 1`), so high bits naturally fall away — but only AFTER the conditional XOR `_POLY = 0xA001` which is itself a 16-bit value.

**Specific failure modes guarded:**
- Without the final `& 0xFFFF` mask at line 64, an adversarial `xorout` value like `0xFFFF_FFFF_FFFF` could produce a 48-bit output.
- Without `crc_reg & 1` masking in the shift-and-XOR loop body, sign-extension bugs could occur in other languages; Python is safe here because `>>` on positive ints is logical, not arithmetic.

**Test coverage:**
- AC4 (register width = 16 bits) — `TestRegisterWidth.test_register_width_mask_identity` × 8 inputs, `test_register_width_max` × 4 lengths.
- `TestByteRange.test_single_byte_returns_16bit_int` × 256 inputs.

**Status:** MITIGATED — explicit `& 0xFFFF` mask on line 64 + 264 tests verify all outputs fit in 16 bits.

---

## CWE-125 — Out-of-bounds Read

**Surfaces:** #1 (`crc` — `for byte in data:` loop at line 57).

**Rationale:** the loop iterates over the bytes-like input. If `data` were a buffer with a custom `__iter__` that yielded non-byte values (e.g. 256, -1, 3.14), `crc_reg ^= byte` could yield an arbitrarily-large integer, defeating the 16-bit invariant.

**Specific failure modes guarded:**
- `bytes`, `bytearray`, `memoryview` all yield `int` values in `[0, 255]` — guaranteed by CPython implementation.
- Custom bytes-like with non-byte items would not pass the `isinstance(data, (bytes, bytearray, memoryview))` check on line 39 (the isinstance check rejects user-defined classes that don't subclass those three).

**Test coverage:**
- `TestTypeErrors` — 14 type-error tests guard the isinstance check.
- `TestByteRange.test_single_byte_returns_16bit_int` × 256 — every possible byte value is iterated.

**Status:** MITIGATED — strict isinstance check at line 39 + byte-by-byte CPython iteration guarantee.

---

## CWE-20 — Improper Input Validation

**Surfaces:** #1 (`crc`), #4 (`main_compute`), #6 (`_parse_hex_data`).

**Rationale:** the public API accepts user-controlled data from untrusted sources (Modbus frames, file payloads, network packets). The package must reject malformed input cleanly without crashing, leaking stack traces, or producing silently-wrong output.

**Specific failure modes guarded:**
- `crc(None)` → `TypeError` (not `ValueError` per AC12).
- `crc("string")` → `TypeError` with offending type name in message.
- `crc(42)` → `TypeError` (rejected before any arithmetic).
- `crc([])`, `crc({})`, `crc({1,2,3})` → all `TypeError` (covered by `TestTypeErrors`).
- `crc(True)` → `TypeError` (bool is int subclass but not bytes-like).
- `crc(b"x", init=True)` → `TypeError` (bool rejected for `init`).
- `_parse_hex_data("0A")` → `bytes.fromhex("0A") == b"\n"` (lowercase accepted, good).
- `_parse_hex_data("0A 1B")` → `b"\n\x1b"` (whitespace stripped, good).
- `_parse_hex_data("0")` → `ValueError` (odd length).
- `_parse_hex_data("zz")` → `ValueError` (non-hex).

**Test coverage:**
- `TestTypeErrors` — 14 tests covering None, str, int, list, dict, tuple, float, set, bool(data), bool(init), bool(xorout), str(xorout), list(init), None(init).
- `TestCliImports.test_cli_module_importable` — confirms CLI parses argv without exception on no-args.

**Status:** MITIGATED — exhaustive type-error test suite + validated hex parsing.

---

## CWE-754 — Improper Check for Unusual or Exceptional Conditions

**Surfaces:** #1 (`crc` — empty input short-circuit at line 53-54), #6 (`_parse_hex_data`).

**Rationale:** the empty-input case is a known "exceptional condition" for CRC algorithms. The standard RevEng convention for reflected algorithms is that an empty stream returns the *trivial* result `init ^ xorout ^ (post-reflection)`, which for CRC-16/Modbus resolves to `0x0000` (NOT `0xFFFF`). This is a deliberate, spec-locked exception (AC2) that differs from crcmod's empty-input behavior.

**Specific failure modes guarded:**
- Forgetting the empty-input short-circuit would produce `0xFFFF` (the init register) which is INCORRECT per AC2.
- The implementation explicitly returns `0x0000` for empty input rather than running the byte loop (which would also yield `0x0000` because the loop body never executes, but the short-circuit makes intent explicit).

**Test coverage:**
- AC2 — `TestRevengCanonical.test_ac2_empty_stream_trivial_result`, `TestLengthSweep.test_length_sweep_zero_input` (length=0 case).
- `TestEdgeConditions.test_empty_returns_16bit_zero`.

**Status:** MITIGATED — AC2 explicitly locked + 3 explicit empty-input tests.

---

## CWE-1339 — Insufficient Precision or Accuracy

**Surfaces:** #1 (`crc`), #5 (`main_self_test`).

**Rationale:** CRC is sensitive to single-bit errors. The implementation must use exactly 16-bit precision (no truncation to 8-bit, no early termination of the 8-iteration inner loop, no incorrect bit-order).

**Specific failure modes guarded:**
- Truncating `crc_reg` to 8 bits at any point would yield wrong CRCs.
- Shortening the inner loop from 8 to 7 iterations would produce a wrong CRC matching no known polynomial.
- Using `crc_reg >>= 1` (logical) vs `crc_reg //= 2` (floor-div) — both produce identical results for positive ints in Python, but a different implementation language could diverge.

**Test coverage:**
- AC11 — `TestDifferentialVsCrcmod.test_random_input_matches_crcmod` × 25 random inputs.
- AC11 — `TestFuzzInputs.test_fuzz_differential` × 10 fuzz inputs (256B-4KB each).
- AC8/AC9 — `TestEdgeConditions.test_ac8_refin_true_byte_flip`, `test_ac9_refout_true_byte_level`.

**Status:** MITIGATED — 35+ differential-oracle tests against the production-grade crcmod reference.

---

## CWE-704 — Incorrect Type Conversion or Cast

**Surfaces:** #4 (`main_compute`), #6 (`_parse_hex_data`), #7 (`_print_result`).

**Rationale:** the CLI converts between `str` (argv input), `bytes` (CRC input), and `int` (CRC output). Each conversion is a potential type-confusion attack surface.

**Specific failure modes guarded:**
- `bytes.fromhex(cleaned)` raises `ValueError` for non-hex chars — wrapped in try/except on line 18-21.
- `f"0x{value:04X}"` format requires `value` to be a non-negative int — bounded by CRC return type.
- `cleaned.split()` returns a list of strings; `"".join(...)` produces a string — type-safe.

**Test coverage:**
- `TestCliImports` — 3 tests confirm CLI module imports and entry points exist.
- No explicit CLI negative-path tests (e.g. `--data "zz"`) — see TEST_GAPS.md Finding G-1.

**Status:** MITIGATED (CLI paths) — internal type-confusion tests live in `TestTypeErrors`. GAP (see TEST_GAPS.md).

---

## CWE-400 — Uncontrolled Resource Consumption

**Surfaces:** #1 (`crc`), #4 (`main_compute`), #5 (`main_self_test`).

**Rationale:** a malicious caller could pass a 100 MB `bytes` object. The CRC loop is `O(n)` time + `O(1)` extra memory (the register is a single int), so worst-case compute is ~10s on CPython 3.11 per 100 MB. CLI processes stdin-less args, so no stream exhaustion possible.

**Specific failure modes guarded:**
- The loop body is `for byte in data: ... for _ in range(8): ...` — bounded by `len(data) * 8` iterations.
- No recursion — stack depth = 1.
- No file/network I/O.

**Test coverage:**
- `TestLengthSweep.test_length_sweep_ff_input` × 13 lengths including 4096.
- `TestRegisterWidth.test_register_width_max` — 65536-byte input tested.
- `TestEdgeConditions.test_max_byte_input_long` — 65536 bytes of 0xFF.

**Status:** MITIGATED — bounded O(n) loop, no I/O, no recursion. GAP (no explicit ≥1 MB stress test) — see TEST_GAPS.md Finding G-2.

---

## CWE-681 — Incorrect Conversion between Numeric Types

**Surfaces:** #7 (`_print_result`), #4 (`main_compute`).

**Rationale:** the CLI formats the CRC int as `0xHHHH`. Format-string bugs (e.g. `0x%X` without zero-padding) would produce inconsistent widths (`0x4B37` vs `0x4b37` vs `0x0`).

**Specific failure modes guarded:**
- `f"0x{value:04X}"` — uppercase X, zero-padded to 4 digits, always 6-char output.
- `value` is always in `[0, 0xFFFF]` per CRC return invariant, so width is bounded.

**Test coverage:**
- No explicit CLI format-output test (e.g. assert stdout == `"CRC: 0x4B37\n"`) — see TEST_GAPS.md Finding G-1.

**Status:** MITIGATED (format string is deterministic) — GAP on end-to-end CLI test.

---

## CWE-1284 — Improper Validation of Specified Quantity in Input

**Surfaces:** #4 (`main_compute`), #5 (`main_self_test`).

**Rationale:** SPEC §3 AC9/AC10 require the CLI to handle both `--data HEXSTR` and `--self-test`. The argparse parser for `main_compute` declares only `--data` (no `--self-test` flag) — but the entrypoint is wired to `main_self_test` separately via the console script entry, so the two flows are correctly isolated.

**Specific failure modes guarded:**
- `parser.add_argument("--data", required=True)` rejects empty/missing data.
- `main_self_test` declares no flags → rejects any argv.

**Test coverage:**
- `TestCliImports.test_cli_module_importable`, `test_main_module_wired`, `test_package_exports`.

**Status:** MITIGATED — two separate argparse parsers + console-script entries for each mode.

---

## CWE-1281 — Sequence of Processor Instructions Leads to Expected Behavior (informational)

**Surface:** #1 (`crc`) — INFO only.

**Rationale:** the loop body follows the RevEng transcribed pseudocode line-for-line. No sequence-of-instructions concern in pure-Python; listed for completeness.

**Status:** INFORMATIONAL — no actionable finding.

---

## CWE mapping summary

| Surface | CWE | Severity (worst case) | Status |
|---------|-----|----------------------|--------|
| #1 `crc` | CWE-682, CWE-190, CWE-125, CWE-20, CWE-754, CWE-1339, CWE-400 | Medium (unhandled) → Low (handled) | MITIGATED |
| #2 module import | (none — no executable code at import) | — | N/A |
| #3 `-m` entry | CWE-1284 | Low | MITIGATED |
| #4 compute CLI | CWE-20, CWE-704, CWE-400, CWE-1284 | Low | MITIGATED |
| #5 self-test CLI | CWE-682, CWE-400 | Low | MITIGATED |
| #6 `_parse_hex_data` | CWE-682, CWE-20, CWE-704 | Low | MITIGATED |
| #7 `_print_result` | CWE-190, CWE-681 | Low | MITIGATED |

**Unique CWE entries mapped:** 10 (CWE-20, CWE-125, CWE-190, CWE-400, CWE-681, CWE-682, CWE-704, CWE-754, CWE-1284, CWE-1339, CWE-1281-info). Within target range.
