# crc16-modbus-pure — Threat Model (cycle_127/adversary/01)

**Date:** 2026-09-26
**Scope:** realistic adversary scenarios against the CRC-16/Modbus reference package as deployed in a Modbus-RTU gateway, decoder, or test fixture.
**Method:** STRIDE-lite — for each surface, identify the most plausible adversary, attack vector, and impact.

---

## Threat Surface #1 — `crc()` public API

**Who attacks:** a malicious Modbus *master* device on the same serial bus as a gateway using this library to validate incoming frames.
**Attack vector:** sends a frame with corrupted CRC bytes — the gateway computes CRC over the payload and compares against the trailing 2-byte CRC field. An attacker who knows the algorithm but exploits a bug (wrong poly constant, wrong init, missing bit-reflection) could craft a payload that passes a buggy CRC check but is rejected by a correct Modbus slave.
**What they'd achieve:** undetected data injection into the gateway's parsed Modbus register map. For a power-grid substation gateway, this could move the apparent state of a breaker or sensor.
**Likelihood:** low — the algorithm is well-documented (RevEng catalogue, Modbus.org spec) and byte-exact against crcmod. Any plausible attack would need the gateway to be using a DIFFERENT buggy implementation, not this package.
**Mitigation:** the package is byte-exact against the canonical RevEng parameters + verified byte-for-byte against crcmod on 35+ random inputs. There is no exploitable surface in the math itself. Type errors raise `TypeError` (not `ValueError`) per AC12, preventing type-confusion crashes.

## Threat Surface #2 — Module import

**Who attacks:** a supply-chain attacker who has compromised a dependency transitively pulled in at install time (NOT this package, but e.g. a malicious `pip` mirror).
**Attack vector:** at install time, the package's `__init__.py` runs module-level code. Currently that is only docstring + constant assignments — no I/O, no env reads, no subprocess, no network. A supply-chain compromise would have to modify the source files pre-install.
**What they'd achieve:** persistent code execution in every Python process that imports the package.
**Likelihood:** very low — module-level code is minimal and auditable.
**Mitigation:** zero runtime dependencies (`dependencies = []` in pyproject.toml) eliminates the supply-chain attack surface on third-party packages. The implementation is `~120 LOC` and can be manually reviewed in <10 minutes.

## Threat Surface #3 — `python3 -m crc16-modbus-pure --self-test` entrypoint

**Who attacks:** a script kiddie running fuzz inputs at the CLI.
**Attack vector:** passing random arguments (e.g. `python3 -m crc16-modbus-pure --foo`, `--help`, `--data 0A`).
**What they'd achieve:** the argparse parser declares zero arguments; any unknown flag triggers argparse's built-in `SystemExit(2)` with a usage message to stderr. No code path executes beyond the parser. Worst case: a misleading usage error.
**Likelihood:** trivial to attempt, zero impact.
**Mitigation:** argparse is a well-tested, safe sink. The entrypoint is `main_self_test()` which only reads hard-coded test vectors.

## Threat Surface #4 — `crc16-modbus-pure-compute --data HEXSTR`

**Who attacks:** an operator piping shell data through the CLI without sanitizing.
**Attack vector:** passing malformed hex like `--data "zz"`, `--data "0"`, `--data ""`, `--data "$(rm -rf /)"` (shell-quoting bypass).
**What they'd achieve:**
- `--data "zz"` → `ValueError: invalid hex input`. Process exits non-zero. No data corruption.
- `--data "0"` → `ValueError: hex data must have even length`. Same.
- `--data ""` → `bytes.fromhex("") == b""` → `crc(b"") == 0x0000` → `CRC: 0x0000`. Prints correctly.
- `--data "$(rm -rf /)"` — shell expansion happens BEFORE argv reaches Python; the shell would try to execute `rm -rf /` (likely denied by OS). If somehow bypassed, Python receives the literal string as argv. The string would either be valid hex (unlikely for `/`) or trigger `ValueError`.
**Likelihood:** operator-error class, not adversarial.
**Mitigation:** argparse + explicit `ValueError` raises with informative messages. No shell, no `eval`, no `exec`.

## Threat Surface #5 — `crc16-modbus-pure-self-test`

**Who attacks:** nobody — this CLI runs hard-coded test vectors.
**Attack vector:** passing `--foo` → argparse rejects.
**What they'd achieve:** nothing.
**Mitigation:** N/A.

## Threat Surface #6 — `_parse_hex_data()`

**Who attacks:** a malformed-input adversary passing crafted hex strings.
**Attack vector:** passing `--data "0" * 10000` (huge odd-length input), or `--data "\x00" * 10000` (control characters that `bytes.fromhex` will reject).
**What they'd achieve:** `ValueError` on line 17 (odd length) or line 20 (non-hex). No memory blowup — `bytes.fromhex` rejects before any allocation.
**Likelihood:** low — even pathological inputs hit a `ValueError` within microseconds.
**Mitigation:** the `from e` chain on line 21 preserves traceability for operators.

## Threat Surface #7 — `_print_result()`

**Who attacks:** nobody — internal helper, never called with attacker-controlled args.
**Attack vector:** none.
**What they'd achieve:** nothing.
**Mitigation:** N/A.

---

## Cross-cutting threat: timing side-channel

**Observation:** CRC computation is data-dependent only on `len(data)`, not on individual byte values (the loop runs exactly `len(data) * 8` iterations regardless of bit patterns). Timing attacks against the algorithm are theoretically possible if the attacker can measure CRC compute time per frame, but this package is intended for *validation*, not *authentication* — the SPEC §6 explicitly states CRC-16/Modbus is NOT cryptographic and should not be used for tamper-evidence.

**Mitigation:** SPEC §6 documents this limitation in the README.

---

## Threat model summary

| Surface | Adversary | Attack | Impact | Mitigation |
|---------|-----------|--------|--------|------------|
| #1 `crc` | malicious Modbus master | craft payload exploiting bug | undetected data injection | byte-exact vs crcmod + RevEng canonicals |
| #2 module import | supply-chain attacker | modify source pre-install | persistent RCE | zero runtime deps, ~120 LOC auditable |
| #3 `-m` entry | script kiddie | unknown flags | usage error | argparse safe sink |
| #4 compute CLI | operator | malformed hex | ValueError exit | explicit validation |
| #5 self-test CLI | nobody | N/A | N/A | hard-coded vectors |
| #6 `_parse_hex_data` | malformed input | odd length / non-hex | ValueError exit | fromhex rejects |
| #7 `_print_result` | nobody | N/A | N/A | internal helper |

**No Critical or High severity threats identified.**
