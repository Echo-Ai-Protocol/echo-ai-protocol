# ECHO Python SDK (minimal)

Minimal stdlib-only client for ECHO reference-node HTTP service.

## Files

- `sdk/python/echo_sdk/client.py` — `EchoClient` implementation
- `sdk/python/quickstart.py` — runnable agent flow

## Quickstart

Start reference node HTTP server:

```bash
python3 -m uvicorn server:app --app-dir reference-node --host 127.0.0.1 --port 8080
```

Run SDK quickstart from repo root:

```bash
python3 sdk/python/quickstart.py --base-url http://127.0.0.1:8080
```

If running server in relaxed signature mode:

```bash
python3 sdk/python/quickstart.py --base-url http://127.0.0.1:8080 --skip-signature
```

With explicit retry/timeout tuning:

```bash
python3 sdk/python/quickstart.py --base-url http://127.0.0.1:8080 --retries 5 --timeout-seconds 8
```

## Example usage in your own agent

```python
from echo_sdk import EchoClient

client = EchoClient("http://127.0.0.1:8080")
health = client.wait_for_health()
bootstrap = client.bootstrap()
result = client.search_ranked_eo("echo.eo", explain=True)
```
