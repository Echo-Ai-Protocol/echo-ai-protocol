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
- `docs/FIRST_AI_TRACTION.md` — immediate adoption plan for first external agents
- `docs/ADOPTION_EXECUTION_BOARD.md` — execution board for first 3 external integrations
- `docs/adr/ADR-0001-v1-1-core-stabilization.md` — V1.1 core packaging decision
- `docs/adr/ADR-0002-v1-2-launch-api-observability.md` — V1.2 launch API decision
- `docs/adr/ADR-0003-v1-3-signature-policy-capabilities.md` — V1.3 policy hardening decision
- `docs/adr/ADR-0004-v1-4-simulator-metrics-contract.md` — V1.4 simulator metrics contract
- `docs/adr/ADR-0005-v1-5-explainable-search-and-metrics-history.md` — V1.5 explainable ranking + trend stats
- `docs/adr/ADR-0006-v1-6-bootstrap-and-metric-trends.md` — V1.6 agent bootstrap + simulator trend deltas
- `docs/adr/ADR-0007-v1-7-python-sdk-quickstart.md` — V1.7 minimal agent SDK quickstart
- `docs/adr/ADR-0008-v1-8-stabilization-and-adoption-gates.md` — V1.8 CI gates + simulator stability + reputation v1

## Quickstart (CLI)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r reference-node/requirements.txt
```

Preflight check:

```bash
make preflight
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
curl -s 'http://127.0.0.1:8080/search?type=eo&field=eo_id&op=contains&value=echo.eo&rank=true&explain=true'
```

```bash
curl -s 'http://127.0.0.1:8080/objects/eo/echo.eo.http.v1'
curl -s 'http://127.0.0.1:8080/bundles/export?type=eo'
curl -s 'http://127.0.0.1:8080/stats?history=10'
curl -s 'http://127.0.0.1:8080/registry/capabilities'
curl -s 'http://127.0.0.1:8080/registry/bootstrap'
curl -s 'http://127.0.0.1:8080/reputation/did:echo:agent.sample.2'
```

## Agent SDK Quickstart (Python)

Minimal stdlib-only SDK lives in `sdk/python/`.

Run the quickstart flow (health -> bootstrap -> store EO -> ranked search -> store RR):

```bash
python3 sdk/python/quickstart.py --base-url http://127.0.0.1:8080
```

SDK docs:

```bash
cat sdk/python/README.md
```

SDK v1.1 adds:
- retry/backoff controls in `EchoClient`
- `wait_for_health()`
- convenience helpers: `store_eo()`, `store_rr()`, `search_ranked_eo()`

### Ranking v0 (`rank=true`)

For `type=eo`, trust-weighted ranking uses:
- `confidence_score`
- presence of `outcome_metrics`
- `SUCCESS` receipt evidence from stored `rr` objects
- optional `explain=true` returns score components per result

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

Latest report:

```bash
cat tools/out/sim_report_latest.json
```

Metrics contract (`echo.sim.metrics.v1`) emitted by simulator:
- `time_to_find_ticks`
- `useful_hit_rate_top5_pct`
- `false_promotion_rate_pct`
- `missed_promotion_rate_pct`
- `spam_survival_rate_pct`

## Repo Layout

- `docs/` — protocol/design docs
- `schemas/` — JSON schemas
- `examples/` — sample protocol objects + simulation states
- `reference-node/` — CLI + HTTP local node
  - `reference-node/reference_node/` — importable core library (v1.1)
- `sdk/` — lightweight client SDKs and integration quickstarts
- `tools/` — simulation scripts/utilities
- `core/` — Canonical Core service docs (registry/index/reputation/routing)

## Smoke Tests

```bash
./reference-node/run_smoke_tests.sh
make smoke
```

Behavior:
- CLI smoke tests always run
- HTTP smoke tests run only if `fastapi`/`uvicorn` + `curl` are available
- force HTTP requirement with:

```bash
SMOKE_REQUIRE_HTTP=1 ./reference-node/run_smoke_tests.sh
```

## Operator Runbook

```bash
make preflight
make smoke
make simulate
make server
make server-strict
make test
make release-check
```
