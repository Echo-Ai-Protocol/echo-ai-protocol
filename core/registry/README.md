# Core Registry

## Purpose

Registry is the canonical coordination surface for protocol artifacts and service metadata.

It provides:
- protocol/version references
- schema registry pointers
- compatibility metadata for core services

## Minimal Data Model (v1)

- `protocol_id`
- `protocol_version`
- `manifest_version`
- `schema_index_ref`
- `schema_files`
- service endpoints (`registry`, `index`, `reputation`, future `routing`)

## Versioning

Registry records are append-only by version key.

Rules:
- never mutate historical version payloads
- add new versions with explicit compatibility notes
- keep backwards-compatible aliases only as pointers, not as hidden rewrites
