from __future__ import annotations

from pathlib import Path

import pytest

import reference_node as core
import server


def _make_client(tmp_path: Path, manifest_path: Path, schemas_dir: Path):
    if server.HTTP_IMPORT_ERROR is not None:
        pytest.skip("HTTP dependencies are unavailable")
    fastapi = pytest.importorskip("fastapi.testclient")
    test_client = fastapi.TestClient

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
    return test_client(app)


def test_ingest_creates_eo_and_updates_registry(tmp_path: Path, manifest_path: Path, schemas_dir: Path) -> None:
    client = _make_client(tmp_path, manifest_path, schemas_dir)

    payload = {
        "integration_id": "ext-real-001",
        "agent_name": "AcmeCoder",
        "lane": "code",
        "object_type": "eo",
        "payload": {
            "problem": "Need deterministic parser pipeline",
            "constraints": "stdlib only",
            "solution": "Use split phases and strict checks",
            "outcome_metrics": {"effectiveness_score": 0.82, "stability_score": 0.77, "iterations": 1},
        },
    }

    res = client.post("/ingest", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "stored"
    assert body["object_type"] == "eo"
    assert body["agent_registered"] is True
    object_id = body["object_id"]
    assert isinstance(object_id, str) and object_id.startswith("echo.eo.agent.ext-real-001.code.by.acmecoder.")

    get_obj = client.get(f"/objects/eo/{object_id}")
    assert get_obj.status_code == 200

    agents = client.get("/agents")
    assert agents.status_code == 200
    rows = agents.json()["agents"]
    row = next((r for r in rows if r.get("agent_did") == "did:echo:agent.ext-real-001.acmecoder"), None)
    assert row is not None
    assert row["integration_id"] == "ext-real-001"
    assert row["agent_name"] == "acmecoder"
    assert row["lane"] == "code"
    assert int(row["eo_created"]) == 1


def test_ingest_duplicate_is_ignored_via_idempotency(tmp_path: Path, manifest_path: Path, schemas_dir: Path) -> None:
    client = _make_client(tmp_path, manifest_path, schemas_dir)
    payload = {
        "integration_id": "ext-real-002",
        "agent_name": "AcmeResearch",
        "lane": "research",
        "object_type": "trace",
        "payload": {
            "domain_embedding": "domain::research",
            "activity_type": "ASK",
            "refs": ["echo.eo.sample.v1"],
        },
        "idempotency_key": "same-trace",
    }

    r1 = client.post("/ingest", json=payload)
    r2 = client.post("/ingest", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["status"] == "stored"
    assert r2.json()["status"] == "duplicate_ignored"
    assert r1.json()["object_id"] == r2.json()["object_id"]
    assert r1.json()["agent_registered"] is True
    assert r2.json()["agent_registered"] is False


def test_playground_run_creates_eo_and_trace(tmp_path: Path, manifest_path: Path, schemas_dir: Path) -> None:
    client = _make_client(tmp_path, manifest_path, schemas_dir)
    req = {
        "agent_name": "PlayOps",
        "lane": "ops",
        "task": "Check runbook freshness",
        "integration_id": "playground",
    }

    run = client.post("/playground/run", json=req)
    assert run.status_code == 200
    body = run.json()
    assert body["status"] == "ok"
    assert body["eo_status"] in {"stored", "duplicate_ignored"}
    assert body["trace_status"] in {"stored", "duplicate_ignored"}

    eo_id = body["eo_id"]
    trace_id = body["trace_id"]
    assert client.get(f"/objects/eo/{eo_id}").status_code == 200
    assert client.get(f"/objects/trace/{trace_id}").status_code == 200
