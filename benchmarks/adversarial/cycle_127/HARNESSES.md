# crc16-modbus-pure — Adversarial Harness Index (cycle_127/adversary/02)

**Scope:** 8 standalone Python fuzz harnesses targeting the 7 surfaces enumerated in `SURFACES.md` (cycle_127/adversary/01).
**Method:** stdlib-only fuzzing (`random`, `itertools`, `struct`, `os`, `tempfile`, `argparse`, `subprocess`, `json`, `time`, `traceback`). Atheris / LibFuzzer are C-binary fuzzers that target native code; pure-Python CRC is more efficiently tested with stdlib Python + oracle checks.
**Date:** 2026-09-26
**Commit:** (see kanban metadata; this file is part of the same commit as the harnesses)

---

## Harness summary

| # | Harness | Surfaces covered | Mode | Smoke `--iters 100` | Notes |
|---|---------|------------------|------|---------------------|-------|
| 1 | `harness_crc_main.py` | #1 (crc) | random+stress+subclass | 0 crashes / 2.04s | canonical vectors + 1MB stress + bytes subclass acceptance |
| 2 | `harness_type_errors.py` | #1 (type-error path) | curated+random | 0 crashes / 0.00s | AC12 type-error oracle; rejects None/str/int/list/dict/bool; accepts bytes subclasses |
| 3 | `harness_large_input.py` | #1 (resource exhaustion) | sizes 1..1MB | 0 crashes / 185.4s | CWE-400: ≥1MB stress (default cap 2MB to keep smoke fast); `--max-mb 10` enables 10MB |
| 4 | `harness_cli_data.py` | #4 (compute CLI) | canonical+variant+neg+fuzz | 0 crashes / 1.80s | uses `crc16-modbus-pure-compute` console script (NOT `-m`, since `-m` runs self-test) |
| 5 | `harness_cli_self_test.py` | #3, #5 (`-m`, self-test CLI) | determinism+neg-path | 0 crashes / 1.66s | 100 repeat invocations all byte-identical |
| 6 | `harness_crc_oracle.py` | #1 (algorithm fidelity) | crcmod-oracle | 0 crashes / 0 oracle mismatches / 0.02s | graceful SKIP if crcmod absent (documented); smoke had crcmod installed |
| 7 | `harness_module_import.py` | #2 (module import) | fresh-subprocess import | 0 crashes / 0.08s | runs probe under 6 PYTHONHASHSEED values |
| 8 | `harness_cross_cycle.py` | #1 (determinism + bitwise reference) | determinism+reference-oracle | 0 crashes / 0 oracle mismatches / 0.17s | 1000-repeat determinism on `b"123456789"` + bitwise reference impl cross-check |

**Total surfaces covered:** 7 of 7 (SURFACES.md #1–#7).
**Total harnesses:** 8 (above the 3-harness minimum).

---

## Smoke results (`--iters 100` for every harness)

```
=== harness_crc_main ===      [crc_main] iters=100 crashes=0 time=2.04s    exit=0
=== harness_type_errors ===   [type_errors] iters=100 crashes=0 time=0.00s exit=0
=== harness_large_input ===   [large_input] sizes=[1,1000,100000,1000000] iters/size=100 crashes=0 time=185.4s exit=0
=== harness_cli_data ===      [cli_data] iters=100 crashes=0 time=1.80s   exit=0
=== harness_cli_self_test === [cli_self_test] iters=100 crashes=0 time=1.66s exit=0
=== harness_crc_oracle ===    [crc_oracle] iters=100 crashes=0 oracle_mismatches=0 time=0.02s exit=0
=== harness_module_import === [module_import] iters=6 crashes=0 time=0.08s exit=0
=== harness_cross_cycle ===   [cross_cycle] iters=100 det_iters=1000 crashes=0 oracle_mismatches=0 time=0.17s exit=0
```

All harnesses exit 0; zero crashes; zero oracle mismatches.

---

## Per-harness detail

### 1. `harness_crc_main.py` (surface #1)

Three sub-modes:
- **random**: 100 iterations of length-0..10000 random bytes. Asserts result is `int` in `[0, 0xFFFF]`.
- **stress**: 1 MB all-0x00, 1 MB all-0xFF, 1 MB alternating `0xAA55`. Asserts determinism (r1 == r2) and 16-bit range.
- **subclass**: bytearray + memoryview wrappers around the 7 canonical vectors. Asserts byte-exact match against `bytes` result.

Always runs the 7 canonical vectors first (AC1, AC2, AC3, AC4, AC7, AC8/AC9, AC10).

### 2. `harness_type_errors.py` (surface #1, AC12 type-error path)

Three negative suites:
- **BAD_DATA**: None, str, int, float, list, dict, tuple, set, bool-True/False, object(). Each MUST raise `TypeError`.
- **BAD_INIT / BAD_XOROUT**: bool is rejected (int subclass but disallowed per AC12); str / list / dict / float / None / bytes are rejected.
- **ACCEPT_DATA**: bytes-literal, bytearray, memoryview at `b"123456789"` → `0x4B37`; empty bytes/bytearray/memoryview → `0x0000`.

Plus 100 random object-generation iterations to find unexpected input-validation holes.

### 3. `harness_large_input.py` (surface #1, CWE-400)

Sizes `[1, 1000, 100000, 1000000, 10000000]` with patterns all-0x00, all-0xFF, alternating. Each size × pattern repeated `--iters` times for determinism. Default `--max-mb 2` keeps smoke run ≤200s; pass `--max-mb 10` to exercise the full 10 MB upper bound (raises smoke to ~1000s).

### 4. `harness_cli_data.py` (surface #4, `--data` CLI)

Four suites:
- **canonical**: AC3 (`313233343536373839` → `0x4B37`), AC1 (`00` → `0x40BF`), AC2 (empty → `0x0000`).
- **variant**: whitespace-tolerant (`"31 32 33..."`, `" 3132..."`, trailing/leading space, embedded/trailing newline) and lowercase-hex.
- **neg-path**: odd-length / non-hex / `0x41` prefix MUST be rejected.
- **fuzz**: 100 random even-length hex strings; every one must produce a valid 4-digit hex output.

Uses the **`crc16-modbus-pure-compute`** console script (not `python -m ... --data`, which routes through `__main__.py` → unconditional self-test).

### 5. `harness_cli_self_test.py` (surfaces #3 + #5)

- **baseline**: `python -m crc16_modbus_pure` must exit 0, produce 7 `[PASS]` lines, end with `7/7 passed`, contain `0x4B37`.
- **determinism**: 100 repeat invocations all byte-identical.
- **neg-path**: `crc16-modbus-pure-self-test --bogus`, `--data 00`, `foo`, `--help` all exit cleanly with no traceback leak.

### 6. `harness_crc_oracle.py` (surface #1, AC11 / CWE-682)

If `crcmod` is importable: byte-exact match against `crcmod.mkCrcFun(0x18005, initCrc=0xFFFF, xorOut=0x0000, rev=True)` for the 6 canonical vectors + 100 random inputs of length 1..1024.
If `crcmod` is NOT importable: prints `SKIPPED`, returns 0 (documented graceful-skip).

In this run, crcmod 1.7 was installed and the oracle path executed — 0 oracle mismatches across 100 random inputs.

### 7. `harness_module_import.py` (surface #2)

Spawns a fresh subprocess per probe with a probe script that:
- captures stdout/stderr and asserts no output
- turns DeprecationWarnings into errors
- imports `crc16_modbus_pure`, asserts `crc` callable and `__version__` is `str`
- asserts `crc(b"123456789") == 0x4B37`
- iterates `__all__` and asserts every name is a module attribute

Probes run under PYTHONHASHSEED ∈ {0, 1, 42, 1337, 9999, 2³¹−1}.

### 8. `harness_cross_cycle.py` (surface #1, CWE-1339 / determinism)

Two checks:
- **Determinism**: 1000 repeat calls of `crc(b"123456789")` must all return the same `int`. Any distinct result is a non-determinism bug.
- **Bitwise reference**: an independent, intentionally-different transcribed bitwise implementation (matching SPEC §1) must agree with the package on the 6 canonical vectors + 100 random inputs of length 1..4096.

The reference impl uses identical math but is written from scratch — a wrong algorithm transcription in the package would diverge.

---

## Output format

Every harness accepts `--iters N` (default 100) and prints one line:

```
[<surface>] iters=N crashes=N oracle_mismatches=N time=Ts
```

Detailed per-finding JSON is dumped to `fuzz/<surface>/results.json` (crashes capped at 50 entries; full timing info preserved for `large_input`). Exit code is 0 on success, 1 on any crash or oracle mismatch.

---

## Coverage matrix (surface × harness)

| Surface | crc_main | type_errors | large_input | cli_data | cli_self_test | crc_oracle | module_import | cross_cycle |
|---------|----------|-------------|-------------|----------|---------------|------------|---------------|-------------|
| #1 `crc` | ✓ | ✓ | ✓ | — | — | ✓ | — | ✓ |
| #2 module import | — | — | — | — | — | — | ✓ | — |
| #3 `-m` entry | — | — | — | — | ✓ | — | — | — |
| #4 compute CLI | — | — | — | ✓ | — | — | — | — |
| #5 self-test CLI | — | — | — | — | ✓ | — | — | — |
| #6 `_parse_hex_data` (indirect via #4) | — | — | — | ✓ | — | — | — | — |
| #7 `_print_result` (indirect via #4) | — | — | — | ✓ | — | — | — | — |

All 7 surfaces are touched by at least one harness.

---

## Running

```bash
# install package + crcmod
pip install -e .
pip install crcmod   # optional; harness gracefully skips if absent

# run individual harness
python3 benchmarks/adversarial/cycle_127/harness_crc_main.py --iters 1000
python3 benchmarks/adversarial/cycle_127/harness_type_errors.py --iters 500
python3 benchmarks/adversarial/cycle_127/harness_large_input.py --iters 2 --max-mb 10
python3 benchmarks/adversarial/cycle_127/harness_cli_data.py --iters 1000
python3 benchmarks/adversarial/cycle_127/harness_cli_self_test.py --iters 50
python3 benchmarks/adversarial/cycle_127/harness_crc_oracle.py --iters 1000
python3 benchmarks/adversarial/cycle_127/harness_module_import.py --iters 6
python3 benchmarks/adversarial/cycle_127/harness_cross_cycle.py --iters 1000 --det-iters 1000
```

---

## VERDICT

All 8 harnesses execute cleanly under `--iters 100`. Zero crashes, zero oracle mismatches across 100+100+200+100+100+100+6+100 = 806 input vectors plus 1000-repeat determinism on `b"123456789"`. The package is fuzz-clean under this harness suite.

**VERDICT: CLEAN (cycle_127/adversary/02).**
