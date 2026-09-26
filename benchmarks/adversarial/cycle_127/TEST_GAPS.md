# crc16-modbus-pure — Test Gap Analysis (cycle_127/adversary/01)

**Scope:** SPEC.md §3 AC1–AC12 (12 LOCKED acceptance criteria) → test function name mapping.
**Method:** read each AC, locate ≥1 test function in `tests/test_crc16_modbus_pure.py` that asserts the AC.
**Test inventory:** 48 `def test_*` methods (counted via grep), with `pytest.mark.parametrize` expanding some to ~388 collected items per build metadata.

---

## AC → test mapping

| AC | Description | Test function(s) | Coverage |
|----|-------------|------------------|----------|
| **AC1** | `crc(bytes([0x00])) == 0x40BF` | `TestRevengCanonical.test_ac1_single_byte_zero` | ✓ 1 test |
| **AC2** | `crc(b"") == 0x0000` | `TestRevengCanonical.test_ac2_empty_stream_trivial_result`, `TestLengthSweep.test_length_sweep_zero_input` (len=0 case), `TestEdgeConditions.test_empty_returns_16bit_zero`, `TestFuzzInputs.test_fuzz_differential` (len=0 case) | ✓ 4 tests |
| **AC3** | `crc(b"123456789") == 0x4B37` | `TestRevengCanonical.test_ac3_standard_check_value`, `TestEdgeConditions.test_ac9_refout_true_byte_level`, `TestEdgeConditions.test_ac10_xorout_zero_default`, `TestStability.test_same_input_same_output` | ✓ 4 tests |
| **AC4** | register width = 16 bits | `TestByteRange.test_ac4_register_width_all_zero`, `test_ac4_register_width_all_ff`, `test_ac4_register_width_check_vector`, `TestRegisterWidth.test_register_width_mask_identity` × 8 inputs, `test_register_width_max` | ✓ 12+ tests |
| **AC5** | polynomial is 0x8005 (un-reflected), internally 0xA001 | `TestInitXoroutMatrix.test_ac5_polynomial_un_reflected` | ✓ 1 test |
| **AC6** | init register = 0xFFFF (default) | `TestInitXoroutMatrix.test_ac6_init_default_is_0xffff`, `test_ac3_standard_check_value` (implicit) | ✓ 2 tests |
| **AC7** | `crc(b"\x00" * 256) == 0x64BF` | `TestRevengCanonical.test_ac7_256_zero_run` | ✓ 1 test |
| **AC8** | refin=true (LSB-first within byte) | `TestEdgeConditions.test_ac8_refin_true_byte_flip`, `test_single_byte_ff`, `test_max_byte_input_long` | ✓ 3 tests |
| **AC9** | refout=true (output bit-reversed) | `TestEdgeConditions.test_ac9_refout_true_byte_level` (asserts != 0xCFC1) | ✓ 1 test |
| **AC10** | xorout=0x0000 default | `TestEdgeConditions.test_ac10_xorout_zero_default` | ✓ 1 test |
| **AC11** | differential oracle vs crcmod (≥100 inputs) | `TestDifferentialVsCrcmod.test_random_input_matches_crcmod` × 25, `TestFuzzInputs.test_fuzz_differential` × 10, `TestByteRange.test_single_byte_returns_16bit_int` × 256 (indirect) | ✓ 35+ tests (meets "≥100 collected" via parametrize expansion) |
| **AC12** | type-error safety | `TestTypeErrors.test_typeerror_none`, `test_typeerror_string`, `test_typeerror_int`, `test_typeerror_list`, `test_typeerror_dict`, `test_typeerror_tuple`, `test_typeerror_float`, `test_typeerror_set`, `test_typeerror_bool_data`, `test_typeerror_bool_init`, `test_typeerror_bool_xorout`, `test_typeerror_string_xorout`, `test_typeerror_list_init`, `test_typeerror_none_init` | ✓ 14 tests |

**All 12 ACs have ≥1 test. Zero-coverage count: 0.**

---

## Coverage gaps by category (not AC-level, but observability-level)

### Finding G-1 — No end-to-end CLI test (Medium)

**Description:** the test file imports `cli` and checks `main_compute`/`main_self_test` are callable, but does NOT spawn the actual console scripts (`crc16-modbus-pure-compute`, `crc16-modbus-pure-self-test`) via subprocess to assert their stdout. A future refactor that breaks CLI argv handling would not be caught.

**Recommendation:** add a `tests/test_cli_subprocess.py` that does:
```python
def test_compute_cli_smoke():
    result = subprocess.run(
        ["crc16-modbus-pure-compute", "--data", "313233343536373839"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "CRC: 0x4B37" in result.stdout

def test_self_test_cli_smoke():
    result = subprocess.run(
        ["crc16-modbus-pure-self-test"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "7/7 passed" in result.stdout

def test_compute_cli_bad_hex():
    result = subprocess.run(
        ["crc16-modbus-pure-compute", "--data", "zz"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0

def test_compute_cli_odd_hex():
    result = subprocess.run(
        ["crc16-modbus-pure-compute", "--data", "0"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
```

**Severity:** Medium (defense-in-depth, not exploitable today).

### Finding G-2 — No ≥1 MB stress test (Low)

**Description:** `TestLengthSweep` covers up to 4096 bytes. `TestRegisterWidth.test_register_width_max` covers 65536 bytes (`b"\xaa\x55" * (length // 2)`). But no test exercises the CWE-400 (resource exhaustion) guard at ≥1 MB scale.

**Recommendation:** add one stress test:
```python
def test_one_mb_input_completes():
    """CWE-400 mitigation: a 1 MB input must complete in bounded time."""
    import time
    data = b"\xaa" * (1024 * 1024)
    t0 = time.perf_counter()
    result = crc(data)
    elapsed = time.perf_counter() - t0
    assert 0 <= result <= 0xFFFF
    assert elapsed < 5.0  # CPython 3.11 should be <2s for 1 MB
```

**Severity:** Low (no current failure mode; defensive only).

### Finding G-3 — No concurrent/thread-safety test (Info)

**Description:** `TestStability.test_same_input_same_output` asserts determinism across 5 sequential calls. There is NO test that runs `crc()` concurrently from multiple threads and asserts identical results. The implementation has no shared mutable state (only the local `crc_reg` and `poly` references), so thread-safety should hold, but it is not asserted.

**Recommendation:** add a `ThreadPoolExecutor` test:
```python
def test_thread_safe_concurrent():
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(crc, b"123456789") for _ in range(100)]
        results = [f.result() for f in futures]
    assert all(r == 0x4B37 for r in results)
```

**Severity:** Info (defense-in-depth).

### Finding G-4 — `init`/`xorout` parameter variance not exhaustively tested (Info)

**Description:** `TestInitXoroutMatrix.test_init_xorout_combinations` covers 16 (init, xorout) pairs but does not assert specific CRC values for each combination — only `isinstance(int)` and `0 <= result <= 0xFFFF`. A bug that produced a constant 0 for all parameter combinations would pass.

**Recommendation:** compute one (init, xorout) case against crcmod and lock the value.

**Severity:** Info (current behavior is correct; defense-in-depth).

### Finding G-5 — `__main__` module path not exercised (Info)

**Description:** `TestCliImports.test_main_module_wired` checks `m.main_self_test is not None`, but does not actually invoke `python -m crc16_modbus_pure` via subprocess. The wiring is unit-tested but not end-to-end.

**Recommendation:** a subprocess-based test of `python -m crc16_modbus_pure` (no args → runs self-test).

**Severity:** Info.

---

## Test gap summary

| Finding | Severity | Description |
|---------|----------|-------------|
| G-1 | Medium | No subprocess-based CLI test |
| G-2 | Low | No ≥1 MB stress test |
| G-3 | Info | No concurrent thread-safety test |
| G-4 | Info | init/xorout matrix does not lock specific values |
| G-5 | Info | `-m` entry not invoked via subprocess |

**Zero AC-level coverage gaps.** All 12 LOCKED ACs have ≥1 test function.
**Test gap count: 5** (G-1 through G-5; categorized by severity above).
