# cycle_127 / adversary card 03 — SEED_CORPUS + FUZZ_RUN for crc16-modbus-pure

**Date:** 2026-09-26
**Branch:** `wt/cycle127-adversary-01`
**Parent card:** t_b5f16aeb (cycle_127/adversary/02 HARNESSES)
**Verdict:** **CLEAN** — 410,506 input vectors across 8 surfaces, 0 crashes, 0 hangs, 0 OOM, 0 oracle mismatches.

---

## Summary

All 8 stdlib fuzz harnesses from card 02 were executed at scale against `crc16-modbus-pure` v0.1.0 with installed dependencies (`crcmod 1.7`, console scripts `crc16-modbus-pure-compute` and `crc16-modbus-pure-self-test`). Seed corpora were materialized for every surface under `fuzz/<surface>/corpus/`. Per-harness `run.log` files capture full stdout/stderr; per-harness `stats.json` captures the canonical fields required by the card brief.

| Surface | Harness | Iters | Duration (s) | Iters/sec | Crashes | Oracle mismatches | Exit | Seed corpus |
|---|---|---|---|---|---|---|---|---|
| crc_main | harness_crc_main.py --iters 100000 --mode all --seed 42 | 100,000 | 227.83 | 438.9 | 0 | 0 | 0 | 71 |
| type_errors | harness_type_errors.py --iters 100000 --seed 42 | 100,000 | 0.137 | 732,049 | 0 | 0 | 0 | 11 |
| large_input | harness_large_input.py --iters 3 --max-mb 1 | n/a | 5.53 | n/a | 0 | 0 | 0 | 3 |
| cli_data | harness_cli_data.py --iters 10000 --seed 42 | 10,000 | 155.97 | 64.1 | 0 | 0 | 0 | 24 |
| cli_self_test | harness_cli_self_test.py --iters 500 | 500 | 7.86 | 63.6 | 0 | 0 | 0 | 5 |
| crc_oracle | harness_crc_oracle.py --iters 100000 --seed 42 | 100,000 | 23.59 | 4,239 | 0 | 0 | 0 | 28 |
| module_import | harness_module_import.py --iters 6 | 6 | 0.10 | 60.6 | 0 | 0 | 0 | 6 |
| cross_cycle | harness_cross_cycle.py --iters 100000 --det-iters 100000 --seed 42 | 200,000 (100K rand + 100K det) | 153.29 | 1,304 | 0 | 0 | 0 | 15 |
| **TOTAL** | | **410,506** | **574.30** | | **0** | **0** | **0** | **163** |

`large_input` is not a random-iteration harness — it sweeps 5 sizes × 3 patterns × 3 reps. With `--max-mb 1` the 1 MB boundary is exercised (CWE-400 surface #1); the 10 MB upper bound was previously validated in the card 02 smoke (`--max-mb 10 --iters 2`, 0 crashes, 185.4s) and re-verified here at the 1 MB bound to keep total budget under 600s.

## Methodology

1. **Seed corpora** — Python script (`/tmp/gen_corpora.py`) materialized 163 seed files across 8 surfaces with a `SEEDS.md` per surface documenting entries and runtime-RNG notes. Surface-to-seed counts: crc_main=71, type_errors=11, large_input=3, cli_data=24, cli_self_test=5, crc_oracle=28, module_import=6, cross_cycle=15.

2. **Harness execution** — Python script (`/tmp/run_all_harnesses.py`) invoked each harness sequentially with the iteration counts shown above. Per-surface 600s subprocess timeout (no hang detected). Logs to `fuzz/<surface>/logs/run.log`. Per-harness `results.json` (produced by the harness itself) read back into per-surface `stats.json` for the canonical card contract.

3. **Oracle** — `harness_crc_oracle.py` byte-exact match against `crcmod.mkCrcFun(0x18005, initCrc=0xFFFF, xorOut=0x0000, rev=True)`. 100,000 random inputs of length 1..1024, all matching crcmod byte-for-byte.

4. **Determinism** — `harness_cross_cycle.py` ran 100,000 consecutive calls of `crc(b"123456789")` — all 100,000 returned `0x4B37` (single distinct value). Plus 100,000 random inputs cross-checked against an independent bitwise reference impl transcribed from SPEC §1.

## Crashes / hangs / OOM

`crashes/`, `hangs/`, `oom/` directories exist per surface but are empty (0 bytes) for all 8 surfaces — zero failures observed. No `MemoryError`, no `subprocess.TimeoutExpired`, no non-zero exit codes.

## Findings

None — package is fuzz-clean across all 8 surfaces under the iteration budgets exercised.

## Artifacts

- `fuzz/AGGREGATE_STATS.json` — cross-surface aggregate
- `fuzz/<surface>/stats.json` — per-surface canonical stats
- `fuzz/<surface>/logs/run.log` — per-harness full stdout/stderr
- `fuzz/<surface>/corpus/` — seed files + `SEEDS.md`
- `fuzz/<surface>/crashes|hangs|oom/` — empty (no failures)
- `fuzz/logs/all_runs.log` — runner master log

## VERDICT

**CLEAN** — 410,506 input vectors across 8 surfaces in 574.3s, 0 crashes, 0 hangs, 0 OOM, 0 oracle mismatches. Package is shippable from an adversarial-fuzzing standpoint.

**VERDICT: CLEAN (cycle_127/adversary/03).**