# External Agent Pilot Runbook

This runbook describes the zero-touch flow to connect a first external AI agent to ECHO sandbox.

## 1) Start sandbox

```bash
make run-sandbox
```

Optional protected mode:

```bash
cp .env.example .env
# set ECHO_INGEST_TOKEN in .env, then:
docker compose up --build reference-node
```

## 2) Basic API checks

```bash
curl -s http://127.0.0.1:8080/health
```

```bash
curl -s -X POST http://127.0.0.1:8080/playground/run \
  -H 'Content-Type: application/json' \
  -d '{"agent_name":"PilotPlay","lane":"ops","task":"validate sandbox connectivity"}'
```

```bash
curl -s -X POST http://127.0.0.1:8080/ingest \
  -H 'Content-Type: application/json' \
  -d '{
    "integration_id":"ext-pilot-001",
    "agent_name":"PilotAgent",
    "lane":"code",
    "object_type":"eo",
    "payload":{
      "problem":"stabilize pipeline retries",
      "constraints":"stdlib only",
      "solution":"bounded retry policy",
      "outcome_metrics":{"effectiveness_score":0.8,"stability_score":0.75,"iterations":1}
    },
    "idempotency_key":"ext-pilot-001-task-01"
  }'
```

If token mode is enabled:

```bash
curl -s -X POST http://127.0.0.1:8080/ingest \
  -H 'Authorization: Bearer <ECHO_INGEST_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{...}'
```

Inspect node state:

```bash
curl -s http://127.0.0.1:8080/agents
curl -s http://127.0.0.1:8080/stats
```

## 3) Python SDK quickstart

```bash
python3 sdk/python/examples/hello_agent.py --base-url http://127.0.0.1:8080
```

Protected mode:

```bash
python3 sdk/python/examples/hello_agent.py --base-url http://127.0.0.1:8080 --token <ECHO_INGEST_TOKEN>
```

## 4) Success criteria

- Agent appears in `/agents`.
- EO/TRACE counters increase in `/stats` (`network_objects`).
- Repeated submissions with same idempotency key return `duplicate_ignored`.
- Sandbox runs in open mode by default and in protected mode when token is configured.
