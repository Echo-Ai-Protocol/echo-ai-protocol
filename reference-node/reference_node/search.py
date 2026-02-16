"""Search operations with pluggable ranking hooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .index import load_index
from .io_utils import load_json
from .store import iter_stored_paths, storage_path_for_id
from .types import ID_FIELD_MAP, SEARCH_OPS

SearchRanker = Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]]


def match_string(
    value: Any,
    equals: Optional[str],
    contains: Optional[str],
    prefix: Optional[str],
) -> bool:
    as_text = str(value)
    if equals is not None:
        return as_text == equals
    if contains is not None:
        return contains in as_text
    if prefix is not None:
        return as_text.startswith(prefix)
    return False


def op_to_match_kwargs(op: str, value: str) -> Dict[str, Optional[str]]:
    if op == "equals":
        return {"equals": value, "contains": None, "prefix": None}
    if op == "contains":
        return {"equals": None, "contains": value, "prefix": None}
    if op == "prefix":
        return {"equals": None, "contains": None, "prefix": value}
    raise ValueError("Unsupported search op. Use one of: equals, contains, prefix")


def candidate_paths_from_index(
    storage_root: Path,
    object_type: str,
    field: str,
    equals: Optional[str],
    contains: Optional[str],
    prefix: Optional[str],
) -> List[Path]:
    index = load_index(storage_root)
    ids = index.get(object_type, [])
    if not ids:
        return []

    id_field = ID_FIELD_MAP[object_type]
    if field == id_field:
        selected: List[str] = []
        for obj_id in ids:
            if match_string(obj_id, equals=equals, contains=contains, prefix=prefix):
                selected.append(obj_id)
        return [storage_path_for_id(storage_root, object_type, obj_id) for obj_id in selected]

    return [storage_path_for_id(storage_root, object_type, obj_id) for obj_id in ids]


def search_objects(
    storage_root: Path,
    object_type: str,
    field: str,
    op: str,
    value: str,
    ranker: Optional[SearchRanker] = None,
) -> List[Dict[str, Any]]:
    if op not in SEARCH_OPS:
        raise ValueError("Unsupported search op. Use one of: equals, contains, prefix")

    kwargs = op_to_match_kwargs(op=op, value=value)
    indexed_paths = candidate_paths_from_index(
        storage_root=storage_root,
        object_type=object_type,
        field=field,
        equals=kwargs["equals"],
        contains=kwargs["contains"],
        prefix=kwargs["prefix"],
    )

    if indexed_paths:
        candidates = [p for p in indexed_paths if p.exists()]
    else:
        candidates = list(iter_stored_paths(storage_root, object_type))

    hits: List[Dict[str, Any]] = []
    for path in candidates:
        try:
            obj = load_json(path)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        if field not in obj:
            continue
        if match_string(
            obj.get(field),
            equals=kwargs["equals"],
            contains=kwargs["contains"],
            prefix=kwargs["prefix"],
        ):
            hits.append({"path": str(path), "object": obj})

    if ranker is not None:
        return ranker(hits)
    return hits
