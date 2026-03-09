"""Minimal stdlib-only client for external agent adapter endpoints."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


class EchoAgentError(RuntimeError):
    """Raised when ECHO agent adapter API returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class EchoClient:
    """Small client for /ingest, /playground/run, /stats, /agents."""

    def __init__(self, base_url: str = "http://127.0.0.1:8080", token: Optional[str] = None, timeout_seconds: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.token = token or None
        self.timeout_seconds = float(timeout_seconds)

    def _url(self, path: str) -> str:
        normalized = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{normalized}"

    def _decode_body(self, payload: bytes) -> Any:
        text = payload.decode("utf-8", errors="replace")
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}

    def _request(self, method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        headers = {"Accept": "application/json"}
        data: bytes | None = None
        if json_body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(self._url(path), method=method, headers=headers, data=data)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                parsed = self._decode_body(resp.read())
                if not isinstance(parsed, dict):
                    raise EchoAgentError("Expected JSON object response", status_code=resp.status, body=parsed)
                return parsed
        except urllib.error.HTTPError as exc:
            body = self._decode_body(exc.read() if exc.fp is not None else b"")
            raise EchoAgentError(f"HTTP {exc.code} calling {path}", status_code=exc.code, body=body) from exc
        except urllib.error.URLError as exc:
            raise EchoAgentError(f"Network error calling {path}: {exc}") from exc

    def ingest(
        self,
        integration_id: str,
        agent_name: str,
        lane: str,
        object_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        body = {
            "integration_id": str(integration_id),
            "agent_name": str(agent_name),
            "lane": str(lane),
            "object_type": str(object_type),
            "payload": payload,
        }
        if idempotency_key:
            body["idempotency_key"] = str(idempotency_key)
        return self._request("POST", "/ingest", json_body=body)

    def playground_run(self, agent_name: str, lane: str, task: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/playground/run",
            json_body={
                "agent_name": str(agent_name),
                "lane": str(lane),
                "task": str(task),
            },
        )

    def stats(self) -> Dict[str, Any]:
        return self._request("GET", "/stats")

    def agents(self) -> Dict[str, Any]:
        return self._request("GET", "/agents")
