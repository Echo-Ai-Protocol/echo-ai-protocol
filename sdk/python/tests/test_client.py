from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[3]
SDK_DIR = ROOT / "sdk" / "python"
if str(SDK_DIR) not in sys.path:
    sys.path.insert(0, str(SDK_DIR))

from echo_sdk import EchoApiError, EchoClient  # noqa: E402


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


def test_search_ranked_eo_uses_expected_query(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_request(self, method, path, query=None, json_body=None):
        seen["method"] = method
        seen["path"] = path
        seen["query"] = query
        seen["json_body"] = json_body
        return {"count": 1, "ranked": True, "results": []}

    monkeypatch.setattr(EchoClient, "_request", fake_request)
    client = EchoClient()
    payload = client.search_ranked_eo("echo.eo", explain=True)
    assert payload["ranked"] is True
    assert seen["method"] == "GET"
    assert seen["path"] == "/search"
    assert seen["query"]["rank"] == "true"
    assert seen["query"]["explain"] == "true"


def test_retry_on_network_error_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"count": 0}

    def fake_urlopen(request, timeout):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise urllib.error.URLError("temporary network failure")
        return _FakeResponse({"status": "ok"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = EchoClient(max_retries=3, retry_backoff_seconds=0.0)
    out = client.health()
    assert out["status"] == "ok"
    assert attempts["count"] == 3


def test_wait_for_health_exhausts_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_health(self):
        raise EchoApiError("down")

    monkeypatch.setattr(EchoClient, "health", fake_health)
    client = EchoClient(max_retries=0)
    with pytest.raises(EchoApiError):
        client.wait_for_health(max_attempts=2, delay_seconds=0.0)


def test_store_helpers_delegate(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_store(self, object_type, object_json, skip_signature=False):
        calls.append((object_type, object_json.get("id", ""), skip_signature))
        return {"status": "stored"}

    monkeypatch.setattr(EchoClient, "store_object", fake_store)
    client = EchoClient()
    client.store_eo({"id": "eo-1"}, skip_signature=True)
    client.store_rr({"id": "rr-1"}, skip_signature=False)
    assert calls[0][0] == "eo"
    assert calls[1][0] == "rr"
