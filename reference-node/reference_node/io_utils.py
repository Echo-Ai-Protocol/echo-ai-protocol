"""Path + JSON helpers shared by the reference-node package."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def package_dir() -> Path:
    return Path(__file__).resolve().parent


def reference_node_dir() -> Path:
    return package_dir().parent


def repo_root() -> Path:
    return reference_node_dir().parent


def default_manifest_path() -> Path:
    return (reference_node_dir() / "../manifest.json").resolve()


def default_schemas_dir() -> Path:
    return (reference_node_dir() / "../schemas").resolve()


def default_storage_root() -> Path:
    return reference_node_dir() / "storage"


def default_capabilities_path() -> Path:
    return reference_node_dir() / "capabilities.local.json"


def default_tools_out_dir() -> Path:
    return repo_root() / "tools" / "out"


def safe_filename(value: str) -> str:
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
