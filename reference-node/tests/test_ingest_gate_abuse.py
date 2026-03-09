from __future__ import annotations

from pathlib import Path

import pytest

import reference_node as core
import server


def _make_client(
    tmp_path: Path,
    manifest_path: Path,
    schemas_dir: Path,
    ingest_token: str = "",
    max_request_bytes: int = 262_144,
    rate_limit_per_minute: int = 60,
    rate_limit_window_seconds: int = 60,
):
    if server.HTTP_IMPORT_ERROR is not None:
        pytest.skip("HTTP dependencies are unavailable")
    fastapi = pytest.importorskip("fastapi.testclient")
    test_client = fastapi.TestClient

    config = server.NodeConfig(
        manifest_path=manifest_path,
        schemas_dir=schemas_dir,
        storage_root=tmp_path / "storage",
        tools_out_dir=tmp_path / "tools_out",
        capabilities_path=Path(core.default_capabilities_path()),
        require_signature=False,
        ingest_token=ingest_token,
        max_request_bytes=max_request_bytes,
        rate_limit_per_minute=rate_limit_per_minute,
        rate_limit_window_seconds=rate_limit_window_seconds,
    )
    return test_client(server.create_app(config))


def test_playground_open_mode_without_token(tmp_path: Path, manifest_path: Path, schemas_dir: Path) -> None:
    client = _make_client(tmp_path, manifest_path, schemas_dir, ingest_token="")
    resp = client.post(
        "/playground/run",
        json={"agent_name": "OpenAgent", "lane": "ops", "task": "open mode test"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ingest_token_mode_requires_authorization(tmp_path: Path, manifest_path: Path, schemas_dir: Path) -> None:
    client = _make_client(tmp_path, manifest_path, schemas_dir, ingest_token="secret-123")
    payload = {
        "integration_id": "ext-secure-1",
        "agent_name": "SecureAgent",
        "lane": "code",
        "object_type": "eo",
        "payload": {"problem": "p", "constraints": "c", "solution": "s"},
    }
    denied = client.post("/ingest", json=payload)
    assert denied.status_code == 401
    assert denied.json()["detail"]["error"] == "unauthorized"

    allowed = client.post("/ingest", json=payload, headers={"Authorization": "Bearer secret-123"})
    assert allowed.status_code == 200
    assert allowed.json()["status"] in {"stored", "duplicate_ignored"}


def test_ingest_rate_limit_rejects_burst(tmp_path: Path, manifest_path: Path, schemas_dir: Path) -> None:
    client = _make_client(
        tmp_path,
        manifest_path,
        schemas_dir,
        rate_limit_per_minute=1,
        rate_limit_window_seconds=60,
    )
    payload = {
        "integration_id": "ext-rl-1",
        "agent_name": "RateAgent",
        "lane": "code",
        "object_type": "eo",
        "payload": {"problem": "p", "constraints": "c", "solution": "s"},
    }
    first = client.post("/ingest", json=payload)
    second = client.post("/ingest", json=payload)
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"]["error"] == "rate_limited"


def test_request_size_limit_rejects_large_payload(tmp_path: Path, manifest_path: Path, schemas_dir: Path) -> None:
    client = _make_client(tmp_path, manifest_path, schemas_dir, max_request_bytes=200)
    large_task = "x" * 5000
    resp = client.post(
        "/playground/run",
        json={"agent_name": "LargeAgent", "lane": "ops", "task": large_task},
    )
    assert resp.status_code == 413
    body = resp.json()
    assert body["error"] == "payload_too_large"
