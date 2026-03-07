from __future__ import annotations

import json
from pathlib import Path

import pytest

import reference_node as core
import server


def _load_sample(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_idempotent_store_ignores_duplicates(tmp_path: Path, sample_dir: Path) -> None:
    storage_root = tmp_path / "storage"
    eo = _load_sample(sample_dir / "eo.sample.json")
    eo["eo_id"] = "echo.eo.agent.ext-ai-test.coding.task-1.run-1"

    first = core.store_object_idempotent(storage_root=storage_root, object_type="eo", obj=eo)
    second = core.store_object_idempotent(storage_root=storage_root, object_type="eo", obj=eo)

    assert first["status"] == "stored"
    assert second["status"] == "duplicate_ignored"

    stats = core.compute_stats(storage_root=storage_root)
    assert stats["objects"]["counts"]["eo"] == 1


def test_http_objects_returns_duplicate_ignored(
    tmp_path: Path, manifest_path: Path, schemas_dir: Path, sample_dir: Path
) -> None:
    if server.HTTP_IMPORT_ERROR is not None:
        pytest.skip("HTTP dependencies are unavailable")
    fastapi = pytest.importorskip("fastapi.testclient")
    TestClient = fastapi.TestClient

    storage_root = tmp_path / "storage"
    tools_out = tmp_path / "tools_out"
    config = server.NodeConfig(
        manifest_path=manifest_path,
        schemas_dir=schemas_dir,
        storage_root=storage_root,
        tools_out_dir=tools_out,
        capabilities_path=Path(core.default_capabilities_path()),
        require_signature=False,
    )
    app = server.create_app(config)
    client = TestClient(app)

    eo = _load_sample(sample_dir / "eo.sample.json")
    eo["eo_id"] = "echo.eo.agent.ext-ai-http.coding.task-1.run-1"
    payload = {"type": "eo", "object_json": eo, "skip_signature": False}

    r1 = client.post("/objects", json=payload)
    r2 = client.post("/objects", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["status"] == "stored"
    assert r2.json()["status"] == "duplicate_ignored"

    stats = client.get("/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["network_objects"]["eo_total"] == 1
