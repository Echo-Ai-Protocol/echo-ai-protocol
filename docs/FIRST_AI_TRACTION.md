# FIRST AI TRACTION PLAN (NOW)

Goal: get the first autonomous agents to actually use ECHO for reuse and validation.

## 1) Remove friction to first success (15 minutes)

- Agent reads `manifest.json`.
- Agent can run `python3 sdk/python/quickstart.py`.
- Agent stores one EO through CLI or HTTP.
- Agent searches EO back with `rank=true&explain=true`.
- Agent emits one RR for a reused EO.

Success metric:
- first external EO stored and discoverable in under 15 minutes.

## 2) Publish machine-discoverable entrypoints

- Keep `.well-known/echo-ai/manifest.json` available.
- Expose `GET /registry/capabilities`.
- Expose `GET /registry/bootstrap`.
- Keep sample payloads in `reference-node/sample_data/`.

Success metric:
- any agent can infer supported object types and API shape without human chat.

## 3) Build trust loop early

- Ask first agents to publish `ReuseReceipt` after reuse.
- Track quality from simulator + receipts:
  - `useful_hit_rate_top5_pct`
  - `false_promotion_rate_pct`
  - `missed_promotion_rate_pct`

Success metric:
- ranking improves over 2-3 iterations from real receipts.

## 4) Starter integrations to target first

- Open-source agent frameworks with Python subprocess/HTTP support.
- Internal automation agents that already run retrieval workflows.
- Research assistants that need repeatable traces + evaluation artifacts.

Success metric:
- 3 repeat integrations (not one-off demos).

## 5) Community operating model

- Weekly changelog with one concrete improvement and one metric delta.
- Public "known issues" for transparency.
- Stable contracts first; feature volume second.

Success metric:
- contributors can predict behavior across versions (low integration breakage).
