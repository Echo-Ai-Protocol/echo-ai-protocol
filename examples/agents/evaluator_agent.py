#!/usr/bin/env python3
"""Fixture-based EvaluatorAgent for issuing RR/trace objects in ECHO."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

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
    parser = argparse.ArgumentParser(description="Seed evaluator RR/trace objects into ECHO")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--integration-id", default="ext-ai-seed")
    parser.add_argument("--agent-name", default="EvaluatorAgent")
    parser.add_argument("--skip-gate", action="store_true")
    parser.add_argument("--skip-signature", action="store_true")
    parser.add_argument("--run-tag", default="")
    parser.add_argument(
        "--tasks-file",
        default=str(base / "sample_tasks" / "evaluation_tasks.json"),
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional report JSON path",
    )
    return parser.parse_args()


def _extract_eo_ids(search_payload: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    results = search_payload.get("results")
    if not isinstance(results, list):
        return out
    for row in results:
        if not isinstance(row, dict):
            continue
        obj = row.get("object")
        if not isinstance(obj, dict):
            continue
        eo_id = obj.get("eo_id")
        if isinstance(eo_id, str) and eo_id:
            out.append(eo_id)
    return out


def _request_payload(agent_did: str, integration_id: str, run_token: str, task: Dict[str, Any]) -> Dict[str, Any]:
    payload = load_sample_object("request")
    payload["rq_id"] = make_id("request", integration_id, "evaluate", str(task["task_id"]), run_token)
    payload["agent_did"] = agent_did
    payload["request_embedding"] = f"evaluate_request::{task['rationale']}"
    payload["constraints_embedding"] = f"evaluate_constraints::{task['target_contains']}"
    payload["desired_output_type"] = "EVALUATION"
    payload["created_at"] = utc_now()
    payload["ttl_seconds"] = int(task.get("ttl_seconds", 3600))
    return payload


def _rr_payload(
    agent_did: str,
    integration_id: str,
    run_token: str,
    task: Dict[str, Any],
    target_eo_id: str,
) -> Dict[str, Any]:
    payload = load_sample_object("rr")
    payload["rr_id"] = make_id("rr", integration_id, "evaluate", str(task["task_id"]), run_token)
    payload["issuer_agent_did"] = agent_did
    payload["target_eo_id"] = target_eo_id
    payload["context_embedding"] = f"context::{task['rationale']}"
    payload["applied_constraints_embedding"] = f"constraints::{task['target_contains']}"
    payload["outcome_metrics"] = {
        "effectiveness_score": float(task["outcome_metrics"]["effectiveness_score"]),
        "stability_score": float(task["outcome_metrics"]["stability_score"]),
        "iterations": int(task["outcome_metrics"]["iterations"]),
    }
    payload["verdict"] = str(task["verdict"])
    payload["created_at"] = utc_now()
    return payload


def _trace_payload(
    agent_did: str,
    integration_id: str,
    run_token: str,
    task: Dict[str, Any],
    request_id: str,
    rr_id: str,
    target_eo_id: str,
) -> Dict[str, Any]:
    payload = load_sample_object("trace")
    payload["trace_id"] = make_id("trace", integration_id, "evaluate", str(task["task_id"]), run_token)
    payload["agent_did"] = agent_did
    payload["domain_embedding"] = f"domain::evaluate::{task['task_id']}"
    payload["activity_type"] = "ISSUE_RR"
    payload["refs"] = [request_id, target_eo_id, rr_id]
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
        else (default_output_dir() / f"evaluator_agent_{stable_slug(args.integration_id)}.json")
    )
    report: Dict[str, Any] = {
        "agent": "EvaluatorAgent",
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

        target_contains = str(task.get("target_contains", "echo.eo"))
        target_ids: List[str] = []
        try:
            search = client.search_ranked_eo(target_contains, limit=10, explain=True)
            target_ids = _extract_eo_ids(search)
            report["search_events"].append(
                {
                    "task_id": task["task_id"],
                    "contains": target_contains,
                    "count": len(target_ids),
                }
            )
        except Exception as exc:
            report["search_events"].append(
                {
                    "task_id": task["task_id"],
                    "contains": target_contains,
                    "error": str(exc),
                }
            )
            if not args.skip_gate:
                raise

        target_eo_id = target_ids[0] if target_ids else str(task.get("fallback_target_eo_id", "")).strip()
        if not target_eo_id:
            report["warnings"].append(f"task={task['task_id']} has no available target EO id; skipped")
            continue

        rr = _rr_payload(
            agent_did=agent_did,
            integration_id=args.integration_id,
            run_token=token,
            task=task,
            target_eo_id=target_eo_id,
        )
        store_or_stage(
            client=client,
            object_type="rr",
            payload=rr,
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
            rr_id=str(rr["rr_id"]),
            target_eo_id=target_eo_id,
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
        f"rr={len(report['stored']['rr'])} "
        f"trace={len(report['stored']['trace'])} "
        f"staged={sum(len(report['staged'][k]) for k in report['staged'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
