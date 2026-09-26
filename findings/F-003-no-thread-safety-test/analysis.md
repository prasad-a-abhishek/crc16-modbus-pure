# F-003 — No concurrent thread-safety test (Info)

- **Severity:** Info (defense-in-depth, invariant unverified)
- **Surface:** #1 `crc(data, init=0xFFFF, xorout=0x0000)`
- **CWE:** CWE-1281 (Sequence of Operations — informational)
- **Origin:** cycle_127/adversary/01 VULN_AUDIT.md (G-3 in TEST_GAPS.md)
- **Card-03 fuzzer status:** Did not trigger. `fuzz/cross_cycle` ran 100 000 + 100 000 deterministic
  iterations across crc_main + crc_oracle with no observable race; both surfaces remained byte-exact.

## Failure mode (hypothetical)

A future change that introduced module-level mutable state (e.g. a memoization
cache on `(data, init, xorout)`) without a lock could produce inconsistent
results under concurrent invocations on the same input.

## Why it is Info, not Low

- The current implementation has only module-level constants `_POLY = 0xA001`
  and `__version__`. There is no shared mutable state by design.
- No security boundary is crossed; the worst case would be a wrong CRC value
  on concurrent invocation, which would surface as an oracle mismatch — and
  `fuzz/crc_oracle` ran 100 000 random single-threaded invocations with zero
  mismatches, plus the cross-cycle surface confirmed determinism across 200 000
  total iterations.
- The cross_cycle harness uses a single-process loop, not real threads, so it
  is not a substitute for `ThreadPoolExecutor`.

## Recommendation

Add to `tests/test_crc16_modbus_pure.py::TestConcurrency`:

```python
def test_thread_safe_100_concurrent(self):
    import concurrent.futures
    data = b"123456789" * 1000  # 9 KB
    expected = crc16_modbus_pure.crc(data)
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as ex:
        results = list(ex.map(lambda _: crc16_modbus_pure.crc(data), range(100)))
    assert all(r == expected for r in results)
```

## Evidence

- `src/crc16_modbus_pure/__init__.py:1-67` — no mutable module state
- `fuzz/cross_cycle/stats.json` — 200 000 iters, zero mismatches, exit 0
- `fuzz/crc_oracle/stats.json` — 100 000 iters vs crcmod, zero mismatches
- `benchmarks/adversarial/cycle_127/VULN_AUDIT.md` §F-003
- `benchmarks/adversarial/cycle_127/TEST_GAPS.md` G-3
