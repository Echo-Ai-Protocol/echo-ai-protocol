from __future__ import annotations

import json
from pathlib import Path

import pytest

import reference_node as core
import server


def _load_sample(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_agent_registry_updates_on_eo_rr_trace_store(tmp_path: Path, sample_dir: Path) -> None:
    storage_root = tmp_path / "storage"
    did = "did:echo:agent.ext-ai-001.coding"

    eo = _load_sample(sample_dir / "eo.sample.json")
    eo["eo_id"] = "echo.eo.agent.ext-ai-001.coding.task-1.run-1"

    rr = _load_sample(sample_dir / "rr.sample.json")
    rr["rr_id"] = "echo.rr.agent.ext-ai-001.coding.task-1.run-1"
    rr["issuer_agent_did"] = did
    rr["target_eo_id"] = eo["eo_id"]

    trace = _load_sample(sample_dir / "trace.sample.json")
    trace["trace_id"] = "echo.trace.agent.ext-ai-001.coding.task-1.run-1"
    trace["agent_did"] = did
    trace["refs"] = [eo["eo_id"], rr["rr_id"]]

    core.store_object_idempotent(storage_root=storage_root, object_type="eo", obj=eo)
    core.store_object_idempotent(storage_root=storage_root, object_type="rr", obj=rr)
    core.store_object_idempotent(storage_root=storage_root, object_type="trace", obj=trace)

    rows = core.load_agent_registry(storage_root)
    match = next((r for r in rows if r.get("agent_did") == did), None)
    assert match is not None
    assert match["integration_id"] == "ext-ai-001"
    assert match["lane"] == "coding"
    assert int(match["eo_created"]) == 1
    assert int(match["rr_created"]) == 1
    assert int(match["trace_created"]) == 1
    assert isinstance(match["first_seen"], str) and match["first_seen"]
    assert isinstance(match["last_seen"], str) and match["last_seen"]


def test_agents_endpoint_returns_registry(
    tmp_path: Path, manifest_path: Path, schemas_dir: Path, sample_dir: Path
) -> None:
    if server.HTTP_IMPORT_ERROR is not None:
        pytest.skip("HTTP dependencies are unavailable")
    fastapi = pytest.importorskip("fastapi.testclient")
    TestClient = fastapi.TestClient

    storage_root = tmp_path / "storage"
    tools_out = tmp_path / "tools_out"
    did = "did:echo:agent.ext-ai-001.research"

    trace = _load_sample(sample_dir / "trace.sample.json")
    trace["trace_id"] = "echo.trace.agent.ext-ai-001.research.task-1.run-1"
    trace["agent_did"] = did
    core.store_object_idempotent(storage_root=storage_root, object_type="trace", obj=trace)

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

    res = client.get("/agents")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] >= 1
    assert body["summary"]["total_known_agents"] >= 1
    assert any(item.get("agent_did") == did for item in body["agents"])
