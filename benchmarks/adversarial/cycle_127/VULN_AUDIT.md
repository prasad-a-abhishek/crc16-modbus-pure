# crc16-modbus-pure — Vulnerability Audit (cycle_127/adversary/01)

**Auditor:** @repo-adversary (cycle_127/adversary/01)
**Date:** 2026-09-26
**Package:** crc16-modbus-pure v0.1.0
**Branch:** `wt/cycle127-adversary-01` @ commit `db16731`

---

## Executive summary

| Metric | Value |
|--------|-------|
| Surfaces enumerated | 7 |
| Unique CWE entries mapped | 11 (10 actionable + 1 informational) |
| ACs test-mapped | 12 of 12 (100%) |
| Findings — Critical | 0 |
| Findings — High | 0 |
| Findings — Medium | 0 |
| Findings — Low | 0 |
| Findings — Info | 5 (test-coverage defense-in-depth, see TEST_GAPS.md) |

**Verdict rationale:** zero Critical/High/Medium/Low findings. The 5 Info findings (G-1 to G-5 in TEST_GAPS.md) are defense-in-depth recommendations for additional test coverage — none represent exploitable vulnerabilities in the current implementation. The implementation is byte-exact against the canonical RevEng/Modbus.org CRC-16/Modbus algorithm and matches `crcmod.mkCrcFun(0x18005, initCrc=0xFFFF, xorOut=0x0000, rev=True)` on 35+ differential-oracle test inputs.

---

## Methodology

### Surface enumeration

Read the complete source of `src/crc16_modbus_pure/__init__.py` (67 lines), `cli.py` (71 lines), `__main__.py` (8 lines), and `pyproject.toml` (verified `dependencies = []` and console-script entries). Enumerated every public callable + module-level entry point. Cross-referenced each surface with SPEC.md §3 AC1–AC12 and `tests/test_crc16_modbus_pure.py`.

### CWE mapping

For each surface, identified 1–3 most-relevant CWE entries by asking: "what failure mode would this surface HAVE if its current guards were removed?" Mapped 10 actionable CWEs (CWE-20, CWE-125, CWE-190, CWE-400, CWE-681, CWE-682, CWE-704, CWE-754, CWE-1284, CWE-1339) plus 1 informational (CWE-1281).

### Test gap analysis

For each of the 12 LOCKED ACs in SPEC.md §3, located ≥1 test function name in `tests/test_crc16_modbus_pure.py` that asserts the AC. All 12 ACs have ≥1 test. Additionally identified 5 observability-level gaps (CLI subprocess coverage, stress test, thread-safety test, init/xorout matrix locking, `-m` entry coverage).

### Reference cross-checks

- **RevEng CRC Catalogue** — `https://reveng.sourceforge.io/crc-catalogue/all.htm` — CRC-16/MODBUS entry: width=16, poly=0x8005, init=0xFFFF, refin=true, refout=true, xorout=0x0000, check=0x4B37. Verified byte-exact match via `TestDifferentialVsCrcmod`.
- **Modbus.org Application Protocol V1.1b3** — `https://www.modbus.org/docs/Modbus_Application_Protocol_V1_1b3.pdf` — §6.2 "CRC Generating Function" specifies the same parameters + reflected polynomial `0xA001` for LSB-first implementation. Matches `src/crc16_modbus_pure/__init__.py` line 19.
- **Wikipedia Modbus article** — `https://en.wikipedia.org/wiki/Modbus` — RTU framing section confirms CRC-16 polynomial `0xA001` reflected, init `0xFFFF`, used for every RTU frame.
- **MITRE CWE database** — https://cwe.mitre.org/ — referenced for all 11 CWE entries cited.

---

## Findings table

| # | Severity | Surface | CWE | Description | Recommendation |
|---|----------|---------|-----|-------------|----------------|
| F-001 | Info | #4 CLI / #6 `_parse_hex_data` | CWE-20, CWE-704 | No subprocess-based CLI test asserting stdout content (G-1 in TEST_GAPS.md). | Add `tests/test_cli_subprocess.py` with 4 scenarios (compute success, self-test success, bad hex, odd-length hex). |
| F-002 | Info | #1 `crc` | CWE-400 | No ≥1 MB stress test asserting bounded compute time (G-2). | Add `test_one_mb_input_completes` (1 MB input, assert <5s). |
| F-003 | Info | #1 `crc` | CWE-1281 (info) | No concurrent thread-safety test (G-3). | Add `ThreadPoolExecutor` test asserting 100 concurrent calls all return identical CRC. |
| F-004 | Info | #1 `crc` | CWE-1339 | `TestInitXoroutMatrix` does not lock specific CRC values per (init, xorout) pair (G-4). | Compute one (init, xorout) case against crcmod and lock the exact value. |
| F-005 | Info | #3 `-m` entry | CWE-1284 | No subprocess test of `python -m crc16_modbus_pure` (G-5). | Add subprocess test invoking `python -m crc16_modbus_pure` with no args. |

---

## Per-finding narrative

### F-001 (Info) — No subprocess-based CLI test

The package ships two console scripts (`crc16-modbus-pure-compute`, `crc16-modbus-pure-self-test`) and a `python -m` entry. The current test suite imports `cli.py` and checks function signatures, but never spawns the actual console script binaries via subprocess. A regression that broke argparse handling (e.g. accidentally renaming `--data` to `--hex-data`) would not be caught by the current tests. Recommended addition is 4 subprocess-based assertions covering happy path + 2 failure paths + format validation. This is defense-in-depth — no current failure mode exists.

### F-002 (Info) — No ≥1 MB stress test

The longest input currently tested is 65536 bytes (`TestRegisterWidth.test_register_width_max`). CWE-400 (Uncontrolled Resource Consumption) is mitigated by the loop's bounded `O(n)` structure, but no test asserts this empirically at ≥1 MB scale. Recommended addition: a single `test_one_mb_input_completes` that allocates 1 MB, computes CRC, asserts the result is in `[0, 0xFFFF]` and that compute time is <5s on CPython 3.11. Pure defense-in-depth.

### F-003 (Info) — No concurrent thread-safety test

The implementation has no shared mutable state (only module-level constants `_POLY` and `__version__`), so thread-safety should hold trivially. But the test suite does not assert it. A `ThreadPoolExecutor`-based test with 100 concurrent invocations on a shared input would lock this invariant.

### F-004 (Info) — `init`/`xorout` matrix does not lock specific values

`TestInitXoroutMatrix` covers 16 (init, xorout) pairs and asserts only `isinstance(int)` + `0 <= result <= 0xFFFF`. A bug that produced a constant 0 for all parameter combinations would pass this test. Computing one (init, xorout) pair against crcmod (e.g. `init=0x0000`, `xorout=0xFFFF` on `b"123456789"`) and locking the exact value would close this gap.

### F-005 (Info) — `python -m crc16_modbus_pure` not exercised end-to-end

`TestCliImports.test_main_module_wired` confirms the `__main__` module imports without error and that `main_self_test` is bound. But no test actually invokes `python -m crc16_modbus_pure` via subprocess to confirm the `__main__.py` → `cli.py` → `main_self_test` chain produces the expected output. This is a low-risk gap because both modules are individually tested.

---

## Cross-cycle comparison

| Property | crc16-modbus-pure (cycle_127) | crc7-umts-pure (cycle_124) |
|----------|-------------------------------|----------------------------|
| Public API surface | `crc(data, init, xorout) -> int` | `crc(data, init=0, xorout=0) -> int` |
| Surface count | 7 | 7 (estimated analogous) |
| CWE count | 10 actionable + 1 info | 10 (estimated) |
| Verdict | CLEAN | CLEAN (per cycle_124 history) |
| Info findings | 5 (test-coverage defense-in-depth) | similar count expected |
| Runtime deps | 0 | 0 |

**Observation:** crc16-modbus-pure follows the same architectural pattern as the previously-shipped crc7-umts-pure — small public API, zero runtime deps, byte-exact against crcmod on RevEng vectors, ~120 LOC core implementation, ~400 pytest items. The cycle_124 work established the pattern; cycle_127 follows it.

---

## Acceptance summary

The three pillars of the highest-quality-repo contract are met:

- **Useful:** the package solves a real problem (Modbus-RTU CRC-16 reference for embedded/industrial Python environments where `crcmod` is unavailable). SPEC §1 documents the workflow gap. Discoverer passed `check_existing.py` with `VERDICT: APPROVED`.
- **Proven:** 388 pytest items across 9 categories, byte-exact against crcmod on 35+ random inputs, all 12 LOCKED ACs covered. Fresh-venv smoke test confirms CLI works.
- **Honest:** README's install command (`pip install git+https://github.com/...`) matches the (non-PyPI) reality. Test count matches `pytest --collect-only` output. SPEC §6 documents "NOT cryptographic, NOT optimized, NOT a multi-CRC library" in both SPEC and README.

---

## VERDICT: CLEAN

Zero Critical, High, Medium, or Low findings. Five Info findings (F-001 through F-005) are defense-in-depth test-coverage recommendations tracked in TEST_GAPS.md and do not represent exploitable vulnerabilities in the current implementation.

VERDICT: CLEAN
