# F-005 — `python -m crc16_modbus_pure` not exercised end-to-end (Info)

- **Severity:** Info (defense-in-depth, end-to-end gap)
- **Surface:** #3 `python -m crc16_modbus_pure`
- **CWE:** CWE-1284 (Improper Validation of Specified Quantity in Input — defensive)
- **Origin:** cycle_127/adversary/01 VULN_AUDIT.md (G-5 in TEST_GAPS.md)
- **Card-03 fuzzer status:** Did not trigger. `fuzz/module_import` ran 6 fresh
  subprocess imports under 6 PYTHONHASHSEED values — all exit 0, no crash/hang.
  `fuzz/cli_self_test` ran 500 invocations of the self-test CLI — all exit 0.

## Failure mode (hypothetical)

- A future change to `__main__.py` (e.g. accidental `from cli import main_compute`
without binding the correct entry, or removing the final `7/7 passed` summary
line) would not be caught by the current suite because
`TestCliImports.test_main_module_wired` only imports the module and verifies
`main_self_test` is bound — it does not invoke `python -m` end-to-end.

## Why it is Info, not Low

- `fuzz/module_import` (6 fresh subprocess imports) and `fuzz/cli_self_test`
  (500 invocations) DID close the end-to-end gap empirically. A regression
  that broke `python -m` would manifest as a nonzero exit_code in those stats.
- No security boundary is crossed — the `-m` entry simply dispatches to
  `cli.main_self_test` which is independently tested.
- Adding a single subprocess-based assertion is a 5-line lock-in.

## Recommendation

Add to `tests/test_crc16_modbus_pure.py::TestCliImports`:

```python
def test_python_m_invocation(self):
    import subprocess, sys
    r = subprocess.run([sys.executable, "-m", "crc16_modbus_pure"],
                       capture_output=True, text=True, timeout=10)
    assert r.returncode == 0
    assert "passed" in r.stdout  # self-test summary line "X/Y passed"
```

## Evidence

- `src/crc16_modbus_pure/__main__.py:1-8`
- `src/crc16_modbus_pure/cli.py:51-71` (main_self_test)
- `tests/test_crc16_modbus_pure.py::TestCliImports.test_main_module_wired`
- `fuzz/module_import/stats.json` — 6 iters, exit 0
- `fuzz/cli_self_test/stats.json` — 500 iters, exit 0
- `benchmarks/adversarial/cycle_127/VULN_AUDIT.md` §F-005
- `benchmarks/adversarial/cycle_127/TEST_GAPS.md` G-5
