# ADR-0003: V1.3 Signature Policy + Capability Discovery Hardening

## Status
Accepted (2026-02-16)

## Context
For launch readiness, ECHO reference-node needs a clearer split between:
- development mode (signature bypass allowed), and
- strict mode (signature bypass prohibited).

Agents and operators also need machine-readable node capability metadata and better
operational stats including last simulator run context.

## Decision
1. Add strict signature policy controls:
- CLI global flag: `--require-signature`
- HTTP server flag: `--require-signature`
- When strict policy is enabled, requests that attempt `skip_signature=true` are rejected.

2. Add capability discovery endpoint:
- `GET /registry/capabilities`
- backed by `reference-node/capabilities.local.json`

3. Extend node stats:
- `/stats` now includes latest simulator report payload metadata from `tools/out/sim_report_*.json` when available.

## Consequences
Positive:
- Clear operational policy boundary between dev and strict mode.
- Better interoperability setup for agent discovery.
- More actionable runtime observability for benchmark-driven iterations.

Tradeoffs:
- Additional config surface to document and maintain.
- Capability schema may need future versioning as services expand.

## Follow-up
- Add signed capability documents for network mode.
- Add authn/authz for capability and stats endpoints in hosted deployments.
- Standardize simulator metric contract for stable dashboards.
