# ADR-0005: Explainable Search + Metrics History (V1.5)

Status: Accepted  
Date: 2026-02-16

## Context

ECHO search already supports trust-weighted EO ranking (`rank=true`), but agents and
operators need to understand *why* a result was ranked high.

`/stats` also exposes only the latest simulator snapshot, which is insufficient for
trend tracking and launch decisions.

## Decision

Add:

1. `GET /search` query flag `explain=true`
- when ranking EO results, include `score_explain` with score components.

2. `GET /stats?history=N`
- include `simulator_history` with up to N recent report summaries.
- each history row contains normalized `metrics_v1` and `evaluation_v1`.

## Consequences

Positive:
- agents can debug ranking behavior deterministically
- operators can track trend regressions without external tooling
- better release confidence before enabling hosted services

Tradeoffs:
- response payloads get larger when explain/history are enabled
- historical view depends on local report retention policy
