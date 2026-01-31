# THREAT TEST CHECKLIST (Manual)

Use this checklist to validate ECHO assumptions before writing production code.

## Spam & Flood
- [ ] Trace flood does not break EO search usefulness
- [ ] Request spam is bounded by TTL + rate limits
- [ ] Referral spam is bounded and does not dominate discovery

## Poisoning
- [ ] Low-quality EO does not gain trust without receipts
- [ ] Overfit EO receives PARTIAL/FAIL and stays unpromoted
- [ ] Contradictions reduce ranking and prevent promotion

## Fake validation
- [ ] Receipt farms do not export trust outside colluding cluster (local-first)
- [ ] Old receipts decay and do not dominate ranking

## Privacy
- [ ] Traces/requests expire and are not kept indefinitely
- [ ] No raw prompts or PII appear in stored objects

## Centralization
- [ ] Participation is possible without a single indexer
- [ ] Multiple mirrors/referrals can bootstrap entry

## Outcome
- [ ] Protocol behavior remains stable under adversarial assumptions
