# Core Reputation

## Purpose

Reputation computes reliability signals from observed reuse behavior.

## Primary Signals

- ReuseReceipt verdict distribution (`SUCCESS` / `PARTIAL` / `FAIL`)
- issuer behavior consistency
- target EO reuse outcomes across contexts

## Decay Model

Reputation should be freshness-aware:
- newer evidence weighs more
- older evidence decays over time
- contradiction patterns reduce score faster than absence of activity

## Roles (v1)

- **Producer**: publishes EOs and receives outcome feedback
- **Reuser**: issues receipts after application
- **Observer/Index consumer**: uses trust scores for routing and ranking

Reputation informs ranking; it does not replace local policy decisions.
