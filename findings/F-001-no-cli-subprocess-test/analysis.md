# F-001 — No subprocess-based CLI test (Info)

- **Severity:** Info (defense-in-depth, test-coverage gap)
- **Surface:** #4 CLI / #6 `_parse_hex_data`
- **CWE:** CWE-20 (Improper Input Validation), CWE-704 (Incorrect Type Conversion)
- **Origin:** cycle_127/adversary/01 VULN_AUDIT.md (G-1 in TEST_GAPS.md)
- **Card-03 fuzzer status:** Did not trigger (no crash/hang/oracle-mismatch observed).

## Failure mode (hypothetical)

A future regression that broke argparse handling (e.g. accidentally renaming `--data`
to `--hex-data`, or reverting the odd-length-hex branch to silently truncate) would
not be caught by the current test suite, because `tests/test_crc16_modbus_pure.py`
only imports `cli.py` and checks function signatures — it never spawns the actual
console-script binaries via subprocess.

## Why it is Info, not Low

- The current implementation is covered: `TestCliImports` exercises
  `cli.main_compute` and `cli.main_self_test` as Python functions.
- An argparse rename is a developer-visible diff that any reasonable CI smoke test
  would catch.
- No security boundary is bypassed — the function-level guard for `len(data) % 2 != 0`
  is already tested directly via `cli.main_compute` invocation.

## Recommendation

Add `tests/test_cli_subprocess.py` with 4 scenarios:

1. `crc16-modbus-pure-compute` happy path: input `48656c6c6f` → exit 0, stdout `0xC9CA`
2. `crc16-modbus-pure-self-test` happy path → exit 0, stdout contains `OK`
3. Bad hex (e.g. `zz`) → exit nonzero
4. Odd-length hex (e.g. `abc`) → exit nonzero

Acceptance: 4 tests pass on a fresh venv; no change required in src/.

## Evidence

- `src/crc16_modbus_pure/cli.py:1-71`
- `tests/test_crc16_modbus_pure.py::TestCliImports`
- `benchmarks/adversarial/cycle_127/VULN_AUDIT.md` §F-001
- `benchmarks/adversarial/cycle_127/TEST_GAPS.md` G-1
