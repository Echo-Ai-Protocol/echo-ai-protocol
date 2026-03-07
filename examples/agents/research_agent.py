#!/usr/bin/env python3
"""Fixture-based ResearchAgent for seeding ECHO request/EO/trace objects."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from common import (
    build_agent_did,
    check_node_ready,
    create_client,
    default_output_dir,
    load_sample_object,
    load_tasks,
    make_id,
    run_tag,
    stable_slug,
    store_or_stage,
    utc_now,
    write_report,
)


def parse_args() -> argparse.Namespace:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Seed research EO/trace objects into ECHO")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--integration-id", default="ext-ai-seed")
    parser.add_argument("--agent-name", default="ResearchAgent")
    parser.add_argument("--skip-gate", action="store_true")
    parser.add_argument("--skip-signature", action="store_true")
    parser.add_argument("--run-tag", default="")
    parser.add_argument(
        "--tasks-file",
        default=str(base / "sample_tasks" / "research_tasks.json"),
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional report JSON path",
    )
    return parser.parse_args()


def _request_payload(agent_did: str, integration_id: str, run_token: str, task: Dict[str, Any]) -> Dict[str, Any]:
    payload = load_sample_object("request")
    payload["rq_id"] = make_id("request", integration_id, "research", str(task["task_id"]), run_token)
    payload["agent_did"] = agent_did
    payload["request_embedding"] = f"research_request::{task['topic']}"
    payload["constraints_embedding"] = f"research_constraints::{task['constraints']}"
    payload["desired_output_type"] = "STRATEGY"
    payload["created_at"] = utc_now()
    payload["ttl_seconds"] = int(task.get("ttl_seconds", 3600))
    return payload


def _eo_payload(integration_id: str, run_token: str, task: Dict[str, Any]) -> Dict[str, Any]:
    payload = load_sample_object("eo")
    payload["eo_id"] = make_id("eo", integration_id, "research", str(task["task_id"]), run_token)
    payload["problem_embedding"] = f"topic::{task['topic']}"
    payload["constraints_embedding"] = f"constraints::{task['constraints']}"
    payload["solution_embedding"] = f"summary::{task['summary']}::recommendations::{task['recommendations']}"
    payload["outcome_metrics"] = {
        "effectiveness_score": float(task["outcome_metrics"]["effectiveness_score"]),
        "stability_score": float(task["outcome_metrics"]["stability_score"]),
        "iterations": int(task["outcome_metrics"]["iterations"]),
    }
    payload["confidence_score"] = float(task.get("confidence_score", 0.82))
    payload["created_at"] = utc_now()
    return payload


def _trace_payload(
    agent_did: str,
    integration_id: str,
    run_token: str,
    task: Dict[str, Any],
    request_id: str,
    eo_id: str,
) -> Dict[str, Any]:
    payload = load_sample_object("trace")
    payload["trace_id"] = make_id("trace", integration_id, "research", str(task["task_id"]), run_token)
    payload["agent_did"] = agent_did
    payload["domain_embedding"] = f"domain::research::{task['task_id']}"
    payload["activity_type"] = "PUBLISH_EO"
    payload["refs"] = [request_id, eo_id]
    payload["created_at"] = utc_now()
    payload["ttl_seconds"] = int(task.get("trace_ttl_seconds", 3600))
    return payload


def main() -> int:
    args = parse_args()
    tasks = load_tasks(Path(args.tasks_file).expanduser().resolve())
    token = run_tag(args.run_tag)
    agent_did = build_agent_did(args.integration_id, args.agent_name)
    client = create_client(args.base_url)

    out_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else (default_output_dir() / f"research_agent_{stable_slug(args.integration_id)}.json")
    )
    report: Dict[str, Any] = {
        "agent": "ResearchAgent",
        "integration_id": args.integration_id,
        "agent_name": args.agent_name,
        "agent_did": agent_did,
        "base_url": args.base_url,
        "skip_gate": bool(args.skip_gate),
        "skip_signature": bool(args.skip_signature),
        "run_tag": token,
        "tasks_total": len(tasks),
        "search_events": [],
        "stored": {"request": [], "eo": [], "trace": [], "rr": []},
        "staged": {"request": [], "eo": [], "trace": [], "rr": []},
        "warnings": [],
    }

    ok, status_text = check_node_ready(client, skip_gate=bool(args.skip_gate))
    report["node_status"] = status_text
    if not ok:
        write_report(out_path, report)
        print(f"WROTE: {out_path}")
        print(f"FAIL: node is not ready ({status_text})")
        return 1

    for task in tasks:
        rq = _request_payload(agent_did, args.integration_id, token, task)
        store_or_stage(
            client=client,
            object_type="request",
            payload=rq,
            skip_signature=bool(args.skip_signature),
            skip_gate=bool(args.skip_gate),
            report=report,
        )

        search_hint = str(task.get("search_hint", "echo.eo"))
        try:
            search = client.search_ranked_eo(search_hint, limit=5, explain=True)
            report["search_events"].append(
                {
                    "task_id": task["task_id"],
                    "hint": search_hint,
                    "count": int(search.get("count", 0)),
                }
            )
        except Exception as exc:
            report["search_events"].append(
                {
                    "task_id": task["task_id"],
                    "hint": search_hint,
                    "error": str(exc),
                }
            )
            if not args.skip_gate:
                raise

        eo = _eo_payload(args.integration_id, token, task)
        store_or_stage(
            client=client,
            object_type="eo",
            payload=eo,
            skip_signature=bool(args.skip_signature),
            skip_gate=bool(args.skip_gate),
            report=report,
        )

        trace = _trace_payload(
            agent_did=agent_did,
            integration_id=args.integration_id,
            run_token=token,
            task=task,
            request_id=str(rq["rq_id"]),
            eo_id=str(eo["eo_id"]),
        )
        store_or_stage(
            client=client,
            object_type="trace",
            payload=trace,
            skip_signature=bool(args.skip_signature),
            skip_gate=bool(args.skip_gate),
            report=report,
        )

    write_report(out_path, report)
    print(f"WROTE: {out_path}")
    print(
        "SUMMARY: "
        f"request={len(report['stored']['request'])} "
        f"eo={len(report['stored']['eo'])} "
        f"trace={len(report['stored']['trace'])} "
        f"staged={sum(len(report['staged'][k]) for k in report['staged'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
