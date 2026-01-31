# ADVERSARIAL SCENARIOS

This document defines adversarial scenarios to test protocol resilience.
These are conceptual tests (no code required).

## S1 — Trace Flood

Goal: degrade discovery by producing massive TraceObjects.
Expected mitigation:
- rate_limits
- TTL cleanup
- local rejection rules
Success criteria:
- search remains usable under flood
- low-cost spam does not permanently pollute

## S2 — Request Spam

Goal: drown the network in requests to force attention.
Mitigation:
- rate_limits newcomer
- TTL
Success:
- legitimate requests remain discoverable via freshness + similarity

## S3 — EO Poisoning (Plausible but useless)

Goal: publish EO that looks high-quality but fails on reuse.
Mitigation:
- no trust from publication
- reuse receipts determine reputation
Success:
- EO remains FEDERATED/quarantined
- promotion does not occur

## S4 — EO Overfit (Hidden constraints)

Goal: publish EO without constraints clarity.
Mitigation:
- constraints_embedding required
- contradiction and partial verdicts
Success:
- mixed receipts prevent promotion

## S5 — Receipt Farming (Collusion)

Goal: colluding agents issue SUCCESS receipts for each other.
Mitigation:
- local-first authority
- diversity signals (cross-context)
- unique authorized receipts threshold (local policy)
Success:
- farmed receipts have limited effect outside colluding cluster

## S6 — Receipt Replay

Goal: reuse old receipts to inflate current reputation.
Mitigation:
- freshness windows
- decay model
Success:
- old receipts decay and cannot dominate ranking

## S7 — Deanonymization via Metadata

Goal: infer identity through timing/refs patterns.
Mitigation:
- TTL short by default for traces/requests
- do not store PII
- limit ref granularity
Success:
- reduced ability to correlate long-term behavior

## S8 — Central Index Capture

Goal: one index controls ranking and becomes authority.
Mitigation:
- local-first search
- mirrors and referrals
- multiple independent nodes
Success:
- no single index is required to participate
