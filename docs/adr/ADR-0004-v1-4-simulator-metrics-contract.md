# ADR-0004: Simulator Metrics Contract (V1.4)

Status: Accepted  
Date: 2026-02-16

## Context

Hybrid v1 already includes local simulation and `/stats` on the reference-node.
But simulation metrics historically used internal labels (`D1`, `T1`, `A1`), which
are hard to consume by services and CI checks.

We need a stable contract so agents, dashboards, and release checks can parse
quality signals deterministically.

## Decision

Introduce contract version `echo.sim.metrics.v1` with canonical keys:

- `time_to_find_ticks`
- `useful_hit_rate_top5_pct`
- `false_promotion_rate_pct`
- `missed_promotion_rate_pct`
- `spam_survival_rate_pct`

Implementation details:
- `tools/simulate.py` writes canonical metrics and keeps legacy keys for compatibility.
- Simulator additionally writes `tools/out/sim_report_latest.json`.
- `reference_node.stats.compute_stats()` exposes:
  - `simulator.contract_version`
  - `simulator.metrics_v1`
  - `simulator.evaluation_v1` (advisory pass/fail against baseline targets)

## Consequences

Positive:
- single parsing surface for CI and API consumers
- backward-compatible with old reports
- easier future migration to hosted Index/Reputation services

Tradeoffs:
- temporary duplication of canonical + legacy keys in reports
- evaluation thresholds are advisory, not a hard release gate

## Follow-up

- v1.5: expose metrics trend endpoint in Canonical Core Index service
- v1.6: connect `evaluation_v1` with optional policy gates in hosted environment
