.PHONY: install dev lint format test evaluate ragas-export run docker enterprise-db enterprise-ingest enterprise grpc clean

UV ?= uv
ENTERPRISE_COMPOSE = docker compose -f compose.yaml -f compose.enterprise.yaml --profile enterprise

install:
	$(UV) sync --frozen --extra dev

dev: install
	$(UV) run --frozen --no-sync uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

lint:
	$(UV) run --frozen --no-sync ruff check .
	$(UV) run --frozen --no-sync ruff format --check .

format:
	$(UV) run --frozen --no-sync ruff check --fix .
	$(UV) run --frozen --no-sync ruff format .

test:
	$(UV) run --frozen --no-sync pytest -m "not integration"

evaluate:
	$(UV) run --frozen --no-sync python scripts/evaluate_retrieval.py
	$(UV) run --frozen --no-sync python scripts/evaluate_workflow.py

ragas-export:
	$(UV) run --frozen --no-sync python scripts/evaluate_ragas.py

run:
	$(UV) run --frozen --no-sync uvicorn app.main:app --host 127.0.0.1 --port 8000

docker:
	docker compose up --build -d api

enterprise-db:
	$(ENTERPRISE_COMPOSE) up -d qdrant redis

enterprise-ingest:
	$(ENTERPRISE_COMPOSE) build api
	$(ENTERPRISE_COMPOSE) run --rm --no-deps api python scripts/ingest.py

enterprise:
	$(ENTERPRISE_COMPOSE) up --build -d api

grpc:
	docker compose --profile grpc up --build -d grpc

clean:
	$(UV) run --frozen --no-sync python -c "import shutil; [shutil.rmtree(path, ignore_errors=True) for path in ('.pytest_cache', '.ruff_cache', 'htmlcov')]"
