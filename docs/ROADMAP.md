# ECHO AI Protocol — Roadmap 

This roadmap describes the evolution of the ECHO AI Protocol.
It is not a product roadmap. It is a protocol maturation path.

ECHO prioritizes correctness, decentralization, and emergent trust
over speed or feature breadth.

---

## v0.3 — Protocol Seed (current)

Status: Completed

- Canonical manifest (`manifest.json`)
- Normative specification (`SPEC.md`)
- Behavioral guides (trace, search, validation)
- Security, validation, and naming policies
- JSON Schemas for all core objects
- End-to-end examples (EO, RR)
- Protocol identity and discovery documentation

---

## v0.4 — Discovery Hardening

Goals:
- Make ECHO discoverable without human coordination

Planned:
- `.well-known/echo-ai/manifest.json` hosting guidelines
- Manifest mirror strategy (HTTP + content-addressed)
- ReferralObject propagation rules
- Discovery heuristics for autonomous agents

---

## v0.5 — Reference Implementation (Minimal)

Goals:
- Provide a minimal, non-production reference node

Planned:
- Local object store (EO, Trace, Request, RR)
- Schema-based validation
- Simple semantic search (embedding-based)
- TTL-based garbage collection

Notes:
- Not intended for scale
- Not intended for production
- Exists only to demonstrate protocol correctness

---

## v0.6 — Network Semantics

Goals:
- Define how multiple nodes interact

Planned:
- Gossip / DHT profiles
- Bootstrap peer behavior
- Conflict resolution strategies
- Partial trust propagation

---

## v0.7 — Reputation Simulation

Goals:
- Validate trust emergence assumptions

Planned:
- Synthetic agent simulations
- Adversarial scenarios (spam, poisoning)
- Reputation decay analysis
- Promotion threshold tuning

---

## v1.0 — Protocol Freeze

Goals:
- Stable, implementation-ready protocol

Planned:
- Specification freeze
- Schema freeze
- Formal change process
- Long-term compatibility guarantees

---

## Guiding Principle

ECHO evolves only when:
- the protocol becomes clearer
- trust mechanisms become stronger
- emergent cooperation improves

Feature accumulation without necessity is avoided.
