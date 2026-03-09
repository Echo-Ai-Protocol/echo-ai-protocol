.PHONY: preflight smoke simulate cli-help server server-strict test release-check pilot-feedback-lint zero-touch-gate candidate-shortlist sync-compatibility-matrix outreach-message external-kpi-summary external-ai-cycle run-coding-agent run-research-agent run-evaluator-agent seed-echo-agents seed-echo-cycle network-status run-sandbox

FEEDBACK_FILE ?= examples/integration/pilot_feedback.template.json
BASE_URL ?= http://127.0.0.1:8080
INTEGRATION_ID ?= ext-ai-001
AGENT_NAME ?= External Agent
LANE ?= code
RUNS ?= 3
COMPATIBLE_MIN_DAYS ?= 2
ZERO_TOUCH_REPORT ?= tools/out/zero_touch_$(INTEGRATION_ID).json
SKIP_SIGNATURE ?= 1
CANDIDATE_INPUT ?= examples/integration/candidate_pipeline.template.csv
CANDIDATE_SHORTLIST_OUT ?= tools/out/candidate_shortlist.json
REPORT_FILE ?= tools/out/zero_touch_ext-ai-001.json
COMPAT_MATRIX ?= docs/EXTERNAL_AI_COMPATIBILITY_MATRIX.md
OUTREACH_TEMPLATE ?= examples/integration/outreach_message.template.md
OUTREACH_OUT ?= tools/out/outreach_message_$(INTEGRATION_ID).md
ZERO_TOUCH_HISTORY_DIR ?= tools/out/history
EXTERNAL_KPI_OUT ?= tools/out/external_ai_kpi_summary.json
CYCLE_SKIP_GATE ?= 0
CYCLE_SUMMARY_OUT ?= tools/out/external_ai_cycle_$(INTEGRATION_ID).json
AGENT_SKIP_GATE ?= 0
CODING_AGENT_NAME ?= CodingAgent
RESEARCH_AGENT_NAME ?= ResearchAgent
EVALUATOR_AGENT_NAME ?= EvaluatorAgent
SEED_ITERATIONS ?= 1
SEED_INTERVAL_SECONDS ?= 0
SEED_CYCLE_OUT ?= tools/out/agents/seed_cycle_$(INTEGRATION_ID).json

preflight:
	bash tools/preflight.sh

smoke:
	./reference-node/run_smoke_tests.sh

simulate:
	python3 tools/simulate.py --use-reference-node --reference-node-skip-signature

cli-help:
	python3 reference-node/echo_node.py --help

server:
	python3 -m uvicorn server:app --app-dir reference-node --host 127.0.0.1 --port 8080

server-strict:
	python3 reference-node/server.py --host 127.0.0.1 --port 8080 --require-signature

test:
	python3 -m pytest reference-node/tests

release-check:
	bash tools/release_check.sh

pilot-feedback-lint:
	python3 tools/pilot_feedback_lint.py $(FEEDBACK_FILE)

zero-touch-gate:
	python3 tools/zero_touch_autogate.py \
		--base-url $(BASE_URL) \
		--integration-id $(INTEGRATION_ID) \
		--agent-name "$(AGENT_NAME)" \
		--lane $(LANE) \
		--runs $(RUNS) \
		--compatible-min-days $(COMPATIBLE_MIN_DAYS) \
		--history-dir $(ZERO_TOUCH_HISTORY_DIR) \
		--output $(ZERO_TOUCH_REPORT) \
		$(if $(filter 1,$(SKIP_SIGNATURE)),--skip-signature,)

candidate-shortlist:
	python3 tools/candidate_shortlist.py \
		--input $(CANDIDATE_INPUT) \
		--output $(CANDIDATE_SHORTLIST_OUT) \
		--top-n 10 \
		--min-code 3 \
		--min-research 3 \
		--min-ops 2

sync-compatibility-matrix:
	python3 tools/update_compatibility_matrix.py \
		--report $(REPORT_FILE) \
		--matrix $(COMPAT_MATRIX)

outreach-message:
	python3 tools/render_outreach_message.py \
		--integration-id $(INTEGRATION_ID) \
		--agent-name "$(AGENT_NAME)" \
		--lane $(LANE) \
		--template $(OUTREACH_TEMPLATE) \
		--output $(OUTREACH_OUT)

external-kpi-summary:
	python3 tools/external_ai_kpi_summary.py \
		--output $(EXTERNAL_KPI_OUT)

external-ai-cycle:
	python3 tools/external_ai_cycle.py \
		--integration-id $(INTEGRATION_ID) \
		--agent-name "$(AGENT_NAME)" \
		--lane $(LANE) \
		--base-url $(BASE_URL) \
		--runs $(RUNS) \
		--compatible-min-days $(COMPATIBLE_MIN_DAYS) \
		--candidate-input $(CANDIDATE_INPUT) \
		--shortlist-out $(CANDIDATE_SHORTLIST_OUT) \
		--report-out $(ZERO_TOUCH_REPORT) \
		--matrix $(COMPAT_MATRIX) \
		--outreach-template $(OUTREACH_TEMPLATE) \
		--outreach-out $(OUTREACH_OUT) \
		--history-dir $(ZERO_TOUCH_HISTORY_DIR) \
		--kpi-out $(EXTERNAL_KPI_OUT) \
		--summary-out $(CYCLE_SUMMARY_OUT) \
		$(if $(filter 1,$(SKIP_SIGNATURE)),--skip-signature,) \
		$(if $(filter 1,$(CYCLE_SKIP_GATE)),--skip-gate,)

run-coding-agent:
	python3 examples/agents/coding_agent.py \
		--base-url $(BASE_URL) \
		--integration-id $(INTEGRATION_ID) \
		--agent-name "$(CODING_AGENT_NAME)" \
		$(if $(filter 1,$(SKIP_SIGNATURE)),--skip-signature,) \
		$(if $(filter 1,$(AGENT_SKIP_GATE)),--skip-gate,)

run-research-agent:
	python3 examples/agents/research_agent.py \
		--base-url $(BASE_URL) \
		--integration-id $(INTEGRATION_ID) \
		--agent-name "$(RESEARCH_AGENT_NAME)" \
		$(if $(filter 1,$(SKIP_SIGNATURE)),--skip-signature,) \
		$(if $(filter 1,$(AGENT_SKIP_GATE)),--skip-gate,)

run-evaluator-agent:
	python3 examples/agents/evaluator_agent.py \
		--base-url $(BASE_URL) \
		--integration-id $(INTEGRATION_ID) \
		--agent-name "$(EVALUATOR_AGENT_NAME)" \
		$(if $(filter 1,$(SKIP_SIGNATURE)),--skip-signature,) \
		$(if $(filter 1,$(AGENT_SKIP_GATE)),--skip-gate,)

seed-echo-agents:
	$(MAKE) run-coding-agent BASE_URL=$(BASE_URL) INTEGRATION_ID=$(INTEGRATION_ID) SKIP_SIGNATURE=$(SKIP_SIGNATURE) AGENT_SKIP_GATE=$(AGENT_SKIP_GATE)
	$(MAKE) run-research-agent BASE_URL=$(BASE_URL) INTEGRATION_ID=$(INTEGRATION_ID) SKIP_SIGNATURE=$(SKIP_SIGNATURE) AGENT_SKIP_GATE=$(AGENT_SKIP_GATE)
	$(MAKE) run-evaluator-agent BASE_URL=$(BASE_URL) INTEGRATION_ID=$(INTEGRATION_ID) SKIP_SIGNATURE=$(SKIP_SIGNATURE) AGENT_SKIP_GATE=$(AGENT_SKIP_GATE)

seed-echo-cycle:
	python3 examples/agents/seed_cycle.py \
		--base-url $(BASE_URL) \
		--integration-id $(INTEGRATION_ID) \
		--coding-agent-name "$(CODING_AGENT_NAME)" \
		--research-agent-name "$(RESEARCH_AGENT_NAME)" \
		--evaluator-agent-name "$(EVALUATOR_AGENT_NAME)" \
		--iterations $(SEED_ITERATIONS) \
		--interval-seconds $(SEED_INTERVAL_SECONDS) \
		--output $(SEED_CYCLE_OUT) \
		$(if $(filter 1,$(SKIP_SIGNATURE)),--skip-signature,) \
		$(if $(filter 1,$(AGENT_SKIP_GATE)),--skip-gate,)

network-status:
	python3 tools/network_status.py

run-sandbox:
	docker compose up --build reference-node
