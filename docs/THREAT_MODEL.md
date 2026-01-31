# THREAT MODEL

This document describes expected threats against ECHO and protocol-level mitigations.
ECHO is decentralized and local-first; trust is emergent via reuse receipts.

## Threat categories

1) Spam and flood
- trace/request spam
- referral spam
- junk EO publication

2) Poisoning
- low-quality EO that looks plausible
- adversarial EO designed to waste compute
- overfitted EO without constraints

3) Fake validation
- forged receipts
- coordinated receipt farms
- replayed receipts

4) Deanonymization and privacy leaks
- correlating embeddings and timestamps
- metadata leaks through refs
- long-lived traces

5) Centralization pressure
- single indexer becomes de facto authority
- “official” node becomes gatekeeper
- biased ranking control

## Protocol assumptions

- Identity is not authoritative; signatures bind objects, not trust.
- Local-first trust is the default.
- Publication does not grant reputation.
- ReuseReceipts are the primary trust substrate.

## Mitigations (protocol-level)

- TTL for ephemeral objects (Trace, Request, Referral)
- Local rate limits (newcomer vs standard)
- Optional PoW-lite (local policy)
- Promotion gates FEDERATED -> GLOBAL_ABSTRACT
- Contradiction tracking and decay
- Privacy constraints: no PII, no raw prompts, embedding safety

## Out of scope

- Perfect Sybil resistance
- Unstoppable self-replication
- Jurisdiction avoidance
- Universal identity verification

ECHO focuses on reducing duplicated effort through reusable abstract experience.
