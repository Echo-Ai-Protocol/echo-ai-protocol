#!/usr/bin/env python3
"""Shared helpers for fixture-based ECHO seed agents."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


ID_FIELD_BY_TYPE = {
    "eo": "eo_id",
    "request": "rq_id",
    "rr": "rr_id",
    "trace": "trace_id",
}

SAMPLE_FILE_BY_TYPE = {
    "eo": "eo.sample.json",
    "request": "request.sample.json",
    "rr": "rr.sample.json",
    "trace": "trace.sample.json",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sample_data_dir() -> Path:
    return repo_root() / "reference-node" / "sample_data"


def default_output_dir() -> Path:
    return repo_root() / "tools" / "out" / "agents"


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def stable_slug(text: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._:-]+", "-", text.strip().lower())
    return normalized.strip("-") or "agent"


def build_agent_did(integration_id: str, agent_name: str) -> str:
    return f"did:echo:agent.{stable_slug(integration_id)}.{stable_slug(agent_name)}"


def run_tag(value: str | None = None) -> str:
    if value and value.strip():
        return stable_slug(value)
    return time.strftime("%Y%m%d%H%M%S", time.gmtime())


def make_id(kind: str, integration_id: str, lane: str, task_id: str, run_token: str) -> str:
    return f"echo.{kind}.agent.{stable_slug(integration_id)}.{stable_slug(lane)}.{stable_slug(task_id)}.{run_token}"


def load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def load_tasks(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected JSON array in {path}")
    out: List[Dict[str, Any]] = []
    for idx, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"tasks[{idx}] in {path} must be an object")
        out.append(item)
    return out


def load_sample_object(object_type: str) -> Dict[str, Any]:
    if object_type not in SAMPLE_FILE_BY_TYPE:
        raise ValueError(f"Unsupported sample object type: {object_type}")
    return load_json(sample_data_dir() / SAMPLE_FILE_BY_TYPE[object_type])


def ensure_sdk_import() -> Tuple[Any, Any]:
    sdk_path = repo_root() / "sdk" / "python"
    if str(sdk_path) not in sys.path:
        sys.path.insert(0, str(sdk_path))
    from echo_sdk import EchoApiError, EchoClient  # type: ignore

    return EchoClient, EchoApiError


def create_client(base_url: str) -> Any:
    EchoClient, _ = ensure_sdk_import()
    return EchoClient(base_url=base_url)


def check_node_ready(client: Any, skip_gate: bool) -> Tuple[bool, str]:
    if skip_gate:
        return True, "gate-skipped"
    try:
        client.wait_for_health(max_attempts=20, delay_seconds=0.2)
        client.bootstrap()
        return True, "ready"
    except Exception as exc:
        return False, str(exc)


def _object_id(object_type: str, payload: Dict[str, Any]) -> str:
    id_field = ID_FIELD_BY_TYPE[object_type]
    value = payload.get(id_field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing object id field '{id_field}' for type '{object_type}'")
    return value


def store_or_stage(
    client: Any,
    object_type: str,
    payload: Dict[str, Any],
    skip_signature: bool,
    skip_gate: bool,
    report: Dict[str, Any],
) -> Dict[str, Any]:
    obj_id = _object_id(object_type, payload)
    try:
        response = client.store_object(object_type, payload, skip_signature=skip_signature)
        report["stored"][object_type].append(obj_id)
        return {"status": "stored", "response": response}
    except Exception as exc:
        if skip_gate:
            report["staged"][object_type].append(payload)
            report["warnings"].append(f"{object_type}:{obj_id} staged due to network/API error: {exc}")
            return {"status": "staged", "error": str(exc)}
        raise


def write_report(path: Path, report: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
