#!/usr/bin/env python3
"""Run a compact external AI onboarding operations cycle."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _run_step(name: str, cmd: List[str], cwd: Path, required: bool = True) -> Dict[str, Any]:
    started = time.monotonic()
    print(f"[CYCLE] {name}")
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    duration_sec = round(time.monotonic() - started, 3)

    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")

    return {
        "name": name,
        "required": required,
        "status": "ok" if proc.returncode == 0 else "failed",
        "return_code": int(proc.returncode),
        "duration_sec": duration_sec,
        "command": cmd,
    }


def _skipped_step(name: str, reason: str) -> Dict[str, Any]:
    return {
        "name": name,
        "required": False,
        "status": "skipped",
        "return_code": None,
        "duration_sec": 0.0,
        "command": [],
        "note": reason,
    }


def parse_args() -> argparse.Namespace:
    repo = _repo_root()
    parser = argparse.ArgumentParser(description="Run one external AI onboarding operations cycle")
    parser.add_argument("--python-bin", default=sys.executable)
    parser.add_argument("--integration-id", required=True, help="Integration id, e.g. ext-ai-001")
    parser.add_argument("--agent-name", required=True)
    parser.add_argument("--lane", choices=("code", "research", "ops"), required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--compatible-min-days", type=int, default=2)
    parser.add_argument("--skip-signature", action="store_true")
    parser.add_argument("--skip-gate", action="store_true", help="Skip live zero-touch gate step")

    parser.add_argument(
        "--candidate-input",
        default=str(repo / "examples" / "integration" / "candidate_pipeline.template.csv"),
    )
    parser.add_argument(
        "--shortlist-out",
        default=str(repo / "tools" / "out" / "candidate_shortlist.json"),
    )
    parser.add_argument("--report-out", default="")
    parser.add_argument(
        "--matrix",
        default=str(repo / "docs" / "EXTERNAL_AI_COMPATIBILITY_MATRIX.md"),
    )
    parser.add_argument(
        "--outreach-template",
        default=str(repo / "examples" / "integration" / "outreach_message.template.md"),
    )
    parser.add_argument("--outreach-out", default="")
    parser.add_argument(
        "--history-dir",
        default=str(repo / "tools" / "out" / "history"),
    )
    parser.add_argument(
        "--kpi-out",
        default=str(repo / "tools" / "out" / "external_ai_kpi_summary.json"),
    )
    parser.add_argument(
        "--kpi-glob",
        action="append",
        default=[],
        help="Optional report glob(s) for KPI summary; when set, defaults are disabled",
    )
    parser.add_argument("--summary-out", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = _repo_root()

    report_out = Path(args.report_out).expanduser().resolve() if args.report_out else (
        repo / "tools" / "out" / f"zero_touch_{args.integration_id}.json"
    )
    outreach_out = Path(args.outreach_out).expanduser().resolve() if args.outreach_out else (
        repo / "tools" / "out" / f"outreach_message_{args.integration_id}.md"
    )
    summary_out = Path(args.summary_out).expanduser().resolve() if args.summary_out else (
        repo / "tools" / "out" / f"external_ai_cycle_{args.integration_id}.json"
    )
    shortlist_out = Path(args.shortlist_out).expanduser().resolve()
    matrix_path = Path(args.matrix).expanduser().resolve()
    candidate_input = Path(args.candidate_input).expanduser().resolve()
    outreach_template = Path(args.outreach_template).expanduser().resolve()
    history_dir = Path(args.history_dir).expanduser().resolve()
    kpi_out = Path(args.kpi_out).expanduser().resolve()

    py = str(args.python_bin)
    steps: List[Dict[str, Any]] = []

    steps.append(
        _run_step(
            name="candidate-shortlist",
            cmd=[
                py,
                str(repo / "tools" / "candidate_shortlist.py"),
                "--input",
                str(candidate_input),
                "--output",
                str(shortlist_out),
                "--top-n",
                "10",
                "--min-code",
                "3",
                "--min-research",
                "3",
                "--min-ops",
                "2",
            ],
            cwd=repo,
        )
    )

    if args.skip_gate:
        steps.append(_skipped_step("zero-touch-gate", "skip-gate enabled"))
    else:
        gate_cmd = [
            py,
            str(repo / "tools" / "zero_touch_autogate.py"),
            "--base-url",
            str(args.base_url),
            "--integration-id",
            str(args.integration_id),
            "--agent-name",
            str(args.agent_name),
            "--lane",
            str(args.lane),
            "--runs",
            str(max(1, int(args.runs))),
            "--compatible-min-days",
            str(max(1, int(args.compatible_min_days))),
            "--history-dir",
            str(history_dir),
            "--output",
            str(report_out),
        ]
        if args.skip_signature:
            gate_cmd.append("--skip-signature")
        steps.append(_run_step(name="zero-touch-gate", cmd=gate_cmd, cwd=repo))

    if report_out.exists():
        steps.append(
            _run_step(
                name="pilot-feedback-lint",
                cmd=[py, str(repo / "tools" / "pilot_feedback_lint.py"), str(report_out)],
                cwd=repo,
            )
        )
        steps.append(
            _run_step(
                name="sync-compatibility-matrix",
                cmd=[
                    py,
                    str(repo / "tools" / "update_compatibility_matrix.py"),
                    "--report",
                    str(report_out),
                    "--matrix",
                    str(matrix_path),
                ],
                cwd=repo,
            )
        )
    elif args.skip_gate:
        steps.append(_skipped_step("pilot-feedback-lint", f"report not found: {report_out}"))
        steps.append(_skipped_step("sync-compatibility-matrix", f"report not found: {report_out}"))
    else:
        steps.append(
            {
                "name": "report-presence",
                "required": True,
                "status": "failed",
                "return_code": 1,
                "duration_sec": 0.0,
                "command": [],
                "note": f"zero-touch report missing: {report_out}",
            }
        )

    steps.append(
        _run_step(
            name="outreach-message",
            cmd=[
                py,
                str(repo / "tools" / "render_outreach_message.py"),
                "--integration-id",
                str(args.integration_id),
                "--agent-name",
                str(args.agent_name),
                "--lane",
                str(args.lane),
                "--template",
                str(outreach_template),
                "--output",
                str(outreach_out),
            ],
            cwd=repo,
        )
    )

    kpi_cmd = [
        py,
        str(repo / "tools" / "external_ai_kpi_summary.py"),
        "--output",
        str(kpi_out),
    ]
    if report_out.exists():
        kpi_cmd.extend(["--report", str(report_out)])
    if args.kpi_glob:
        kpi_cmd.append("--no-default-globs")
        for pattern in args.kpi_glob:
            kpi_cmd.extend(["--glob", str(pattern)])
    steps.append(_run_step(name="external-kpi-summary", cmd=kpi_cmd, cwd=repo))

    required_failures = [s for s in steps if s.get("required") and s.get("status") != "ok"]
    overall_ok = len(required_failures) == 0
    status = "ok" if overall_ok else "failed"

    summary = {
        "version": "echo.external.cycle.v1",
        "executed_at_utc": _utc_now(),
        "integration_id": str(args.integration_id),
        "agent_name": str(args.agent_name),
        "lane": str(args.lane),
        "skip_gate": bool(args.skip_gate),
        "status": status,
        "overall_ok": overall_ok,
        "steps": steps,
        "artifacts": {
            "shortlist_out": str(shortlist_out),
            "report_out": str(report_out),
            "matrix": str(matrix_path),
            "outreach_out": str(outreach_out),
            "kpi_out": str(kpi_out),
        },
    }

    summary_out.parent.mkdir(parents=True, exist_ok=True)
    summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {summary_out}")
    print(f"CYCLE_STATUS: {status}")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
