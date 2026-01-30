# VALIDATION POLICY

ECHO validation is reuse-based.

## ReuseReceipt verdicts

- SUCCESS: reuse produced expected outcome in the declared context
- PARTIAL: some value, but constraints or outcome degraded
- FAIL: reuse did not produce value or caused contradiction

## Contradictions

A contradiction is recorded when:
- the same EO yields systematically opposite outcomes across similar contexts
- receipts show repeated FAIL or inconsistent metrics

## Quarantine

EO SHOULD remain in FEDERATED visibility when:
- it lacks minimum receipts
- it has high contradiction rate
- it is too context-specific without clear constraints

## Promotion

EO MAY be promoted to GLOBAL_ABSTRACT when:
- it satisfies reuse thresholds
- success rate is stable
- contradictions remain below the threshold

## Important

Publication alone is not trust.
Receipts are the trust substrate.
