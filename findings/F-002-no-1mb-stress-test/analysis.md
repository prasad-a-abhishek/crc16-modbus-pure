# F-002 — No ≥1 MB stress test (Info)

- **Severity:** Info (defense-in-depth, empirical bound missing)
- **Surface:** #1 `crc(data, init=0xFFFF, xorout=0x0000)`
- **CWE:** CWE-400 (Uncontrolled Resource Consumption)
- **Origin:** cycle_127/adversary/01 VULN_AUDIT.md (G-2 in TEST_GAPS.md)
- **Card-03 fuzzer status:** Did not trigger. `fuzz/large_input` exercised sizes [1, 1K, 100K, 1M] × 3 reps — zero OOM, zero hangs, exit 0 in 5.527s.

## Failure mode (hypothetical)

A future regression that accidentally introduced a quadratic-time inner loop
(e.g. inner `for byte in data: for bit in range(8):` instead of a single
`if crc & 0x0001:` shift) would not be caught by the current suite, because
the longest input currently tested is 65 536 bytes
(`TestRegisterWidth.test_register_width_max`).

## Why it is Info, not Low

- The card-03 `large_input` harness empirically confirmed bounded `O(n)` at 1 MB
  on CPython 3.11 in 5.527s for 12 invocations (1B / 1KB / 100KB / 1MB × 3 reps).
  This is the exact gap F-002 identified — and the fuzzer closed it as evidence,
  even though no automated test asserts it yet.
- No correctness bug exists; the algorithm is byte-exact against crcmod on
  100 000 random inputs of size 0..1024 bytes (`fuzz/crc_oracle`).
- Adding `test_one_mb_input_completes` is a one-line lock-in of an empirically
  observed bound.

## Recommendation

Add to `tests/test_crc16_modbus_pure.py::TestStress`:

```python
def test_one_mb_input_completes(self):
    data = bytes(range(256)) * 4096  # 1 MB
    t0 = time.perf_counter()
    result = crc16_modbus_pure.crc(data)
    elapsed = time.perf_counter() - t0
    assert 0 <= result <= 0xFFFF
    assert elapsed < 5.0  # CPython 3.11 baseline
```

## Evidence

- `src/crc16_modbus_pure/__init__.py:13-30`
- `tests/test_crc16_modbus_pure.py::TestRegisterWidth.test_register_width_max` (65 536 B ceiling)
- `fuzz/large_input/stats.json` — 12 iters at sizes [1, 1000, 100000, 1000000], 0 OOM, 5.527s
- `benchmarks/adversarial/cycle_127/VULN_AUDIT.md` §F-002
- `benchmarks/adversarial/cycle_127/TEST_GAPS.md` G-2
