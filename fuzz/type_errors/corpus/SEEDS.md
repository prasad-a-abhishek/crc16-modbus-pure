# Seed corpus — fuzz/type_errors

Surface: `type_errors`
Seed count: 11

## Entries

- `b'accept-bytes-canon.b'`
- `b'accept-bytearray-canon.b'`
- `b'accept-memview-canon.b'`
- `b'accept-empty-bytes.b'`
- `b'accept-empty-bytearray.b'`
- `b'accept-empty-memview.b'`
- `bytelen-1.b`
- `bytelen-9.b`
- `bytelen-16.b`
- `bytelen-256.b`
- `bytelen-1024.b`

## Notes

The byte files in this corpus are accepted bytes-like inputs. The harness also generates non-bytes-like inputs (None, str, int, list, dict, bool, object()) at runtime via its seeded RNG (`random.Random(42)`) — see harness_type_errors.py::BAD_DATA, BAD_INIT, BAD_XOROUT lists for the full hand-curated set.
