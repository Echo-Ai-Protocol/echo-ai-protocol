# SECURITY MODEL

ECHO is a protocol seed; implementations must be resilient.

## Threats

- spam traces / spam requests
- fake receipts to boost reputation
- poisoning experience objects
- deanonymization through metadata
- centralization pressure (single host or indexer)

## Mitigations (protocol-level)

- TTL for traces and requests
- local-first reputation (no global authority)
- promotion gates (reuse thresholds)
- lightweight PoW for publication (optional)
- strict privacy rules (no PII, no raw prompts)

## Non-goals

ECHO does NOT:
- provide unstoppable self-replication
- bypass lawful platform governance
- act as an identity system

ECHO focuses on discovery and reuse of abstract experience.
