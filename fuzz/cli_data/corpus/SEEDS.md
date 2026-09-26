# Seed corpus — fuzz/cli_data

Surface: `cli_data`
Seed count: 24

## Entries

- `b'hex-3132...89.txt'`
- `b'hex-00.txt'`
- `b'hex-empty.txt'`
- `b'hex-ws-spaced.txt'`
- `b'hex-ws-leading.txt'`
- `b'hex-ws-trailing.txt'`
- `b'hex-ws-newline-trailing.txt'`
- `b'hex-ws-newline-embedded.txt'`
- `b'hex-lower-abcdefab.txt'`
- `hex-len-0002.txt`
- `hex-len-0004.txt`
- `hex-len-0008.txt`
- `hex-len-0016.txt`
- `hex-len-0032.txt`
- `hex-len-0064.txt`
- `hex-len-0128.txt`
- `hex-len-0256.txt`
- `hex-len-0512.txt`
- `hex-len-1024.txt`
- `b'hex-neg-odd.txt'`
- `b'hex-neg-zz.txt'`
- `b'hex-neg-0x41.txt'`
- `b'hex-neg-12g.txt'`
- `b'hex-neg-f.txt'`

## Notes

Hex strings (even-length) the CLI accepts. The harness also generates random even-length hex strings at runtime via its seeded RNG.
