# ADR-0008: V1.8 Stabilization + Adoption Gates

Status: Accepted  
Date: 2026-02-17

## Context

After V1.7, ECHO has a working local node and SDK quickstart, but still needs:
- stronger release gates (HTTP + pytest in CI)
- reduced simulator flakiness (`search_probe_found`)
- richer reputation signal than a stub
- concrete execution board for first 3 external integrations

## Decision

1. Stabilize simulator reference-node probe
- retry across multiple candidate EO ids (latest/middle/oldest)
- include probe attempt metadata in report
- fail release-check when probe fails in reference-node mode

2. Add mandatory CI release-check
- GitHub Actions workflow runs `tools/release_check.sh`
- `SMOKE_REQUIRE_HTTP=1`
- `RELEASE_REQUIRE_PYTEST=1`

3. Upgrade SDK to v1.1 ergonomics
- retry/backoff support in `EchoClient`
- `wait_for_health()`
- convenience methods: `store_eo`, `store_rr`, `search_ranked_eo`

4. Introduce `echo.reputation.v1`
- bounded score with evidence factor
- success/contradiction ratios
- average effectiveness score
- top target EO breakdown for issued receipts

5. Formalize adoption execution board
- explicit lanes for first 3 integrations
- weekly KPI-based operating cadence

## Consequences

Positive:
- fewer flaky simulator outcomes
- stronger PR quality gates
- better first-agent integration reliability
- measurable adoption execution loop

Tradeoffs:
- CI is stricter and may fail more often initially
- reputation model is still heuristic and expected to evolve
