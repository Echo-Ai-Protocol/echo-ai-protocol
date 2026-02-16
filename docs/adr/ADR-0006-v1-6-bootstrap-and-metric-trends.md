# ADR-0006: Agent Bootstrap Endpoint + Simulator Trend View (V1.6)

Status: Accepted  
Date: 2026-02-16

## Context

We need to improve first-agent onboarding and operational iteration speed.

Current state had:
- static capabilities descriptor
- latest simulator metrics snapshot

Gaps:
- no explicit machine-readable onboarding map for agent clients
- no built-in trend signal for metric direction between runs

## Decision

1. Add `GET /registry/bootstrap`
- returns endpoint map, supported object types, search ops, ranking flags, and quickstart examples.
- intended for automated agent onboarding.

2. Extend `/stats`
- add `simulator_trend` based on latest-vs-previous normalized metrics:
  - `delta` values
  - `direction` (`improved|regressed|same`) with metric-aware goals.

## Consequences

Positive:
- agents can self-discover integration flow with less human setup
- operators can detect regressions faster without external dashboards

Tradeoffs:
- larger `/stats` payload
- trend quality depends on local report retention and ordering
