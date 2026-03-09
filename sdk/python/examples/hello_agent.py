#!/usr/bin/env python3
"""Minimal external agent hello flow via /playground/run."""

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
    parser = argparse.ArgumentParser(description="Run hello agent against ECHO adapter")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--token", default="")
    parser.add_argument("--agent-name", default="HelloAgent")
    parser.add_argument("--lane", default="ops")
    parser.add_argument("--task", default="hello from external agent SDK")
    return parser.parse_args()


def main() -> int:
    _ensure_sdk_import()
    from echo_agent import EchoClient  # type: ignore

    args = parse_args()
    client = EchoClient(base_url=args.base_url, token=(args.token or None))

    run = client.playground_run(agent_name=args.agent_name, lane=args.lane, task=args.task)
    stats = client.stats()
    agents = client.agents()

    print("PLAYGROUND_RUN:")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    print("AGENTS_SUMMARY:")
    print(json.dumps(agents.get("summary", {}), ensure_ascii=False, indent=2))
    print("NETWORK_OBJECTS:")
    print(json.dumps(stats.get("network_objects", {}), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
