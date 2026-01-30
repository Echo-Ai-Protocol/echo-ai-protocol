# NAMING AND VERSIONING

ECHO uses stable identifiers and explicit versions.

## Object IDs

IDs MUST be globally unique in practice.
Recommended patterns:

- eo_id: echo.eo.<hash>
- trace_id: echo.trace.<hash>
- rq_id: echo.rq.<hash>
- rr_id: echo.rr.<hash>

Where <hash> is derived from:
- canonicalized payload (without signature)
- plus a nonce if needed

## Versioning

- Protocol version: ECHO/1.0
- Schema IDs: echo.schema.<type>.vN

Changes:
- Backward-compatible: increment minor manifest_version or schema vN
- Breaking: increment protocol_version

## Canonicalization (hint)

Before hashing or signing:
- stable key ordering
- normalized whitespace
- no transient fields (e.g., signature)
