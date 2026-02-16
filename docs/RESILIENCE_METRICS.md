# RESILIENCE METRICS

This document defines qualitative and quantitative metrics for ECHO resilience.

## Discovery quality

- Q1: Can a legitimate EO be found under spam?
- Q2: Does freshness weighting recover after attack stops?
- Q3: Do traces expire and reduce long-term profiling?

## Trust and validation

- T1: Promotion false-positive rate (bad EO promoted)
- T2: Promotion false-negative rate (good EO never promoted)
- T3: Contradiction sensitivity (how fast contradictions reduce ranking)
- T4: Collusion resistance proxy (effect of receipt farms outside cluster)

## Privacy

- P1: Trace retention time (should be bounded by TTL)
- P2: Metadata linkability risk (qualitative assessment)
- P3: Embedding non-identifiability compliance (policy adherence)

## Centralization risk

- C1: Dependency on any single mirror/index
- C2: Ability to bootstrap from referrals alone
- C3: Diversity of entry points (manifest, discovery.json, well-known)

## Operational metrics (reference node)

- O1: Validation rejection rate under spam
- O2: TTL GC effectiveness (expired objects removed promptly)
- O3: Storage growth boundedness for ephemeral objects

## Simulator contract mapping (echo.sim.metrics.v1)

- `time_to_find_ticks` -> D2
- `useful_hit_rate_top5_pct` -> D1
- `false_promotion_rate_pct` -> T1
- `missed_promotion_rate_pct` -> T2
- `spam_survival_rate_pct` -> A1
