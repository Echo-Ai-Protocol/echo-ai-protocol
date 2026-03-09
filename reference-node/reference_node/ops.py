"""Operational helpers: idempotent store, agent registry, live status snapshots."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from .index import load_index
from .io_utils import load_json, write_json
from .store import iter_stored_paths, object_id_for_type, store_object
from .types import ID_FIELD_MAP, TYPE_DIR


AGENT_REGISTRY_FILE = "agent_registry.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(text: str) -> datetime | None:
    if not isinstance(text, str):
        return None
    raw = text.strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def canonical_json_payload(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def object_fingerprint(object_type: str, obj: Dict[str, Any]) -> str:
    canonical = canonical_json_payload(obj).encode("utf-8")
    prefix = f"{object_type}|".encode("utf-8")
    return hashlib.sha256(prefix + canonical).hexdigest()


def _find_duplicate_by_fingerprint(storage_root: Path, object_type: str, obj: Dict[str, Any]) -> Dict[str, Any] | None:
    target_fingerprint = object_fingerprint(object_type, obj)
    for path in iter_stored_paths(storage_root, object_type):
        try:
            existing = load_json(path)
        except Exception:
            continue
        if not isinstance(existing, dict):
            continue
        if object_fingerprint(object_type, existing) != target_fingerprint:
            continue
        existing_id = ""
        try:
            existing_id = object_id_for_type(object_type, existing)
        except Exception:
            existing_id = ""
        return {
            "fingerprint": target_fingerprint,
            "path": str(path),
            "id": existing_id,
        }
    return None


def agent_registry_path(storage_root: Path) -> Path:
    return storage_root / AGENT_REGISTRY_FILE


def load_agent_registry(storage_root: Path) -> List[Dict[str, Any]]:
    path = agent_registry_path(storage_root)
    if not path.exists():
        return []
    try:
        payload = load_json(path)
    except Exception:
        return []
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("agents"), list):
        rows = payload.get("agents", [])
    else:
        return []
    out: List[Dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(dict(row))
    return out


def save_agent_registry(storage_root: Path, rows: List[Dict[str, Any]]) -> None:
    clean: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        did = row.get("agent_did")
        if not isinstance(did, str) or not did.strip():
            continue
        clean.append(dict(row))
    clean.sort(key=lambda r: (str(r.get("agent_did", "")), str(r.get("lane", ""))))
    write_json(agent_registry_path(storage_root), clean)


def _parse_did(agent_did: str) -> Dict[str, str]:
    if not isinstance(agent_did, str):
        return {"integration_id": "", "agent_name": ""}
    prefix = "did:echo:agent."
    if not agent_did.startswith(prefix):
        return {"integration_id": "", "agent_name": ""}
    rest = agent_did[len(prefix) :]
    parts = [p for p in rest.split(".") if p]
    if not parts:
        return {"integration_id": "", "agent_name": ""}
    integration_id = parts[0]
    agent_name = ".".join(parts[1:]) if len(parts) > 1 else ""
    return {"integration_id": integration_id, "agent_name": agent_name}


def _parse_lane_and_integration_from_object_id(object_type: str, obj: Dict[str, Any]) -> Dict[str, str]:
    id_field = ID_FIELD_MAP.get(object_type, "")
    raw = obj.get(id_field)
    if not isinstance(raw, str):
        return {"integration_id": "", "lane": "", "agent_name": ""}
    parts = [p for p in raw.split(".") if p]
    # Expected seed shape: echo.<type>.agent.<integration_id>.<lane>.<task>.<run>
    if len(parts) >= 6 and parts[0] == "echo" and parts[2] == "agent":
        agent_name = ""
        # Optional adapter marker:
        # echo.<type>.agent.<integration>.<lane>.by.<agent_name>.<token>
        if len(parts) >= 8 and parts[5] == "by":
            agent_name = parts[6]
        return {"integration_id": parts[3], "lane": parts[4], "agent_name": agent_name}
    return {"integration_id": "", "lane": "", "agent_name": ""}


def _metadata_for_registry(object_type: str, obj: Dict[str, Any]) -> Dict[str, str] | None:
    if object_type not in {"eo", "rr", "trace"}:
        return None

    if object_type == "rr":
        agent_did = obj.get("issuer_agent_did")
    else:
        agent_did = obj.get("agent_did")
    if not isinstance(agent_did, str):
        agent_did = ""
    agent_did = agent_did.strip()

    did_parts = _parse_did(agent_did) if agent_did else {"integration_id": "", "agent_name": ""}
    id_parts = _parse_lane_and_integration_from_object_id(object_type, obj)

    integration_id = did_parts["integration_id"] or id_parts["integration_id"] or "unknown"
    lane = id_parts["lane"] or "unknown"
    agent_name = did_parts["agent_name"] or id_parts.get("agent_name", "") or lane or "unknown"

    if not agent_did:
        agent_did = f"did:echo:agent.{integration_id}.{agent_name}"

    return {
        "agent_did": agent_did,
        "integration_id": integration_id,
        "agent_name": agent_name,
        "lane": lane,
    }


def ensure_agent_registry_entry(storage_root: Path, object_type: str, obj: Dict[str, Any]) -> bool:
    meta = _metadata_for_registry(object_type, obj)
    if meta is None:
        return False

    created_at_raw = obj.get("created_at")
    created_at = created_at_raw if isinstance(created_at_raw, str) and created_at_raw.strip() else utc_now()

    rows = load_agent_registry(storage_root)
    for row in rows:
        if row.get("agent_did") == meta["agent_did"]:
            return False

    rows.append(
        {
            "agent_did": meta["agent_did"],
            "integration_id": meta["integration_id"],
            "agent_name": meta["agent_name"],
            "lane": meta["lane"],
            "first_seen": created_at,
            "last_seen": created_at,
            "eo_created": 0,
            "rr_created": 0,
            "trace_created": 0,
            "errors": 0,
        }
    )
    save_agent_registry(storage_root, rows)
    return True


def update_agent_registry_on_store(storage_root: Path, object_type: str, obj: Dict[str, Any]) -> None:
    meta = _metadata_for_registry(object_type, obj)
    if meta is None:
        return

    created_at_raw = obj.get("created_at")
    created_at = created_at_raw if isinstance(created_at_raw, str) and created_at_raw.strip() else utc_now()

    rows = load_agent_registry(storage_root)
    target = None
    for row in rows:
        if row.get("agent_did") == meta["agent_did"]:
            target = row
            break

    if target is None:
        target = {
            "agent_did": meta["agent_did"],
            "integration_id": meta["integration_id"],
            "agent_name": meta["agent_name"],
            "lane": meta["lane"],
            "first_seen": created_at,
            "last_seen": created_at,
            "eo_created": 0,
            "rr_created": 0,
            "trace_created": 0,
            "errors": 0,
        }
        rows.append(target)

    # Keep known metadata when we discover better values later.
    for k in ("integration_id", "agent_name", "lane"):
        current = str(target.get(k, "")).strip()
        incoming = str(meta.get(k, "")).strip()
        if current in {"", "unknown"} and incoming:
            target[k] = incoming

    first_seen = str(target.get("first_seen", "")).strip()
    if not first_seen:
        target["first_seen"] = created_at
    else:
        dt_first = _parse_utc(first_seen)
        dt_new = _parse_utc(created_at)
        if dt_first is None:
            target["first_seen"] = created_at
        elif dt_new is not None and dt_new < dt_first:
            target["first_seen"] = created_at

    target["last_seen"] = created_at
    if object_type == "eo":
        target["eo_created"] = int(target.get("eo_created", 0)) + 1
    elif object_type == "rr":
        target["rr_created"] = int(target.get("rr_created", 0)) + 1
    elif object_type == "trace":
        target["trace_created"] = int(target.get("trace_created", 0)) + 1

    save_agent_registry(storage_root, rows)


def summarize_agents(storage_root: Path, now_utc: datetime | None = None) -> Dict[str, int]:
    rows = load_agent_registry(storage_root)
    now = now_utc or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    active = 0
    for row in rows:
        dt = _parse_utc(str(row.get("last_seen", "")))
        if dt is not None and dt >= cutoff:
            active += 1
    return {
        "total_known_agents": len(rows),
        "active_agents_last_24h": active,
    }


def store_object_idempotent(storage_root: Path, object_type: str, obj: Dict[str, Any]) -> Dict[str, Any]:
    obj_id = object_id_for_type(object_type, obj)
    duplicate = _find_duplicate_by_fingerprint(storage_root, object_type, obj)
    if duplicate is not None:
        return {
            "status": "duplicate_ignored",
            "type": object_type,
            "id": obj_id,
            "path": duplicate["path"],
            "fingerprint": duplicate["fingerprint"],
            "duplicate_of": duplicate.get("id", ""),
        }

    out = store_object(storage_root=storage_root, object_type=object_type, obj=obj)
    update_agent_registry_on_store(storage_root=storage_root, object_type=object_type, obj=obj)
    return {
        "status": "stored",
        "type": object_type,
        "id": obj_id,
        "path": str(out),
        "fingerprint": object_fingerprint(object_type, obj),
    }


def latest_seed_cycle_summary(tools_out_dir: Path) -> Dict[str, Any]:
    candidates = sorted((tools_out_dir / "agents").glob("seed_cycle_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return {"last_run": "", "iterations_completed": 0, "failed_runs": 0, "report_path": ""}

    path = candidates[0]
    try:
        payload = load_json(path)
    except Exception:
        return {"last_run": "", "iterations_completed": 0, "failed_runs": 0, "report_path": str(path)}
    if not isinstance(payload, dict):
        return {"last_run": "", "iterations_completed": 0, "failed_runs": 0, "report_path": str(path)}

    rows = payload.get("iteration_results", [])
    iterations = rows if isinstance(rows, list) else []
    failed = 0
    for row in iterations:
        if not isinstance(row, dict):
            continue
        if row.get("ok") is False:
            failed += 1
    return {
        "last_run": str(payload.get("created_at", "")),
        "iterations_completed": len(iterations),
        "failed_runs": failed,
        "report_path": str(path),
    }


def _agent_runs_failed_count(tools_out_dir: Path) -> int:
    base = tools_out_dir / "agents"
    if not base.exists():
        return 0
    failed = 0
    for path in sorted(base.glob("*_agent_*.json")):
        if path.name.startswith("seed_cycle_"):
            continue
        try:
            payload = load_json(path)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        node_status = str(payload.get("node_status", ""))
        warnings = payload.get("warnings", [])
        node_ok = node_status in {"ready", "gate-skipped"}
        has_warnings = isinstance(warnings, list) and len(warnings) > 0
        if (not node_ok) or has_warnings:
            failed += 1
    return failed


def build_live_network_status(storage_root: Path, tools_out_dir: Path) -> Dict[str, Any]:
    idx = load_index(storage_root)
    counts: Dict[str, int] = {}
    for object_type in TYPE_DIR.keys():
        stored_count = len(list(iter_stored_paths(storage_root, object_type)))
        indexed_count = len(idx.get(object_type, []))
        counts[object_type] = max(stored_count, indexed_count)

    seed_cycle = latest_seed_cycle_summary(tools_out_dir)
    agent_failed_runs = _agent_runs_failed_count(tools_out_dir)
    agents = summarize_agents(storage_root)
    return {
        "timestamp": utc_now(),
        "network_objects": {
            "eo_total": int(counts.get("eo", 0)),
            "rr_total": int(counts.get("rr", 0)),
            "trace_total": int(counts.get("trace", 0)),
            "request_total": int(counts.get("request", 0)),
        },
        "agents": agents,
        "seed_cycle": {
            "last_run": str(seed_cycle.get("last_run", "")),
            "iterations_completed": int(seed_cycle.get("iterations_completed", 0)),
        },
        "errors": {
            "failed_runs": int(seed_cycle.get("failed_runs", 0)) + int(agent_failed_runs),
        },
    }


def load_live_status_history(tools_out_dir: Path, limit: int) -> List[Dict[str, Any]]:
    if limit <= 0:
        return []
    history_dir = tools_out_dir / "history"
    if not history_dir.exists():
        return []
    candidates = sorted(history_dir.glob("live_network_status_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out: List[Dict[str, Any]] = []
    for path in candidates[:limit]:
        try:
            payload = load_json(path)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        row = dict(payload)
        row["_path"] = str(path)
        out.append(row)
    return out
