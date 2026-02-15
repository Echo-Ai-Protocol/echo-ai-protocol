#!/usr/bin/env bash
set -euo pipefail

# NOTE: This script is intentionally smoke-only.
# Unit tests are executed separately via pytest.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NODE="$ROOT_DIR/reference-node/echo_node.py"
SERVER="$ROOT_DIR/reference-node/server.py"
MANIFEST="$ROOT_DIR/manifest.json"
SCHEMAS_DIR="$ROOT_DIR/schemas"
SAMPLE_DIR="$ROOT_DIR/reference-node/sample_data"
STORAGE_DIR="$ROOT_DIR/reference-node/storage"
INDEX_FILE="$STORAGE_DIR/index.json"
SERVER_HOST="127.0.0.1"
SERVER_PORT="18080"
SERVER_LOG="/tmp/echo-reference-node-server.log"
SMOKE_REQUIRE_HTTP="${SMOKE_REQUIRE_HTTP:-0}"

SERVER_PID=""
BUNDLE_FILE=""
HTTP_PAYLOAD=""
HTTP_POST_OUT="/tmp/echo-http-post.out"
HTTP_SEARCH_OUT="/tmp/echo-http-search.out"
HTTP_OBJ_OUT="/tmp/echo-http-object.out"
HTTP_STATS_OUT="/tmp/echo-http-stats.out"
HTTP_BUNDLE_OUT="/tmp/echo-http-bundle.out"
HTTP_BUNDLE_IMPORT_PAYLOAD=""

TYPES=(eo trace request rr aao referral seedupdate)

print_pass() { echo "PASS: $1"; }
print_fail() { echo "FAIL: $1" >&2; }
print_skip() { echo "SKIP: $1"; }

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" 2>/dev/null || true
    SERVER_PID=""
  fi
  if [[ -n "${BUNDLE_FILE:-}" ]]; then
    rm -f "$BUNDLE_FILE" || true
  fi
  if [[ -n "${HTTP_PAYLOAD:-}" ]]; then
    rm -f "$HTTP_PAYLOAD" || true
  fi
  if [[ -n "${HTTP_BUNDLE_IMPORT_PAYLOAD:-}" ]]; then
    rm -f "$HTTP_BUNDLE_IMPORT_PAYLOAD" || true
  fi
  rm -f "$HTTP_POST_OUT" "$HTTP_SEARCH_OUT" "$HTTP_OBJ_OUT" "$HTTP_STATS_OUT" "$HTTP_BUNDLE_OUT" || true
}
trap cleanup EXIT

id_field_for_type() {
  case "$1" in
    eo) echo "eo_id" ;;
    trace) echo "trace_id" ;;
    request) echo "rq_id" ;;
    rr) echo "rr_id" ;;
    aao) echo "aao_id" ;;
    referral) echo "ref_id" ;;
    seedupdate) echo "su_id" ;;
    *)
      echo "Unknown type: $1" >&2
      return 1
      ;;
  esac
}

sample_file_for_type() {
  echo "$SAMPLE_DIR/$1.sample.json"
}

run_node() {
  python3 "$NODE" --manifest "$MANIFEST" --schemas-dir "$SCHEMAS_DIR" "$@"
}

extract_id_value() {
  python3 - "$1" "$2" <<'PY'
import json
import sys

path, field = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as f:
    obj = json.load(f)
print(obj[field])
PY
}

assert_index_contains_id() {
  python3 - "$1" "$2" "$3" <<'PY'
import json
import sys

idx_path, typ, obj_id = sys.argv[1], sys.argv[2], sys.argv[3]
with open(idx_path, "r", encoding="utf-8") as f:
    idx = json.load(f)
ids = idx.get(typ, [])
if obj_id not in ids:
    raise SystemExit(1)
PY
}

run_cli_smoke() {
  echo "[SMOKE] Clearing storage..."
  rm -rf "$STORAGE_DIR"
  mkdir -p "$STORAGE_DIR"
  touch "$STORAGE_DIR/.gitkeep"
  print_pass "storage cleared"

  for t in "${TYPES[@]}"; do
    f="$(sample_file_for_type "$t")"
    if [[ ! -f "$f" ]]; then
      print_fail "missing sample file for $t: $f"
      return 1
    fi

    echo "[SMOKE] validate ($t)"
    if ! out="$(run_node validate --type "$t" --file "$f" 2>&1)"; then
      echo "$out"
      print_fail "validate failed for $t"
      return 1
    fi
    print_pass "validate $t"

    echo "[SMOKE] validate --skip-signature ($t)"
    if ! out="$(run_node validate --skip-signature --type "$t" --file "$f" 2>&1)"; then
      echo "$out"
      print_fail "validate --skip-signature failed for $t"
      return 1
    fi
    print_pass "validate --skip-signature $t"

    echo "[SMOKE] store ($t)"
    if ! out="$(run_node store --type "$t" --file "$f" 2>&1)"; then
      echo "$out"
      print_fail "store failed for $t"
      return 1
    fi
    print_pass "store $t"
  done

  if [[ ! -f "$INDEX_FILE" ]]; then
    print_fail "storage index file not found: $INDEX_FILE"
    return 1
  fi
  print_pass "storage index exists"

  for t in "${TYPES[@]}"; do
    f="$(sample_file_for_type "$t")"
    id_field="$(id_field_for_type "$t")"
    id_value="$(extract_id_value "$f" "$id_field")"

    echo "[SMOKE] index contains id ($t)"
    if ! assert_index_contains_id "$INDEX_FILE" "$t" "$id_value"; then
      print_fail "index does not contain $t id: $id_value"
      return 1
    fi
    print_pass "index contains id $t"

    echo "[SMOKE] search equals ($t)"
    out="$(run_node search --type "$t" --field "$id_field" --equals "$id_value" 2>&1)"
    if ! grep -q '^count: 1$' <<<"$out"; then
      echo "$out"
      print_fail "search equals expected count:1 for $t"
      return 1
    fi
    print_pass "search equals $t"
  done

  echo "[SMOKE] search contains (eo)"
  eo_contains_out="$(run_node search --type eo --field eo_id --contains 'echo.eo.sample' 2>&1)"
  if ! grep -q '^count: 1$' <<<"$eo_contains_out"; then
    echo "$eo_contains_out"
    print_fail "search contains expected count:1 for eo"
    return 1
  fi
  print_pass "search contains eo"

  echo "[SMOKE] search prefix (eo)"
  eo_prefix_out="$(run_node search --type eo --field eo_id --prefix 'echo.eo.sample' 2>&1)"
  if ! grep -q '^count: 1$' <<<"$eo_prefix_out"; then
    echo "$eo_prefix_out"
    print_fail "search prefix expected count:1 for eo"
    return 1
  fi
  print_pass "search prefix eo"

  BUNDLE_FILE="$(mktemp /tmp/echo-bundle.XXXXXX.json)"

  echo "[SMOKE] export bundle (eo)"
  if ! out="$(run_node export --type eo --out "$BUNDLE_FILE" 2>&1)"; then
    echo "$out"
    print_fail "export failed"
    return 1
  fi
  print_pass "export bundle"

  echo "[SMOKE] reset storage before import"
  rm -rf "$STORAGE_DIR"
  mkdir -p "$STORAGE_DIR"
  touch "$STORAGE_DIR/.gitkeep"
  print_pass "storage reset"

  echo "[SMOKE] import bundle"
  if ! out="$(run_node import --file "$BUNDLE_FILE" 2>&1)"; then
    echo "$out"
    print_fail "import failed"
    return 1
  fi
  print_pass "import bundle"

  echo "[SMOKE] verify imported object"
  import_check="$(run_node search --type eo --field eo_id --equals 'echo.eo.sample.v1' 2>&1)"
  if ! grep -q '^count: 1$' <<<"$import_check"; then
    echo "$import_check"
    print_fail "import verification failed"
    return 1
  fi
  print_pass "import verified"

  return 0
}

http_prereqs_available() {
  if ! command -v curl >/dev/null 2>&1; then
    return 1
  fi
  python3 - <<'PY' >/dev/null 2>&1
import importlib
for m in ("fastapi", "uvicorn"):
    importlib.import_module(m)
PY
}

wait_for_health() {
  local tries=60
  for _ in $(seq 1 "$tries"); do
    if curl -fsS "http://$SERVER_HOST:$SERVER_PORT/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  return 1
}

run_http_smoke() {
  if ! http_prereqs_available; then
    local msg="HTTP smoke skipped: missing curl and/or Python deps (fastapi, uvicorn)."
    if [[ "$SMOKE_REQUIRE_HTTP" == "1" ]]; then
      print_fail "$msg Set deps and rerun with SMOKE_REQUIRE_HTTP=1."
      return 1
    fi
    print_skip "$msg Set SMOKE_REQUIRE_HTTP=1 to make this mandatory."
    return 0
  fi

  echo "[SMOKE] start HTTP server"
  python3 "$SERVER" \
    --host "$SERVER_HOST" \
    --port "$SERVER_PORT" \
    --manifest "$MANIFEST" \
    --schemas-dir "$SCHEMAS_DIR" \
    >"$SERVER_LOG" 2>&1 &
  SERVER_PID=$!

  echo "[SMOKE] wait for /health"
  if ! wait_for_health; then
    tail -n 100 "$SERVER_LOG" || true
    print_fail "server did not become healthy"
    return 1
  fi
  print_pass "server health"

  HTTP_PAYLOAD="$(mktemp /tmp/echo-http-payload.XXXXXX.json)"
  python3 - "$SAMPLE_DIR/eo.sample.json" "$HTTP_PAYLOAD" <<'PY'
import json
import sys

in_path, out_path = sys.argv[1], sys.argv[2]
with open(in_path, "r", encoding="utf-8") as f:
    eo = json.load(f)
eo["eo_id"] = "echo.eo.http.smoke.v1"
payload = {"type": "eo", "object_json": eo, "skip_signature": False}
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)
PY

  echo "[SMOKE] HTTP POST /objects"
  http_code="$(curl -sS -o "$HTTP_POST_OUT" -w '%{http_code}' \
    -X POST "http://$SERVER_HOST:$SERVER_PORT/objects" \
    -H 'Content-Type: application/json' \
    --data-binary "@$HTTP_PAYLOAD")"
  if [[ "$http_code" != "200" ]]; then
    cat "$HTTP_POST_OUT"
    print_fail "HTTP POST /objects failed with status $http_code"
    return 1
  fi
  print_pass "HTTP POST /objects"

  echo "[SMOKE] HTTP GET /objects/{type}/{id}"
  http_code="$(curl -sS -o "$HTTP_OBJ_OUT" -w '%{http_code}' \
    "http://$SERVER_HOST:$SERVER_PORT/objects/eo/echo.eo.http.smoke.v1")"
  if [[ "$http_code" != "200" ]]; then
    cat "$HTTP_OBJ_OUT"
    print_fail "HTTP GET /objects/{type}/{id} failed with status $http_code"
    return 1
  fi
  if ! python3 - "$HTTP_OBJ_OUT" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    payload = json.load(f)
if payload.get("id") != "echo.eo.http.smoke.v1":
    raise SystemExit(1)
PY
  then
    cat "$HTTP_OBJ_OUT"
    print_fail "HTTP GET /objects returned unexpected payload"
    return 1
  fi
  print_pass "HTTP GET /objects/{type}/{id}"

  echo "[SMOKE] HTTP GET /search rank=true"
  http_code="$(curl -sS -o "$HTTP_SEARCH_OUT" -w '%{http_code}' \
    "http://$SERVER_HOST:$SERVER_PORT/search?type=eo&field=eo_id&op=contains&value=echo.eo.http&rank=true")"
  if [[ "$http_code" != "200" ]]; then
    cat "$HTTP_SEARCH_OUT"
    print_fail "HTTP GET /search failed with status $http_code"
    return 1
  fi
  if ! python3 - "$HTTP_SEARCH_OUT" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    payload = json.load(f)
if int(payload.get("count", 0)) < 1:
    raise SystemExit(1)
PY
  then
    cat "$HTTP_SEARCH_OUT"
    print_fail "HTTP GET /search returned empty results"
    return 1
  fi
  print_pass "HTTP GET /search rank=true"

  echo "[SMOKE] HTTP GET /bundles/export"
  http_code="$(curl -sS -o "$HTTP_BUNDLE_OUT" -w '%{http_code}' \
    "http://$SERVER_HOST:$SERVER_PORT/bundles/export?type=eo")"
  if [[ "$http_code" != "200" ]]; then
    cat "$HTTP_BUNDLE_OUT"
    print_fail "HTTP GET /bundles/export failed with status $http_code"
    return 1
  fi
  if ! python3 - "$HTTP_BUNDLE_OUT" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    payload = json.load(f)
objs = payload.get("objects")
if not isinstance(objs, list) or len(objs) < 1:
    raise SystemExit(1)
PY
  then
    cat "$HTTP_BUNDLE_OUT"
    print_fail "HTTP GET /bundles/export returned invalid bundle"
    return 1
  fi
  print_pass "HTTP GET /bundles/export"

  HTTP_BUNDLE_IMPORT_PAYLOAD="$(mktemp /tmp/echo-http-bundle-import.XXXXXX.json)"
  python3 - "$HTTP_BUNDLE_OUT" "$HTTP_BUNDLE_IMPORT_PAYLOAD" <<'PY'
import json
import sys
bundle_path, out_path = sys.argv[1], sys.argv[2]
with open(bundle_path, "r", encoding="utf-8") as f:
    bundle = json.load(f)
payload = {"bundle": bundle, "skip_signature": False}
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)
PY

  echo "[SMOKE] HTTP POST /bundles/import"
  http_code="$(curl -sS -o "$HTTP_POST_OUT" -w '%{http_code}' \
    -X POST "http://$SERVER_HOST:$SERVER_PORT/bundles/import" \
    -H 'Content-Type: application/json' \
    --data-binary "@$HTTP_BUNDLE_IMPORT_PAYLOAD")"
  if [[ "$http_code" != "200" ]]; then
    cat "$HTTP_POST_OUT"
    print_fail "HTTP POST /bundles/import failed with status $http_code"
    return 1
  fi
  print_pass "HTTP POST /bundles/import"

  echo "[SMOKE] HTTP GET /stats"
  http_code="$(curl -sS -o "$HTTP_STATS_OUT" -w '%{http_code}' \
    "http://$SERVER_HOST:$SERVER_PORT/stats")"
  if [[ "$http_code" != "200" ]]; then
    cat "$HTTP_STATS_OUT"
    print_fail "HTTP GET /stats failed with status $http_code"
    return 1
  fi
  if ! python3 - "$HTTP_STATS_OUT" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    payload = json.load(f)
counts = payload.get("objects", {}).get("counts", {})
if int(counts.get("eo", 0)) < 1:
    raise SystemExit(1)
PY
  then
    cat "$HTTP_STATS_OUT"
    print_fail "HTTP GET /stats returned unexpected counts"
    return 1
  fi
  print_pass "HTTP GET /stats"

  cleanup
  return 0
}

run_cli_smoke
run_http_smoke

echo "ALL SMOKE TESTS PASSED"
