"""File store operations for reference-node objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable

from .index import load_index, save_index
from .io_utils import safe_filename, write_json
from .types import ID_FIELD_MAP, TYPE_DIR


def object_id_for_type(object_type: str, obj: Dict[str, Any]) -> str:
    id_field = ID_FIELD_MAP[object_type]
    raw = obj.get(id_field)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"Missing or invalid id field '{id_field}' for type '{object_type}'")
    return raw.strip()


def storage_path_for_id(storage_root: Path, object_type: str, obj_id: str) -> Path:
    base = storage_root / TYPE_DIR[object_type]
    return base / f"{safe_filename(obj_id)}.json"


def iter_stored_paths(storage_root: Path, object_type: str) -> Iterable[Path]:
    base = storage_root / TYPE_DIR[object_type]
    if not base.is_dir():
        return []
    return (p for p in sorted(base.iterdir()) if p.is_file() and p.suffix == ".json")


def store_object(storage_root: Path, object_type: str, obj: Dict[str, Any]) -> Path:
    obj_id = object_id_for_type(object_type, obj)
    out = storage_path_for_id(storage_root, object_type, obj_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, obj)

    index = load_index(storage_root)
    if obj_id not in index[object_type]:
        index[object_type].append(obj_id)
        save_index(storage_root, index)

    return out
