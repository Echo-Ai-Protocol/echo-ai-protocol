"""Manifest-driven schema validation for reference-node objects."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, List, Optional

from jsonschema import Draft202012Validator

from .io_utils import load_json
from .types import type_to_family


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    raw = load_json(manifest_path)
    if not isinstance(raw, dict):
        raise ValueError(f"Manifest must be a JSON object: {manifest_path}")
    return raw


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


def resolve_schema_path(
    object_type: str,
    manifest: Dict[str, Any],
    schemas_dir: Path,
    repo_root: Path,
) -> Path:
    """Resolve schema path from manifest.schema_id and optional schema_files hints."""
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
    manifest = load_manifest(manifest_path)
    schema_path = resolve_schema_path(
        object_type=object_type,
        manifest=manifest,
        schemas_dir=schemas_dir,
        repo_root=manifest_path.parent,
    )

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found for type '{object_type}': {schema_path}")

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
    candidate = _prepare_for_signature_skip(obj=obj, skip_signature=skip_signature)

    validator = Draft202012Validator(schema)
    errors: List[str] = []
    for err in sorted(validator.iter_errors(candidate), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path) if err.path else "(root)"
        errors.append(f"{loc}: {err.message}")

    errors.extend(_signature_errors(obj=obj, skip_signature=skip_signature))
    return errors
