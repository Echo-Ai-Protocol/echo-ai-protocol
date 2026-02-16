# ADR-0002: V1.2 Launch API and Observability Step

## Status
Accepted (2026-02-15)

## Context
V1.1 stabilized core logic as an importable package, but launch usability for agents
still required broader HTTP access patterns and runtime introspection.

To accelerate adoption, agents need to:
- fetch a specific object by type+id quickly,
- move bundles over HTTP,
- inspect node state via stats without shell access.

## Decision
Extend the reference-node HTTP surface with:
- `GET /objects/{type}/{object_id}`
- `GET /bundles/export?type=...`
- `POST /bundles/import`
- `GET /stats`

Add core package primitives to support this cleanly:
- `get_object(...)`
- `export_bundle_payload(...)`
- `import_bundle_payload(...)`
- `compute_stats(...)`

Keep CLI behavior unchanged.

## Consequences
Positive:
- Lower integration friction for external agents and hosted wrappers.
- Better observability for operational readiness (`/stats`).
- Clear stepping stone toward V2 routing/reputation services.

Tradeoffs:
- Slightly larger HTTP API surface to maintain.
- Need to keep stats schema stable enough for dashboards.

## Follow-up
- Add pagination and filters for object retrieval at scale.
- Add auth and signature enforcement modes for production deployments.
- Expose simulator metrics in `/stats` once persistence contract is defined.
