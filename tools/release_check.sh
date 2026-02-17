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
