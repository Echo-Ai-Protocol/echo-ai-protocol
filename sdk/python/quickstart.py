#!/usr/bin/env python3
"""Agent quickstart: health -> bootstrap -> store EO -> ranked search -> store RR."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict

from echo_sdk import EchoApiError, EchoClient


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def with_unique_id(obj: Dict[str, Any], field: str, prefix: str) -> Dict[str, Any]:
    out = dict(obj)
    stamp = int(time.time())
    out[field] = f"{prefix}.{stamp}"
    out["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ECHO SDK quickstart flow")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--skip-signature", action="store_true")
    parser.add_argument("--retries", type=int, default=3, help="HTTP retries per request")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument(
        "--sample-dir",
        default=str(Path(__file__).resolve().parents[2] / "reference-node" / "sample_data"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sample_dir = Path(args.sample_dir).expanduser().resolve()
    eo_sample = read_json(sample_dir / "eo.sample.json")
    rr_sample = read_json(sample_dir / "rr.sample.json")

    client = EchoClient(
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.retries,
    )

    try:
        health = client.wait_for_health(max_attempts=20, delay_seconds=0.2)
    except EchoApiError as exc:
        print(f"[FAIL] health check failed: {exc}")
        if exc.body is not None:
            print(exc.body)
        return 2

    print("[OK] /health", health.get("status"))
    bootstrap = client.bootstrap()
    print("[OK] /registry/bootstrap", bootstrap.get("bootstrap_version"))

    eo = with_unique_id(eo_sample, "eo_id", "echo.eo.sdk.quickstart")
    stored_eo = client.store_eo(eo, skip_signature=args.skip_signature)
    eo_id = eo["eo_id"]
    print("[OK] stored eo", stored_eo.get("id"))

    search = client.search_ranked_eo(eo_id_contains=eo_id, limit=5, explain=True)
    count = int(search.get("count", 0))
    if count < 1:
        print("[FAIL] expected at least 1 search hit for stored EO")
        return 2
    print("[OK] search hits", count)

    rr = with_unique_id(rr_sample, "rr_id", "echo.rr.sdk.quickstart")
    rr["target_eo_id"] = eo_id
    stored_rr = client.store_rr(rr, skip_signature=args.skip_signature)
    print("[OK] stored rr", stored_rr.get("id"))

    reputation = client.reputation(rr.get("issuer_agent_did", "did:echo:unknown"))
    print("[OK] reputation", reputation.get("score"))

    stats = client.stats(history=2)
    trend = stats.get("simulator_trend", {})
    print("[OK] stats trend baseline", trend.get("has_baseline"))
    print("\nQuickstart flow completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
