"""Operational stats helpers for local reference-node observability."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .index import index_path, load_index
from .io_utils import default_tools_out_dir, load_json
from .metrics import SIM_METRICS_CONTRACT_VERSION, evaluate_sim_metrics_v1, extract_sim_metrics_v1
from .store import iter_stored_paths
from .types import TYPE_DIR


def _empty_sim_payload() -> Dict[str, Any]:
    return {
        "found": False,
        "path": None,
        "report": None,
        "contract_version": SIM_METRICS_CONTRACT_VERSION,
        "metrics_v1": None,
        "evaluation_v1": None,
    }


def _sim_report_candidates(tools_out_dir: Path) -> List[Path]:
    if not tools_out_dir.exists():
        return []
    return sorted(tools_out_dir.glob("sim_report_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def _sim_report_payload(report_path: Path) -> Dict[str, Any]:
    try:
        report = load_json(report_path)
    except Exception:
        return {
            "found": True,
            "path": str(report_path),
            "report": None,
            "contract_version": SIM_METRICS_CONTRACT_VERSION,
            "metrics_v1": None,
            "evaluation_v1": None,
        }
    if not isinstance(report, dict):
        return {
            "found": True,
            "path": str(report_path),
            "report": None,
            "contract_version": SIM_METRICS_CONTRACT_VERSION,
            "metrics_v1": None,
            "evaluation_v1": None,
        }

    metrics = extract_sim_metrics_v1(report)
    evaluation = evaluate_sim_metrics_v1(metrics) if metrics is not None else None
    return {
        "found": True,
        "path": str(report_path),
        "report": report,
        "contract_version": SIM_METRICS_CONTRACT_VERSION,
        "metrics_v1": metrics,
        "evaluation_v1": evaluation,
    }


def _latest_sim_report_payload(tools_out_dir: Path) -> Dict[str, Any]:
    candidates = _sim_report_candidates(tools_out_dir)
    if not candidates:
        return _empty_sim_payload()
    return _sim_report_payload(candidates[0])


def _sim_history_payload(tools_out_dir: Path, limit: int) -> List[Dict[str, Any]]:
    if limit <= 0:
        return []

    candidates = _sim_report_candidates(tools_out_dir)
    if not candidates:
        return []

    # Keep historical scenario reports first; include alias fallback only when needed.
    timeline = [p for p in candidates if p.name != "sim_report_latest.json"]
    if not timeline:
        timeline = candidates
    timeline = timeline[:limit]

    history: List[Dict[str, Any]] = []
    for path in timeline:
        payload = _sim_report_payload(path)
        history.append(
            {
                "path": payload["path"],
                "metrics_v1": payload["metrics_v1"],
                "evaluation_v1": payload["evaluation_v1"],
            }
        )
    return history


def compute_stats(storage_root: Path, tools_out_dir: Path | None = None, history_limit: int = 0) -> Dict[str, Any]:
    idx = load_index(storage_root)
    idx_path = index_path(storage_root)
    out_dir = tools_out_dir or default_tools_out_dir()

    stored_counts: Dict[str, int] = {}
    indexed_counts: Dict[str, int] = {}
    index_missing_files: Dict[str, int] = {}

    for object_type in TYPE_DIR.keys():
        stored_paths = list(iter_stored_paths(storage_root, object_type))
        stored_counts[object_type] = len(stored_paths)
        indexed_ids = idx.get(object_type, [])
        indexed_counts[object_type] = len(indexed_ids)

        missing = 0
        existing_names = {p.stem for p in stored_paths}
        for obj_id in indexed_ids:
            if obj_id not in existing_names:
                # Safe filename normalization can change names, so this is only a quick signal.
                # We treat this as advisory health info, not a strict corruption marker.
                missing += 1
        index_missing_files[object_type] = missing

    return {
        "storage_root": str(storage_root),
        "index": {
            "path": str(idx_path),
            "exists": idx_path.exists(),
            "indexed_counts": indexed_counts,
            "missing_file_hints": index_missing_files,
        },
        "objects": {
            "counts": stored_counts,
            "total": sum(stored_counts.values()),
        },
        "simulator": _latest_sim_report_payload(out_dir),
        "simulator_history": _sim_history_payload(out_dir, history_limit),
    }
