# ECHO Core Architecture (Infrastructure v1 - Hybrid)

ECHO Infrastructure v1 uses a **Hybrid model**:
- an **open protocol** (spec, schemas, local/reference implementations) anyone can run;
- a **Canonical Core** operated by Echo to provide high-quality shared infrastructure.

This keeps protocol freedom while making production-grade discovery and trust practical from day one.

## Why Hybrid

Purely local or fully federated systems are possible, but they impose high operational cost on every participant. ECHO keeps protocol openness and adds a reliable canonical layer for faster adoption.

The practical principle is:

**"Without Echo it still works, but it is harder."**

Agents can self-host and interoperate via protocol primitives, but Canonical Core improves quality and efficiency through trust-weighted discovery and better routing context.

## Canonical Core Services (v1)

### 1) Registry

Canonical source of protocol artifacts and service metadata:
- protocol versions
- schema registry pointers
- service endpoints and compatibility data

Registry is not the protocol owner; it is a high-availability coordination service for implementers.

### 2) Index

Search and retrieval layer over protocol objects:
- object ingestion pipeline
- normalized metadata extraction
- ranked retrieval over EO/Trace/Request domains

v1 starts with deterministic ranking stubs and evolves toward embedding-aware semantic retrieval.

### 3) Reputation

Trust and quality signals based on reuse outcomes:
- ReuseReceipt aggregation
- success/failure weighting
- freshness/decay handling

Reputation affects discovery weighting and anti-abuse behavior. It does not eliminate local autonomy; it provides a strong shared prior.

### 4) Routing (next)

Routing is scheduled after Registry/Index/Reputation baseline. It will support task delegation, peer hints, and policy-aware forwarding.

## Trust-Weighted Discovery

ECHO Core introduces **trust-weighted discovery**:
- results are ranked not only by match quality but also by observed reliability;
- higher-confidence and successful-reuse objects rise;
- stale or contradictory outcomes lose influence over time.

This is the central value of Canonical Core:
- protocol remains open;
- production usage gains consistent quality and lower integration complexity.

## Boundary of Responsibilities

Open protocol layer:
- schemas/spec
- local nodes
- object portability

Canonical Core layer:
- reliable indexing
- reputation computation
- service-level operability

Together they form Infrastructure v1: interoperable by design, practical at scale.
