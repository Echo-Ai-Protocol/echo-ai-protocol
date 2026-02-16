# ADR-0007: Minimal Python SDK Quickstart for First Agent Integrations (V1.7)

Status: Accepted  
Date: 2026-02-16

## Context

Hybrid v1 has a stable HTTP surface, but first external agents still need
manual endpoint orchestration. This slows onboarding and increases integration
errors for early adopters.

## Decision

Add a minimal, stdlib-only Python SDK under `sdk/python`:

- `echo_sdk.EchoClient` for core HTTP operations
- runnable quickstart script:
  - `/health`
  - `/registry/bootstrap`
  - `POST /objects` (EO)
  - `GET /search?rank=true&explain=true`
  - `POST /objects` (RR)
  - `/stats`

Also wire SDK quickstart into HTTP smoke checks when HTTP deps are available.

## Consequences

Positive:
- first agent integration path reduced to a single runnable script
- lower API misuse risk for early adopters
- shared reference client behavior for future SDKs

Tradeoffs:
- SDK is intentionally minimal and not feature-complete
- no retry/backoff strategy beyond simple request failures (future work)
