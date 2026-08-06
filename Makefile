SHELL := /bin/bash

.PHONY: setup up down logs ps test lint demo reset

setup:
	@test -f .env || cp .env.example .env
	docker compose pull
	docker compose build

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

test:
	docker compose run --rm backend pytest -q

lint:
	docker compose run --rm backend ruff check app tests

demo:
	python scripts/demo_seed.py

reset:
	docker compose down -v --remove-orphans
