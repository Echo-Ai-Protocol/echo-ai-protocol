#!/usr/bin/env python3
"""Run Coding/Research/Evaluator seed agents in order, optionally in a loop."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from common import create_client, default_output_dir, run_tag, stable_slug, utc_now, write_report


AGENTS: Tuple[Tuple[str, str], ...] = (
    ("coding", "coding_agent.py"),
    ("research", "research_agent.py"),
    ("evaluator", "evaluator_agent.py"),
)

ID_KEYS = ("request", "eo", "rr", "trace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ECHO seed agents in a deterministic closed loop")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--integration-id", default="ext-ai-seed")
    parser.add_argument("--skip-gate", action="store_true")
    parser.add_argument("--skip-signature", action="store_true")
    parser.add_argument("--run-tag", default="")
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--interval-seconds", type=float, default=0.0)
    parser.add_argument("--coding-agent-name", default="CodingAgent")
    parser.add_argument("--research-agent-name", default="ResearchAgent")
    parser.add_argument("--evaluator-agent-name", default="EvaluatorAgent")
    parser.add_argument("--output", default="", help="Optional cycle report JSON path")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue next iteration when one agent fails",
    )
    return parser.parse_args()


def _agent_name(args: argparse.Namespace, lane: str) -> str:
    if lane == "coding":
        return str(args.coding_agent_name)
    if lane == "research":
        return str(args.research_agent_name)
    return str(args.evaluator_agent_name)


def _empty_totals() -> Dict[str, int]:
    return {key: 0 for key in ID_KEYS}


def _add_counts(dst: Dict[str, int], src: Dict[str, Any]) -> None:
    for key in ID_KEYS:
        value = src.get(key, 0)
        if isinstance(value, int):
            dst[key] = int(dst.get(key, 0)) + value


def _count_map(report: Dict[str, Any], field: str) -> Dict[str, int]:
    raw = report.get(field)
    out = _empty_totals()
    if not isinstance(raw, dict):
        return out
    for key in ID_KEYS:
        items = raw.get(key, [])
        if isinstance(items, list):
            out[key] = len(items)
    return out


def _run_agent(
    repo_root: Path,
    script_name: str,
    agent_name: str,
    args: argparse.Namespace,
    iteration_tag: str,
    output_path: Path,
) -> subprocess.CompletedProcess[str]:
    cmd: List[str] = [
        sys.executable,
        str(repo_root / "examples" / "agents" / script_name),
        "--base-url",
        str(args.base_url),
        "--integration-id",
        str(args.integration_id),
        "--agent-name",
        str(agent_name),
        "--run-tag",
        iteration_tag,
        "--output",
        str(output_path),
    ]
    if args.skip_signature:
        cmd.append("--skip-signature")
    if args.skip_gate:
        cmd.append("--skip-gate")
    return subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root)


def _safe_tail(text: str, max_lines: int = 8) -> str:
    lines = [line for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])


def _try_stats(base_url: str) -> Dict[str, Any]:
    client = create_client(base_url)
    try:
        return {"ok": True, "payload": client.stats(history=1)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> int:
    args = parse_args()
    if args.iterations < 1:
        raise SystemExit("--iterations must be >= 1")
    if args.interval_seconds < 0:
        raise SystemExit("--interval-seconds must be >= 0")

    repo_root = Path(__file__).resolve().parents[2]
    token_base = run_tag(args.run_tag)
    integration_slug = stable_slug(args.integration_id)
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else (default_output_dir() / f"seed_cycle_{integration_slug}.json")
    )

    report: Dict[str, Any] = {
        "kind": "seed-cycle",
        "created_at": utc_now(),
        "base_url": args.base_url,
        "integration_id": args.integration_id,
        "skip_gate": bool(args.skip_gate),
        "skip_signature": bool(args.skip_signature),
        "iterations_total": int(args.iterations),
        "interval_seconds": float(args.interval_seconds),
        "run_tag_base": token_base,
        "iteration_results": [],
        "aggregate": {
            "stored": _empty_totals(),
            "staged": _empty_totals(),
        },
        "errors": [],
    }

    for idx in range(1, args.iterations + 1):
        iter_tag = token_base if args.iterations == 1 else f"{token_base}-i{idx:03d}"
        iter_dir = default_output_dir() / "seed_cycle" / integration_slug / iter_tag
        iteration_row: Dict[str, Any] = {
            "index": idx,
            "run_tag": iter_tag,
            "started_at": utc_now(),
            "agents": [],
            "ok": True,
            "stats": {},
        }

        for lane, script_name in AGENTS:
            agent_name = _agent_name(args, lane)
            agent_output = iter_dir / f"{lane}.json"
            proc = _run_agent(
                repo_root=repo_root,
                script_name=script_name,
                agent_name=agent_name,
                args=args,
                iteration_tag=iter_tag,
                output_path=agent_output,
            )
            row: Dict[str, Any] = {
                "lane": lane,
                "script": script_name,
                "agent_name": agent_name,
                "returncode": proc.returncode,
                "output": str(agent_output),
                "stdout_tail": _safe_tail(proc.stdout),
                "stderr_tail": _safe_tail(proc.stderr),
                "stored_counts": _empty_totals(),
                "staged_counts": _empty_totals(),
            }

            if agent_output.exists():
                agent_report = json.loads(agent_output.read_text(encoding="utf-8"))
                stored_counts = _count_map(agent_report, "stored")
                staged_counts = _count_map(agent_report, "staged")
                row["stored_counts"] = stored_counts
                row["staged_counts"] = staged_counts
                _add_counts(report["aggregate"]["stored"], stored_counts)
                _add_counts(report["aggregate"]["staged"], staged_counts)
            else:
                msg = f"missing output for {lane} iteration={idx}: {agent_output}"
                row["error"] = msg
                report["errors"].append(msg)

            if proc.returncode != 0:
                iteration_row["ok"] = False
                msg = f"agent {lane} failed in iteration {idx} (exit={proc.returncode})"
                row["error"] = msg
                report["errors"].append(msg)

            iteration_row["agents"].append(row)

            if not iteration_row["ok"] and not args.continue_on_error:
                break

        if not args.skip_gate:
            iteration_row["stats"] = _try_stats(args.base_url)

        iteration_row["finished_at"] = utc_now()
        report["iteration_results"].append(iteration_row)

        if not iteration_row["ok"] and not args.continue_on_error:
            write_report(output_path, report)
            print(f"WROTE: {output_path}")
            print(f"FAIL: seed cycle stopped on iteration {idx}")
            return 1

        if idx < args.iterations and args.interval_seconds > 0:
            time.sleep(args.interval_seconds)

    write_report(output_path, report)
    print(f"WROTE: {output_path}")
    print(
        "SUMMARY: "
        f"iterations={len(report['iteration_results'])} "
        f"stored_total={sum(report['aggregate']['stored'].values())} "
        f"staged_total={sum(report['aggregate']['staged'].values())} "
        f"errors={len(report['errors'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
