.DEFAULT_GOAL := help

# Container runtime. This project runs on Docker or Podman: shared machines
# (like university DGX servers) often provide rootless Podman instead of
# Docker. Auto-detects podman first; override per invocation if needed:
#   make up RUNTIME=docker
RUNTIME ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)

# Fully qualified image name. Docker assumes bare names live on docker.io;
# Podman (correctly) assumes nothing, so we always say it explicitly.
QDRANT_IMAGE := docker.io/qdrant/qdrant:v1.19.0

install: ## Sync the virtualenv with pyproject.toml + uv.lock
	uv sync

dev: ## Run the API locally with auto-reload
	uv run uvicorn citegrep.app:app --reload --port 8000

# Recipe lines starting with "-" tell make to continue even if that command
# fails: creating an existing volume or removing an absent container are
# both fine, and this keeps `make up` idempotent.
up: ## Start infrastructure (Qdrant); data persists in the qdrant_data volume
	-$(RUNTIME) volume create qdrant_data 2>/dev/null
	-$(RUNTIME) rm -f qdrant 2>/dev/null
	$(RUNTIME) run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_data:/qdrant/storage $(QDRANT_IMAGE)

down: ## Stop infrastructure (the qdrant_data volume survives)
	-$(RUNTIME) rm -f qdrant 2>/dev/null

logs: ## Tail Qdrant logs
	$(RUNTIME) logs -f qdrant

lint: ## Static checks, no file changes
	uv run ruff check .
	uv run ruff format --check .

format: ## Auto-fix lint findings and formatting
	uv run ruff check --fix .
	uv run ruff format .

test: ## Unit tests
	uv run pytest

check: lint test ## Everything CI runs — green here means green in CI

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-10s %s\n", $$1, $$2}'

.PHONY: install dev up down logs lint format test check help
