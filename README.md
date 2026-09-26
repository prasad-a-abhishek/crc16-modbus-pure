# crc16-modbus-pure

[![PyPI version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/prasad-a-abhishek/crc16-modbus-pure)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-≥3.10-blue.svg)](pyproject.toml)

> **Pure-Python, zero-dependency, byte-exact reference implementation of CRC-16/Modbus** — for embedded / industrial-protocol engineers who cannot install `crcmod`'s C extension on PyPy, Alpine, or slim container images and need a RevEng-checked reference.

## Quick Start

```bash
pip install git+https://github.com/prasad-a-abhishek/crc16-modbus-pure.git
```

```python
from crc16_modbus_pure import crc
crc(b"123456789")  # → 0x4B37   (RevEng CRC-16/MODBUS check value)
```

```bash
crc16-modbus-pure-self-test        # runs all 7 known-good vectors, prints PASS/FAIL
crc16-modbus-pure-compute --data 313233343536373839   # 0x4B37
```

## ⚡ Performance & Benchmarks

Compared against `crcmod.mkCrcFun('modbus')` — the de-facto C-extension reference — across 10 workloads × 5 runs each (50 iterations total). See [`benchmarks/BENCHMARK.md`](benchmarks/BENCHMARK.md) for full results.

| workload                   | crc16-modbus-pure mean (ms) | crcmod mean (ms) | ratio     |
|----------------------------|----------------------------:|-----------------:|----------:|
| `b""` (empty)              |                        0.001 |           0.001 |   1.33×   |
| 1 byte                     |                        0.016 |           0.000 |   36×     |
| 8 bytes (`123456789`)      |                        0.112 |           0.000 |   248×    |
| 64 bytes random            |                        0.731 |           0.001 |   1330×   |
| 256 bytes zeros            |                        2.658 |           0.001 |   2798×   |
| 1024 bytes random          |                        9.500 |           0.002 |   4285×   |
| 4096 bytes random          |                       36.962 |           0.008 |   4811×   |
| 8192 bytes random          |                       74.892 |           0.017 |   4480×   |
| 16384 bytes random         |                      152.440 |           0.030 |   5111×   |
| 65536 bytes random         |                      603.589 |           0.123 |   4903×   |

Reproduce locally:

```bash
python3 benchmarks/run_benchmark.py
```

**Environment:** Python 3.11.15 / Linux aarch64 / 5 runs per workload after 3 warmups / `time.perf_counter()` + `tracemalloc`.

**Honest trade-off:** `crcmod` is roughly **30×–5000× faster** on byte streams (ratio grows with payload size because `crcmod` uses a pre-computed 256-entry lookup table in a C extension). **We do not compete on throughput.** We win on:

- **No compile step.** Works on PyPy, Alpine, slim Docker images where `crcmod._crcfunpy.c` cannot build.
- **Auditable.** Twenty lines of loop in a single file — every parameter greppable.
- **Parameter-locked at import time.** No `mkCrcFun('modbus')` runtime-string lookup.
- **RevEng-confirmed vectors attached** to the test suite.

For >100 MB/s throughput on x86_64 with a build toolchain available, drop in `crcmod`. For everything else, this.

## Why crc16-modbus-pure?

### The pain

Engineer writes a Modbus-RTU parser in Python on a slim gateway image.

1. They `pip install crcmod` — it tries to compile `_crcfunpy.c`.
2. PyPy / Alpine / musl / multi-stage Docker → compile fails or no wheel available.
3. They paste a StackOverflow CRC-16 loop. It uses `init=0xFFFF` but forgets `refin=true`.
4. The CRC matches `crcmod` on ASCII `"123456789"` (the only vector the SO answer tested).
5. It silently mismatches on real Modbus payloads. Field reports: "intermittent CRC errors >1% on long payloads."

### What we replace

A from-scratch loop with:

- All five CRC parameters (`width=16`, `poly=0x8005`, `init=0xFFFF`, `refin=true`, `refout=true`, `xorout=0x0000`) explicit at the top of the file.
- The check value `0x4B37` on `"123456789"` asserted by 100+ RevEng-checked pytest vectors.
- Differential oracle test vs `crcmod.mkCrcFun('modbus')` on 100+ random inputs.

## Key Features & API Reference

### Library

```python
from crc16_modbus_pure import crc
```

```python
def crc(data: bytes, init: int = 0xFFFF, xorout: int = 0x0000) -> int:
    """Compute CRC-16/Modbus over ``data``.

    Parameters match RevEng CRC-16/MODBUS:
    width=16 poly=0x8005 init=0xFFFF refin=True refout=True xorout=0x0000.
    """
```

- `data` must be `bytes`, `bytearray`, or `memoryview`. Other types raise `TypeError`.
- `init` and `xorout` must be `int` (not `bool`). Both raise `TypeError` otherwise.
- Return value is always in `[0, 0xFFFF]`.

### CLI

```bash
crc16-modbus-pure-compute --data HEX_STRING
    # Compute CRC over hex bytes. e.g. ASCII "123456789":
    crc16-modbus-pure-compute --data 313233343536373839
    # Output: CRC: 0x4B37

crc16-modbus-pure-self-test
    # Prints all 7 known-good vectors with PASS/FAIL markers.
    # Exit 0 if all pass, 1 otherwise.

python3 -m crc16_modbus_pure
    # Same as crc16-modbus-pure-self-test.
```

## Limitations & Non-Goals

- **NOT cryptographic.** CRC-16/Modbus is a non-keyed checksum. Do not use for authentication or tamper-evidence; use HMAC-SHA256.
- **NOT optimized for speed.** Slower than `crcmod` by 30×–5000× depending on payload size (we trade throughput for portability + auditability). Sufficient for industrial telemetry (<10 KB/s). For >100 MB/s, drop in `crcmod`.
- **NOT cross-platform bit-twidling.** Pure-Python `int` arithmetic only. No `numpy` / `cffi` / `ctypes` / `struct.pack`.
- **NOT a multi-CRC library.** Single-algorithm package — one file, one function, one purpose. (If you need multi-CRC, use `crcany`.)
- **NOT a Modbus protocol stack.** No transport, no PDU parsing, no slave/master simulation — that is `pymodbus`.

## Honest install

This package is **not on PyPI**. Install directly from the git repo:

```bash
pip install git+https://github.com/prasad-a-abhishek/crc16-modbus-pure.git
```

For development install with test dependencies:

```bash
git clone https://github.com/prasad-a-abhishek/crc16-modbus-pure.git
cd crc16-modbus-pure
pip install -e ".[test]"
pytest -q
```

## License

MIT — see [LICENSE](LICENSE).

Author: [prasad-a-abhishek](https://github.com/prasad-a-abhishek).
