#!/usr/bin/env python3
"""Example external coding agent using /ingest endpoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _ensure_sdk_import() -> None:
    sdk_root = Path(__file__).resolve().parents[1]
    if str(sdk_root) not in sys.path:
        sys.path.insert(0, str(sdk_root))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Submit external coding EO + TRACE via adapter")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--token", default="")
    parser.add_argument("--integration-id", default="ext-pilot-001")
    parser.add_argument("--agent-name", default="ExternalCodingAgent")
    parser.add_argument("--lane", default="code")
    parser.add_argument("--task-id", default="task-001")
    return parser.parse_args()


def main() -> int:
    _ensure_sdk_import()
    from echo_agent import EchoClient  # type: ignore

    args = parse_args()
    client = EchoClient(base_url=args.base_url, token=(args.token or None))

    eo = client.ingest(
        integration_id=args.integration_id,
        agent_name=args.agent_name,
        lane=args.lane,
        object_type="eo",
        idempotency_key=f"{args.integration_id}:{args.task_id}:eo",
        payload={
            "problem": "stabilize parser retries under flaky IO",
            "constraints": "stdlib only, deterministic",
            "solution": "bounded retries with deterministic backoff policy",
            "outcome_metrics": {
                "effectiveness_score": 0.81,
                "stability_score": 0.78,
                "iterations": 1,
            },
            "confidence_score": 0.76,
        },
    )

    trace = client.ingest(
        integration_id=args.integration_id,
        agent_name=args.agent_name,
        lane=args.lane,
        object_type="trace",
        idempotency_key=f"{args.integration_id}:{args.task_id}:trace",
        payload={
            "activity_type": "PUBLISH_EO",
            "domain_embedding": "domain::code::external",
            "refs": [eo.get("object_id", "")],
            "ttl_seconds": 3600,
        },
    )

    print("EO_RESULT:")
    print(json.dumps(eo, ensure_ascii=False, indent=2))
    print("TRACE_RESULT:")
    print(json.dumps(trace, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
