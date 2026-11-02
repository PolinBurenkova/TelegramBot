SHELL := /bin/bash
PY ?= python
APP := app
DOCKER_COMPOSE := docker compose

.PHONY: help venv install install-dev run up down logs migrate revision seed reset-db healthcheck check test test-cov lint format typecheck shell clean pre-commit

help:
	@echo "Available targets:"
	@echo "  venv          Create .venv and install runtime dependencies"
	@echo "  install       Install runtime dependencies"
	@echo "  install-dev   Install dev dependencies"
	@echo "  run           python -m app.main"
	@echo "  healthcheck   Offline self-check (no Telegram needed)"
	@echo "  check         Static smoke check (imports, routers, dispatcher)"
	@echo "  up            docker compose up -d"
	@echo "  down          docker compose down"
	@echo "  logs          docker compose logs -f bot"
	@echo "  migrate       alembic upgrade head"
	@echo "  revision      alembic revision --autogenerate -m 'MSG'"
	@echo "  seed          Run all seed scripts"
	@echo "  reset-db      Drop + migrate + seed (DEV only)"
	@echo "  test          pytest"
	@echo "  test-cov      pytest with coverage"
	@echo "  lint          ruff check + mypy"
	@echo "  format        ruff format"
	@echo "  typecheck     mypy"
	@echo "  shell         docker compose exec bot bash"
	@echo "  clean         Remove caches"

venv:
	$(PY) -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -r requirements.txt
	@echo "Готово. Активируйте: . .venv/bin/activate (Windows: .venv\\Scripts\\activate)"

run:
	$(PY) -m app.main

healthcheck:
	$(PY) -m scripts.healthcheck

check:
	$(PY) check.py

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	pre-commit install

up:
	$(DOCKER_COMPOSE) up -d --build

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f bot

migrate:
	alembic upgrade head

revision:
	@[ "$(m)" ] || (echo "Usage: make revision m='message'" && exit 1)
	alembic revision --autogenerate -m "$(m)"

seed:
	$(PY) -m scripts.load_cities
	$(PY) -m scripts.load_countries
	$(PY) -m scripts.seed_achievements
	$(PY) -m scripts.seed_geo_locations

reset-db:
	$(PY) -m scripts.reset_db

test:
	pytest -q

test-cov:
	pytest --cov=app --cov-report=term-missing --cov-report=html

lint:
	ruff check app tests
	mypy app

format:
	ruff format app tests
	ruff check --fix app tests

typecheck:
	mypy app

shell:
	$(DOCKER_COMPOSE) exec bot bash

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +