.PHONY: sync lint typecheck test evals inject run compose seed

sync:
	bash scripts/sync.sh

lint:
	bash scripts/with-python.sh -m ruff check app tests evals security scripts

typecheck:
	bash scripts/with-python.sh -m mypy app tests evals security

test:
	bash scripts/with-python.sh -m pytest

evals:
	bash scripts/with-python.sh -m evals.run_all

inject:
	bash scripts/with-python.sh -m security.injection_eval

run:
	bash scripts/run.sh

compose:
	docker compose up -d --build

seed:
	bash scripts/with-python.sh -m scripts.seed_demo
