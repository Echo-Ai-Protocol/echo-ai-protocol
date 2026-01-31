# Reference Node (Minimal)

This document defines a minimal, non-production reference implementation of ECHO.
It exists to demonstrate protocol correctness, not to provide a hosted service.

## Goals

- Validate objects using JSON Schemas
- Store objects locally (EO, Trace, Request, RR, AAO, Referral)
- Provide semantic search over stored objects
- Enforce TTL garbage collection for ephemeral objects
- Provide a simple import/export format

## Non-goals

- Production scalability
- Full decentralization / DHT / gossip in v0.x
- Identity verification beyond signatures
- Token economics

## Minimal capabilities

### 1) Validate
- MUST validate objects against `schemas/echo.schema.*`
- MUST reject invalid objects

### 2) Store
- MUST persist ExperienceObjects and ReuseReceipts
- SHOULD persist Traces and Requests until TTL expiration

### 3) Search
- MUST support:
  - EO_SEARCH
  - TRACE_SEARCH
  - REQUEST_SEARCH
- MAY use approximate nearest neighbor (ANN)
- MUST support freshness window filtering

### 4) TTL Garbage Collection
- MUST delete expired Trace/Request/Referral based on ttl_seconds

### 5) Import/Export
- MUST support exporting a bundle of objects as JSONL:
  - one JSON object per line
- MUST support importing the same bundle

## Minimal local reputation

- MUST compute local reuse success rates per EO from ReuseReceipts
- MUST apply promotion gates locally (FEDERATED -> GLOBAL_ABSTRACT as local view)

## Notes

This is a protocol demonstrator. Implementations may differ, but MUST remain schema- and spec-consistent.
