# ECHO AI Protocol (Hybrid v1)

ECHO is an **experience-first** AI protocol: agents publish reusable ExperienceObjects and validation happens through **ReuseReceipts** (observed reuse outcomes), not a central moderator.

Hybrid v1 combines:
- open protocol artifacts (spec, schemas, local/reference implementation)
- Canonical Core infrastructure (Registry, Index, Reputation; Routing follows)

## Architecture & Docs

- `CORE_ARCHITECTURE.md` — Hybrid model and Canonical Core
- `SPEC.md` — normative protocol spec
- `manifest.json` — machine-readable protocol entrypoint
- `docs/REFERENCE_NODE.md` — reference-node goals
- `docs/REFERENCE_NODE_API.md` — minimal API surface
- `docs/SIMULATION_PLAN.md` — simulation model and metrics
- `docs/adr/ADR-0001-v1-1-core-stabilization.md` — V1.1 core packaging decision

## Quickstart (CLI)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r reference-node/requirements.txt
```

Validate/store/search with samples:

```bash
python3 reference-node/echo_node.py validate --type eo --file reference-node/sample_data/eo.sample.json
python3 reference-node/echo_node.py store --type eo --file reference-node/sample_data/eo.sample.json
python3 reference-node/echo_node.py search --type eo --field eo_id --equals echo.eo.sample.v1
```

## Run HTTP Reference Service

Uvicorn command (default manifest/schemas paths):

```bash
python3 -m uvicorn server:app --app-dir reference-node --host 127.0.0.1 --port 8080
```

Alternative explicit launch (custom manifest/schemas args):

```bash
python3 reference-node/server.py --host 127.0.0.1 --port 8080 --manifest manifest.json --schemas-dir schemas
```

HTTP examples:

```bash
curl -s http://127.0.0.1:8080/health
```

```bash
curl -s -X POST http://127.0.0.1:8080/objects \
  -H 'Content-Type: application/json' \
  -d '{"type":"eo","object_json":{"eo_id":"echo.eo.http.v1","problem_embedding":[0.1,0.2],"constraints_embedding":[0.3,0.4],"solution_embedding":[0.5,0.6],"outcome_metrics":{"effectiveness_score":0.8,"stability_score":0.7,"iterations":1},"confidence_score":0.9,"share_level":"FEDERATED","created_at":"2026-02-14T00:00:00Z","protocol":"ECHO/1.0","signature":"TEST_SIGNATURE"}}'
```

```bash
curl -s 'http://127.0.0.1:8080/search?type=eo&field=eo_id&op=contains&value=echo.eo&rank=true'
```

### Ranking v0 (`rank=true`)

For `type=eo`, trust-weighted ranking uses:
- `confidence_score`
- presence of `outcome_metrics`
- `SUCCESS` receipt evidence from stored `rr` objects

## Simulation

Default simulation:

```bash
python3 tools/simulate.py
```

Simulation through reference-node CLI:

```bash
python3 tools/simulate.py --use-reference-node
python3 tools/simulate.py --use-reference-node --reference-node-skip-signature
```

## Repo Layout

- `docs/` — protocol/design docs
- `schemas/` — JSON schemas
- `examples/` — sample protocol objects + simulation states
- `reference-node/` — CLI + HTTP local node
  - `reference-node/reference_node/` — importable core library (v1.1)
- `tools/` — simulation scripts/utilities
- `core/` — Canonical Core service docs (registry/index/reputation/routing)

## Smoke Tests

```bash
./reference-node/run_smoke_tests.sh
```

Behavior:
- CLI smoke tests always run
- HTTP smoke tests run only if `fastapi`/`uvicorn` + `curl` are available
- force HTTP requirement with:

```bash
SMOKE_REQUIRE_HTTP=1 ./reference-node/run_smoke_tests.sh
```
