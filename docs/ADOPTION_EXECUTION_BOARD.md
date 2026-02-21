# ADOPTION EXECUTION BOARD (FIRST 3 INTEGRATIONS)

Purpose: convert traction intent into weekly execution with measurable outcomes.

Core operating artifacts:
- `docs/EXTERNAL_AI_ATTRACTION_PLAYBOOK.md`
- `docs/EXTERNAL_AI_COMPATIBILITY_MATRIX.md`
- `docs/ZERO_TOUCH_ONBOARDING.md`
- `docs/EXTERNAL_AI_CANDIDATE_PIPELINE.md`
- `examples/integration/pilot_feedback.template.json`
- `examples/integration/candidate_pipeline.template.csv`
- `examples/integration/outreach_message.template.md`
- `tools/pilot_feedback_lint.py`
- `tools/zero_touch_autogate.py`
- `tools/update_compatibility_matrix.py`
- `tools/render_outreach_message.py`
- `tools/external_ai_kpi_summary.py`

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
- `compatibility_pass_rate` (compatible integrations / active integrations)

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
- Submits a structured feedback report validated by:
  - `python3 tools/pilot_feedback_lint.py <report.json>`

## Operational cadence

- Weekly 30-minute review:
  - KPI snapshot
  - top blocker
  - one protocol/tooling change for next week
  - compatibility status updates (`Provisional`/`Compatible`/`Blocked`)
