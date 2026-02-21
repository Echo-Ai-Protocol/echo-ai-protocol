# EXTERNAL AI CANDIDATE PIPELINE

Purpose: standardize candidate sourcing and prioritization for the first integration waves.

Primary output:
- ranked candidate list for pilot outreach and self-serve onboarding.

Templates:
- `examples/integration/candidate_pipeline.template.csv`
- shortlist builder: `tools/candidate_shortlist.py`
- outreach template: `examples/integration/outreach_message.template.md`
- outreach renderer: `tools/render_outreach_message.py`

## Source Channels

1. GitHub projects (active commits in last 90 days)
2. Hugging Face Spaces and model repos
3. Agent framework communities (LangChain, LlamaIndex, AutoGen, CrewAI)
4. Public demos and hackathon projects
5. Open-source maintainers building agent runtimes/tooling

## Scoring Rubric (0-5 each)

1. Technical fit
   - Uses APIs, tool-calling, or autonomous loop patterns compatible with ECHO.
2. Integration readiness
   - Has runnable repo/docs and clear owner.
3. Activity freshness
   - Recent maintenance and visible issue response.
4. Expected feedback quality
   - Likelihood of structured, reproducible bug reports.
5. Strategic value
   - Domain diversity and potential to generate real RR signals.

Total priority score:
- `score_total = technical_fit + readiness + freshness + feedback_quality + strategic_value`

## Selection Rules

1. Build shortlist of 30 candidates (10 code, 10 research, 10 ops).
2. Pick top-10 by `score_total`.
3. Ensure lane diversity:
   - at least 3 code,
   - at least 3 research,
   - at least 2 ops.
4. Promote first 5 into pilot wave.

## Weekly Workflow

1. Refresh candidate activity data.
2. Recompute scores and lane balance.
3. Update pilot status:
   - `queued`, `invited`, `self-serve-running`, `provisional`, `compatible`, `blocked`.
4. Move blockers into adoption board with owner and due date.
5. Recompute KPI rollup after updates:
   - `python3 tools/external_ai_kpi_summary.py --output tools/out/external_ai_kpi_summary.json`

## Outreach Message Generation

Render a personalized invite:

```bash
python3 tools/render_outreach_message.py \
  --integration-id ext-ai-001 \
  --agent-name "Candidate Agent" \
  --lane code \
  --output tools/out/outreach_message_ext-ai-001.md
```

## Automation

Build lane-balanced shortlist:

```bash
python3 tools/candidate_shortlist.py \
  --input examples/integration/candidate_pipeline.template.csv \
  --output tools/out/candidate_shortlist.json \
  --top-n 10 \
  --min-code 3 \
  --min-research 3 \
  --min-ops 2
```
