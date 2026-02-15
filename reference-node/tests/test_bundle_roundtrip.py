from __future__ import annotations

import json
from pathlib import Path

import reference_node as core


def load_sample(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_export_import_roundtrip(tmp_path: Path, manifest_path: Path, schemas_dir: Path, sample_dir: Path) -> None:
    source_storage = tmp_path / "src_storage"
    target_storage = tmp_path / "dst_storage"
    bundle_path = tmp_path / "eo_bundle.json"

    eo = load_sample(sample_dir / "eo.sample.json")
    core.store_object(storage_root=source_storage, object_type="eo", obj=eo)

    bundle = core.export_bundle(
        storage_root=source_storage,
        manifest_path=manifest_path,
        object_type="eo",
        out_path=bundle_path,
    )
    assert bundle_path.exists()
    assert isinstance(bundle.get("objects"), list)
    assert len(bundle["objects"]) == 1

    imported_count = core.import_bundle(
        storage_root=target_storage,
        manifest_path=manifest_path,
        schemas_dir=schemas_dir,
        bundle_path=bundle_path,
        skip_signature=False,
    )
    assert imported_count == 1

    hits = core.search_objects(
        storage_root=target_storage,
        object_type="eo",
        field="eo_id",
        op="equals",
        value=eo["eo_id"],
    )
    assert len(hits) == 1
