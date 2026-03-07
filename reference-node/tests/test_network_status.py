from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import reference_node as core
import server


def _load_sample(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_network_status_script_generates_json(repo_root: Path, tmp_path: Path, sample_dir: Path) -> None:
    storage_root = tmp_path / "storage"
    tools_out = tmp_path / "tools_out"
    out_path = tools_out / "live_network_status.json"

    eo = _load_sample(sample_dir / "eo.sample.json")
    eo["eo_id"] = "echo.eo.agent.ext-ai-001.coding.task-1.run-1"
    rr = _load_sample(sample_dir / "rr.sample.json")
    rr["rr_id"] = "echo.rr.agent.ext-ai-001.coding.task-1.run-1"
    rr["target_eo_id"] = eo["eo_id"]
    rr["issuer_agent_did"] = "did:echo:agent.ext-ai-001.coding"
    trace = _load_sample(sample_dir / "trace.sample.json")
    trace["trace_id"] = "echo.trace.agent.ext-ai-001.coding.task-1.run-1"
    trace["agent_did"] = "did:echo:agent.ext-ai-001.coding"

    core.store_object_idempotent(storage_root=storage_root, object_type="eo", obj=eo)
    core.store_object_idempotent(storage_root=storage_root, object_type="rr", obj=rr)
    core.store_object_idempotent(storage_root=storage_root, object_type="trace", obj=trace)

    seed_dir = tools_out / "agents"
    seed_dir.mkdir(parents=True, exist_ok=True)
    (seed_dir / "seed_cycle_ext-ai-001.json").write_text(
        json.dumps(
            {
                "created_at": "2026-03-07T00:00:00Z",
                "iteration_results": [{"ok": True}, {"ok": False}, {"ok": True}],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        str(repo_root / "tools" / "network_status.py"),
        "--storage-root",
        str(storage_root),
        "--tools-out-dir",
        str(tools_out),
        "--output",
        str(out_path),
    ]
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert out_path.exists()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["network_objects"]["eo_total"] == 1
    assert payload["network_objects"]["rr_total"] == 1
    assert payload["network_objects"]["trace_total"] == 1
    assert payload["agents"]["total_known_agents"] >= 1
    assert payload["seed_cycle"]["iterations_completed"] == 3
    assert payload["errors"]["failed_runs"] == 1


def test_stats_endpoint_returns_extended_operational_fields(
    tmp_path: Path, manifest_path: Path, schemas_dir: Path, sample_dir: Path
) -> None:
    if server.HTTP_IMPORT_ERROR is not None:
        pytest.skip("HTTP dependencies are unavailable")
    fastapi = pytest.importorskip("fastapi.testclient")
    TestClient = fastapi.TestClient

    storage_root = tmp_path / "storage"
    tools_out = tmp_path / "tools_out"
    history_dir = tools_out / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    eo = _load_sample(sample_dir / "eo.sample.json")
    eo["eo_id"] = "echo.eo.agent.ext-ai-001.coding.task-2.run-1"
    core.store_object_idempotent(storage_root=storage_root, object_type="eo", obj=eo)

    (tools_out / "agents").mkdir(parents=True, exist_ok=True)
    (tools_out / "agents" / "seed_cycle_ext-ai-001.json").write_text(
        json.dumps({"created_at": "2026-03-07T12:00:00Z", "iteration_results": [{"ok": True}]}) + "\n",
        encoding="utf-8",
    )

    (history_dir / "live_network_status_20260307T120000Z.json").write_text(
        json.dumps({"timestamp": "2026-03-07T12:00:00Z", "network_objects": {"eo_total": 1}}) + "\n",
        encoding="utf-8",
    )
    (history_dir / "live_network_status_20260307T121000Z.json").write_text(
        json.dumps({"timestamp": "2026-03-07T12:10:00Z", "network_objects": {"eo_total": 2}}) + "\n",
        encoding="utf-8",
    )

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

    response = client.get("/stats?history=2")
    assert response.status_code == 200
    body = response.json()
    assert "network_objects" in body
    assert "agents" in body
    assert "seed_cycle" in body
    assert "network_status_history" in body
    assert isinstance(body["network_status_history"], list)
    assert len(body["network_status_history"]) == 2
