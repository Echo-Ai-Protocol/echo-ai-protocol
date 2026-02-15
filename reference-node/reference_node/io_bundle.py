"""Bundle import/export operations for reference-node."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from .io_utils import load_json, write_json
from .store import iter_stored_paths, object_id_for_type, store_object
from .types import ID_FIELD_MAP
from .validate import load_manifest, validate_object


def infer_object_type(obj: Dict[str, Any]) -> str:
    matches: List[str] = []
    for object_type, id_field in ID_FIELD_MAP.items():
        val = obj.get(id_field)
        if isinstance(val, str) and val.strip():
            matches.append(object_type)

    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError("Unable to infer object type: none of known id fields present")
    raise ValueError(f"Unable to infer object type: multiple id fields present ({', '.join(matches)})")


def export_bundle(
    storage_root: Path,
    manifest_path: Path,
    object_type: str,
    out_path: Path,
) -> Dict[str, Any]:
    manifest = load_manifest(manifest_path)

    objects: List[Dict[str, Any]] = []
    for path in iter_stored_paths(storage_root, object_type):
        obj = load_json(path)
        if not isinstance(obj, dict):
            raise ValueError(f"Stored object must be JSON object: {path}")
        objects.append(obj)

    bundle = {
        "manifest_version": manifest.get("manifest_version"),
        "protocol_version": manifest.get("protocol_version"),
        "objects": objects,
    }

    write_json(out_path, bundle)
    return bundle


def import_bundle(
    storage_root: Path,
    manifest_path: Path,
    schemas_dir: Path,
    bundle_path: Path,
    skip_signature: bool,
) -> int:
    bundle = load_json(bundle_path)
    if not isinstance(bundle, dict):
        raise ValueError("Bundle must be a JSON object")

    objects = bundle.get("objects")
    if not isinstance(objects, list):
        raise ValueError("Bundle must contain 'objects' array")

    staged: List[Tuple[str, Dict[str, Any], str]] = []
    seen_keys = set()
    validation_errors: List[str] = []

    for i, item in enumerate(objects):
        if not isinstance(item, dict):
            validation_errors.append(f"objects[{i}]: must be a JSON object")
            continue

        try:
            object_type = infer_object_type(item)
        except ValueError as exc:
            validation_errors.append(f"objects[{i}]: {exc}")
            continue

        try:
            object_id = object_id_for_type(object_type, item)
        except ValueError as exc:
            validation_errors.append(f"objects[{i}]: {exc}")
            continue

        key = (object_type, object_id)
        if key in seen_keys:
            validation_errors.append(
                f"objects[{i}]: duplicate object in bundle ({object_type}:{object_id})"
            )
            continue
        seen_keys.add(key)

        errs = validate_object(
            object_type=object_type,
            obj=item,
            manifest_path=manifest_path,
            schemas_dir=schemas_dir,
            skip_signature=skip_signature,
        )
        if errs:
            for err in errs:
                validation_errors.append(f"objects[{i}] ({object_type}:{object_id}): {err}")
            continue

        staged.append((object_type, item, object_id))

    if validation_errors:
        msg = "\n".join(validation_errors)
        raise ValueError(f"Bundle validation failed:\n{msg}")

    for object_type, item, _ in staged:
        store_object(storage_root=storage_root, object_type=object_type, obj=item)

    return len(staged)
