from __future__ import annotations

import json
from pathlib import Path

import reference_node as core


def load_sample(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_validate_store_and_search_ops(tmp_path: Path, manifest_path: Path, schemas_dir: Path, sample_dir: Path) -> None:
    storage_root = tmp_path / "storage"
    eo = load_sample(sample_dir / "eo.sample.json")

    errors = core.validate_object(
        object_type="eo",
        obj=eo,
        manifest_path=manifest_path,
        schemas_dir=schemas_dir,
        skip_signature=False,
    )
    assert errors == []

    stored_path = core.store_object(storage_root=storage_root, object_type="eo", obj=eo)
    assert stored_path.exists()

    eq_hits = core.search_objects(
        storage_root=storage_root,
        object_type="eo",
        field="eo_id",
        op="equals",
        value=eo["eo_id"],
    )
    assert len(eq_hits) == 1

    contains_hits = core.search_objects(
        storage_root=storage_root,
        object_type="eo",
        field="eo_id",
        op="contains",
        value="echo.eo.sample",
    )
    assert len(contains_hits) == 1

    prefix_hits = core.search_objects(
        storage_root=storage_root,
        object_type="eo",
        field="eo_id",
        op="prefix",
        value="echo.eo",
    )
    assert len(prefix_hits) == 1


def test_signature_bypass_mode(tmp_path: Path, manifest_path: Path, schemas_dir: Path, sample_dir: Path) -> None:
    _ = tmp_path
    eo = load_sample(sample_dir / "eo.sample.json")
    eo.pop("signature", None)

    strict_errors = core.validate_object(
        object_type="eo",
        obj=eo,
        manifest_path=manifest_path,
        schemas_dir=schemas_dir,
        skip_signature=False,
    )
    assert strict_errors

    bypass_errors = core.validate_object(
        object_type="eo",
        obj=eo,
        manifest_path=manifest_path,
        schemas_dir=schemas_dir,
        skip_signature=True,
    )
    assert bypass_errors == []
