"""Stdlib-only ECHO HTTP client for agent integrations."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


class EchoApiError(RuntimeError):
    """Raised when ECHO API responds with an error or invalid payload."""

    def __init__(self, message: str, status_code: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class EchoClient:
    """Thin HTTP client for reference-node endpoints."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.2,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))

    def _url(self, path: str, query: Optional[Dict[str, Any]] = None) -> str:
        normalized = path if path.startswith("/") else f"/{path}"
        url = f"{self.base_url}{normalized}"
        if not query:
            return url
        filtered = {k: str(v) for k, v in query.items() if v is not None}
        return f"{url}?{urllib.parse.urlencode(filtered)}"

    def _decode_body(self, payload: bytes) -> Any:
        text = payload.decode("utf-8", errors="replace")
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}

    def _should_retry_http(self, status_code: int) -> bool:
        return status_code >= 500

    def _request(
        self,
        method: str,
        path: str,
        query: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = self._url(path, query=query)
        headers = {"Accept": "application/json"}
        data: Optional[bytes] = None
        if json_body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")

        request = urllib.request.Request(url=url, method=method, headers=headers, data=data)

        attempts = self.max_retries + 1
        last_error: Optional[EchoApiError] = None

        for attempt in range(1, attempts + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    parsed = self._decode_body(response.read())
                    if not isinstance(parsed, dict):
                        raise EchoApiError(
                            "Expected JSON object in response",
                            status_code=response.status,
                            body=parsed,
                        )
                    return parsed
            except urllib.error.HTTPError as exc:
                body = self._decode_body(exc.read() if exc.fp is not None else b"")
                err = EchoApiError(
                    f"HTTP {exc.code} calling {path}",
                    status_code=exc.code,
                    body=body,
                )
                should_retry = self._should_retry_http(exc.code) and attempt < attempts
                if not should_retry:
                    raise err from exc
                last_error = err
            except urllib.error.URLError as exc:
                err = EchoApiError(f"Network error calling {path}: {exc}")
                if attempt >= attempts:
                    raise err from exc
                last_error = err

            time.sleep(self.retry_backoff_seconds * attempt)

        if last_error is not None:
            raise last_error
        raise EchoApiError(f"Request failed calling {path}")

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health")

    def wait_for_health(self, max_attempts: int = 20, delay_seconds: float = 0.2) -> Dict[str, Any]:
        last_error: Optional[EchoApiError] = None
        for _ in range(max(1, int(max_attempts))):
            try:
                return self.health()
            except EchoApiError as exc:
                last_error = exc
                time.sleep(max(0.0, delay_seconds))
        if last_error is not None:
            raise last_error
        raise EchoApiError("health check failed")

    def bootstrap(self) -> Dict[str, Any]:
        return self._request("GET", "/registry/bootstrap")

    def capabilities(self) -> Dict[str, Any]:
        return self._request("GET", "/registry/capabilities")

    def stats(self, history: int = 0) -> Dict[str, Any]:
        return self._request("GET", "/stats", query={"history": history})

    def reputation(self, agent_did: str) -> Dict[str, Any]:
        encoded = urllib.parse.quote(agent_did, safe="")
        return self._request("GET", f"/reputation/{encoded}")

    def store_object(self, object_type: str, object_json: Dict[str, Any], skip_signature: bool = False) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/objects",
            json_body={
                "type": object_type,
                "object_json": object_json,
                "skip_signature": bool(skip_signature),
            },
        )

    def store_eo(self, eo: Dict[str, Any], skip_signature: bool = False) -> Dict[str, Any]:
        return self.store_object("eo", eo, skip_signature=skip_signature)

    def store_rr(self, rr: Dict[str, Any], skip_signature: bool = False) -> Dict[str, Any]:
        return self.store_object("rr", rr, skip_signature=skip_signature)

    def get_object(self, object_type: str, object_id: str) -> Dict[str, Any]:
        encoded = urllib.parse.quote(object_id, safe="")
        return self._request("GET", f"/objects/{object_type}/{encoded}")

    def search(
        self,
        object_type: str,
        field: str,
        op: str,
        value: str,
        rank: bool = False,
        explain: bool = False,
        limit: int = 50,
    ) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/search",
            query={
                "type": object_type,
                "field": field,
                "op": op,
                "value": value,
                "rank": str(bool(rank)).lower(),
                "explain": str(bool(explain)).lower(),
                "limit": limit,
            },
        )

    def search_ranked_eo(self, eo_id_contains: str, limit: int = 10, explain: bool = True) -> Dict[str, Any]:
        return self.search(
            object_type="eo",
            field="eo_id",
            op="contains",
            value=eo_id_contains,
            rank=True,
            explain=explain,
            limit=limit,
        )

    def export_bundle(self, object_type: str) -> Dict[str, Any]:
        return self._request("GET", "/bundles/export", query={"type": object_type})

    def import_bundle(self, bundle: Dict[str, Any], skip_signature: bool = False) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/bundles/import",
            json_body={"bundle": bundle, "skip_signature": bool(skip_signature)},
        )
