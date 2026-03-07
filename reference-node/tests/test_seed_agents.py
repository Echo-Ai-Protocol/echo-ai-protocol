from __future__ import annotations

import json
import subprocess
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple


ID_FIELD_BY_TYPE = {
    "eo": "eo_id",
    "request": "rq_id",
    "rr": "rr_id",
    "trace": "trace_id",
}


class _FakeEchoHandler(BaseHTTPRequestHandler):
    server_version = "FakeEcho/0.1"

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/health":
            self._send_json({"status": "ok"})
            return

        if path == "/registry/bootstrap":
            self._send_json(
                {
                    "protocol": "ECHO/1.0",
                    "object_types": ["eo", "request", "rr", "trace"],
                }
            )
            return

        if path == "/search":
            object_type = query.get("type", [""])[0]
            field = query.get("field", [""])[0]
            op = query.get("op", ["equals"])[0]
            value = query.get("value", [""])[0]
            with self.server.state_lock:  # type: ignore[attr-defined]
                objs = list(self.server.objects.get(object_type, {}).values())  # type: ignore[attr-defined]

            hits: List[Dict[str, Any]] = []
            for obj in objs:
                f = str(obj.get(field, ""))
                if op == "equals" and f == value:
                    hits.append({"path": "memory://fake", "object": obj})
                elif op == "contains" and value in f:
                    hits.append({"path": "memory://fake", "object": obj})
                elif op == "prefix" and f.startswith(value):
                    hits.append({"path": "memory://fake", "object": obj})

            self._send_json(
                {
                    "count": len(hits),
                    "ranked": query.get("rank", ["false"])[0] == "true",
                    "explain": query.get("explain", ["false"])[0] == "true",
                    "results": hits,
                }
            )
            return

        if path == "/stats":
            with self.server.state_lock:  # type: ignore[attr-defined]
                counts = {k: len(v) for k, v in self.server.objects.items()}  # type: ignore[attr-defined]
            self._send_json({"objects": {"counts": counts, "total": sum(counts.values())}})
            return

        self._send_json({"detail": f"not found: {path}"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/objects":
            self._send_json({"detail": f"not found: {self.path}"}, status=404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            object_type = payload["type"]
            obj = payload["object_json"]
            obj_id = obj[ID_FIELD_BY_TYPE[object_type]]
        except Exception as exc:
            self._send_json({"detail": f"bad request: {exc}"}, status=400)
            return

        with self.server.state_lock:  # type: ignore[attr-defined]
            self.server.objects.setdefault(object_type, {})[obj_id] = obj  # type: ignore[attr-defined]
        self._send_json({"status": "stored", "type": object_type, "id": obj_id})


def _start_fake_server() -> Tuple[ThreadingHTTPServer, threading.Thread, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeEchoHandler)
    server.objects = {"eo": {}, "request": {}, "rr": {}, "trace": {}}  # type: ignore[attr-defined]
    server.state_lock = threading.Lock()  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, thread, f"http://{host}:{port}"


def _run_agent(repo_root: Path, script_name: str, args: List[str]) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(repo_root / "examples" / "agents" / script_name)] + args
    return subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)


def test_seed_agents_offline_skip_gate(repo_root: Path, tmp_path: Path) -> None:
    base_url = "http://127.0.0.1:9"
    scripts = [
        ("coding_agent.py", "coding_offline.json"),
        ("research_agent.py", "research_offline.json"),
        ("evaluator_agent.py", "evaluator_offline.json"),
    ]

    for script_name, output_name in scripts:
        out_path = tmp_path / output_name
        result = _run_agent(
            repo_root=repo_root,
            script_name=script_name,
            args=[
                "--base-url",
                base_url,
                "--integration-id",
                "ext-ai-test",
                "--agent-name",
                script_name.replace(".py", ""),
                "--skip-gate",
                "--skip-signature",
                "--run-tag",
                "offline",
                "--output",
                str(out_path),
            ],
        )
        assert result.returncode == 0, result.stdout + "\n" + result.stderr
        report = json.loads(out_path.read_text(encoding="utf-8"))
        staged_total = sum(len(report["staged"][k]) for k in report["staged"])
        assert staged_total > 0


def test_seed_agents_closed_loop_via_fake_http(repo_root: Path) -> None:
    server, thread, base_url = _start_fake_server()
    try:
        common_args = [
            "--base-url",
            base_url,
            "--integration-id",
            "ext-ai-test",
            "--skip-signature",
            "--run-tag",
            "loop1",
        ]

        r1 = _run_agent(
            repo_root=repo_root,
            script_name="coding_agent.py",
            args=common_args + ["--agent-name", "CodingAgent"],
        )
        assert r1.returncode == 0, r1.stdout + "\n" + r1.stderr

        r2 = _run_agent(
            repo_root=repo_root,
            script_name="research_agent.py",
            args=common_args + ["--agent-name", "ResearchAgent"],
        )
        assert r2.returncode == 0, r2.stdout + "\n" + r2.stderr

        r3 = _run_agent(
            repo_root=repo_root,
            script_name="evaluator_agent.py",
            args=common_args + ["--agent-name", "EvaluatorAgent"],
        )
        assert r3.returncode == 0, r3.stdout + "\n" + r3.stderr

        with server.state_lock:  # type: ignore[attr-defined]
            counts = {k: len(v) for k, v in server.objects.items()}  # type: ignore[attr-defined]

        assert counts["eo"] >= 4
        assert counts["rr"] >= 1
        assert counts["trace"] >= 3
        assert counts["request"] >= 3
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
