# ECHO Seed Agents (Reference)

This folder contains three minimal fixture-based agents to bootstrap a living ECHO loop:

1. `coding_agent.py`
2. `research_agent.py`
3. `evaluator_agent.py`

They are reference agents, not production AI systems.  
They use deterministic sample tasks and existing ECHO HTTP endpoints.

## What each agent does

- `coding_agent.py`:
  - reads `sample_tasks/coding_tasks.json`
  - stores `request`, optional ranked `search`, `eo`, `trace`

- `research_agent.py`:
  - reads `sample_tasks/research_tasks.json`
  - stores `request`, optional ranked `search`, `eo`, `trace`

- `evaluator_agent.py`:
  - reads `sample_tasks/evaluation_tasks.json`
  - searches existing `eo`
  - stores `request`, `rr`, `trace`

Closed loop produced:

`REQUEST -> SEARCH -> EO -> RR -> TRACE`

## Run agents directly

```bash
python3 examples/agents/coding_agent.py --base-url http://127.0.0.1:8080 --integration-id ext-ai-001 --agent-name CodingAgent
python3 examples/agents/research_agent.py --base-url http://127.0.0.1:8080 --integration-id ext-ai-001 --agent-name ResearchAgent
python3 examples/agents/evaluator_agent.py --base-url http://127.0.0.1:8080 --integration-id ext-ai-001 --agent-name EvaluatorAgent
```

All agents support:

- `--base-url`
- `--integration-id`
- `--agent-name`
- `--skip-gate`

Optional:

- `--skip-signature`
- `--run-tag`
- `--tasks-file`
- `--output`

## Offline / skip-gate mode

If `--skip-gate` is enabled and the node is unavailable:

- agents do not fail on store/search network errors
- objects are staged in the per-agent report under `staged`

Reports are written to:

- `tools/out/agents/coding_agent_<integration>.json`
- `tools/out/agents/research_agent_<integration>.json`
- `tools/out/agents/evaluator_agent_<integration>.json`

## Seed all agents (Make)

```bash
make seed-echo-agents BASE_URL=http://127.0.0.1:8080 INTEGRATION_ID=ext-ai-001
```

Then inspect:

```bash
curl -s http://127.0.0.1:8080/stats
```
