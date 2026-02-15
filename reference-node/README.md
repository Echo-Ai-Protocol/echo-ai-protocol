# ECHO Reference Node (v0.9)

Reference Node now supports both:
- local CLI workflows (`validate`, `store`, `search`, `export`, `import`)
- minimal HTTP service for integration tests and infrastructure wiring

## Architecture Overview

Reference-node is a local protocol node with modular layers:
- Manifest resolver: schema selection from `manifest.json`
- Validation engine: `jsonschema.Draft202012Validator`
- Storage engine: file-based object store + `storage/index.json`
- Query engine: deterministic field search (`equals`, `contains`, `prefix`)
- Bundle engine: export/import for object portability
- HTTP adapter: FastAPI endpoints over the same library functions

The CLI and HTTP server share the same importable package logic in
`reference-node/reference_node/`.

## Package Layout

Core package:
- `reference-node/reference_node/types.py`
- `reference-node/reference_node/validate.py`
- `reference-node/reference_node/store.py`
- `reference-node/reference_node/search.py`
- `reference-node/reference_node/io_bundle.py`
- `reference-node/reference_node/index.py`

Adapters:
- `reference-node/echo_node.py` (thin CLI wrapper)
- `reference-node/server.py` (HTTP wrapper)

Public Python APIs:
- `validate_object`
- `store_object`
- `search_objects`
- `export_bundle`
- `import_bundle`

## Schema Resolution via Manifest

For each type (`eo`, `trace`, `request`, `rr`, `aao`, `referral`, `seedupdate`):
1. map type -> canonical family (`ExperienceObject`, ...)
2. read `schema_id` from `manifest.schemas[Family].schema_id`
3. resolve schema filename (`<schema_id>.json`)
4. load from `--schemas-dir` (default: `../schemas`)

Validation fails with explicit errors if schema is missing or invalid.

## Storage Model

Objects are stored under:
- `reference-node/storage/<type>/<id>.json`

ID fields:
- `eo -> eo_id`
- `trace -> trace_id`
- `request -> rq_id`
- `rr -> rr_id`
- `aao -> aao_id`
- `referral -> ref_id`
- `seedupdate -> su_id`

Index file:
- `reference-node/storage/index.json`
- tracks IDs by type, deduplicated

## Install

```bash
python3 -m pip install -r reference-node/requirements.txt
```

### Reproducible venv setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r reference-node/requirements.txt
```

### Dev/Test dependencies

```bash
pip install -r reference-node/requirements-dev.txt
```

## CLI Examples

### Validate

```bash
python3 reference-node/echo_node.py validate \
  --type eo \
  --file reference-node/sample_data/eo.sample.json
```

### Store

```bash
python3 reference-node/echo_node.py store \
  --type eo \
  --file reference-node/sample_data/eo.sample.json
```

### Search

```bash
python3 reference-node/echo_node.py search \
  --type eo \
  --field eo_id \
  --equals echo.eo.sample.v1
```

```bash
python3 reference-node/echo_node.py search \
  --type eo \
  --field eo_id \
  --contains echo.eo.sample
```

```bash
python3 reference-node/echo_node.py search \
  --type eo \
  --field eo_id \
  --prefix echo.eo
```

### Export / Import

```bash
python3 reference-node/echo_node.py export --type eo --out /tmp/echo_eo_bundle.json
python3 reference-node/echo_node.py import --file /tmp/echo_eo_bundle.json
```

## HTTP Service

Server file:
- `reference-node/server.py`

Run:

```bash
python3 -m uvicorn server:app --app-dir reference-node --host 127.0.0.1 --port 8080
```

or with explicit manifest/schemas arguments:

```bash
python3 reference-node/server.py \
  --host 127.0.0.1 \
  --port 8080 \
  --manifest manifest.json \
  --schemas-dir schemas
```

### Endpoints

- `GET /health`
- `POST /objects`
- `GET /objects/{type}/{object_id}`
- `GET /search`
- `GET /bundles/export`
- `POST /bundles/import`
- `GET /stats`
- `GET /reputation/{agent_did}`

### curl Examples

Health:

```bash
curl -s http://127.0.0.1:8080/health
```

Store object:

```bash
curl -s -X POST http://127.0.0.1:8080/objects \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "eo",
    "object_json": {
      "eo_id": "echo.eo.http.v1",
      "problem_embedding": [0.1, 0.2],
      "constraints_embedding": [0.3, 0.4],
      "solution_embedding": [0.5, 0.6],
      "outcome_metrics": {"effectiveness_score": 0.8, "stability_score": 0.7, "iterations": 1},
      "confidence_score": 0.9,
      "share_level": "FEDERATED",
      "created_at": "2026-02-14T00:00:00Z",
      "protocol": "ECHO/1.0",
      "signature": "TEST_SIGNATURE"
    }
  }'
```

Search with ranking:

```bash
curl -s 'http://127.0.0.1:8080/search?type=eo&field=eo_id&op=contains&value=echo.eo&rank=true'
```

Get object by ID:

```bash
curl -s 'http://127.0.0.1:8080/objects/eo/echo.eo.http.v1'
```

Bundle export/import:

```bash
curl -s 'http://127.0.0.1:8080/bundles/export?type=eo'
curl -s -X POST http://127.0.0.1:8080/bundles/import \
  -H 'Content-Type: application/json' \
  -d '{"bundle":{"manifest_version":"echo.manifest.v1","protocol_version":"ECHO/1.0","objects":[]},"skip_signature":true}'
```

Node stats:

```bash
curl -s 'http://127.0.0.1:8080/stats'
```

Reputation stub:

```bash
curl -s http://127.0.0.1:8080/reputation/did:echo:agent.sample.2
```

## Trust-weighted Ranking v0

`GET /search?...&rank=true` enables deterministic ranking for `type=eo`:
- higher `confidence_score` ranks higher
- EO with `outcome_metrics` gets a bonus
- `SUCCESS` receipts from stored `rr` objects increase rank

This is a v0 stub to prepare for semantic ranking and reputation integration.

## Smoke Tests

```bash
./reference-node/run_smoke_tests.sh
```

Script checks:
- CLI validate/store/search/index/export/import
- HTTP startup + `/health`
- HTTP `POST /objects`, `GET /objects/{type}/{id}`, `GET /search?rank=true`
- HTTP `GET /bundles/export`, `POST /bundles/import`, `GET /stats`

If HTTP deps are not installed, HTTP section is skipped by default.
To require HTTP section and fail when unavailable:

```bash
SMOKE_REQUIRE_HTTP=1 ./reference-node/run_smoke_tests.sh
```

## Unit Tests

```bash
pytest reference-node/tests
```

## Simulation Through Reference Node

```bash
python3 tools/simulate.py --use-reference-node --reference-node-skip-signature
```

## Future Roadmap

- semantic embedding search backend
- cryptographic signature verification
- TTL garbage collection for ephemeral objects
- P2P routing and peer delegation
