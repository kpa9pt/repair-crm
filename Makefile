.PHONY: up down build logs

# Проверяем наличие .env, если нет — создаем из .env.example
check-env:
	@if [ ! -f .env ]; then \
		if [ -f .env.example ]; then \
			echo "📝 Creating .env from .env.example..."; \
			cp .env.example .env; \
			echo "⚠️  Please edit .env file if needed"; \
		else \
			echo "⚠️  No .env.example found, creating empty .env"; \
			touch .env; \
		fi \
	fi

up: check-env
		docker-compose up -d

down:
	docker-compose down -v

build: check-env
		docker-compose up -d --build

logs:
	docker-compose logs -f

test-unit: check-env
		pytest tests/unit -v

test-api: check-env
		./scripts/test.sh tests/api

test-integration: check-env
		./scripts/test.sh tests/integration

test-e2e: check-env
		./scripts/test.sh tests/e2e

test:
	make test-unit
	make test-api
	make test-integration

generate-migrations: check-env
		@echo "📝 Generating migrations..."
		@docker-compose up -d postgres
		@sleep 2
		@alembic revision --autogenerate -m "$(message)"
		@echo "✅ Migration created in shared/db/migrations/versions/"
		@echo "⚠️  Don't forget to commit this file!"

# Помощь
help:
	@echo "Available commands:"
	@echo "  make up                  - Start all services"
	@echo "  make down                - Stop all services"
	@echo "  make build               - Rebuild and start"
	@echo "  make test                - Run all tests"
	@echo "  make generate-migrations message='name' - Create migration"