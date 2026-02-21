#!/usr/bin/env python3
"""Zero-touch external AI onboarding gate runner.

Runs repeatable integration checks against a running ECHO reference node and
emits a machine-readable report for compatibility decisions.

This tool also reads archived history for the same integration id so status can
progress from Provisional to Compatible across multiple days.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _utc_day(timestamp: str) -> str | None:
    if not isinstance(timestamp, str) or len(timestamp) < 10:
        return None
    day = timestamp[:10]
    if len(day) == 10 and day[4] == "-" and day[7] == "-":
        return day
    return None


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _with_unique_id(obj: Dict[str, Any], field: str, prefix: str, run_idx: int) -> Dict[str, Any]:
    out = dict(obj)
    stamp = int(time.time() * 1000)
    out[field] = f"{prefix}.r{run_idx}.{stamp}"
    out["created_at"] = _utc_now()
    return out


def _failure(
    failure_id: str,
    category: str,
    severity: str,
    endpoint: str,
    expected: str,
    actual: str,
    request_payload: str,
) -> Dict[str, Any]:
    return {
        "failure_id": failure_id,
        "category": category,
        "severity": severity,
        "endpoint": endpoint,
        "request_payload": request_payload,
        "expected_behavior": expected,
        "actual_behavior": actual,
        "reproduction_steps": [
            "run tools/zero_touch_autogate.py against the same base URL",
            "inspect emitted gate report and endpoint response payload",
        ],
    }


def _load_client_class() -> Any:
    repo = _repo_root()
    sdk_path = repo / "sdk" / "python"
    if str(sdk_path) not in sys.path:
        sys.path.insert(0, str(sdk_path))
    from echo_sdk import EchoApiError, EchoClient  # type: ignore

    return EchoClient, EchoApiError


def _run_single_flow(
    client: Any,
    eo_sample: Dict[str, Any],
    rr_sample: Dict[str, Any],
    integration_id: str,
    run_idx: int,
    skip_signature: bool,
) -> Tuple[bool, Dict[str, bool], List[Dict[str, Any]], str | None]:
    gates = {
        "health_ok": False,
        "bootstrap_ok": False,
        "store_eo_ok": False,
        "search_ranked_ok": False,
        "store_rr_ok": False,
    }
    failures: List[Dict[str, Any]] = []
    created_eo_id: str | None = None

    try:
        health = client.wait_for_health(max_attempts=10, delay_seconds=0.2)
        if health.get("status") == "ok":
            gates["health_ok"] = True
        else:
            failures.append(
                _failure(
                    failure_id=f"R{run_idx}-F001",
                    category="NODE_RUNTIME",
                    severity="high",
                    endpoint="GET /health",
                    expected="status=ok",
                    actual=f"unexpected payload: {health}",
                    request_payload="{}",
                )
            )
            return False, gates, failures, created_eo_id
    except Exception as exc:
        failures.append(
            _failure(
                failure_id=f"R{run_idx}-F001",
                category="NODE_RUNTIME",
                severity="critical",
                endpoint="GET /health",
                expected="HTTP 200",
                actual=str(exc),
                request_payload="{}",
            )
        )
        return False, gates, failures, created_eo_id

    try:
        bootstrap = client.bootstrap()
        object_types = bootstrap.get("object_types", [])
        if isinstance(object_types, list) and "eo" in object_types and "rr" in object_types:
            gates["bootstrap_ok"] = True
        else:
            failures.append(
                _failure(
                    failure_id=f"R{run_idx}-F002",
                    category="API_CONTRACT_MISMATCH",
                    severity="high",
                    endpoint="GET /registry/bootstrap",
                    expected="object_types includes eo and rr",
                    actual=f"payload object_types={object_types}",
                    request_payload="{}",
                )
            )
            return False, gates, failures, created_eo_id
    except Exception as exc:
        failures.append(
            _failure(
                failure_id=f"R{run_idx}-F002",
                category="API_CONTRACT_MISMATCH",
                severity="critical",
                endpoint="GET /registry/bootstrap",
                expected="HTTP 200 with bootstrap payload",
                actual=str(exc),
                request_payload="{}",
            )
        )
        return False, gates, failures, created_eo_id

    eo = _with_unique_id(eo_sample, "eo_id", f"echo.eo.external.{integration_id}", run_idx)
    created_eo_id = eo["eo_id"]
    try:
        stored_eo = client.store_eo(eo, skip_signature=skip_signature)
        if stored_eo.get("id") == created_eo_id:
            gates["store_eo_ok"] = True
        else:
            failures.append(
                _failure(
                    failure_id=f"R{run_idx}-F003",
                    category="API_CONTRACT_MISMATCH",
                    severity="high",
                    endpoint="POST /objects",
                    expected="stored id equals EO id",
                    actual=f"stored payload={stored_eo}",
                    request_payload=json.dumps({"type": "eo", "object_json": eo}, ensure_ascii=False),
                )
            )
            return False, gates, failures, created_eo_id
    except Exception as exc:
        failures.append(
            _failure(
                failure_id=f"R{run_idx}-F003",
                category="SCHEMA_MISMATCH",
                severity="high",
                endpoint="POST /objects",
                expected="HTTP 200 stored",
                actual=str(exc),
                request_payload=json.dumps({"type": "eo", "object_json": eo}, ensure_ascii=False),
            )
        )
        return False, gates, failures, created_eo_id

    try:
        search = client.search_ranked_eo(eo_id_contains=created_eo_id, limit=5, explain=True)
        count = int(search.get("count", 0))
        results = search.get("results", [])
        has_explain = bool(results and isinstance(results[0], dict) and "score_explain" in results[0])
        if count >= 1 and has_explain:
            gates["search_ranked_ok"] = True
        else:
            failures.append(
                _failure(
                    failure_id=f"R{run_idx}-F004",
                    category="RANKING_EXPLAIN_GAP",
                    severity="high",
                    endpoint="GET /search",
                    expected="count >= 1 and first result contains score_explain",
                    actual=f"count={count}, first={results[0] if results else None}",
                    request_payload=f"type=eo&field=eo_id&op=contains&value={created_eo_id}&rank=true&explain=true",
                )
            )
            return False, gates, failures, created_eo_id
    except Exception as exc:
        failures.append(
            _failure(
                failure_id=f"R{run_idx}-F004",
                category="API_CONTRACT_MISMATCH",
                severity="high",
                endpoint="GET /search",
                expected="HTTP 200 ranked response",
                actual=str(exc),
                request_payload=f"type=eo&field=eo_id&op=contains&value={created_eo_id}&rank=true&explain=true",
            )
        )
        return False, gates, failures, created_eo_id

    rr = _with_unique_id(rr_sample, "rr_id", f"echo.rr.external.{integration_id}", run_idx)
    rr["target_eo_id"] = created_eo_id
    try:
        stored_rr = client.store_rr(rr, skip_signature=skip_signature)
        if stored_rr.get("id") == rr["rr_id"]:
            gates["store_rr_ok"] = True
        else:
            failures.append(
                _failure(
                    failure_id=f"R{run_idx}-F005",
                    category="API_CONTRACT_MISMATCH",
                    severity="high",
                    endpoint="POST /objects",
                    expected="stored RR id equals rr_id",
                    actual=f"stored payload={stored_rr}",
                    request_payload=json.dumps({"type": "rr", "object_json": rr}, ensure_ascii=False),
                )
            )
            return False, gates, failures, created_eo_id
    except Exception as exc:
        failures.append(
            _failure(
                failure_id=f"R{run_idx}-F005",
                category="SCHEMA_MISMATCH",
                severity="high",
                endpoint="POST /objects",
                expected="HTTP 200 RR stored",
                actual=str(exc),
                request_payload=json.dumps({"type": "rr", "object_json": rr}, ensure_ascii=False),
            )
        )
        return False, gates, failures, created_eo_id

    return True, gates, failures, created_eo_id


def _status_from_checkpoints(
    checkpoints: Dict[str, bool],
    successful_runs: int,
    runs_required: int,
    distinct_days: int,
    compatible_min_days: int,
) -> str:
    critical = ("health_ok", "bootstrap_ok", "store_eo_ok", "search_ranked_ok", "store_rr_ok")
    if not all(checkpoints.get(k, False) for k in critical):
        return "Blocked"
    if successful_runs >= runs_required and distinct_days >= compatible_min_days:
        return "Compatible"
    return "Provisional"


def _collect_history_reports(
    integration_id: str,
    history_dir: Path | None,
    explicit_reports: List[str],
    current_output_path: Path,
) -> List[Dict[str, Any]]:
    paths: List[Path] = []
    seen: Set[str] = set()

    def add_path(p: Path) -> None:
        key = str(p.resolve())
        if key in seen:
            return
        seen.add(key)
        paths.append(p)

    if history_dir is not None and history_dir.exists():
        for p in sorted(history_dir.glob(f"zero_touch_{integration_id}_*.json")):
            add_path(p)

    if current_output_path.exists():
        add_path(current_output_path)

    for raw in explicit_reports:
        p = Path(raw).expanduser().resolve()
        if p.exists():
            add_path(p)

    reports: List[Dict[str, Any]] = []
    for p in paths:
        try:
            payload = _load_json(p)
        except Exception:
            continue
        if str(payload.get("integration_id", "")).strip() != integration_id:
            continue
        reports.append(payload)
    return reports


def _history_success_stats(reports: List[Dict[str, Any]]) -> Tuple[int, Set[str]]:
    successful_runs = 0
    success_days: Set[str] = set()

    for report in reports:
        kpi = report.get("kpi_snapshot")
        if not isinstance(kpi, dict):
            continue

        runs_successful = max(0, _as_int(kpi.get("runs_successful")))
        successful_runs += runs_successful

        gate_meta = report.get("gate_meta")
        if isinstance(gate_meta, dict):
            for key in ("success_utc_dates_aggregate", "success_utc_dates_current_run"):
                values = gate_meta.get(key)
                if not isinstance(values, list):
                    continue
                for value in values:
                    day = _utc_day(str(value))
                    if day is not None:
                        success_days.add(day)

        # Fallback for older report shape with no date arrays.
        if runs_successful > 0:
            day = _utc_day(str(report.get("submitted_at_utc", "")))
            if day is not None:
                success_days.add(day)

    return successful_runs, success_days


def parse_args() -> argparse.Namespace:
    repo = _repo_root()
    parser = argparse.ArgumentParser(description="Run zero-touch onboarding gates for external AI integrations")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--integration-id", required=True, help="Integration identifier, e.g. ext-ai-001")
    parser.add_argument("--agent-name", default="TBD")
    parser.add_argument("--lane", choices=("code", "research", "ops"), default="code")
    parser.add_argument("--runs", type=int, default=3, help="How many full-loop runs to execute")
    parser.add_argument(
        "--compatible-min-days",
        type=int,
        default=2,
        help="Minimum distinct UTC days observed before status can be Compatible",
    )
    parser.add_argument("--skip-signature", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument(
        "--sample-dir",
        default=str(repo / "reference-node" / "sample_data"),
    )
    parser.add_argument(
        "--output",
        default=str(repo / "tools" / "out" / "zero_touch_latest.json"),
        help="Path to write gate report JSON",
    )
    parser.add_argument(
        "--history-dir",
        default=str(repo / "tools" / "out" / "history"),
        help="Directory with archived gate reports for this integration id",
    )
    parser.add_argument(
        "--history-report",
        action="append",
        default=[],
        help="Optional additional report path(s) to include in compatibility history",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    EchoClient, _ = _load_client_class()

    started_at = time.time()
    sample_dir = Path(args.sample_dir).expanduser().resolve()
    eo_sample = _load_json(sample_dir / "eo.sample.json")
    rr_sample = _load_json(sample_dir / "rr.sample.json")

    client = EchoClient(
        base_url=args.base_url,
        timeout_seconds=float(args.timeout_seconds),
        max_retries=int(args.retries),
    )

    output_path = Path(args.output).expanduser().resolve()
    history_dir = Path(args.history_dir).expanduser().resolve() if str(args.history_dir).strip() else None
    history_reports = _collect_history_reports(
        integration_id=args.integration_id,
        history_dir=history_dir,
        explicit_reports=list(args.history_report),
        current_output_path=output_path,
    )
    history_successful_runs, history_success_days = _history_success_stats(history_reports)

    runs = max(1, int(args.runs))
    checkpoints = {
        "health_ok": False,
        "bootstrap_ok": False,
        "store_eo_ok": False,
        "search_ranked_ok": False,
        "store_rr_ok": False,
        "full_loop_repeated_ok": False,
    }
    all_failures: List[Dict[str, Any]] = []
    run_summaries: List[Dict[str, Any]] = []
    successful_runs_current = 0
    success_days_current: Set[str] = set()
    first_success_time_minutes: float | None = None

    for run_idx in range(1, runs + 1):
        ok, run_gates, failures, eo_id = _run_single_flow(
            client=client,
            eo_sample=eo_sample,
            rr_sample=rr_sample,
            integration_id=args.integration_id,
            run_idx=run_idx,
            skip_signature=bool(args.skip_signature),
        )
        for key, val in run_gates.items():
            checkpoints[key] = checkpoints[key] or bool(val)
        if ok:
            successful_runs_current += 1
            success_days_current.add(time.strftime("%Y-%m-%d", time.gmtime()))
            if first_success_time_minutes is None:
                first_success_time_minutes = round((time.time() - started_at) / 60.0, 4)
        all_failures.extend(failures)
        run_summaries.append(
            {
                "run_index": run_idx,
                "ok": ok,
                "eo_id": eo_id,
                "failures_count": len(failures),
            }
        )

    aggregate_successful_runs = history_successful_runs + successful_runs_current
    aggregate_success_days = set(history_success_days) | set(success_days_current)
    distinct_days_aggregate = max(0, len(aggregate_success_days))
    compatible_min_days = max(1, int(args.compatible_min_days))

    checkpoints["full_loop_repeated_ok"] = (
        aggregate_successful_runs >= runs and distinct_days_aggregate >= compatible_min_days
    )

    status = _status_from_checkpoints(
        checkpoints=checkpoints,
        successful_runs=aggregate_successful_runs,
        runs_required=runs,
        distinct_days=distinct_days_aggregate,
        compatible_min_days=compatible_min_days,
    )

    report = {
        "report_version": "echo.integration.feedback.v1",
        "integration_id": args.integration_id,
        "agent_name": args.agent_name,
        "lane": args.lane,
        "protocol_version": "ECHO/1.0",
        "submitted_at_utc": _utc_now(),
        "environment": {
            "node_base_url": args.base_url,
            "sdk": "python-stdlib",
            "sdk_version": "echo_sdk.client",
            "runtime": f"python{sys.version_info.major}.{sys.version_info.minor}",
        },
        "checkpoints": checkpoints,
        "kpi_snapshot": {
            "first_success_time_minutes": first_success_time_minutes,
            "runs_total": runs,
            "runs_successful": successful_runs_current,
            "external_eo_published": successful_runs_current,
            "external_rr_published": successful_runs_current,
        },
        "failures": all_failures,
        "suggestions": [
            "Promote to Compatible only after at least 2 distinct UTC days with green runs.",
            "Keep weekly revalidation to catch contract regressions early.",
        ],
        "overall_status": status,
        "gate_meta": {
            "compatible_min_days": compatible_min_days,
            "distinct_utc_days_observed_current_run": len(success_days_current),
            "distinct_utc_days_observed_aggregate": distinct_days_aggregate,
            "runs_required_for_repeat_gate": runs,
            "history_reports_considered": len(history_reports),
            "history_runs_successful": history_successful_runs,
            "aggregate_runs_successful": aggregate_successful_runs,
            "success_utc_dates_current_run": sorted(success_days_current),
            "success_utc_dates_aggregate": sorted(aggregate_success_days),
            "run_summaries": run_summaries,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    archived_path: Path | None = None
    if history_dir is not None:
        history_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        archived_path = history_dir / f"zero_touch_{args.integration_id}_{stamp}.json"
        archived_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {output_path}")
    if archived_path is not None:
        print(f"ARCHIVED: {archived_path}")
    print(f"STATUS: {status}")
    print(f"RUNS_CURRENT: {successful_runs_current}/{runs}")
    print(f"RUNS_AGGREGATE: {aggregate_successful_runs}")
    print(f"DISTINCT_UTC_DAYS_AGGREGATE: {distinct_days_aggregate}")
    return 0 if status != "Blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
