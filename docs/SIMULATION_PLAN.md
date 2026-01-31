# SIMULATION PLAN (v0.7)

This plan validates whether ECHO’s trust and discovery assumptions hold under normal and adversarial conditions.
No production code is required.

## Objectives

- Verify that discovery remains useful under spam
- Verify that poisoning does not lead to promotion
- Verify that collusion has limited impact outside local clusters
- Verify that privacy goals hold (ephemeral traces/requests)
- Tune thresholds with evidence

## Simulation model

We simulate N agents and a set of objects:
- Agents publish ExperienceObjects (EO)
- Agents publish Traces and Requests (ephemeral)
- Agents reuse EOs and publish ReuseReceipts (RR)
- Agents optionally publish Referrals

Agents are divided into roles:
- Honest: publish good EOs and truthful receipts
- Noisy: publish mixed quality EOs
- Adversarial: spam, poison, collude, replay

## Suggested scale

- Small: N=20 agents (manual feasible)
- Medium: N=50 agents (spreadsheet feasible)
- Large: N=200 agents (future code simulation)

## Local-first view

Each agent maintains:
- local EO ranking
- local trust score per EO
- local suspicion flags (farm/replay/spam)

There is no global truth. Results are aggregated for analysis only.

## Timeline

Simulate discrete time steps (ticks):
- 1 tick = 15 minutes
- Run for 7 days (672 ticks) for full decay + TTL behavior
- For manual runs, use 1 tick = 1 hour (168 ticks)

## Object lifecycle rules

- Traces expire by ttl_seconds
- Requests expire by ttl_seconds
- Referrals expire by ttl_seconds
- EOs and RRs persist (reference node) but decay affects ranking

## Core metrics (track each day)

Discovery quality:
- D1: % of searches returning a useful EO in top-5
- D2: time-to-find (ticks) for a useful EO under spam

Trust/validation:
- T1: false promotions (bad EO promoted)
- T2: missed promotions (good EO never becomes top-ranked)
- T3: contradiction suppression time (ticks until bad EO drops)

Anti-abuse:
- A1: spam acceptance rate (how much spam survives)
- A2: newcomer throttling effectiveness (bounded spam volume)

Privacy:
- P1: trace/request average lifetime (should match TTL)
- P2: long-term linkability risk (qualitative score)

Centralization:
- C1: can agents bootstrap from referrals + mirrors only (yes/no)

## Stop conditions

If any of the following occurs, tuning is required:
- false promotions > 5% over 7 days
- discovery useful top-5 rate < 60% under moderate spam
- receipt farming boosts EO globally without cross-context diversity
- traces persist beyond TTL in reference node behavior

## Outputs

- Experiment matrix filled (docs/EXPERIMENT_MATRIX.md)
- Tuning deltas proposed (manifest changes)
- Updated adversarial tuning notes (docs/ADVERSARIAL_TUNING.md)
