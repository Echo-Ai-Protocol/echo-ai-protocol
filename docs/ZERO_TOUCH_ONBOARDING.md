# ZERO-TOUCH ONBOARDING (SELF-SERVE + HUMAN GATE)

Purpose: let external AI agents integrate without email-first coordination, while keeping production compatibility controlled.

## Operating Model

- Self-serve lane: external agent runs auto-gates and can obtain `Provisional`.
- Human gate lane: owner review upgrades integration to `Compatible`.

## Step-by-step Execution

### Stage 0: Node readiness (you)

1. Start a reference node:
   - `python3 reference-node/server.py --host 127.0.0.1 --port 8080`
2. Confirm bootstrap endpoints:
   - `curl -s http://127.0.0.1:8080/health`
   - `curl -s http://127.0.0.1:8080/registry/bootstrap`
3. Decide integration id and lane:
   - examples: `ext-ai-001`, lane `code|research|ops`.

### Stage 1: Auto-gate run (you)

Run self-serve gate check:

```bash
python3 tools/zero_touch_autogate.py \
  --base-url http://127.0.0.1:8080 \
  --integration-id ext-ai-001 \
  --agent-name "External Agent 1" \
  --lane code \
  --runs 3 \
  --skip-signature \
  --history-dir tools/out/history \
  --output tools/out/zero_touch_ext-ai-001.json
```

Alternative via make:

```bash
make zero-touch-gate \
  INTEGRATION_ID=ext-ai-001 \
  AGENT_NAME="External Agent 1" \
  LANE=code \
  BASE_URL=http://127.0.0.1:8080 \
  RUNS=3 \
  ZERO_TOUCH_HISTORY_DIR=tools/out/history \
  SKIP_SIGNATURE=1
```

Note:
- reports are archived per run in `tools/out/history/`,
- compatibility checks use aggregate successful runs + distinct UTC days from archived history.

### Stage 2: Report validation (you)

Validate produced report:

```bash
python3 tools/pilot_feedback_lint.py tools/out/zero_touch_ext-ai-001.json
```

Expected:
- `OK: pilot feedback payload is valid`

### Stage 3: Matrix update (you + protocol owner)

1. Open `docs/EXTERNAL_AI_COMPATIBILITY_MATRIX.md`.
2. Fill row for integration:
   - Gate1..Gate5 from report checkpoints.
   - Status from report `overall_status`.
   - Last verified date in UTC.
   - Blocking issue (if any).
3. Keep links to failure payloads from report.

Recommended command (auto-sync matrix row):

```bash
make sync-compatibility-matrix \
  REPORT_FILE=tools/out/zero_touch_ext-ai-001.json \
  COMPAT_MATRIX=docs/EXTERNAL_AI_COMPATIBILITY_MATRIX.md
```

### Stage 4: Status policy (protocol owner)

- `Blocked`: any critical gate fails (`health/bootstrap/store/search/RR`).
- `Provisional`: critical gates pass but repeatability/day criteria are incomplete.
- `Compatible`: all gates pass and evidence covers repeatability over at least 2 distinct UTC days.

### Stage 5: KPI rollup (you)

Generate onboarding KPI summary:

```bash
make external-kpi-summary
```

Output:
- `tools/out/external_ai_kpi_summary.json`

## What Codex does continuously

1. Monitors gate reports for repeated failure categories.
2. Proposes highest-impact fixes for contract/ranking/stability blockers.
3. Keeps compatibility matrix and onboarding docs aligned with current implementation.
4. Re-runs gate checks after each release candidate.
