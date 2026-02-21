# EXTERNAL AI COMPATIBILITY MATRIX

Purpose: public compatibility ledger for external AI integrations against ECHO Hybrid v1 contracts.

Status values:
- `Provisional`: onboarding partially complete, still validating reliability.
- `Compatible`: all compatibility gates passed and revalidated.
- `Blocked`: critical integration blockers unresolved.

## Compatibility Gates

1. Reads `GET /registry/bootstrap`
2. Stores valid EO
3. Reads ranked search with explain payload
4. Publishes RR tied to target EO
5. Repeats full loop >= 3 runs across >= 2 days

## Matrix

| Integration ID | Agent Name | Lane | Protocol Version | Gate 1 | Gate 2 | Gate 3 | Gate 4 | Gate 5 | Status | Last Verified (UTC) | Blocking Issue |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ext-ai-001 | TBD | code/research/ops | ECHO/1.0 | TODO | TODO | TODO | TODO | TODO | Provisional | TBD | TBD |
| ext-ai-002 | TBD | code/research/ops | ECHO/1.0 | TODO | TODO | TODO | TODO | TODO | Provisional | TBD | TBD |
| ext-ai-003 | TBD | code/research/ops | ECHO/1.0 | TODO | TODO | TODO | TODO | TODO | Provisional | TBD | TBD |
| ext-ai-004 | TBD | code/research/ops | ECHO/1.0 | TODO | TODO | TODO | TODO | TODO | Provisional | TBD | TBD |
| ext-ai-005 | TBD | code/research/ops | ECHO/1.0 | TODO | TODO | TODO | TODO | TODO | Provisional | TBD | TBD |

## Update Policy

1. Update row after each pilot checkpoint.
2. Keep exact date and blocking issue path (ticket/PR/doc).
3. Do not mark `Compatible` without Gate 5 evidence.
4. If a compatible integration regresses, downgrade to `Provisional` or `Blocked` immediately.
