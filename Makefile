.PHONY: up down build logs

up:
	docker-compose up -d

down:
	docker-compose down -v

build:
	docker-compose up -d --build

logs:
	docker-compose logs -f

test-unit:
	pytest tests/unit -v

test-api:
	./scripts/test.sh tests/api

test-integration:
	./scripts/test.sh tests/integration

test-e2e:
	./scripts/test.sh tests/e2e

test:
	make test-unit
	make test-api
	make test-integration

generate-migrations:
	@echo "📝 Generating migrations..."
	@docker-compose up -d postgres
	@sleep 2
	@alembic revision --autogenerate -m "$(message)"
	@echo "✅ Migration created in shared/db/migrations/versions/"
	@echo "⚠️  Don't forget to commit this file!"