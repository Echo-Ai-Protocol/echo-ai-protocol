.PHONY: preflight smoke simulate cli-help server test

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

test:
	python3 -m pytest reference-node/tests
