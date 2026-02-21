#!/usr/bin/env python3
"""Validate external integration pilot feedback JSON payloads."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_TOP_LEVEL = {
    "report_version",
    "integration_id",
    "agent_name",
    "lane",
    "protocol_version",
    "submitted_at_utc",
    "environment",
    "checkpoints",
    "kpi_snapshot",
    "failures",
    "suggestions",
    "overall_status",
}

REQUIRED_CHECKPOINTS = {
    "health_ok",
    "bootstrap_ok",
    "store_eo_ok",
    "search_ranked_ok",
    "store_rr_ok",
    "full_loop_repeated_ok",
}

ALLOWED_LANES = {"code", "research", "ops"}
ALLOWED_STATUSES = {"Provisional", "Compatible", "Blocked"}
ALLOWED_FAILURE_SEVERITIES = {"low", "medium", "high", "critical"}
ALLOWED_FAILURE_CATEGORIES = {
    "SCHEMA_MISMATCH",
    "API_CONTRACT_MISMATCH",
    "RANKING_EXPLAIN_GAP",
    "NODE_RUNTIME",
    "OTHER",
}


def _err(errors: List[str], message: str) -> None:
    errors.append(message)


def validate_payload(payload: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    missing = sorted(REQUIRED_TOP_LEVEL - set(payload.keys()))
    if missing:
        _err(errors, f"missing top-level keys: {', '.join(missing)}")

    lane = payload.get("lane")
    if lane not in ALLOWED_LANES:
        _err(errors, f"lane must be one of {sorted(ALLOWED_LANES)}")

    status = payload.get("overall_status")
    if status not in ALLOWED_STATUSES:
        _err(errors, f"overall_status must be one of {sorted(ALLOWED_STATUSES)}")

    checkpoints = payload.get("checkpoints")
    if not isinstance(checkpoints, dict):
        _err(errors, "checkpoints must be an object")
    else:
        missing_cp = sorted(REQUIRED_CHECKPOINTS - set(checkpoints.keys()))
        if missing_cp:
            _err(errors, f"missing checkpoint keys: {', '.join(missing_cp)}")
        for key, value in checkpoints.items():
            if not isinstance(value, bool):
                _err(errors, f"checkpoint '{key}' must be boolean")

    failures = payload.get("failures")
    if not isinstance(failures, list):
        _err(errors, "failures must be an array")
    else:
        for idx, failure in enumerate(failures):
            if not isinstance(failure, dict):
                _err(errors, f"failures[{idx}] must be an object")
                continue
            for field in (
                "failure_id",
                "category",
                "severity",
                "endpoint",
                "expected_behavior",
                "actual_behavior",
                "reproduction_steps",
            ):
                if field not in failure:
                    _err(errors, f"failures[{idx}] missing field '{field}'")
            category = failure.get("category")
            if category not in ALLOWED_FAILURE_CATEGORIES:
                _err(
                    errors,
                    f"failures[{idx}].category must be one of {sorted(ALLOWED_FAILURE_CATEGORIES)}",
                )
            severity = failure.get("severity")
            if severity not in ALLOWED_FAILURE_SEVERITIES:
                _err(
                    errors,
                    f"failures[{idx}].severity must be one of {sorted(ALLOWED_FAILURE_SEVERITIES)}",
                )
            if not isinstance(failure.get("reproduction_steps"), list):
                _err(errors, f"failures[{idx}].reproduction_steps must be an array")

    suggestions = payload.get("suggestions")
    if not isinstance(suggestions, list):
        _err(errors, "suggestions must be an array")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 tools/pilot_feedback_lint.py <feedback.json>")
        return 2

    path = Path(sys.argv[1]).expanduser().resolve()
    if not path.exists():
        print(f"FAIL: file not found: {path}")
        return 2

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: invalid JSON: {exc}")
        return 2

    if not isinstance(payload, dict):
        print("FAIL: root must be a JSON object")
        return 2

    errors = validate_payload(payload)
    if errors:
        print("FAIL: pilot feedback validation errors")
        for msg in errors:
            print(f" - {msg}")
        return 2

    print("OK: pilot feedback payload is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
