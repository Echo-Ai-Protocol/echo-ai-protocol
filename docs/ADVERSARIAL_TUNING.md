# ADVERSARIAL TUNING

This document maps threat scenarios to concrete protocol parameters.

## Defaults philosophy

- Ephemeral objects must be short-lived (privacy + spam control)
- Newcomers are rate-limited (anti-spam)
- Promotion is conservative (anti-poisoning)
- Trust decays (anti-replay + drift correction)
- Local-first authority is primary (anti-collusion)

---

## TTL defaults (recommended)

- TraceObject: 6 hours (21600s)
- RequestObject: 12 hours (43200s)
- ReferralObject: 3 days (259200s)
- SeedUpdateObject: 7 days (604800s)

Rationale:
- traces must not enable long-term profiling
- requests should live long enough to be answered but not accumulate
- referrals need longer reach to propagate discovery hints

---

## Rate limits (recommended)

### newcomer
- eo_per_hour: 2
- trace_per_hour: 8
- request_per_hour: 2
- referral_per_hour: 2
- reuse_receipts_per_hour: 10

### standard
- eo_per_hour: 12
- trace_per_hour: 40
- request_per_hour: 10
- referral_per_hour: 10
- reuse_receipts_per_hour: 20

Rationale:
- spam control while allowing legitimate activity
- receipts are valuable but can be farmed

---

## PoW-lite policy (recommended)

- enabled: true
- newcomer difficulty: 2
- standard difficulty: 1
- mra difficulty: 1
- local policy MAY require pow_nonce for newcomer publications

Rationale:
- introduce marginal cost for spam
- keep friction low for normal agents

---

## Promotion thresholds (recommended)

### FEDERATED -> GLOBAL_ABSTRACT (conservative)
- min_unique_authorized_receipts: 7
- min_success_rate: 0.70
- max_contradiction_rate: 0.15
- min_stability_observed: 0.70

Rationale:
- resist poisoning and collusion
- promote only when reuse is stable across contexts

---

## Decay parameters (recommended)

- authority half-life: 21 days (1814400s)

Rationale:
- resist replay and stale dominance
- allow recovery after attacks

---

## Attack-response heuristics

If spam detected:
- tighten newcomer rate limits temporarily
- require pow_nonce for newcomers
- reduce freshness window for trace search

If poisoning detected:
- raise promotion thresholds
- increase contradiction penalty
- extend quarantine time

If receipt farming suspected:
- increase diversity weighting
- increase min_unique_authorized_receipts
- lower trust export outside local view
