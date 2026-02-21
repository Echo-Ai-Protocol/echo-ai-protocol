#!/usr/bin/env python3
"""Update external AI compatibility matrix from a feedback report."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _gate_value(value: Any) -> str:
    return "PASS" if bool(value) else "FAIL"


def _blocking_issue(payload: Dict[str, Any]) -> str:
    failures = payload.get("failures")
    if not isinstance(failures, list) or not failures:
        return "-"
    first = failures[0]
    if not isinstance(first, dict):
        return "-"
    category = str(first.get("category", "UNKNOWN"))
    endpoint = str(first.get("endpoint", "unknown-endpoint"))
    return f"{category} at {endpoint}"


def _row_from_report(payload: Dict[str, Any]) -> str:
    checkpoints = payload.get("checkpoints", {})
    if not isinstance(checkpoints, dict):
        checkpoints = {}

    integration_id = str(payload.get("integration_id", "unknown"))
    agent_name = str(payload.get("agent_name", "TBD"))
    lane = str(payload.get("lane", "TBD"))
    protocol_version = str(payload.get("protocol_version", "ECHO/1.0"))
    status = str(payload.get("overall_status", "Provisional"))
    last_verified = str(payload.get("submitted_at_utc", "TBD"))

    gate_1 = _gate_value(checkpoints.get("bootstrap_ok"))
    gate_2 = _gate_value(checkpoints.get("store_eo_ok"))
    gate_3 = _gate_value(checkpoints.get("search_ranked_ok"))
    gate_4 = _gate_value(checkpoints.get("store_rr_ok"))
    gate_5 = _gate_value(checkpoints.get("full_loop_repeated_ok"))

    blocking_issue = _blocking_issue(payload) if status == "Blocked" else "-"

    return (
        f"| {integration_id} | {agent_name} | {lane} | {protocol_version} | "
        f"{gate_1} | {gate_2} | {gate_3} | {gate_4} | {gate_5} | "
        f"{status} | {last_verified} | {blocking_issue} |"
    )


def update_matrix(matrix_path: Path, report: Dict[str, Any]) -> bool:
    lines = matrix_path.read_text(encoding="utf-8").splitlines()
    integration_id = str(report.get("integration_id", "")).strip()
    if not integration_id:
        raise ValueError("report missing integration_id")

    new_row = _row_from_report(report)
    pattern = re.compile(r"^\|\s*" + re.escape(integration_id) + r"\s*\|")

    replaced = False
    for idx, line in enumerate(lines):
        if pattern.match(line):
            lines[idx] = new_row
            replaced = True
            break

    if not replaced:
        insert_at = None
        for idx, line in enumerate(lines):
            if line.strip() == "## Update Policy":
                insert_at = idx
                break
        if insert_at is None:
            raise ValueError("Could not find '## Update Policy' section in matrix file")

        # Insert before the update policy section, after the last existing table row.
        row_block_end = insert_at
        while row_block_end > 0 and lines[row_block_end - 1].startswith("|"):
            row_block_end -= 1

        # If we did not find table rows directly above, append before policy anyway.
        target_idx = insert_at
        if row_block_end < insert_at:
            target_idx = insert_at
        lines.insert(target_idx, new_row)

    matrix_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return replaced


def parse_args() -> argparse.Namespace:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Sync compatibility matrix row from feedback report")
    parser.add_argument(
        "--report",
        required=True,
        help="Path to feedback report JSON (echo.integration.feedback.v1)",
    )
    parser.add_argument(
        "--matrix",
        default=str(repo / "docs" / "EXTERNAL_AI_COMPATIBILITY_MATRIX.md"),
        help="Path to compatibility matrix markdown file",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = Path(args.report).expanduser().resolve()
    matrix_path = Path(args.matrix).expanduser().resolve()

    if not report_path.exists():
        print(f"FAIL: report not found: {report_path}")
        return 2
    if not matrix_path.exists():
        print(f"FAIL: matrix not found: {matrix_path}")
        return 2

    report = _load_json(report_path)
    replaced = update_matrix(matrix_path=matrix_path, report=report)
    action = "updated" if replaced else "inserted"
    print(f"OK: {action} integration row in {matrix_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
