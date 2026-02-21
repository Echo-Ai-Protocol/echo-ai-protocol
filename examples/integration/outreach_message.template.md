# ECHO Integration Invite (Self-Serve)

Hello {{agent_or_project_name}} team,

We are inviting selected AI agent projects to a self-serve ECHO Hybrid v1 integration pilot.

Why this pilot:
- No long onboarding calls.
- Deterministic API and compatibility gates.
- Machine-readable report accepted as pilot evidence.

What to run:

1. Start ECHO reference node:

```bash
python3 reference-node/server.py --host 127.0.0.1 --port 8080
```

2. Run zero-touch gate:

```bash
make zero-touch-gate \
  INTEGRATION_ID={{integration_id}} \
  AGENT_NAME="{{agent_or_project_name}}" \
  LANE={{lane}} \
  RUNS=3 \
  BASE_URL=http://127.0.0.1:8080
```

3. Validate report:

```bash
python3 tools/pilot_feedback_lint.py tools/out/zero_touch_{{integration_id}}.json
```

Expected output:
- `tools/out/zero_touch_{{integration_id}}.json` with `overall_status` and checkpoint gates.

If you share the report JSON, we will sync compatibility status and provide concrete feedback on any blocker.
