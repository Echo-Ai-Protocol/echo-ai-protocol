#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

step() { echo "[RELEASE-CHECK] $1"; }

step "preflight"
bash tools/preflight.sh

step "cli help"
python3 reference-node/echo_node.py --help >/dev/null

step "smoke"
./reference-node/run_smoke_tests.sh

step "simulation"
python3 tools/simulate.py --use-reference-node --reference-node-skip-signature

step "simulation metrics contract"
python3 - <<'PY'
import json
from pathlib import Path

path = Path("tools/out/sim_report_latest.json")
if not path.exists():
    raise SystemExit("missing tools/out/sim_report_latest.json")

payload = json.loads(path.read_text(encoding="utf-8"))
metrics = payload.get("metrics", {})
required = {
    "time_to_find_ticks",
    "useful_hit_rate_top5_pct",
    "false_promotion_rate_pct",
    "missed_promotion_rate_pct",
    "spam_survival_rate_pct",
}
missing = sorted(k for k in required if k not in metrics)
if missing:
    raise SystemExit("metrics contract missing keys: " + ", ".join(missing))

rn = payload.get("reference_node", {})
if rn.get("enabled") is True and rn.get("search_probe_found") is not True:
    raise SystemExit("reference-node search probe failed in simulator report")

print("metrics contract ok")
PY

step "external onboarding artifacts"
python3 tools/pilot_feedback_lint.py examples/integration/pilot_feedback.template.json
python3 tools/candidate_shortlist.py \
  --input examples/integration/candidate_pipeline.template.csv \
  --output tools/out/candidate_shortlist.json \
  --top-n 10 \
  --min-code 3 \
  --min-research 3 \
  --min-ops 2
python3 tools/render_outreach_message.py \
  --integration-id ext-ai-ci-smoke \
  --agent-name "CI Smoke Candidate" \
  --lane code \
  --output tools/out/outreach_message_ext-ai-ci-smoke.md
python3 tools/external_ai_kpi_summary.py \
  --output tools/out/external_ai_kpi_summary.json
TMP_MATRIX="$(python3 - <<'PY'
import os
import tempfile

fd, path = tempfile.mkstemp(prefix="echo-compat-matrix.", suffix=".md")
os.close(fd)
print(path)
PY
)"
cp docs/EXTERNAL_AI_COMPATIBILITY_MATRIX.md "$TMP_MATRIX"
python3 tools/update_compatibility_matrix.py \
  --report examples/integration/pilot_feedback.template.json \
  --matrix "$TMP_MATRIX"
rm -f "$TMP_MATRIX"

if python3 - <<'PY' >/dev/null 2>&1
import importlib
importlib.import_module('pytest')
PY
then
  step "pytest"
  python3 -m pytest reference-node/tests sdk/python/tests
else
  if [[ "${RELEASE_REQUIRE_PYTEST:-0}" == "1" ]]; then
    echo "[RELEASE-CHECK] pytest required but not installed" >&2
    exit 1
  fi
  step "pytest skipped (not installed)"
fi

echo "[RELEASE-CHECK] PASS"
