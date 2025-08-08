.PHONY: help install dev test lint clean docker-build docker-up docker-down setup-models

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies with uv
	uv sync

dev: ## Install development dependencies with uv
	uv sync --extra dev

venv: ## Create virtual environment with uv
	uv venv

lock: ## Update lockfile
	uv lock

test: ## Run tests with uv
	uv run pytest

lint: ## Run linting with uv
	uv run black src/ tests/
	uv run isort src/ tests/
	uv run flake8 src/ tests/
	uv run mypy src/

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .venv/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start all services
	docker-compose up -d

docker-down: ## Stop all services
	docker-compose down

docker-logs: ## View logs
	docker-compose logs -f

setup-models: ## Setup Ollama models
	./scripts/setup-models.sh

run-dev: ## Run development server with uv
	uv run uvicorn ollamao.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Run production server with uv
	uv run gunicorn ollamao.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

health: ## Check API health
	curl -f http://localhost:8000/health || echo "API not responding"
