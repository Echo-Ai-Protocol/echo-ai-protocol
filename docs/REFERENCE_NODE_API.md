# Reference Node API (Hybrid v1)

This is the concrete HTTP surface implemented by `reference-node/server.py`.

## Implemented endpoints

### GET /health
Returns node status and active config flags.

### POST /objects
Body:
- `type`: object type (`eo|trace|request|rr|aao|referral|seedupdate`)
- `object_json`: object payload
- `skip_signature` (optional bool)

Behavior:
- validates against manifest-routed schema
- stores to local object store

### GET /objects/{type}/{object_id}
Fetches one stored object by typed ID.

### GET /search
Query params:
- `type`
- `field`
- `op=equals|contains|prefix`
- `value`
- `rank=true|false` (EO ranking v0)
- `explain=true|false` (attach score components)
- `limit` (0..1000)

### GET /bundles/export?type=...
Exports stored objects for one type as JSON bundle.

### POST /bundles/import
Body:
- `bundle` (JSON object)
- `skip_signature` (optional bool)

Behavior:
- validates all objects first
- stores only if bundle fully valid

### GET /stats?history=N
Returns:
- object counts and index health
- latest simulator report parse
- normalized metrics contract (`metrics_v1`)
- optional `simulator_history` for recent reports

### GET /registry/capabilities
Returns local node capabilities descriptor.

### GET /reputation/{agent_did}
Current stub: receipt-based score if receipts exist, otherwise `0`.

## Security notes

- validation failures return explicit details
- signature bypass is intended for dev flows
- strict signature mode can be enabled on server start
