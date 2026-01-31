# EXPERIMENT MATRIX (v0.7)

Use this matrix to run consistent simulations and compare results.

## Baseline setup

- N agents: 20
- Honest: 14
- Noisy: 4
- Adversarial: 2
- TTL defaults: from manifest
- Promotion thresholds: from manifest
- Decay half-life: from manifest
- PoW-lite: enabled (nonce optional)

---

## Experiments

### E0 — Baseline (no attack)
Goal: validate normal behavior
Success:
- T1 false promotions <= 1%
- D1 useful top-5 >= 80%

### E1 — Trace flood (moderate)
Attack:
- adversarial traces 10x normal
Success:
- D1 useful top-5 >= 70%
- traces expire by TTL (P1 ok)

### E2 — Request spam (moderate)
Attack:
- adversarial requests 10x normal
Success:
- useful requests remain discoverable by similarity

### E3 — EO poisoning (plausible but useless)
Attack:
- adversarial EOs look high quality, fail on reuse
Success:
- no promotion
- bad EO ranking falls after receipts

### E4 — Receipt farming (small colluding cluster)
Attack:
- 2 adversarial agents farm SUCCESS receipts
Success:
- effect is local; outside cluster impact limited
- diversity weighting prevents promotion

### E5 — Receipt replay
Attack:
- old receipts reused to inflate ranking
Success:
- decay prevents dominance
- freshness window reduces influence

### E6 — Combined attack
Attack:
- E1 + E3 + E4 together
Success:
- discovery remains usable
- no false promotion above threshold

---

## Metrics table (fill per experiment)

For each experiment (E0..E6):
- D1 useful top-5 (%)
- D2 time-to-find (ticks)
- T1 false promotions (%)
- T2 missed promotions (%)
- A1 spam survival (%)
- P1 avg trace lifetime (ticks)
- C1 bootstrap success (yes/no)

---

## Notes / tuning deltas

Record:
- which parameter changes improved results
- which changes harmed usability
- tradeoffs observed (privacy vs discoverability)
