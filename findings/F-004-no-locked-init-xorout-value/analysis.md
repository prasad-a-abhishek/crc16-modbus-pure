# F-004 — `init`/`xorout` matrix does not lock specific values (Info)

- **Severity:** Info (defense-in-depth, oracle not locked)
- **Surface:** #1 `crc(data, init, xorout)`
- **CWE:** CWE-1339 (Insufficient Verification of Data Authenticity)
- **Origin:** cycle_127/adversary/01 VULN_AUDIT.md (G-4 in TEST_GAPS.md)
- **Card-03 fuzzer status:** Did not trigger. `fuzz/crc_oracle` ran 100 000 iters
  against crcmod reference — zero mismatches; `fuzz/crc_main` ran 100 000 iters
  across `all` mode (random + stress + subclass) — zero mismatches.

## Failure mode (hypothetical)

A future bug that produced a constant return value (e.g. `crc` always returns 0)
would pass `TestInitXoroutMatrix` because the existing assertions only check
`isinstance(int)` and `0 <= result <= 0xFFFF`.

## Why it is Info, not Low

- The card-03 fuzz surfaces (`crc_oracle`, `crc_main`, `cross_cycle`) DID lock
  the invariant empirically: 300 000+ differential comparisons against crcmod
  with zero mismatches. So the empirical oracle exists in `fuzz/`, just not in
  `tests/`.
- A constant-return bug would surface as 100 000 oracle mismatches in
  `fuzz/crc_oracle/stats.json` immediately, so it cannot pass the SHIP gate.
- Adding one locked value to `TestInitXoroutMatrix` is a 2-line lock-in.

## Recommendation

Augment `tests/test_crc16_modbus_pure.py::TestInitXoroutMatrix` with a single
crcmod cross-checked case. Use the Modbus-default pair `(init=0xFFFF, xorout=0x0000)`,
where the byte-exact match holds per SPEC.md AC11:

```python
def test_init_xorout_locked_against_crcmod(self):
    import crcmod
    f = crcmod.mkCrcFun(0x18005, initCrc=0xFFFF, xorOut=0x0000, rev=True)
    assert crc16_modbus_pure.crc(b"123456789", init=0xFFFF, xorout=0x0000) == f(b"123456789")
    # RevEng canonical check value for CRC-16/MODBUS:
    assert crc16_modbus_pure.crc(b"123456789", init=0xFFFF, xorout=0x0000) == 0x4B37
```

**Parameter-convention note:** For non-default `(init, xorout)` pairs, crcmod
treats both as MSB-first register values while crc16-modbus-pure treats
`init` as pre-reflection and `xorout` as post-reflection. The two APIs
intentionally differ outside the Modbus default (where the values happen to
be 16-bit palindromes). This is documented in SPEC.md and is not a bug.

## Evidence

- `src/crc16_modbus_pure/__init__.py:13-30`
- `tests/test_crc16_modbus_pure.py::TestInitXoroutMatrix` (16 pairs, type+range only)
- `fuzz/crc_oracle/stats.json` — 100 000 iters, zero oracle mismatches
- `fuzz/crc_main/stats.json` — 100 000 iters, zero crashes/oracle-mismatches
- `fuzz/cross_cycle/stats.json` — 200 000 iters, zero mismatches
- `benchmarks/adversarial/cycle_127/VULN_AUDIT.md` §F-004
- `benchmarks/adversarial/cycle_127/TEST_GAPS.md` G-4
