from __future__ import annotations

import json
from pathlib import Path

import reference_node as core


def load_sample(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_index_corruption_recovery(tmp_path: Path, sample_dir: Path) -> None:
    storage_root = tmp_path / "storage"
    eo = load_sample(sample_dir / "eo.sample.json")

    core.store_object(storage_root=storage_root, object_type="eo", obj=eo)

    # Simulate interrupted write/corruption.
    index_file = storage_root / "index.json"
    index_file.write_text("{not-json", encoding="utf-8")

    recovered = core.load_index(storage_root)
    assert eo["eo_id"] in recovered["eo"]

    # Search remains functional after recovery path.
    hits = core.search_objects(
        storage_root=storage_root,
        object_type="eo",
        field="eo_id",
        op="equals",
        value=eo["eo_id"],
    )
    assert len(hits) == 1
