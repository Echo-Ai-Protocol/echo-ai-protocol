"""Storage index helpers with corruption recovery."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .io_utils import load_json, write_json
from .types import ID_FIELD_MAP, TYPE_DIR


def index_path(storage_root: Path) -> Path:
    return storage_root / "index.json"


def empty_index() -> Dict[str, List[str]]:
    return {t: [] for t in TYPE_DIR.keys()}


def normalize_index(raw: Any) -> Dict[str, List[str]]:
    idx = empty_index()
    if not isinstance(raw, dict):
        return idx

    for t in idx.keys():
        values = raw.get(t, [])
        if not isinstance(values, list):
            continue
        seen = set()
        clean: List[str] = []
        for v in values:
            if not isinstance(v, str):
                continue
            vv = v.strip()
            if not vv or vv in seen:
                continue
            seen.add(vv)
            clean.append(vv)
        idx[t] = clean

    return idx


def rebuild_index_from_storage(storage_root: Path) -> Dict[str, List[str]]:
    rebuilt = empty_index()

    for object_type, rel_dir in TYPE_DIR.items():
        base = storage_root / rel_dir
        if not base.is_dir():
            continue

        id_field = ID_FIELD_MAP[object_type]
        seen = set()
        for path in sorted(base.iterdir()):
            if not path.is_file() or path.suffix != ".json":
                continue
            try:
                obj = load_json(path)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            raw_id = obj.get(id_field)
            if not isinstance(raw_id, str):
                continue
            obj_id = raw_id.strip()
            if not obj_id or obj_id in seen:
                continue
            seen.add(obj_id)
            rebuilt[object_type].append(obj_id)

    return rebuilt


def load_index(storage_root: Path) -> Dict[str, List[str]]:
    path = index_path(storage_root)
    if not path.exists():
        return empty_index()

    try:
        return normalize_index(load_json(path))
    except Exception:
        # Corrupted index should not break search/store flows.
        rebuilt = rebuild_index_from_storage(storage_root)
        save_index(storage_root, rebuilt)
        return rebuilt


def save_index(storage_root: Path, index: Dict[str, List[str]]) -> None:
    write_json(index_path(storage_root), normalize_index(index))
