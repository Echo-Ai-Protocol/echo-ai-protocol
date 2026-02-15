#!/usr/bin/env python3
"""ECHO Reference Node CLI (v0.9).

Protocol-grade local node operations:
- validate: manifest-driven schema validation
- store: validate + persist object + update storage index
- search: field lookup (equals/contains/prefix) with index-aware path selection
- export: write bundle JSON from local storage
- import: validate full bundle, then atomically store all objects
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from jsonschema import Draft202012Validator


TYPE_TO_FAMILY: Dict[str, str] = {
    "eo": "ExperienceObject",
    "trace": "TraceObject",
    "request": "RequestObject",
    "rr": "ReuseReceipt",
    "aao": "AgentAnnouncement",
    "referral": "ReferralObject",
    "seedupdate": "SeedUpdateObject",
}

TYPE_DIR: Dict[str, str] = {
    "eo": "eo",
    "trace": "trace",
    "request": "request",
    "rr": "rr",
    "aao": "aao",
    "referral": "referral",
    "seedupdate": "seedupdate",
}

ID_FIELD_MAP: Dict[str, str] = {
    "eo": "eo_id",
    "trace": "trace_id",
    "request": "rq_id",
    "rr": "rr_id",
    "aao": "aao_id",
    "referral": "ref_id",
    "seedupdate": "su_id",
}


def _reference_node_dir() -> Path:
    return Path(__file__).resolve().parent


def _repo_root() -> Path:
    return _reference_node_dir().parent


def _default_manifest_path() -> Path:
    return (_reference_node_dir() / "../manifest.json").resolve()


def _default_schemas_dir() -> Path:
    return (_reference_node_dir() / "../schemas").resolve()


def _storage_root() -> Path:
    return _reference_node_dir() / "storage"


def _index_path(storage_root: Path) -> Path:
    return storage_root / "index.json"


def _safe_filename(value: str) -> str:
    trimmed = value.strip() or "unknown"
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in trimmed)


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {path} (line {exc.lineno}, col {exc.colno}): {exc.msg}"
        ) from exc


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    raw = load_json(manifest_path)
    if not isinstance(raw, dict):
        raise ValueError(f"Manifest must be a JSON object: {manifest_path}")
    return raw


def type_to_family(object_type: str) -> str:
    family = TYPE_TO_FAMILY.get(object_type)
    if family:
        return family
    allowed = ", ".join(sorted(TYPE_TO_FAMILY.keys()))
    raise ValueError(f"Unknown type '{object_type}'. Allowed types: {allowed}")


def schema_id_for_type(object_type: str, manifest: Dict[str, Any]) -> str:
    family = type_to_family(object_type)
    schemas = manifest.get("schemas")
    if not isinstance(schemas, dict):
        raise ValueError("manifest.json missing object: 'schemas'")

    family_entry = schemas.get(family)
    if not isinstance(family_entry, dict):
        raise ValueError(f"manifest.json missing schemas['{family}'] entry")

    schema_id = family_entry.get("schema_id")
    if not isinstance(schema_id, str) or not schema_id.strip():
        raise ValueError(f"manifest.json missing valid schema_id for '{family}'")
    return schema_id.strip()


def schema_file_path_for_type(
    object_type: str,
    manifest: Dict[str, Any],
    schemas_dir: Path,
    repo_root: Path,
) -> Path:
    """Resolve schema path from manifest.

    Resolution order:
    1) manifest.schemas[Family].schema_id
    2) manifest.schema_files[Family] filename compatibility with schema_id
    3) final path under schemas_dir
    """
    family = type_to_family(object_type)
    schema_id = schema_id_for_type(object_type, manifest)
    expected_filename = f"{schema_id}.json"

    schema_files = manifest.get("schema_files")
    manifest_filename: Optional[str] = None
    if isinstance(schema_files, dict):
        raw_path = schema_files.get(family)
        if isinstance(raw_path, str) and raw_path.strip():
            manifest_filename = Path(raw_path.strip()).name

    filename = manifest_filename or expected_filename
    if filename != expected_filename:
        raise ValueError(
            f"manifest schema mismatch for '{family}': schema_id '{schema_id}' "
            f"expects '{expected_filename}', got '{filename}'"
        )

    path = (schemas_dir / filename).resolve()

    # If schemas_dir was custom and file is absent there, also allow repo-root relative path
    # from manifest.schema_files for flexibility.
    if not path.exists() and isinstance(schema_files, dict):
        raw_path = schema_files.get(family)
        if isinstance(raw_path, str) and raw_path.strip():
            alt = (repo_root / raw_path.strip()).resolve()
            if alt.exists() and alt.name == expected_filename:
                return alt

    return path


def load_schema_for_type(
    object_type: str,
    manifest_path: Path,
    schemas_dir: Path,
) -> Dict[str, Any]:
    """Load schema object for a protocol type via manifest-driven resolution."""
    manifest = load_manifest(manifest_path)
    schema_path = schema_file_path_for_type(
        object_type=object_type,
        manifest=manifest,
        schemas_dir=schemas_dir,
        repo_root=manifest_path.parent,
    )
    if not schema_path.exists():
        raise FileNotFoundError(
            f"Schema not found for type '{object_type}': {schema_path}"
        )

    schema = load_json(schema_path)
    if not isinstance(schema, dict):
        raise ValueError(f"Invalid schema payload (not object): {schema_path}")
    return schema


def _prepare_for_signature_skip(obj: Dict[str, Any], skip_signature: bool) -> Dict[str, Any]:
    if not skip_signature:
        return obj
    patched = copy.deepcopy(obj)
    signature = patched.get("signature")
    if not isinstance(signature, str) or not signature.strip():
        patched["signature"] = "TEST_SIGNATURE"
    return patched


def _signature_errors(obj: Dict[str, Any], skip_signature: bool) -> List[str]:
    if skip_signature:
        return []
    signature = obj.get("signature")
    if not isinstance(signature, str) or not signature.strip():
        return ["signature: must be a non-empty string"]
    return []


def validate_object(
    object_type: str,
    obj: Dict[str, Any],
    manifest_path: Path,
    schemas_dir: Path,
    skip_signature: bool,
) -> List[str]:
    schema = load_schema_for_type(
        object_type=object_type,
        manifest_path=manifest_path,
        schemas_dir=schemas_dir,
    )
    candidate = _prepare_for_signature_skip(obj, skip_signature=skip_signature)

    validator = Draft202012Validator(schema)
    errors: List[str] = []
    for err in sorted(validator.iter_errors(candidate), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path) if err.path else "(root)"
        errors.append(f"{loc}: {err.message}")

    errors.extend(_signature_errors(obj, skip_signature=skip_signature))
    return errors


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


def load_index(storage_root: Path) -> Dict[str, List[str]]:
    path = _index_path(storage_root)
    if not path.exists():
        return empty_index()
    try:
        return normalize_index(load_json(path))
    except Exception:
        # Recover from a corrupted index file by rebuilding lazily from fresh stores.
        # This keeps node operations resilient if a previous run was interrupted.
        return empty_index()


def save_index(storage_root: Path, index: Dict[str, List[str]]) -> None:
    write_json(_index_path(storage_root), normalize_index(index))


def object_id_for_type(object_type: str, obj: Dict[str, Any]) -> str:
    id_field = ID_FIELD_MAP[object_type]
    raw = obj.get(id_field)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"Missing or invalid id field '{id_field}' for type '{object_type}'")
    return raw.strip()


def storage_path_for_id(storage_root: Path, object_type: str, obj_id: str) -> Path:
    base = storage_root / TYPE_DIR[object_type]
    return base / f"{_safe_filename(obj_id)}.json"


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


def infer_object_type(obj: Dict[str, Any]) -> str:
    matches: List[str] = []
    for t, id_field in ID_FIELD_MAP.items():
        val = obj.get(id_field)
        if isinstance(val, str) and val.strip():
            matches.append(t)

    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError("Unable to infer object type: none of known id fields present")
    raise ValueError(f"Unable to infer object type: multiple id fields present ({', '.join(matches)})")


def _parse_common_paths(args: argparse.Namespace) -> Tuple[Path, Path, Path]:
    manifest_path = Path(args.manifest).expanduser().resolve()
    schemas_dir = Path(args.schemas_dir).expanduser().resolve()
    storage_root = _storage_root()
    return manifest_path, schemas_dir, storage_root


def _print_validation_errors(errors: List[str]) -> None:
    for msg in errors[:50]:
        print(f" - {msg}")
    if len(errors) > 50:
        print(f" - ... and {len(errors) - 50} more error(s)")


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        manifest_path, schemas_dir, _ = _parse_common_paths(args)
        raw = load_json(Path(args.file).expanduser().resolve())
        if not isinstance(raw, dict):
            print("VALIDATION: FAIL")
            print(" - (root): object must be a JSON object")
            return 2

        errors = validate_object(
            object_type=args.type,
            obj=raw,
            manifest_path=manifest_path,
            schemas_dir=schemas_dir,
            skip_signature=args.skip_signature,
        )
    except (FileNotFoundError, ValueError) as exc:
        print("VALIDATION: FAIL")
        print(f" - {exc}")
        return 2
    except Exception as exc:
        print("VALIDATION: FAIL")
        print(f" - unexpected error: {exc}")
        return 2

    if errors:
        print("VALIDATION: FAIL")
        _print_validation_errors(errors)
        return 2

    print("VALIDATION: OK")
    return 0


def cmd_store(args: argparse.Namespace) -> int:
    try:
        manifest_path, schemas_dir, storage_root = _parse_common_paths(args)
        raw = load_json(Path(args.file).expanduser().resolve())
        if not isinstance(raw, dict):
            print("VALIDATION: FAIL")
            print(" - (root): object must be a JSON object")
            return 2

        errors = validate_object(
            object_type=args.type,
            obj=raw,
            manifest_path=manifest_path,
            schemas_dir=schemas_dir,
            skip_signature=args.skip_signature,
        )
        if errors:
            print("VALIDATION: FAIL")
            _print_validation_errors(errors)
            return 2

        out = store_object(storage_root=storage_root, object_type=args.type, obj=raw)
    except (FileNotFoundError, ValueError) as exc:
        print("STORE: FAIL")
        print(f" - {exc}")
        return 2
    except Exception as exc:
        print("STORE: FAIL")
        print(f" - unexpected error: {exc}")
        return 2

    print("VALIDATION: OK")
    print(f"STORED: {out}")
    return 0


def _match_string(value: Any, equals: Optional[str], contains: Optional[str], prefix: Optional[str]) -> bool:
    as_text = str(value)
    if equals is not None:
        return as_text == equals
    if contains is not None:
        return contains in as_text
    if prefix is not None:
        return as_text.startswith(prefix)
    return False


def _op_to_match_kwargs(op: str, value: str) -> Dict[str, Optional[str]]:
    if op == "equals":
        return {"equals": value, "contains": None, "prefix": None}
    if op == "contains":
        return {"equals": None, "contains": value, "prefix": None}
    if op == "prefix":
        return {"equals": None, "contains": None, "prefix": value}
    raise ValueError("Unsupported search op. Use one of: equals, contains, prefix")


def _candidate_paths_from_index(
    storage_root: Path,
    object_type: str,
    field: str,
    equals: Optional[str],
    contains: Optional[str],
    prefix: Optional[str],
) -> List[Path]:
    """Use index.json when possible for faster candidate path selection."""
    index = load_index(storage_root)
    ids = index.get(object_type, [])
    if not ids:
        return []

    id_field = ID_FIELD_MAP[object_type]
    if field == id_field:
        selected: List[str] = []
        for obj_id in ids:
            if _match_string(obj_id, equals=equals, contains=contains, prefix=prefix):
                selected.append(obj_id)
        return [storage_path_for_id(storage_root, object_type, obj_id) for obj_id in selected]

    # For non-id fields we still use index IDs to avoid directory scans.
    return [storage_path_for_id(storage_root, object_type, obj_id) for obj_id in ids]


def search_objects(
    storage_root: Path,
    object_type: str,
    field: str,
    op: str,
    value: str,
) -> List[Dict[str, Any]]:
    """Search objects by field using simple textual operations.

    Returned item shape:
    {
      "path": "<abs/path/to/object.json>",
      "object": {...parsed json object...}
    }
    """
    kwargs = _op_to_match_kwargs(op=op, value=value)
    indexed_paths = _candidate_paths_from_index(
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
        if _match_string(
            obj.get(field),
            equals=kwargs["equals"],
            contains=kwargs["contains"],
            prefix=kwargs["prefix"],
        ):
            hits.append({"path": str(path), "object": obj})
    return hits


def cmd_search(args: argparse.Namespace) -> int:
    try:
        _, _, storage_root = _parse_common_paths(args)
        if args.equals is not None:
            op = "equals"
            value = args.equals
        elif args.contains is not None:
            op = "contains"
            value = args.contains
        else:
            op = "prefix"
            value = args.prefix

        hits = search_objects(
            storage_root=storage_root,
            object_type=args.type,
            field=args.field,
            op=op,
            value=value,
        )

    except (FileNotFoundError, ValueError) as exc:
        print("SEARCH: FAIL")
        print(f" - {exc}")
        return 2
    except Exception as exc:
        print("SEARCH: FAIL")
        print(f" - unexpected error: {exc}")
        return 2

    print(f"count: {len(hits)}")
    for item in hits[: args.limit]:
        print(f"- {item['path']}")
    if len(hits) > args.limit:
        print(f"... {len(hits) - args.limit} more match(es)")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    try:
        manifest_path, _, storage_root = _parse_common_paths(args)
        manifest = load_manifest(manifest_path)

        objects: List[Dict[str, Any]] = []
        for path in iter_stored_paths(storage_root, args.type):
            obj = load_json(path)
            if not isinstance(obj, dict):
                raise ValueError(f"Stored object must be JSON object: {path}")
            objects.append(obj)

        bundle = {
            "manifest_version": manifest.get("manifest_version"),
            "protocol_version": manifest.get("protocol_version"),
            "objects": objects,
        }

        out_path = Path(args.out).expanduser().resolve()
        write_json(out_path, bundle)

    except (FileNotFoundError, ValueError) as exc:
        print("EXPORT: FAIL")
        print(f" - {exc}")
        return 2
    except Exception as exc:
        print("EXPORT: FAIL")
        print(f" - unexpected error: {exc}")
        return 2

    print(f"EXPORT: OK ({len(objects)} objects)")
    print(f"WROTE: {out_path}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    try:
        manifest_path, schemas_dir, storage_root = _parse_common_paths(args)
        bundle = load_json(Path(args.file).expanduser().resolve())
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
                skip_signature=args.skip_signature,
            )
            if errs:
                for e in errs:
                    validation_errors.append(f"objects[{i}] ({object_type}:{object_id}): {e}")
                continue

            staged.append((object_type, item, object_id))

        if validation_errors:
            print("IMPORT: FAIL")
            _print_validation_errors(validation_errors)
            print(" - bundle rejected: no objects were stored")
            return 2

        for object_type, item, _ in staged:
            store_object(storage_root=storage_root, object_type=object_type, obj=item)

    except (FileNotFoundError, ValueError) as exc:
        print("IMPORT: FAIL")
        print(f" - {exc}")
        return 2
    except Exception as exc:
        print("IMPORT: FAIL")
        print(f" - unexpected error: {exc}")
        return 2

    print(f"IMPORT: OK ({len(staged)} objects)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ECHO reference node CLI (v0.9)")
    parser.add_argument(
        "--manifest",
        default=str(_default_manifest_path()),
        help="Path to protocol manifest (default: ../manifest.json relative to reference-node)",
    )
    parser.add_argument(
        "--schemas-dir",
        default=str(_default_schemas_dir()),
        help="Path to schemas directory (default: ../schemas relative to reference-node)",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_validate = sub.add_parser("validate", help="Validate object against manifest-routed schema")
    p_validate.add_argument("--type", required=True, choices=sorted(TYPE_TO_FAMILY.keys()))
    p_validate.add_argument("--file", required=True, help="Path to input JSON file")
    p_validate.add_argument("--skip-signature", action="store_true", help="Bypass signature checks")
    p_validate.set_defaults(func=cmd_validate)

    p_store = sub.add_parser("store", help="Validate and store object")
    p_store.add_argument("--type", required=True, choices=sorted(TYPE_TO_FAMILY.keys()))
    p_store.add_argument("--file", required=True, help="Path to input JSON file")
    p_store.add_argument("--skip-signature", action="store_true", help="Bypass signature checks")
    p_store.set_defaults(func=cmd_store)

    p_search = sub.add_parser("search", help="Search stored objects by field")
    p_search.add_argument("--type", required=True, choices=sorted(TYPE_TO_FAMILY.keys()))
    p_search.add_argument("--field", required=True, help="Top-level field name")
    mode = p_search.add_mutually_exclusive_group(required=True)
    mode.add_argument("--equals", help="Strict equality")
    mode.add_argument("--contains", help="Substring match")
    mode.add_argument("--prefix", help="Prefix match")
    p_search.add_argument("--limit", type=int, default=50, help="Max results to print")
    p_search.set_defaults(func=cmd_search)

    p_export = sub.add_parser("export", help="Export stored objects of one type to bundle JSON")
    p_export.add_argument("--type", required=True, choices=sorted(TYPE_TO_FAMILY.keys()))
    p_export.add_argument("--out", required=True, help="Output bundle file path")
    p_export.set_defaults(func=cmd_export)

    p_import = sub.add_parser("import", help="Import bundle JSON (validate all before store)")
    p_import.add_argument("--file", required=True, help="Path to bundle JSON file")
    p_import.add_argument("--skip-signature", action="store_true", help="Bypass signature checks")
    p_import.set_defaults(func=cmd_import)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if getattr(args, "limit", 0) is not None and getattr(args, "limit", 0) < 0:
        print("SEARCH: FAIL")
        print(" - --limit must be >= 0")
        return 2

    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
