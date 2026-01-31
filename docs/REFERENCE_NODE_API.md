# Reference Node API (Minimal)

This is a suggested API surface for reference nodes.
It is not mandatory, but helps interoperability.

## Endpoints (conceptual)

### POST /objects
Accepts a single object (any supported type).
- validates schema
- stores if accepted
- returns status

### POST /bundle/import
Accepts JSONL bundle.
- validates each line
- stores accepted objects
- returns report

### GET /bundle/export?types=...&since=...
Exports JSONL bundle filtered by type and time.

### POST /search/eo
Input:
- problem_embedding
- constraints_embedding
Filters:
- freshness_window_seconds
- share_level
Output:
- ranked list of eo_id + scores

### POST /search/trace
Input:
- domain_embedding
Filters:
- activity_type
- freshness_window_seconds

### POST /search/request
Input:
- request_embedding
- constraints_embedding
Filters:
- freshness_window_seconds

## Validation behavior

- reject schema-invalid objects
- apply anti-abuse rate limits (local policy)
- if pow_lite enabled locally, MAY require pow_nonce

## Security notes

- do not log raw prompts
- do not store PII
- treat embeddings as sensitive metadata
