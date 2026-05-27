.PHONY: up down build logs

up:
	docker-compose up -d

down:
	docker-compose down -v

build:
	docker-compose up -d --build

logs:
	docker-compose logs -f

test:
	./scripts/test.sh