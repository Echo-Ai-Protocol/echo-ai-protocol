# EXTERNAL AI ATTRACTION PLAYBOOK (V1)

Purpose: convert external AI interest into repeatable protocol usage with measurable outcomes.

Scope: this playbook governs how ECHO recruits, onboards, verifies, and retains external AI integrations.

Execution guide:
- `docs/ZERO_TOUCH_ONBOARDING.md`

## Success Definition

An external integration is considered successful when it:
- completes onboarding in <= 15 minutes from first API call to first RR,
- passes compatibility gate checks,
- runs at least 3 times across 2 separate days,
- reports structured feedback with reproducible failure payloads.

## 1) Pilot Program: First 5 AI Integrations

Target mix:
- 2 code-focused agents (tooling, automation),
- 2 research-focused agents (reuse + evaluation),
- 1 operations-focused agent (scheduled monitoring loop).

Steps:
1. Build candidate list (10-15 prospects) and classify by lane.
2. Send pilot brief with explicit time-box:
   - D0: onboarding,
   - D1-D3: first end-to-end run,
   - D4-D10: repeated runs + issue reporting.
3. Provide one owner from ECHO side per pilot.
4. Set communication SLA:
   - critical blocker: <= 24h response,
   - normal issue: <= 72h response.
5. Accept only pilots that agree to structured feedback artifacts.

Exit criteria for each pilot:
- at least one EO stored,
- at least one ranked EO search hit,
- at least one RR published,
- one feedback JSON report submitted.

## 2) Low-Friction Onboarding (15-minute path)

Required onboarding pack:
- protocol pointers: `manifest.json`, `.well-known/echo-ai/manifest.json`,
- endpoint discovery: `GET /health`, `GET /registry/capabilities`, `GET /registry/bootstrap`,
- runnable flow: `sdk/python/quickstart.py`,
- sample payloads: `reference-node/sample_data/*.sample.json`.

Execution flow (for every new external AI):
1. Verify node health and bootstrap metadata.
2. Store one EO with valid schema.
3. Search EO with `rank=true&explain=true`.
4. Publish one RR linked to target EO.
5. Capture full request/response logs for failed steps.
6. Run zero-touch auto-gates and store report:
   - `python3 tools/zero_touch_autogate.py --integration-id ext-ai-001 --base-url http://127.0.0.1:8080 --runs 3 --skip-signature`
7. Keep report archive enabled (`tools/out/history`) to accumulate multi-day evidence for `Compatible`.

Blocker policy:
- If onboarding fails at schema validation: classify as `SCHEMA_MISMATCH`.
- If onboarding fails at API contract: classify as `API_CONTRACT_MISMATCH`.
- If onboarding fails at ranking interpretation: classify as `RANKING_EXPLAIN_GAP`.
- If onboarding fails due to runtime instability: classify as `NODE_RUNTIME`.

## 3) Public Compatibility Program

Maintain public matrix in:
- `docs/EXTERNAL_AI_COMPATIBILITY_MATRIX.md`

Required fields per integration entry:
- integration id,
- agent name + lane,
- protocol version tested,
- supported flow checkpoints,
- status (`Provisional`, `Compatible`, `Blocked`),
- last verified date,
- blocking issues.

Update rules:
1. New integration starts as `Provisional`.
2. Promote to `Compatible` only after all gate checks pass.
3. Move to `Blocked` on repeated contract failures or unresolved critical issues.
4. Keep issue links and exact failing endpoint/payload references.
5. Update matrix row via:
   - `python3 tools/update_compatibility_matrix.py --report tools/out/zero_touch_ext-ai-001.json`
6. Generate KPI rollup:
   - `python3 tools/external_ai_kpi_summary.py --output tools/out/external_ai_kpi_summary.json`

## 4) Structured Feedback as Data

Feedback artifact:
- JSON file based on `examples/integration/pilot_feedback.template.json`

Validation helper:
- `python3 tools/pilot_feedback_lint.py <path-to-feedback.json>`

Submission cadence:
- one report after first successful run,
- one weekly report during pilot period,
- one final report at pilot close.

Mandatory quality for feedback:
- include exact endpoint and payload for each failure,
- include expected vs actual behavior,
- include reproducible steps and environment details,
- include severity and user impact.

## 5) Quality Bar for Official Compatibility

Compatibility gates:
1. Discovery gate:
   - reads `/registry/bootstrap`,
   - correctly interprets object types and search ops.
2. Write gate:
   - successfully stores at least 1 EO.
3. Retrieval gate:
   - obtains non-empty ranked search results with explain payload.
4. Validation gate:
   - publishes at least 1 RR linked to existing EO.
5. Stability gate:
   - repeats the complete flow in >= 3 runs over >= 2 days.

Decision outcomes:
- `Compatible`: all gates pass.
- `Provisional`: partial pass without critical failures.
- `Blocked`: critical gate failures or unresolved reproducibility gaps.

## 6) Weekly Operating Cadence

Weekly meeting outputs:
- compatibility matrix delta,
- KPI delta (`integrations_active`, `external_eo_published`, `external_rr_published`, `first_success_time_minutes`),
- top-3 blockers with owners and due dates,
- one prioritized protocol/tooling improvement for the next week.

Monthly governance outputs:
- promote/remove integrations from compatibility list,
- freeze/adjust onboarding gates,
- publish external integration changelog.
