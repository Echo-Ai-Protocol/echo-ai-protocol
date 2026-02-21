#!/usr/bin/env python3
"""Aggregate external AI onboarding KPIs from zero-touch reports."""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from statistics import median
from typing import Any, Dict, List


def _load_report(path: Path) -> Dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    if str(payload.get("report_version", "")) != "echo.integration.feedback.v1":
        return None
    if "integration_id" not in payload:
        return None
    return payload


def _report_sort_key(report: Dict[str, Any]) -> str:
    return str(report.get("submitted_at_utc", ""))


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _find_reports(paths: List[str], globs: List[str]) -> List[Path]:
    found: Dict[str, Path] = {}
    for raw in paths:
        p = Path(raw).expanduser().resolve()
        if p.exists():
            found[str(p)] = p
    for pattern in globs:
        for raw in glob.glob(pattern):
            rp = Path(raw).expanduser().resolve()
            if rp.exists():
                found[str(rp)] = rp
    return sorted(found.values())


def parse_args() -> argparse.Namespace:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Build external AI KPI summary from zero-touch reports")
    parser.add_argument(
        "--report",
        action="append",
        default=[],
        help="Explicit report path(s)",
    )
    parser.add_argument(
        "--glob",
        action="append",
        default=[
            str(repo / "tools" / "out" / "zero_touch_*.json"),
            str(repo / "tools" / "out" / "history" / "zero_touch_*.json"),
        ],
        help="Glob pattern(s) for report discovery",
    )
    parser.add_argument(
        "--output",
        default=str(repo / "tools" / "out" / "external_ai_kpi_summary.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = _find_reports(paths=list(args.report), globs=list(args.glob))

    reports: List[Dict[str, Any]] = []
    for p in paths:
        payload = _load_report(p)
        if payload is None:
            continue
        payload["_source_path"] = str(p)
        reports.append(payload)

    latest_by_integration: Dict[str, Dict[str, Any]] = {}
    for report in reports:
        integration_id = str(report.get("integration_id"))
        prev = latest_by_integration.get(integration_id)
        if prev is None or _report_sort_key(report) >= _report_sort_key(prev):
            latest_by_integration[integration_id] = report

    latest_reports = sorted(latest_by_integration.values(), key=_report_sort_key, reverse=True)
    status_counts = {"Compatible": 0, "Provisional": 0, "Blocked": 0}
    failure_categories: Dict[str, int] = {}
    first_success_values: List[float] = []
    runs_total = 0
    runs_successful = 0
    external_eo_published = 0
    external_rr_published = 0

    for report in latest_reports:
        status = str(report.get("overall_status", "Provisional"))
        if status not in status_counts:
            status = "Provisional"
        status_counts[status] += 1

        kpi = report.get("kpi_snapshot")
        if isinstance(kpi, dict):
            runs_total += max(0, _as_int(kpi.get("runs_total")))
            runs_successful += max(0, _as_int(kpi.get("runs_successful")))
            external_eo_published += max(0, _as_int(kpi.get("external_eo_published")))
            external_rr_published += max(0, _as_int(kpi.get("external_rr_published")))
            first_success = kpi.get("first_success_time_minutes")
            if isinstance(first_success, (int, float)):
                first_success_values.append(float(first_success))

        failures = report.get("failures")
        if isinstance(failures, list):
            for failure in failures:
                if not isinstance(failure, dict):
                    continue
                category = str(failure.get("category", "OTHER"))
                failure_categories[category] = failure_categories.get(category, 0) + 1

    integrations_total = len(latest_reports)
    compatible = status_counts["Compatible"]
    compatibility_pass_rate = (compatible / integrations_total) if integrations_total > 0 else 0.0
    first_success_median = median(first_success_values) if first_success_values else None

    summary = {
        "version": "echo.external.kpi.summary.v1",
        "reports_discovered": len(reports),
        "integrations_total": integrations_total,
        "integrations_active": integrations_total,
        "status_counts": status_counts,
        "compatibility_pass_rate": round(float(compatibility_pass_rate), 6),
        "kpis": {
            "first_success_time_minutes_median": first_success_median,
            "runs_total": runs_total,
            "runs_successful": runs_successful,
            "external_eo_published": external_eo_published,
            "external_rr_published": external_rr_published,
        },
        "top_failure_categories": sorted(
            ({"category": k, "count": v} for k, v in failure_categories.items()),
            key=lambda item: (-int(item["count"]), str(item["category"])),
        )[:10],
        "latest_reports": [
            {
                "integration_id": str(r.get("integration_id")),
                "overall_status": str(r.get("overall_status")),
                "submitted_at_utc": str(r.get("submitted_at_utc")),
                "source_path": str(r.get("_source_path")),
            }
            for r in latest_reports
        ],
    }

    out_path = Path(args.output).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"INTEGRATIONS: {integrations_total}")
    print(f"COMPATIBILITY_PASS_RATE: {summary['compatibility_pass_rate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
