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

if python3 - <<'PY' >/dev/null 2>&1
import importlib
importlib.import_module('pytest')
PY
then
  step "pytest"
  python3 -m pytest reference-node/tests
else
  step "pytest skipped (not installed)"
fi

echo "[RELEASE-CHECK] PASS"
