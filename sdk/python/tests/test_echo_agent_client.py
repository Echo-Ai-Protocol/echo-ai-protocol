from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[3]
SDK_DIR = ROOT / "sdk" / "python"
if str(SDK_DIR) not in sys.path:
    sys.path.insert(0, str(SDK_DIR))

from echo_agent import EchoClient  # noqa: E402


class _FakeResponse:
    def __init__(self, payload: Any, status: int = 200):
        self.status = status
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None


def test_ingest_uses_expected_path_and_body(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_request(self, method, path, json_body=None):
        seen["method"] = method
        seen["path"] = path
        seen["json_body"] = json_body
        return {"status": "stored"}

    monkeypatch.setattr(EchoClient, "_request", fake_request)
    client = EchoClient(base_url="http://127.0.0.1:8080")
    out = client.ingest(
        integration_id="ext-1",
        agent_name="AgentX",
        lane="code",
        object_type="eo",
        payload={"problem": "p"},
        idempotency_key="k1",
    )
    assert out["status"] == "stored"
    assert seen["method"] == "POST"
    assert seen["path"] == "/ingest"
    assert seen["json_body"]["integration_id"] == "ext-1"
    assert seen["json_body"]["idempotency_key"] == "k1"


def test_stats_and_agents_call_expected_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    paths = []

    def fake_request(self, method, path, json_body=None):
        paths.append((method, path))
        return {"ok": True}

    monkeypatch.setattr(EchoClient, "_request", fake_request)
    client = EchoClient()
    client.stats()
    client.agents()
    assert ("GET", "/stats") in paths
    assert ("GET", "/agents") in paths


def test_client_sends_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_urlopen(request: urllib.request.Request, timeout: float):
        seen["auth"] = request.headers.get("Authorization")
        return _FakeResponse({"ok": True})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = EchoClient(base_url="http://127.0.0.1:8080", token="secret-token")
    out = client.playground_run(agent_name="A", lane="ops", task="t")
    assert out["ok"] is True
    assert seen["auth"] == "Bearer secret-token"
