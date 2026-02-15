#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

pass() { echo "PASS: $1"; }
warn() { echo "WARN: $1"; }
fail() { echo "FAIL: $1"; exit 1; }

command -v python3 >/dev/null 2>&1 || fail "python3 not found"
pass "python3 found"

python3 - <<'PY'
import importlib
modules = ["jsonschema"]
missing = []
for m in modules:
    try:
        importlib.import_module(m)
    except Exception:
        missing.append(m)
if missing:
    raise SystemExit("missing:" + ",".join(missing))
print("ok")
PY
pass "required Python module jsonschema available"

if python3 - <<'PY' >/dev/null 2>&1
import importlib
for m in ("fastapi", "uvicorn"):
    importlib.import_module(m)
PY
then
  pass "optional HTTP modules fastapi/uvicorn available"
else
  warn "optional HTTP modules fastapi/uvicorn not installed (HTTP smoke will be skipped)"
fi

if python3 - <<'PY' >/dev/null 2>&1
import importlib
importlib.import_module("pytest")
PY
then
  pass "optional pytest available"
else
  warn "optional pytest not installed (unit tests unavailable)"
fi

if [[ -f "$ROOT_DIR/manifest.json" && -d "$ROOT_DIR/schemas" ]]; then
  pass "manifest.json and schemas/ found"
else
  fail "manifest.json or schemas/ missing"
fi

pass "preflight completed"
