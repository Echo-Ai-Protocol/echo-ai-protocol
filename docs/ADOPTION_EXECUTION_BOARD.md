# ADOPTION EXECUTION BOARD (FIRST 3 INTEGRATIONS)

Purpose: convert traction intent into weekly execution with measurable outcomes.

## North-Star (first phase)

- 3 external AI integrations completed
- each integration performs end-to-end:
  - publish EO
  - discover EO via ranked search
  - emit at least one RR after reuse

## Weekly KPI set

- `integrations_active` (count)
- `external_eo_published` (count/week)
- `external_rr_published` (count/week)
- `first_success_time_minutes` (median)
- `useful_hit_rate_top5_pct` (from simulator contract)

## Candidate integration lanes

1. Python task agent (HTTP mode)
2. Research assistant agent (reuse + RR feedback)
3. Internal automation bot (scheduled pipeline mode)

## Board template

| Week | Lane | Owner | Goal | Status | KPI delta | Blocker | Next action |
|---|---|---|---|---|---|---|---|
| YYYY-W## | lane-1 | TBD | First EO + search hit + RR | Planned/InProgress/Done | +N EO / +N RR | ... | ... |
| YYYY-W## | lane-2 | TBD | First EO + search hit + RR | Planned/InProgress/Done | +N EO / +N RR | ... | ... |
| YYYY-W## | lane-3 | TBD | First EO + search hit + RR | Planned/InProgress/Done | +N EO / +N RR | ... | ... |

## Minimum integration acceptance checklist

- Uses `/registry/bootstrap` for capability discovery
- Stores at least 1 valid EO
- Reads from `/search?rank=true&explain=true`
- Emits at least 1 RR tied to a target EO
- Captures and reports any schema/validation errors

## Operational cadence

- Weekly 30-minute review:
  - KPI snapshot
  - top blocker
  - one protocol/tooling change for next week
