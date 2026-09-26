# Seed corpus — fuzz/large_input

Surface: `large_input`
Seed count: 3

## Entries

- `b'shape-1byte-ff.b'`
- `b'shape-1byte-00.b'`
- `b'shape-2byte-aa55.b'`

## Notes

Sizes [1, 1000, 100_000, 1_000_000, 10_000_000] are generated at runtime by the harness. The shape files here are pointers to the patterns used (all-0x00, all-0xFF, alternating 0xAA55).
