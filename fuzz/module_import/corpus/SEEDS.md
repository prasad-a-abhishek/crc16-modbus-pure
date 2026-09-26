# Seed corpus — fuzz/module_import

Surface: `module_import`
Seed count: 6

## Entries

- `hashseed-0.txt`
- `hashseed-1.txt`
- `hashseed-42.txt`
- `hashseed-1337.txt`
- `hashseed-9999.txt`
- `hashseed-2147483647.txt`

## Notes

No real input — the harness spawns fresh subprocesses under different PYTHONHASHSEED values [0, 1, 42, 1337, 9999, 2**31-1]. The seed files document which PYTHONHASHSEED values are probed.
