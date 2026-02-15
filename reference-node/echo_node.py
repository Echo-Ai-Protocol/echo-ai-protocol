#!/usr/bin/env python3
"""ECHO Reference Node CLI (v1.1 core stabilization).

Thin CLI wrapper over the importable `reference_node` package.
Commands remain backward compatible:
- validate
- store
- search
- export
- import
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

import reference_node as core


# Backward-compatible names used by existing scripts.
TYPE_TO_FAMILY = core.TYPE_TO_FAMILY
TYPE_DIR = core.TYPE_DIR
ID_FIELD_MAP = core.ID_FIELD_MAP
load_json = core.load_json
write_json = core.write_json
load_manifest = core.load_manifest
load_schema_for_type = core.load_schema_for_type
validate_object = core.validate_object
store_object = core.store_object
search_objects = core.search_objects
iter_stored_paths = core.iter_stored_paths
object_id_for_type = core.object_id_for_type
infer_object_type = core.infer_object_type
load_index = core.load_index
save_index = core.save_index


def _default_manifest_path() -> Path:
    return core.default_manifest_path()


def _default_schemas_dir() -> Path:
    return core.default_schemas_dir()


def _storage_root() -> Path:
    return core.default_storage_root()


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
        raw = core.load_json(Path(args.file).expanduser().resolve())
        if not isinstance(raw, dict):
            print("VALIDATION: FAIL")
            print(" - (root): object must be a JSON object")
            return 2

        errors = core.validate_object(
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
        raw = core.load_json(Path(args.file).expanduser().resolve())
        if not isinstance(raw, dict):
            print("VALIDATION: FAIL")
            print(" - (root): object must be a JSON object")
            return 2

        errors = core.validate_object(
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

        out = core.store_object(storage_root=storage_root, object_type=args.type, obj=raw)
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

        hits = core.search_objects(
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
        out_path = Path(args.out).expanduser().resolve()
        bundle = core.export_bundle(
            storage_root=storage_root,
            manifest_path=manifest_path,
            object_type=args.type,
            out_path=out_path,
        )
    except (FileNotFoundError, ValueError) as exc:
        print("EXPORT: FAIL")
        print(f" - {exc}")
        return 2
    except Exception as exc:
        print("EXPORT: FAIL")
        print(f" - unexpected error: {exc}")
        return 2

    print(f"EXPORT: OK ({len(bundle.get('objects', []))} objects)")
    print(f"WROTE: {out_path}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    try:
        manifest_path, schemas_dir, storage_root = _parse_common_paths(args)
        count = core.import_bundle(
            storage_root=storage_root,
            manifest_path=manifest_path,
            schemas_dir=schemas_dir,
            bundle_path=Path(args.file).expanduser().resolve(),
            skip_signature=args.skip_signature,
        )
    except (FileNotFoundError, ValueError) as exc:
        print("IMPORT: FAIL")
        text = str(exc)
        if text.startswith("Bundle validation failed:"):
            body = text.split("\n", 1)
            if len(body) == 2:
                _print_validation_errors(body[1].splitlines())
            else:
                print(f" - {text}")
            print(" - bundle rejected: no objects were stored")
        else:
            print(f" - {text}")
        return 2
    except Exception as exc:
        print("IMPORT: FAIL")
        print(f" - unexpected error: {exc}")
        return 2

    print(f"IMPORT: OK ({count} objects)")
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
