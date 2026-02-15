# Core Index

## Purpose

Index is the retrieval layer for protocol objects (EO, Trace, Request, RR, etc.).

## Indexing Pipeline (v1)

1. Ingest object payload
2. Validate schema/version compatibility
3. Extract searchable fields and metadata
4. Persist index entries
5. Serve ranked retrieval

## Ranking Signals (v1)

Deterministic baseline signals:
- exact/contains/prefix field match
- object confidence (`confidence_score` for EO)
- presence of outcome metrics
- receipt-backed success counts where available

## Future Embeddings

Planned upgrades:
- vector storage for embedding fields
- ANN retrieval
- hybrid scoring (semantic + trust + freshness)
- query-time policy filters and tenant controls
