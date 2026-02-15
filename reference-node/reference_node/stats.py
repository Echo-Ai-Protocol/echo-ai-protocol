"""Operational stats helpers for local reference-node observability."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .index import index_path, load_index
from .store import iter_stored_paths
from .types import TYPE_DIR


def compute_stats(storage_root: Path) -> Dict[str, Any]:
    idx = load_index(storage_root)
    idx_path = index_path(storage_root)

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
    }
