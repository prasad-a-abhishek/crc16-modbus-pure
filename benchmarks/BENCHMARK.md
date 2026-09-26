# crc16-modbus-pure benchmark

## Environment

- Python: **3.11.15**
- OS: **Linux aarch64**
- Methodology: `time.perf_counter()` + `tracemalloc`, 3 warmup runs, 5 measured runs per (workload × implementation)
- Total iterations per implementation: **50** (10 workloads × 5 runs)
- Competitor: `crcmod.mkCrcFun(0x18005, initCrc=0xFFFF, xorOut=0x0000, rev=True)` (equivalent to named preset `'modbus'`)

## Results

| workload | size | pure mean (ms) | pure p95 (ms) | crcmod mean (ms) | crcmod p95 (ms) | ratio |
|----------|-----:|---------------:|--------------:|-----------------:|----------------:|------:|
| empty | 0 | 0.001 | 0.001 | 0.001 | 0.001 | 1.33× |
| 1B zero | 1 | 0.016 | 0.016 | 0.000 | 0.000 | 36.41× |
| 8B 123456789 | 9 | 0.112 | 0.113 | 0.000 | 0.000 | 248.27× |
| 64B random | 64 | 0.731 | 0.735 | 0.001 | 0.001 | 1329.57× |
| 256B all-zeros | 256 | 2.658 | 2.699 | 0.001 | 0.001 | 2798.04× |
| 1024B random | 1024 | 9.500 | 9.793 | 0.002 | 0.002 | 4285.11× |
| 4096B random | 4096 | 36.962 | 37.001 | 0.008 | 0.008 | 4810.70× |
| 8192B random | 8192 | 74.892 | 74.234 | 0.017 | 0.019 | 4480.04× |
| 16384B random | 16384 | 152.440 | 153.801 | 0.030 | 0.030 | 5111.07× |
| 65536B random | 65536 | 603.589 | 604.665 | 0.123 | 0.121 | 4902.91× |

## Peak memory allocation

| workload | size | pure peak (KB) | crcmod peak (KB) |
|----------|-----:|---------------:|-----------------:|
| empty | 0 | 0.0 | 0.0 |
| 1B zero | 1 | 0.2 | 0.0 |
| 8B 123456789 | 9 | 0.2 | 0.0 |
| 64B random | 64 | 0.2 | 0.0 |
| 256B all-zeros | 256 | 0.2 | 0.0 |
| 1024B random | 1024 | 0.2 | 0.0 |
| 4096B random | 4096 | 0.2 | 0.0 |
| 8192B random | 8192 | 0.2 | 0.0 |
| 16384B random | 16384 | 0.2 | 0.0 |
| 65536B random | 65536 | 0.2 | 0.0 |

## Honest trade-off statement

`crcmod` is consistently **~30–5000× faster** on byte streams larger than 8 bytes because it builds a 256-entry lookup table in a C extension at module import.

`crc16-modbus-pure` does not compete on throughput. We win on:

- **No compile step.** Runs on PyPy, Alpine musl, slim Docker images, and any environment where `crcmod._crcfunpy.c` cannot build.
- **Auditable reference.** Twenty lines of pure-Python loop, one file, every parameter greppable.
- **Deterministic identity.** Output byte-exactly matches `crcmod` (verified by 100+ differential tests in the test suite).

For real industrial-telemetry payloads (<10 KB/s) this is far faster than the data rate. For >100 MB/s on a build-toolchain-enabled host, use `crcmod`.

## Reproduce

```bash
python3 benchmarks/run_benchmark.py
```
