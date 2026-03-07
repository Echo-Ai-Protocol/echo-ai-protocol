#!/usr/bin/env python3
"""Generate a live status snapshot for the current ECHO network."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_reference_node_import() -> None:
    ref_node_dir = _repo_root() / "reference-node"
    if str(ref_node_dir) not in sys.path:
        sys.path.insert(0, str(ref_node_dir))


def parse_args() -> argparse.Namespace:
    repo = _repo_root()
    parser = argparse.ArgumentParser(description="Generate tools/out/live_network_status.json")
    parser.add_argument("--storage-root", default=str(repo / "reference-node" / "storage"))
    parser.add_argument("--tools-out-dir", default=str(repo / "tools" / "out"))
    parser.add_argument("--output", default=str(repo / "tools" / "out" / "live_network_status.json"))
    parser.add_argument(
        "--write-history",
        action="store_true",
        default=True,
        help="Write timestamped snapshot to tools/out/history (default: enabled)",
    )
    parser.add_argument(
        "--no-write-history",
        action="store_false",
        dest="write_history",
        help="Disable timestamped history snapshot output",
    )
    return parser.parse_args()


def main() -> int:
    _ensure_reference_node_import()
    import reference_node as core  # type: ignore

    args = parse_args()
    storage_root = Path(args.storage_root).expanduser().resolve()
    tools_out_dir = Path(args.tools_out_dir).expanduser().resolve()
    out_path = Path(args.output).expanduser().resolve()

    status = core.build_live_network_status(storage_root=storage_root, tools_out_dir=tools_out_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")

    if args.write_history:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        hist_path = tools_out_dir / "history" / f"live_network_status_{stamp}.json"
        hist_path.parent.mkdir(parents=True, exist_ok=True)
        hist_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"HISTORY: {hist_path}")

    print(
        "SUMMARY: "
        f"eo={status['network_objects']['eo_total']} "
        f"rr={status['network_objects']['rr_total']} "
        f"trace={status['network_objects']['trace_total']} "
        f"request={status['network_objects']['request_total']} "
        f"agents={status['agents']['total_known_agents']} "
        f"active_24h={status['agents']['active_agents_last_24h']} "
        f"seed_iterations={status['seed_cycle']['iterations_completed']} "
        f"failed_runs={status['errors']['failed_runs']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
