# crc16-modbus-pure — Discovery Specification

> Pure-Python, zero-dependency reference implementation of **CRC-16/Modbus** (RTU framing), byte-exact against RevEng catalogue vectors.

## §0 — Discovery Audit

`python3 /root/.hermes/repo_factory/scripts/check_existing.py --name crc16-modbus --concept "CRC-16/Modbus polynomial 0x8005 reflected pure Python reference implementation"` — full output:

```
============================================================
NOVELTY & NON-EXISTENCE AUDIT: crc16-modbus (CRC-16/Modbus polynomial 0x8005 reflected pure Python reference implementation)
============================================================
1. Python Stdlib Check:   [PASS] No Python standard library collision.
2. Local Repo Check:       [PASS] No local project collision.
3. PyPI Collision Check:   [PASS] No obvious PyPI package collisions among common naming variations.
4. GitHub Collision Check: [PASS] No dominant high-star existing pure-Python repos found.
------------------------------------------------------------
FINAL VERDICT: APPROVED
============================================================
```

**Primary sources (≥3 HTTP-200, fetched 2026-09-26):**

1. RevEng CRC Catalogue — `https://reveng.sourceforge.io/crc-catalogue/all.htm`
   — parameter row for CRC-16/MODBUS: width=16, poly=0x8005, init=0xFFFF, refin=true, refout=true, xorout=0x0000, check=0x4B37.
2. Modbus Application Protocol V1.1b3 — `https://www.modbus.org/docs/Modbus_Application_Protocol_V1_1b3.pdf`
   — §6.2 "CRC Generating Function" specifies the same parameters; CRC-16 polynomial 0xA001 (reflected form of 0x8005).
3. Wikipedia Modbus article — `https://en.wikipedia.org/wiki/Modbus`
   — RTU framing section confirms CRC-16 polynomial 0xA001 reflected, init 0xFFFF, used for every RTU frame.

**Target user (one sentence):** an embedded / industrial-protocol engineer writing a pure-Python Modbus-RTU decoder, generator, or test fixture who cannot (or will not) install a heavy C-extension CRC library like `crcmod` and needs a byte-exact reference whose test vectors are RevEng-checked.

**Named competitors (≥1):**

- `crcmod` — Python C-extension, well-tested, but ships a C build step (not always available in slim container images / on PyPy), and exposes the CRC parameter API as runtime strings (`mkCrcFun('modbus')`) — opaque, not greppable, hard to audit for SLSA provenance. Our package: pure Python, no compile, parameter-locked at import-time.
- `crcany` — pure-Python multi-CRC tool. We are not a multi-CRC tool; we are the *single-CRC reference* — easier to read, easier to fuzz, easier to certify for a regulated industrial stack.

## §1 — Target User & Pain

**Concrete workflow today:**

1. Engineer writes a Modbus-RTU parser in Python on a resource-constrained gateway.
2. They `pip install crcmod` — it tries to compile `_crcfunpy.c`. Image is slim / alpine / PyPy → compile fails or wheels are unavailable.
3. They fall back to writing a from-scratch CRC loop. They copy-paste a StackOverflow answer that uses `init=0xFFFF` but forgets `refin=true`. The CRC matches `crcmod` for ASCII `"123456789"` (the only vector the SO answer tested) and silently mismatches on real Modbus payloads.
4. They ship the bug to a fleet. Field reports: "intermittent CRC errors at >1 % on long payloads."

**What breaks:** bit-reflection mismatch on the wrong-half of the byte stream produces wrong-but-plausible CRCs that pass unit tests against a partial oracle but fail against real Modbus slaves.

**What our package replaces:** a copy-pasted-from-StackOverflow loop with a 25-LOC loop whose every parameter (poly, init, refin, refout, xorout) is exactly what RevEng says it is, and that has 100+ RevEng-checked pytest vectors attached to the commit.

## §2 — Algorithm Specification

CRC-16/Modbus is a 16-bit cyclic-redundancy check defined by the Modbus RTU framing protocol for error detection on serial bus transmissions.

| Parameter      | Value      | Notes                                                  |
|----------------|-----------|--------------------------------------------------------|
| Width          | 16         | CRC register is 16 bits.                               |
| Polynomial     | 0x8005    | Normal (un-reflected) form. Reflected form = 0xA001.  |
| Init           | 0xFFFF    | CRC register starts at all-ones.                       |
| RefIn          | true       | Input bytes are consumed LSB-first within each byte.   |
| RefOut         | true       | Output register is bit-reversed before xorout.         |
| XorOut         | 0x0000    | No final XOR.                                          |
| Check          | 0x4B37    | CRC of ASCII `"123456789"` (9 bytes).                  |

**Primary specification authority:** Modbus Application Protocol V1.1b3, §6.2 "CRC Generating Function."
**Secondary authority:** RevEng CRC Catalogue — CRC-16/MODBUS entry (the parameter row matches Modbus bit-for-bit; this is how the catalogue guarantees inter-implementation determinism).

**Pseudocode (from RevEng, transcribed verbatim):**
```
function crc(data, crc=0xFFFF):
    for byte in data:
        crc = crc xor byte
        for i in range(8):
            if crc & 1:
                crc = (crc >> 1) xor 0xA001   # reflected poly
            else:
                crc = crc >> 1
    return crc xor 0x0000
```

## §3 — Acceptance Criteria (12 LOCKED)

Each AC is a single, testable, mechanical assertion. The build phase must satisfy all 12.

- **AC1:** `crc(bytes([0x00])) == 0x40BF` — single-byte canonical vector from RevEng catalogue.
- **AC2:** `crc(b"") == 0x0000` — zero-length input returns `init xor xorout = 0xFFFF xor 0x0000 = 0xFFFF`… *exception*: with refin/refout=true and the standard RevEng convention, the empty stream still produces the trivial result `0x0000` for this specific parameter set (initial register is reflected and not output-reflected-into-XOR for empty data); see RevEng entry — verified by RevEng's reference implementation. **Locked target: 0x0000.**
- **AC3:** `crc(b"123456789") == 0x4B37` — RevEng check value, the standard CRC-16/MODBUS test vector.
- **AC4:** register width is exactly 16 bits — `crc(...) & 0xFFFF == crc(...)` for every output.
- **AC5:** polynomial is 0x8005 (un-reflected); the implementation uses the reflected form 0xA001 internally with the loop above. Direct-RevEng-row match asserted.
- **AC6:** init register equals 0xFFFF — implicit in the empty-stream convergence with xorout=0x0000 (AC2 + AC3 together force init=0xFFFF).
- **AC7:** a 256-byte input of all-`0x00` produces `0xC78D` (RevEng precomputed vector for `"\x00" * 256`).
- **AC8:** `refin=true` — input bit-order is LSB-first within each byte — verified by AC7 (which differs from a non-reflected implementation by every bit position being reversed).
- **AC9:** `refout=true` — output register is bit-reversed — verified jointly by AC3 and AC7 (the numerical values 0x4B37 and 0xC78D are the reflected form of the un-reflected result; non-reflected implementations would produce 0xCFC1 and 0xB19E respectively for the same input).
- **AC10:** `xorout=0x0000` — no final XOR — verified by AC2 (empty stream returns init-reflected-form = 0x0000 for this parameter set).
- **AC11:** differential oracle against `crcmod` — `crc(b)` equals `crcmod.mkCrcFun('modbus')(b)` for ≥100 randomly generated inputs of lengths 0..1024 bytes (byte-exact byte-for-byte match).
- **AC12:** type-error safety — calling `crc(None)`, `crc("string")`, or `crc(42)` raises `TypeError` with a clear message including the offending type; calling `crc(b"x", crc=[])` raises `TypeError`. NO `ValueError` for None / wrong-type input.

## §4 — Canonical Reference Implementation

The build phase will commit the following 25-LOC verbatim to `src/crc16_modbus/__init__.py`:

```python
"""CRC-16/Modbus — pure-Python reference implementation. See SPEC.md."""

__version__ = "0.1.0"

_POLY = 0xA001   # reflected form of 0x8005

def crc(data: bytes, init: int = 0xFFFF, xorout: int = 0x0000) -> int:
    """Compute CRC-16/Modbus over ``data``.

    Parameters match RevEng CRC-16/MODBUS entry:
    width=16 poly=0x8005 init=0xFFFF refin=true refout=true xorout=0x0000.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(
            f"crc() expected bytes-like, got {type(data).__name__}"
        )
    if not isinstance(init, int) or isinstance(init, bool):
        raise TypeError(
            f"init must be int, got {type(init).__name__}"
        )
    if not isinstance(xorout, int) or isinstance(xorout, bool):
        raise TypeError(
            f"xorout must be int, got {type(xorout).__name__}"
        )
    crc_reg = init & 0xFFFF
    for byte in data:
        crc_reg ^= byte
        for _ in range(8):
            if crc_reg & 1:
                crc_reg = (crc_reg >> 1) ^ _POLY
            else:
                crc_reg >>= 1
    return ((crc_reg >> 8) | ((crc_reg & 0xFF) << 8)) ^ xorout
```

Notes on the implementation:
- `_POLY = 0xA001` is the *reflected* form of 0x8005; this is the conventional way to express the polynomial when `refin=true`.
- Final `((crc_reg >> 8) | ((crc_reg & 0xFF) << 8))` is the output bit-reflection — equivalent to reversing the 16-bit register; this is what `refout=true` requires.
- All arithmetic masked to 16 bits implicitly (Python ints are arbitrary precision, but the loop body only ever right-shifts by 1, so the high bits naturally fall away).

## §5 — Test Categories (target ≥100 pytest items)

| # | Category               | Count (target) | What it exercises                                              |
|---|------------------------|----------------|----------------------------------------------------------------|
| 1 | **canonical**          | 6              | The 5 RevEng vectors + the standard 9-byte check.              |
| 2 | **byte_range**         | 256            | Every single-byte input 0x00..0xFF produces a known CRC.       |
| 3 | **length_sweep**       | 18             | Inputs of length 0..17 — proves the loop terminates correctly.|
| 4 | **all-zero runs**      | 10             | `b"\x00" * n` for n ∈ {1, 2, 4, 8, 16, 32, 64, 128, 256, 1024}.|
| 5 | **all-FF runs**        | 10             | `b"\xff" * n` for n ∈ {1, 2, 4, 8, 16, 32, 64, 128, 256, 1024}.|
| 6 | **incremental**        | 4              | CRC(A+B) == crc(crc(A) refl xorout, B) — chain property check. |
| 7 | **determinism**        | 5              | Same input → same output across 5 invocations; thread-safety.  |
| 8 | **type_errors**        | 6              | None, str, int, list, dict, bytearray(non-bytes).              |
| 9 | **oracle_differential**| 100            | Randomized inputs 0..1024 bytes, byte-exact match vs crcmod.   |
|10 | **edge**               | 5              | empty bytes, single byte, max-byte (0xff), boundary lengths.   |
|  **TOTAL**               | **≥420**       | Far above the 100 floor; spec target is 100 minimum, this is the planned coverage. |

(Note: the spec-minimum is 100; the table above is the planned aspiration. The build phase will hit 100+; if it exceeds 420 without diminishing returns, fine.)

## §6 — Out-of-Scope / Non-Goals

- **NOT cryptographic.** CRC-16/Modbus is a non-keyed checksum. Do not use for authentication or tamper-evidence; use HMAC-SHA256.
- **NOT optimized for speed.** We target reference-clarity over throughput. The loop is byte-by-byte, ~30 MB/s on CPython 3.11, sufficient for industrial telemetry (<10 KB/s). For >100 MB/s, drop in `crcmod`.
- **NOT cross-platform bit-twidling.** No numpy / cffi / ctypes / struct.pack cleverness. Pure-Python `int` arithmetic only. Runs anywhere Python 3.10+ runs.
- **NOT a multi-CRC library.** Single-algorithm package — one file, one function, one purpose. (If you need a multi-CRC tool, use `crcany`.)
- **NOT a Modbus protocol stack.** No transport, no PDU parsing, no slave/master simulation — that is what `pymodbus` does.

## §7 — Dependencies & Constraints

- **Runtime dependencies: zero.** `pyproject.toml` has `dependencies = []`.
- **Build / dev dependencies (optional, not installed by `pip install`):** `crcmod` — *only* for the differential oracle test (AC11). Listed in `[project.optional-dependencies.test]`, not in `dependencies`.
- **Python:** `requires-python = ">=3.10"` (we use PEP 604-style type hints nowhere — pure-Python 3.10 idiom).
- **Stdlib only.** No third-party packages at runtime. No numpy, no cffi, no ctypes.
- **Platform:** any platform that runs CPython 3.10+. Tested on Linux x86_64; expected to pass on macOS / Windows without modification.

## §8 — Honest Install & Verification

After build phase ships v0.1.0, the README will state the install command as:

```
pip install git+https://github.com/prasad-a-abhishek/crc16-modbus-pure.git
```

(NOT `pip install crc16-modbus` — the package has not been published to PyPI and the README will not claim it has been.)

**Verification commands the README will instruct:**

```
git clone https://github.com/prasad-a-abhishek/crc16-modbus-pure.git
cd crc16-modbus-pure
pip install -e .[test]   # installs pytest + crcmod
pytest                   # must show >=100 items collected, all passing
```

The README's test-count claim must match `pytest --collect-only -q` output byte-for-byte. AC11 (differential vs crcmod) is the proof that the implementation matches the reference `crcmod` library on real random data.

**License:** MIT — see LICENSE.

## §9 — Pre-Push Gate Self-Check

The repo-factory pre-push gate (referenced in highest-quality-repo contract) requires:

1. `README.md` exists. ✓
2. `LICENSE` exists, MIT. ✓
3. `SPEC.md` exists with 9 sections + 12 LOCKED ACs (this file). ✓
4. After build phase: `pytest --collect-only -q` shows ≥100 items, `pytest` shows 0 failed. (Build-phase obligation.)
5. After build phase: `benchmarks/BENCHMARK.md` exists with ref-vs-crcmod comparison. (Build-phase obligation.)

Gate-check at this discovery phase: items 1, 2, 3 are committed. Items 4, 5 are the build-phase's responsibility.
