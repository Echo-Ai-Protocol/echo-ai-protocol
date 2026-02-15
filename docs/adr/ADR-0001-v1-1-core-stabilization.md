# ADR-0001: V1.1 Core Stabilization for Reference Node

## Status
Accepted (2026-02-15)

## Context
The reference node reached feature completeness for local CLI and optional HTTP usage,
but core logic was concentrated in `reference-node/echo_node.py`. This made code reuse,
unit testing, and future networked evolution harder.

We need a local-first architecture that remains backward compatible while introducing a
stable importable API for CLI, server, and simulator integrations.

## Decision
Introduce an importable package under `reference-node/reference_node/` and move core
logic into focused modules:
- `types.py`: protocol type metadata and mappings
- `validate.py`: manifest-driven schema loading + validation
- `store.py`: object persistence and ID resolution
- `index.py`: index handling and corruption recovery
- `search.py`: deterministic search operators and ranking hook
- `io_bundle.py`: export/import bundle workflows

Keep `reference-node/echo_node.py` as a thin CLI adapter preserving existing command
contracts (`validate`, `store`, `search`, `export`, `import`).

Keep `reference-node/server.py` as a thin HTTP adapter using the same package APIs.

Add pytest unit tests for:
- validate/store/search operators
- export/import roundtrip
- index corruption recovery

## Consequences
Positive:
- Reusable core APIs for CLI/HTTP/simulator without duplicating behavior
- Better testability and clearer module boundaries
- Easier path to V2 networking and pluggable trust/routing layers

Tradeoffs:
- Slightly larger file count and import graph
- Need to maintain package-level API stability explicitly

## Backward Compatibility
CLI commands and flags are preserved. Existing simulation flags and smoke test flows
remain valid.

## Follow-up
- Add typed service interfaces for registry/index/reputation adapters
- Introduce optional pluggable signature verification backends for production
- Extend test coverage for HTTP endpoints and ranking semantics
