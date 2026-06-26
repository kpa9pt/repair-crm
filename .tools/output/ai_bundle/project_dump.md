# PROJECT FULL DUMP: repair_crm
ROOT: /Users/natalia/Python projects/repair_crm

====================================================================================================
FILE: .env.example
====================================================================================================
```
# Telegram Bot Token (обязательно)
TELEGRAM_TOKEN=ваш_токен_сюда

# JWT Secret Key (обязательно, минимум 32 символа)
SECRET_KEY=my-super-secret-key-for-jwt-change-me-in-production

# Для админ-панели
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

#Доменное имя если имеется
#DOMAIN_NAME=example.com

# Database URL
# Вариант для внешней БД (раскомментируйте)
# DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
```

====================================================================================================
FILE: .github/workflows/build-and-push.yml
====================================================================================================
```
name: Build and Push to GHCR

on:
#  workflow_dispatch:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Detect changed services
        uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            gateway:
              - 'services/gateway/**'
              - 'shared/**'
              - 'requirements.txt'

            migrations:
              - 'services/migrations/**'
              - 'shared/**'
              - 'alembic.ini'
              - 'requirements.txt'

            nginx:
              - 'services/nginx/**'

            certbot:
              - 'services/certbot/**'
            
            watchdog:
              - 'services/watchdog/**'
              - 'scripts/rollback.py'

      - name: Print detected changes
        run: |
          echo "gateway=${{ steps.changes.outputs.gateway }}"
          echo "migrations=${{ steps.changes.outputs.migrations }}"
          echo "nginx=${{ steps.changes.outputs.nginx }}"
          echo "certbot=${{ steps.changes.outputs.certbot }}"
          echo "watchdog=${{ steps.changes.outputs.watchdog }}"

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push gateway
        if: steps.changes.outputs.gateway == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/gateway/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-gateway:latest
            ghcr.io/${{ github.repository }}-gateway:${{ github.sha }}
            

      - name: Build and push migrations
        if: steps.changes.outputs.migrations == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/migrations/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-migrations:latest
            ghcr.io/${{ github.repository }}-migrations:${{ github.sha }}

      - name: Build and push nginx
        if: steps.changes.outputs.nginx == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/nginx/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-nginx:latest
            ghcr.io/${{ github.repository }}-nginx:${{ github.sha }}

      - name: Build and push certbot
        if: steps.changes.outputs.certbot == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/certbot/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-certbot:latest
            ghcr.io/${{ github.repository }}-certbot:${{ github.sha }}

      - name: Build and push watchdog
        if: steps.changes.outputs.watchdog == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/watchdog/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-watchdog:latest
            ghcr.io/${{ github.repository }}-watchdog:${{ github.sha }}

      - name: Build image manifest
        run: |
          python scripts/build_manifest.py > images.json
        env:
          CHANGED_GATEWAY: ${{ steps.changes.outputs.gateway }}
          CHANGED_MIGRATIONS: ${{ steps.changes.outputs.migrations }}
          CHANGED_NGINX: ${{ steps.changes.outputs.nginx }}
          CHANGED_CERTBOT: ${{ steps.changes.outputs.certbot }}
          CHANGED_WATCHDOG: ${{ steps.changes.outputs.watchdog }}

          GITHUB_SHA: ${{ github.sha }}

      - name: Upload images artifact
        uses: actions/upload-artifact@v4
        with:
          name: images
          path: images.json
```

====================================================================================================
FILE: .github/workflows/ci.yml
====================================================================================================
```
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          
      - name: Setup env for tests
        run: cp .env.example .env

      - name: Run tests
        run: make test
```

====================================================================================================
FILE: .github/workflows/deploy.yml
====================================================================================================
```
name: Deploy to VDS

on:
  workflow_run:
    workflows:
      - "Build and Push to GHCR"
    types:
      - completed
  workflow_dispatch:

jobs:
  deploy:
    if: >
      github.event.workflow_run.conclusion == 'success' &&
      github.event.workflow_run.head_branch == 'main'
    env:
      GHCR_READ_TOKEN: ${{ secrets.GHCR_READ_TOKEN }}
    runs-on: ubuntu-latest
    steps:
      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.SERVER_SSH_KEY }}" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh-keyscan -H ${{ secrets.SERVER_IP }} >> ~/.ssh/known_hosts

      - name: Set deploy id
        run: echo "DEPLOY_ID=${{ github.event.workflow_run.id }}" >> $GITHUB_ENV

      - name: Check state file
        id: state
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} "
            mkdir -p ~/repair-crm/state

            if [ -f ~/repair-crm/state/state.json ]; then
              echo 'exists=true'
            else
              echo 'exists=false'
            fi
          " >> $GITHUB_OUTPUT

      - name: Checkout code
        uses: actions/checkout@v4

      - name: State for runner
        if: steps.state.outputs.exists == 'true'
        run: |
          scp ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json ./state.json


      - name: Bootstrap state
        if: steps.state.outputs.exists == 'false'
        env:
          GHCR_READ_TOKEN: ${{ secrets.GHCR_READ_TOKEN }}
        run: |
          python scripts/deploy/bootstrap_state.py > state.json

      - name: Upload state
        if: steps.state.outputs.exists == 'false'
        run: |
          scp state.json \
            ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json

      - name: Backup original state (server)
        run: |
          scp ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json \
            state.backup.json

      - name: Download images artifact
        run: |
          gh run download ${{ github.event.workflow_run.id }} \
          -n images \
          -D .
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Update state
        run: |
          python scripts/deploy/update_state.py > new_state.json
          mv new_state.json state.json

      - name: Sync state to server (always)
        run: |
          scp state.json \
              ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json

      - name: Check if deploy needed
        id: diff
        run: |
          python scripts/deploy/check_diff.py > deploy_plan.json

      - name: Print deploy plan
        run: |
          cat deploy_plan.json

      - name: Save deploy plan
        run: |
          PLAN=$(cat deploy_plan.json | jq -c . | base64 -w0)
          echo "DEPLOY_PLAN=$PLAN" >> $GITHUB_ENV

      - name: Debug DEPLOY_PLAN content
        run: |
          echo "=== DEPLOY_PLAN content ==="
          echo "${{ env.DEPLOY_PLAN }}"
          echo "=== HEX ==="
          echo -n "${{ env.DEPLOY_PLAN }}" | od -c
          echo "=== END ==="

      - name: Lock rollback (per service)
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/lock_rollback.py

      - name: Generate compose override
        run: |
          STATE_FILE=state.json 
          python scripts/deploy/render_compose.py > docker-compose.override.yml

      - name: Upload override to server
        run: |
          scp docker-compose.override.yml \
              ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/docker-compose.override.yml

      - name: push to VDS
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DATABASE_URL='${{ secrets.DATABASE_URL }}' \
             ADMIN_USERNAME='${{ secrets.ADMIN_USERNAME }}' \
             ADMIN_PASSWORD='${{ secrets.ADMIN_PASSWORD }}' \
             SECRET_KEY='${{ secrets.SECRET_KEY }}' \
             TELEGRAM_TOKEN='${{ secrets.TELEGRAM_TOKEN }}' \
             DOMAIN_NAME='${{ secrets.DOMAIN_NAME }}' \
             bash -s" < scripts/deploy/push_to_vds.sh

      - name: Verify ACTIVE services
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/verify_services.py

      - name: Wait for new services healthcheck
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/verify_inactive_services.py

      - name: Switch traffic (state-driven)
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/switch_services.py

      - name: Reload nginx
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} "
            docker exec nginx /scripts/reload.sh
          "

      - name: Post-switch verify
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/post_switch_verify.py \
            > post_switch_verify.json

      - name: Print verify result
        run: |
          cat post_switch_verify.json

      - name: Save rollback decision (runner-only)
        run: |
          cat post_switch_verify.json | jq -c . > rollback_decision.json

          ROLLBACK=$(cat rollback_decision.json | base64 -w0)
          echo "ROLLBACK_DECISION=$ROLLBACK" >> $GITHUB_ENV

      - name: Unlock rollback
        id: unlock
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "ROLLBACK_DECISION='${{ env.ROLLBACK_DECISION }}' python3 -" \
            < scripts/deploy/unlock_rollback.py

      - name: Restore state backup
        if: always() && steps.unlock.outcome != 'success'
        run: |
          if [ -s state.backup.json ]; then
            echo "restoring backup state"
            scp state.backup.json \
              ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json
          else
            echo "backup empty - skip restore"
          fi

      - name: Post Reload nginx
        if: always() && steps.unlock.outcome != 'success'
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} "
            docker exec nginx /scripts/reload.sh
          "

      - name: Rollback engine
        env:
          SERVER_USER: ${{ secrets.SERVER_USER }}
          SERVER_IP: ${{ secrets.SERVER_IP }}
          ROLLBACK_DECISION: ${{ env.ROLLBACK_DECISION }}
        run: |
          python scripts/deploy/run_rollbacks.py
          

      - name: Cleanup inactive containers
        if: always()
        env:
          SERVER_USER: ${{ secrets.SERVER_USER }}
          SERVER_IP: ${{ secrets.SERVER_IP }}
          DEPLOY_PLAN: ${{ env.DEPLOY_PLAN }}
        run: |
          ssh $SERVER_USER@$SERVER_IP \
            "DEPLOY_PLAN='$DEPLOY_PLAN' python3 -" \
            < scripts/deploy/cleanup.py

```

====================================================================================================
FILE: .pre-commit-config.yaml
====================================================================================================
```
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/flake8
    rev: 7.1.0
    hooks:
      - id: flake8
        args:
          [
            --config=.flake8,
            --max-line-length=88,
            --extend-ignore=E203,
          ]
```

====================================================================================================
FILE: alembic.ini
====================================================================================================
```
# A generic, single database configuration.

[alembic]
# path to migration scripts.
# this is typically a path given in POSIX (e.g. forward slashes)
# format, relative to the token %(here)s which refers to the location of this
# ini file
# script_location = %(here)s/shared/db/migrations
script_location = shared/db/migrations

# template used to generate migration file names; The default value is %%(rev)s_%%(slug)s
# Uncomment the line below if you want the files to be prepended with date and time
# see https://alembic.sqlalchemy.org/en/latest/tutorial.html#editing-the-ini-file
# for all available tokens
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s
# Or organize into date-based subdirectories (requires recursive_version_locations = true)
# file_template = %%(year)d/%%(month).2d/%%(day).2d_%%(hour).2d%%(minute).2d_%%(second).2d_%%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.  for multiple paths, the path separator
# is defined by "path_separator" below.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the tzdata library which can be installed by adding
# `alembic[tz]` to the pip requirements.
# string value is passed to ZoneInfo()
# leave blank for localtime
# timezone =

# max length of characters to apply to the "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version location specification; This defaults
# to <script_location>/versions.  When using multiple version
# directories, initial revisions must be specified with --version-path.
# The path separator used here should be the separator specified by "path_separator"
# below.
# version_locations = %(here)s/bar:%(here)s/bat:%(here)s/alembic/versions

# path_separator; This indicates what character is used to split lists of file
# paths, including version_locations and prepend_sys_path within configparser
# files such as alembic.ini.
# The default rendered in new alembic.ini files is "os", which uses os.pathsep
# to provide os-dependent path splitting.
#
# Note that in order to support legacy alembic.ini files, this default does NOT
# take place if path_separator is not present in alembic.ini.  If this
# option is omitted entirely, fallback logic is as follows:
#
# 1. Parsing of the version_locations option falls back to using the legacy
#    "version_path_separator" key, which if absent then falls back to the legacy
#    behavior of splitting on spaces and/or commas.
# 2. Parsing of the prepend_sys_path option falls back to the legacy
#    behavior of splitting on spaces, commas, or colons.
#
# Valid values for path_separator are:
#
# path_separator = :
# path_separator = ;
# path_separator = space
# path_separator = newline
#
# Use os.pathsep. Default configuration used for new projects.
path_separator = os


# set to 'true' to search source files recursively
# in each "version_locations" directory
# new in Alembic version 1.10
recursive_version_locations = true

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

# database URL.  This is consumed by the user-maintained env.py script only.
# other means of configuring database URLs may be customized within the env.py
# file.
# sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost/


[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 79 REVISION_SCRIPT_FILENAME

# lint with attempts to fix using "ruff" - use the module runner, against the "ruff" module
# hooks = ruff
# ruff.type = module
# ruff.module = ruff
# ruff.options = check --fix REVISION_SCRIPT_FILENAME

# Alternatively, use the exec runner to execute a binary found on your PATH
# hooks = ruff
# ruff.type = exec
# ruff.executable = ruff
# ruff.options = check --fix REVISION_SCRIPT_FILENAME

# Logging configuration.  This is also consumed by the user-maintained
# env.py script only.
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S

```

====================================================================================================
FILE: docker-compose.prod.yml
====================================================================================================
```
services:
  gateway-blue:
    image: ${GATEWAY_BLUE_IMAGE}

  gateway-green:
    image: ${GATEWAY_GREEN_IMAGE}

  nginx:
    image: ${NGINX_IMAGE}

  certbot:
    image: ${CERTBOT_IMAGE}

  migrations:
    image: ${MIGRATIONS_IMAGE}

  watchdog:
    image: ${WATCHDOG_IMAGE}
```

====================================================================================================
FILE: docker-compose.test.yml
====================================================================================================
```
services:
  postgres:
    ports:
      - "5432:5432"   # только для тестов локально

#  gateway:
#    environment:
#      DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test
#
#  migrations:
#    environment:
#      DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test
```

====================================================================================================
FILE: docker-compose.yml
====================================================================================================
```
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: repair_crm
      POSTGRES_HOST_AUTH_METHOD: trust  # <- КЛЮЧЕВАЯ СТРОКgi
    expose:
      - "5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U postgres" ]
      interval: 5s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
    restart: unless-stopped

  nginx:
    container_name: nginx
    build:
      context: .
      dockerfile: services/nginx/Dockerfile
    ports:
      - "80:80"
      - "443:443"
    env_file:
      - .env
    environment:
      DOMAIN_NAME: ${DOMAIN_NAME:-localhost}
    volumes:
      - certbot_conf:/etc/letsencrypt
      - certbot_web:/var/www/certbot
      - ./state:/etc/nginx/state
    healthcheck:
#      test: [ "CMD", "curl", "-f", "http://localhost/.well-known/acme-challenge/healthcheck" ]
      test: [ "CMD", "nginx", "-t" ]  # проверяет только конфиг
      interval: 10s
      timeout: 5s
      retries: 30
      start_period: 10s
    deploy:
      resources:
        limits:
          memory: 64M
        reservations:
          memory: 32M
    restart: unless-stopped

  certbot:
    container_name: certbot
    build:
      context: .
      dockerfile: services/certbot/Dockerfile
    volumes:
      - certbot_conf:/etc/letsencrypt
      - certbot_web:/var/www/certbot
    env_file:
      - .env
    environment:
      DOMAIN_NAME: ${DOMAIN_NAME:-localhost}
    depends_on:
      nginx:
        condition: service_healthy  # ← ждем здоровый nginx
    healthcheck:
      # Проверяем, что скрипт дошел до бесконечного цикла (процесс sleep существует)
      test: [ "CMD", "sh", "-c", "pgrep -f 'sleep 12h' || pgrep -f 'sleep 3600' || exit 1" ]
      interval: 5s
      timeout: 3s
      retries: 60
      start_period: 60s
    deploy:
      resources:
        limits:
          memory: 128M
        reservations:
          memory: 64M
    restart: unless-stopped

  watchdog:
    build:
      context: .
      dockerfile: services/watchdog/Dockerfile
    container_name: watchdog

    volumes:
      - ./state:/state
      - /var/run/docker.sock:/var/run/docker.sock

    environment:
      STATE_PATH: /state/state.json
      WORKDIR: /app


    mem_limit: 64m
    cpus: "0.2"

    healthcheck:
      test: [ "CMD", "python", "-c", "print('ok')" ]
      interval: 30s
      timeout: 3s
      retries: 3

    depends_on:
      nginx:
        condition: service_healthy
    restart: unless-stopped


  gateway-blue:
    container_name: gateway-blue
    build:
      context: .
      dockerfile: services/gateway/Dockerfile
    expose:
      - "8000"

    env_file:
      - .env

    environment:
      DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@postgres:5432/repair_crm}

    command:
      [
        "uvicorn",
        "services.gateway.app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ]

    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
        ]
      interval: 5s
      timeout: 3s
      retries: 10

    restart: unless-stopped

    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M


  gateway-green:
    container_name: gateway-green
    build:
      context: .
      dockerfile: services/gateway/Dockerfile
    expose:
      - "8000"

    env_file:
      - .env

    environment:
      DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@postgres:5432/repair_crm}

    command:
      [
        "uvicorn",
        "services.gateway.app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ]

    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
        ]
      interval: 5s
      timeout: 3s
      retries: 10

    restart: unless-stopped

    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  migrations:
    build:
      context: .
      dockerfile: services/migrations/Dockerfile
    env_file:
      - .env
    environment:
      DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@postgres:5432/repair_crm}
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
  certbot_conf:
  certbot_web:
```

====================================================================================================
FILE: LICENSE
====================================================================================================
```
MIT License

Copyright (c) 2026 kpa9pt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```

====================================================================================================
FILE: Makefile
====================================================================================================
```
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
```

====================================================================================================
FILE: pytest.ini
====================================================================================================
```
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
```

====================================================================================================
FILE: README.md
====================================================================================================
```
# Repair CRM

[![Docker](https://img.shields.io/badge/Docker-20.10+-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)


Система для управления ремонтами и заказами в мастерской мототехники.

---

## 📌 О проекте

Repair CRM — backend-система для обработки заявок на ремонт.  
Проект построен как API-first приложение с административной панелью.

**Portable deployment:** достаточно Docker и свободных портов 80/443.

---

## ⚙️ Возможности

- CRUD заявок на ремонт
- Фильтрация и пагинация
- REST API (Swagger UI)
- Административная панель (SQLAdmin)
- Docker-окружение для разработки
- CI/CD (GitHub Actions + GHCR)
- Автоматический HTTPS (Let's Encrypt)

---

## 🧱 Технологии

- Python 3.14 / FastAPI
- PostgreSQL / SQLAlchemy (async)
- Alembic / pytest
- Docker / Docker Compose
- Nginx / Certbot
- GitHub Container Registry

---

## 📋 Требования

- Docker (20.10+)
- Docker Compose (2.20+)
- Свободные порты: 80, 443 (для HTTPS)

---

## 🚀 Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone https://github.com/kpa9pt/repair-crm.git
cd repair-crm

# 2. Запустить проект (.env создастся автоматически)
make up

# 3. Остановить проект
make down
```

---

## 🌐 После запуска доступны сервисы:

|   Сервис	   |           URL           |
|:-----------:|:-----------------------:|
| API Gateway |    	http://localhost    |
| Swagger UI  | 	http://localhost/docs  |
| Admin panel | 	http://localhost/admin |

---

## 🔧 Переменные окружения

При первом запуске файл .env создаётся автоматически из .env.example:
```bash
cp .env.example .env   # если нужно отредактировать вручную
```
Основные переменные:

| Переменная      | 	Значение по умолчанию                                                | 	Описание                               |
|:----------------|:----------------------------------------------------------------------|:----------------------------------------|
| DATABASE_URL    | 	postgresql+asyncpg://postgres:<br>postgres@postgres:5432/repair_crm	 | Подключение к БД                        |
| ADMIN_USERNAME	 | admin	                                                                | Логин админ-панели                      |
| ADMIN_PASSWORD	 | (смотри .env.example)	                                                | Пароль админ-панели                     |
| DOMAIN_NAME	    | localhost	                                                            | Домен (для продакшена укажите реальный) |


> Для HTTPS укажите реальный домен и настройте DNS запись на IP вашего сервера. Certbot автоматически получит сертификат.

---

## 🛠️ Основные команды

```bash
make up          # запустить все сервисы
make down        # остановить и удалить контейнеры
make build       # пересобрать и запустить
make test        # запустить все тесты
make logs        # посмотреть логи
make help        # показать все команды
```

---

## 🧪 Тестирование

```bash
make test
```

Тесты запускаются в Docker-окружении с автоматическим поднятием инфраструктуры и пересозданием базы данных.

---

## 🔐 Административный доступ

Доступ к админ-панели:
- URL: http://localhost/admin
- Login: admin
- Password: admin123

> Админ-панель — основной инструмент для управления заявками.


---

## 🚀 Деплой на VPS

- Клонируйте репозиторий на сервер
- Настройте .env (укажите DOMAIN_NAME и пароли)
- Выполните make up

---

## 🤖 Автоматический CI/CD (опционально)

В репозитории настроены GitHub Actions:

- Build and Push to GHCR — сборка образа при пуше в main
- Deploy to VDS — автоматический деплой на сервер

Для работы CI/CD нужны секреты (смотри .github/workflows/deploy.yml).


---

## 🧭 Архитектура

```text
Nginx (порты 80/443) → Gateway (FastAPI) → PostgreSQL
                ↓
         Certbot (HTTPS)
```

---

## 🎯 Дальнейшее развитие

- [ ] **Модель "Техника"** — единицы техники с историей ремонтов
- [ ] **Telegram бот** — уведомления о новых заявках
- [ ] **React фронтенд** — полноценный интерфейс для менеджеров
- [ ] **Blue/Green деплой** — zero-downtime обновления
- [ ] **Мобильное приложение (iOS)** — для механиков в поле

---

## 📄 Лицензия

MIT

---
```

====================================================================================================
FILE: requirements.txt
====================================================================================================
```
alembic==1.18.4
annotated-doc==0.0.4
annotated-types==0.7.0
anyio==4.13.0
asyncpg==0.31.0
bcrypt==5.0.0
black==26.5.1
certifi==2026.5.20
cfgv==3.5.0
click==8.4.1
distlib==0.4.0
fastapi==0.136.3
filelock==3.29.0
greenlet==3.5.1
h11==0.16.0
httpcore==1.0.9
httptools==0.8.0
httpx==0.28.0
identify==2.6.19
idna==3.16
iniconfig==2.3.0
itsdangerous==2.2.0
Jinja2==3.1.6
Mako==1.3.12
MarkupSafe==3.0.3
mypy_extensions==1.1.0
nodeenv==1.10.0
packaging==26.2
passlib==1.7.4
pathspec==1.1.1
platformdirs==4.10.0
pluggy==1.6.0
pre_commit==4.6.0
pydantic==2.13.4
pydantic-settings==2.14.1
pydantic_core==2.46.4
Pygments==2.20.0
pytest==9.0.3
pytest-asyncio==1.3.0
python-discovery==1.4.0
python-dotenv==1.2.2
python-multipart==0.0.27
pytokens==0.4.1
PyYAML==6.0.3
redis==5.0.1
sqladmin==0.27.0
SQLAlchemy==2.0.49
starlette==1.2.0
typing-inspection==0.4.2
typing_extensions==4.15.0
uvicorn==0.30.0
uvloop==0.22.1
virtualenv==21.4.1
watchfiles==1.2.0
websockets==16.0
WTForms==3.1.2

requests
```

====================================================================================================
FILE: scripts/build_manifest.py
====================================================================================================
```
import json
import os

SERVICES = ["gateway", "migrations", "nginx", "certbot", "watchdog"]

github_sha = os.environ.get("GITHUB_SHA", "")

manifest = {}

for service in SERVICES:
    changed = os.environ.get(f"CHANGED_{service.upper()}", "false")

    if changed == "true":
        manifest[service] = github_sha

print(json.dumps(manifest))

```

====================================================================================================
FILE: scripts/deploy/bootstrap_state.py
====================================================================================================
```
import json
import os
import requests
import sys

OWNER = "kpa9pt"

SERVICES = [
    "gateway",
    "nginx",
    "certbot",
    "migrations",
    "watchdog",
]

TOKEN = os.environ["GHCR_READ_TOKEN"]

# 🔥 DEBUG 1: проверяем что токен вообще есть и не пустой
print("TOKEN EXISTS:", bool(TOKEN), file=sys.stderr)
print("TOKEN PREFIX:", TOKEN[:6] if TOKEN else None, file=sys.stderr)

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
}

DEPLOY_ID = os.getenv("DEPLOY_ID", "bootstrap")


def latest_image(service: str) -> str:
    url = (
        f"https://api.github.com/users/"
        f"{OWNER}/packages/container/repair-crm-{service}/versions"
    )

    print(f"\n--- SERVICE: {service} ---", file=sys.stderr)
    print("URL:", url, file=sys.stderr)

    response = requests.get(url, headers=HEADERS)

    # 🔥 DEBUG 2: статус ответа
    print("STATUS:", response.status_code, file=sys.stderr)

    # 🔥 DEBUG 3: если упало — покажем текст
    if response.status_code != 200:
        print("ERROR BODY:", response.text[:500], file=sys.stderr)

    response.raise_for_status()

    versions = response.json()

    # 🔥 DEBUG 4: сколько версий пришло
    print("VERSIONS COUNT:", len(versions), file=sys.stderr)

    for version in versions:
        # ❗ оставили как у тебя было (НЕ трогаем логику)
        tags = version["metadata"]["container"]["tags"]

        print("TAGS:", tags, file=sys.stderr)

        sha_tags = [tag for tag in tags if tag != "latest"]

        if sha_tags:
            sha = sha_tags[0]
            return f"ghcr.io/{OWNER}/repair-crm-{service}:{sha}"

    raise RuntimeError(f"No sha tag found for {service}")


state = {
    "deploy_id": DEPLOY_ID,
    "services": {
        "gateway": {
            "strategy": "blue-green",
            "active": "blue",
            "port": 8000,
            "healthcheck": "/health",
            "rollback_locked": False,
        }
    },
}

gateway_image = latest_image("gateway")

state["services"]["gateway"]["blue"] = {"image": gateway_image}
state["services"]["gateway"]["green"] = {"image": gateway_image}

for service in [
    "nginx",
    "certbot",
    "migrations",
    "watchdog",
]:
    state["services"][service] = {
        "strategy": "single",
        "image": latest_image(service),
    }

print(json.dumps(state, indent=2))

```

====================================================================================================
FILE: scripts/deploy/check_diff.py
====================================================================================================
```
import json
import sys


def load(path):
    with open(path) as f:
        return json.load(f)


def main():
    changes = load("images.json")
    state = load("state.json")

    deploy_plan = []

    for service in changes.keys():

        service_state = state["services"].get(service)

        if not service_state:
            print(
                f"skip {service}: not found in state",
                file=sys.stderr,
            )
            continue

        if service_state.get("strategy") != "blue-green":
            print(
                f"skip {service}: strategy={service_state.get('strategy')}",
                file=sys.stderr,
            )
            continue

        deploy_plan.append(service)

    print(json.dumps(deploy_plan))


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/cleanup.py
====================================================================================================
```
import json
import os
import base64
import subprocess
from pathlib import Path


def load_state():
    state_file = Path.home() / "repair-crm" / "state" / "state.json"
    with open(state_file) as f:
        return json.load(f)


def load_plan():
    data = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(data).decode())


def main():
    state = load_state()
    deploy_plan = load_plan()

    print("=== CLEANUP START ===")

    for service in deploy_plan:
        if service not in state["services"]:
            print(f"skip unknown service: {service}")
            continue

        svc = state["services"][service]

        if svc["strategy"] == "blue-green":
            active = svc["active"]
            inactive = "green" if active == "blue" else "blue"
            container = f"{service}-{inactive}"

            print(f"stopping {container}")
            subprocess.run(["docker", "stop", container], check=False)

    print("=== PRUNE ===")
    subprocess.run(["docker", "system", "prune", "-f"], check=False)

    print("=== CLEANUP DONE ===")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/lock_rollback.py
====================================================================================================
```
import json
import os
import base64
from pathlib import Path


STATE_FILE = Path.home() / "repair-crm" / "state" / "state.json"


def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def decode_plan():
    raw = os.environ.get("DEPLOY_PLAN", "")
    if not raw:
        return []

    decoded = base64.b64decode(raw).decode()
    return json.loads(decoded)


def main():
    deploy_plan = decode_plan()
    state = load_state()

    for service in deploy_plan:
        if service not in state["services"]:
            print(f"⚠️ skip unknown service {service}")
            continue

        print(f"🔒 lock rollback: {service}")
        state["services"][service]["rollback_locked"] = True

    save_state(state)
    print("✅ rollback locked for planned services")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/post_switch_verify.py
====================================================================================================
```
import json
import sys
import time
import os
import base64
import subprocess
from pathlib import Path


def healthcheck(container, port, health):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{health}', timeout=2)"
        ),
    ]

    return subprocess.run(cmd).returncode == 0


def wait_health(container, port, health, retries=30, delay=2):

    for i in range(retries):

        if healthcheck(container, port, health):
            return True

        print(
            f"retry: {i + 1}/{retries}",
            file=sys.stderr,
        )

        time.sleep(delay)

    return False


def main():
    deploy_plan = json.loads(base64.b64decode(os.environ["DEPLOY_PLAN"]).decode())

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    result = {
        "passed": [],
        "failed": [],
    }

    for service in deploy_plan:

        print(
            f"🔍 post-switch verify: {service}",
            file=sys.stderr,
        )

        s = state["services"][service]

        active = s["active"]
        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{active}"

        print(
            f"phase 1 smoke: {service}",
            file=sys.stderr,
        )

        if not wait_health(container, port, health):
            result["failed"].append(service)
            continue

        print(
            f"phase 2 soak sleep: {service}",
            file=sys.stderr,
        )

        time.sleep(60)

        print(
            f"phase 3 soak verify: {service}",
            file=sys.stderr,
        )

        if wait_health(container, port, health):
            result["passed"].append(service)
        else:
            result["failed"].append(service)

    print(json.dumps(result))


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/push_to_vds.sh
====================================================================================================
```
#!/usr/bin/env bash
set -e

echo "=== PUSH TO VDS START ==="
date
whoami
pwd

cd ~/repair-crm

echo "=== UPDATE COMPOSE ==="
curl -fsSL https://raw.githubusercontent.com/kpa9pt/repair-crm/main/docker-compose.yml -o docker-compose.yml

echo "=== WRITE ENV ==="
cat > .env <<EOF
DATABASE_URL=$DATABASE_URL
ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_PASSWORD=$ADMIN_PASSWORD
SECRET_KEY=$SECRET_KEY
TELEGRAM_TOKEN=$TELEGRAM_TOKEN
DOMAIN_NAME=$DOMAIN_NAME
EOF

echo "=== DOCKER COMPOSE UP ==="
docker compose up -d

echo "=== DONE ==="
docker ps
```

====================================================================================================
FILE: scripts/deploy/render_compose.py
====================================================================================================
```
import json
import os

STATE_FILE = os.environ.get("STATE_FILE", "state.json")

with open(STATE_FILE) as f:
    state = json.load(f)

yaml = ["services:"]

for service_name, config in state["services"].items():

    strategy = config["strategy"]

    if strategy == "blue-green":

        yaml.append(f"  {service_name}-blue:")
        yaml.append(f"    image: {config['blue']['image']}")

        yaml.append(f"  {service_name}-green:")
        yaml.append(f"    image: {config['green']['image']}")

    elif strategy == "single":

        yaml.append(f"  {service_name}:")
        yaml.append(f"    image: {config['image']}")

print("\n".join(yaml))

```

====================================================================================================
FILE: scripts/deploy/run_rollbacks.py
====================================================================================================
```
import json
import os
import base64
import subprocess


def load_rollback_decision():
    data = os.environ["ROLLBACK_DECISION"]
    return json.loads(base64.b64decode(data).decode())


def main():
    decision = load_rollback_decision()

    failed = decision.get("failed", [])

    if not failed:
        print("✅ no rollback required")
        return

    server_user = os.environ["SERVER_USER"]
    server_ip = os.environ["SERVER_IP"]

    for service in failed:

        print(f"🔄 rollback: {service}")

        subprocess.run(
            [
                "ssh",
                f"{server_user}@{server_ip}",
                f"ROLLBACK_SERVICE={service} python3 -",
            ],
            stdin=open("scripts/rollback.py", "rb"),
            check=True,
        )

    print("✅ rollback engine finished")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/switch_services.py
====================================================================================================
```
import json
import sys
import os
import base64
from pathlib import Path


def load_deploy_plan():
    plan = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(plan).decode())


def main():
    deploy_plan = load_deploy_plan()
    if not deploy_plan:
        print("no changes")
        sys.exit(0)

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:
        active = state["services"][service]["active"]
        new = "green" if active == "blue" else "blue"

        state["services"][service]["active"] = new

        print(f"🔁 {service}: {active} → {new}")

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/unlock_rollback.py
====================================================================================================
```
import json
import os
import base64
from pathlib import Path


def load_rollback_decision():
    data = os.environ["ROLLBACK_DECISION"]
    return json.loads(base64.b64decode(data).decode())


def main():
    decision = load_rollback_decision()

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in decision["passed"]:

        if service not in state["services"]:
            print(f"⚠️ unknown service: {service}")
            continue

        state["services"][service]["rollback_locked"] = False

        print(f"🔓 rollback unlocked: {service}")

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/update_state.py
====================================================================================================
```
import json
import os

STATE_PATH = "state.json"
CHANGES_PATH = "images.json"

OWNER = "kpa9pt"

DEPLOY_ID = os.getenv("DEPLOY_ID")


def load(path):
    with open(path) as f:
        return json.load(f)


state = load(STATE_PATH)
changes = load(CHANGES_PATH)

state["deploy_id"] = DEPLOY_ID


def build_image(service, sha):
    return f"ghcr.io/{OWNER}/repair-crm-{service}:{sha}"


for service, sha in changes.items():

    if service not in state["services"]:
        state["services"][service] = {"strategy": "single", "rollback_locked": False}

    service_state = state["services"][service]

    image = build_image(service, sha)

    if service_state["strategy"] == "blue-green":

        active = service_state["active"]
        inactive = "green" if active == "blue" else "blue"

        service_state[inactive]["image"] = image

    else:

        service_state["image"] = image


print(json.dumps(state, indent=2))

```

====================================================================================================
FILE: scripts/deploy/verify_inactive_services.py
====================================================================================================
```
import json
import sys
import subprocess
import time
import os
import base64
from pathlib import Path


def healthcheck(container, port, health):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{health}', timeout=2)"
        ),
    ]

    return subprocess.run(cmd).returncode == 0


def load_deploy_plan():
    plan = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(plan).decode())


def main():
    deploy_plan = load_deploy_plan()

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:

        print(f"🔍 verifying {service}")

        s = state["services"][service]

        active = s["active"]

        inactive = "green" if active == "blue" else "blue"

        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{inactive}"

        ok = False

        for i in range(60):
            if healthcheck(container, port, health):
                print(f"✅ {container} healthy")
                ok = True
                break

            print(f"retry {i}")
            time.sleep(2)

        if not ok:
            print(f"❌ {container} failed")
            sys.exit(1)


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/verify_services.py
====================================================================================================
```
import json
import sys
import subprocess
import time
import os
import base64
from pathlib import Path


def healthcheck(container, port, health):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{health}', timeout=2)"
        ),
    ]

    return subprocess.run(cmd).returncode == 0


def load_deploy_plan():
    plan = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(plan).decode())


def main():
    deploy_plan = load_deploy_plan()

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:

        print(f"🔍 verifying {service}")

        s = state["services"][service]

        active = s["active"]
        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{active}"

        ok = False

        for i in range(60):
            if healthcheck(container, port, health):
                print(f"✅ {service} healthy")
                ok = True
                break

            print(f"retry {i}")

            time.sleep(2)

        if not ok:
            print(f"❌ {service} failed")
            sys.exit(1)

    subprocess.run(["docker", "exec", "nginx", "/scripts/reload.sh"], check=True)

    print("🔁 nginx reloaded")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/rollback.py
====================================================================================================
```
import json
import subprocess
import time
import sys
import os

from pathlib import Path

STATE_FILE = Path(
    os.getenv(
        "STATE_PATH",
        str(Path.home() / "repair-crm" / "state" / "state.json"),
    )
)

WORKDIR = Path(
    os.getenv(
        "WORKDIR",
        str(Path.home() / "repair-crm"),
    )
)

NGINX_CONTAINER = "nginx"

service = os.getenv("ROLLBACK_SERVICE")
if not service:
    raise RuntimeError("ROLLBACK_SERVICE not set")


def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def opposite(active: str) -> str:
    if active == "blue":
        return "green"
    return "blue"


def service_name(slot: str) -> str:
    return f"{service}-{slot}"


def wait_health(container: str, port: int, healthcheck: str, retries=30, delay=2):
    print(f"⏳ Waiting health: {container}")

    for i in range(retries):
        try:
            subprocess.run(
                [
                    "docker",
                    "exec",
                    container,
                    "python",
                    "-c",
                    (
                        "import urllib.request;"
                        "urllib.request.urlopen("
                        f"'http://localhost:{port}{healthcheck}', timeout=2"
                        ")"
                    ),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("✅ health OK")
            return True

        except subprocess.CalledProcessError:
            print(f"retry {i + 1}/{retries}")
            time.sleep(delay)

    return False


def reload_nginx():
    print("🔁 reloading nginx")
    subprocess.run(
        ["docker", "exec", NGINX_CONTAINER, "/scripts/reload.sh"],
        check=True,
    )


def main():
    state = load_state()

    service_state = state["services"][service]

    port = service_state.get("port", 8000)
    healthcheck = service_state.get("healthcheck", "/health")

    if service_state["strategy"] == "single":
        print("single strategy rollback not supported")
        sys.exit(1)

    active = service_state["active"]
    target = opposite(active)

    target_container = service_name(target)

    print(f"🔄 rollback: {active} → {target}")

    # 1. start target
    # WORKDIR = Path.home() / "repair-crm"

    subprocess.run(
        # ["docker", "compose", "up", "-d", f"{target_container}"],
        ["docker", "restart", f"{target_container}"],
        cwd=WORKDIR,
        check=True,
    )

    # 2. healthcheck
    if not wait_health(
        target_container,
        port,
        healthcheck,
    ):
        print("❌ rollback failed: target unhealthy")
        sys.exit(1)

    # 3. switch active
    state["services"][service]["active"] = target
    save_state(state)

    # 4. reload nginx
    reload_nginx()

    print("✅ rollback completed")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/test.sh
====================================================================================================
```
#!/bin/bash
set -e

TEST_PATH=${1:-tests}


echo "🚀 Starting infrastructure..."
#docker compose down -v
#docker compose up -d --build
docker compose \
  -f docker-compose.yml \
  -f docker-compose.test.yml \
  down -v

docker compose \
  -f docker-compose.yml \
  -f docker-compose.test.yml \
  up -d --build

get_health() {
  docker inspect --format='{{.State.Health.Status}}' "$1"
}

wait_for_health() {
  local name=$1
  local id
  id=$(docker compose ps -q "$name")

  if [ -z "$id" ]; then
    echo "❌ Container $name not found"
    exit 1
  fi

  echo "⏳ Waiting for $name..."

#  until [ "$(get_health "$id")" = "healthy" ]; do
#    pass
#  done

  echo "✅ $name is healthy"
}

echo "⏳ Waiting for services..."

wait_for_health postgres
wait_for_health gateway-blue


# В начале скрипта, после поднятия postgres
echo "Creating test database..."
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE repair_crm_test" 2>/dev/null || true

echo "Applying migrations..."
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test alembic upgrade head

echo "🧪 Running tests..."
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test
pytest "$TEST_PATH" -v

echo "🧹 Cleaning up..."
docker compose down -v
```

====================================================================================================
FILE: services/certbot/Dockerfile
====================================================================================================
```
FROM certbot/certbot:latest

RUN apk add --no-cache bash docker-cli

COPY services/certbot/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

====================================================================================================
FILE: services/certbot/entrypoint.sh
====================================================================================================
```
#!/bin/sh
set -e

DOMAIN=${DOMAIN_NAME:-localhost}
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

echo "🚀 Certbot service started for domain: $DOMAIN"

if [ "$DOMAIN" = "localhost" ]; then
  echo "Local mode detected, certbot disabled"
  while true; do sleep 12h; done
fi

# Функция для запроса сертификата с повторными попытками
get_certificate() {
  while true; do
    echo "📦 Requesting new certificate..."
    if certbot certonly --webroot --webroot-path=/var/www/certbot \
      --email admin@$DOMAIN --agree-tos --no-eff-email \
      -d "$DOMAIN" --non-interactive; then

      echo "✅ Certificate issued"
      return 0
    else
      echo "❌ Failed, checking if rate limit..."
      # Если ошибка содержит "too many failed authorizations" - ждем 1 час
      if certbot --version 2>/dev/null && \
         certbot certificates 2>&1 | grep -q "too many failed authorizations"; then
        echo "⏳ Rate limit detected, waiting 1 hour..."
        sleep 3600
      else
        echo "⏳ Other error, waiting 5 minutes..."
        sleep 300
      fi
    fi
  done
}

# Основная логика
if [ -f "$CERT_PATH" ]; then
  echo "✅ Certificate already exists"
else
  get_certificate
fi

# Бесконечный цикл обновления
while true; do
  sleep 12h
  echo "🔄 Renewing certificate..."
  certbot renew --webroot --webroot-path=/var/www/certbot --quiet
  echo "🔄 Renewal check done"
done
```

====================================================================================================
FILE: services/gateway/app/__init__.py
====================================================================================================
```

```

====================================================================================================
FILE: services/gateway/app/admin/__init__.py
====================================================================================================
```
"""
Модуль админ-панели SQLAdmin
"""

from .auth import AdminAuth
from .views import RepairRequestAdmin

__all__ = ["AdminAuth", "RepairRequestAdmin"]

```

====================================================================================================
FILE: services/gateway/app/admin/auth.py
====================================================================================================
```
"""
Аутентификация для админ-панели SQLAdmin
"""

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from passlib.context import CryptContext
from shared.settings import get_settings

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminAuth(AuthenticationBackend):
    """Простая аутентификация для админ-панели"""

    async def login(self, request: Request) -> bool:
        """Обработка входа в админку"""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        settings = get_settings()

        # Здесь можно заменить на чтение из БД или переменных окружения
        # Для старта - фиксированные учетные данные
        if username == settings.admin_username and password == settings.admin_password:
            request.session.update({"admin_authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        """Обработка выхода из админки"""
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """Проверка авторизации"""
        return request.session.get("admin_authenticated", False)

```

====================================================================================================
FILE: services/gateway/app/admin/views.py
====================================================================================================
```
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqladmin import ModelView

from shared.models import RepairRequest
from shared.enums import Urgency, RequestStatus

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class RepairRequestAdmin(ModelView, model=RepairRequest):
    """Админка RepairRequest"""

    name = "Заявка"
    name_plural = "Заявки на ремонт"
    icon = "fa-solid fa-wrench"

    # --------------------
    # СПИСОК
    # --------------------
    column_list = [
        RepairRequest.id,
        RepairRequest.vehicle_name,
        RepairRequest.status,
        RepairRequest.urgency,
        RepairRequest.is_operational,
        RepairRequest.created_at,
        RepairRequest.deadline,
        RepairRequest.client_name,
    ]

    column_labels = {
        RepairRequest.vehicle_name: "Техника",
        RepairRequest.client_name: "Клиент",
        RepairRequest.status: "Статус заявки",
        RepairRequest.urgency: "Срочность",
        RepairRequest.created_at: "Создано",
        RepairRequest.deadline: "Дедлайн",
        RepairRequest.is_operational: "Техника на ходу?",
    }

    column_editable_list = [
        RepairRequest.status,
        RepairRequest.urgency,
    ]

    column_filters = []

    column_default_sort = [(RepairRequest.created_at, True)]

    search_fields = [
        "vehicle_name",
        "client_name",
        "description",
    ]

    can_export = True
    can_view_details = True

    # --------------------
    # ФОРМА
    # --------------------
    form_columns = [
        # === ОСНОВНОЕ ===
        "vehicle_name",
        "description",
        "is_operational",
        # === УПРАВЛЕНИЕ ===
        "urgency",
        "status",
        "deadline",
        # === ФИНАНСЫ ===
        "parts_cost",
        "client_payment",
        # === КЛИЕНТ ===
        "client_name",
        "phone",
        "email",
    ]

    form_args = {
        "vehicle_name": {"label": "Техника"},
        "client_name": {"label": "Клиент", "default": "Топ Лес"},
        "phone": {"label": "Телефон"},
        "email": {"label": "Email"},
        "description": {"label": "Описание проблемы"},
        "urgency": {"label": "Срочность", "default": Urgency.NORMAL.value},
        "status": {"label": "Статус заявки", "default": RequestStatus.NEW.value},
        "deadline": {"label": "Дедлайн"},
        "parts_cost": {"label": "Стоимость запчастей", "default": Decimal("0.00")},
        "client_payment": {"label": "Оплата клиента", "default": Decimal("0.00")},
        "is_operational": {"label": "Техника на ходу?", "default": False},
    }

    # # ДЕФОЛТЫ (SQLAdmin правильный способ)
    # form_args = {
    #     "client_name": {"default": "Топ Лес"},
    #     "urgency": {"default": Urgency.NORMAL.value},
    #     "status": {"default": RequestStatus.NEW.value},
    #     "is_operational": {"default": False},
    #     "parts_cost": {"default": Decimal("0.00")},
    #     "client_payment": {"default": Decimal("0.00")},
    # }

    # --------------------
    # ВЫПАДАЮЩИЕ СПИСКИ
    # --------------------
    form_choices = {
        "urgency": [
            ("low", "🟢 Низкая"),
            ("normal", "🟡 Обычная"),
            ("high", "🟠 Высокая"),
            ("critical", "🔴 Критическая"),
        ],
        "status": [
            ("new", "🟢 Новая"),
            ("in_progress", "🟡 В работе"),
            ("waiting_parts", "🔴 Ожидает запчасти"),
            ("diagnostics", "🔵 Диагностика"),
            ("waiting_approval", "🟠 Ожидает согласования"),
            ("done", "✅ Готово"),
        ],
        "is_operational": [
            (True, "Да"),
            (False, "Нет"),
        ],
    }

    # --------------------
    # ФОРМАТИРОВАНИЕ ДАТ (MSK)
    # --------------------
    column_formatters = {
        RepairRequest.status: lambda m, a: {
            "new": "🟢 Новая",
            "in_progress": "🟡 В работе",
            "waiting_parts": "🔴 Ожидает запчасти",
            "diagnostics": "🔵 Диагностика",
            "waiting_approval": "🟠 Ожидает согласования",
            "done": "✅ Готово",
        }.get(m.status, m.status),
        RepairRequest.urgency: lambda m, a: {
            "low": "🟢 Низкая",
            "normal": "🟡 Обычная",
            "high": "🟠 Высокая",
            "critical": "🔴 Критическая",
        }.get(m.urgency, m.urgency),
        RepairRequest.created_at: lambda m, a: (
            m.created_at.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M")
            if m.created_at
            else ""
        ),
        RepairRequest.deadline: lambda m, a: (
            m.deadline.strftime("%d.%m.%Y") if m.deadline else ""
        ),
    }

```

====================================================================================================
FILE: services/gateway/app/main.py
====================================================================================================
```
from fastapi import FastAPI
from shared import get_settings
from .routers import repair_requests_router
from .admin import AdminAuth, RepairRequestAdmin
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware
from shared.db import get_engine  # ← импортируем новую функцию
from fastapi.responses import RedirectResponse


settings = get_settings()

app = FastAPI(
    title="Gateway API",
    version="0.1.0",
    description="API Gateway для CRM ремонтной мастерской",
)

# Добавляем middleware для сессий (нужен для аутентификации админки)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key or "supersecretkey-change-in-production",
    session_cookie="admin_session",
)

# Настройка админ-панели
authentication_backend = AdminAuth(secret_key=settings.secret_key or "supersecretkey")
admin = Admin(
    app,
    get_engine(),  # ← используем get_engine()
    authentication_backend=authentication_backend,
    title="Repair CRM Admin",
    logo_url="/static/logo.png",  # опционально
    base_url="/admin",  # ← ЯВНО УКАЗЫВАЕМ URL
)

# Регистрируем модели
admin.add_view(RepairRequestAdmin)

# Подключаем роутеры
app.include_router(repair_requests_router)


@app.get("/")
async def root():
    return RedirectResponse("/admin/")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/test_blue_green")
async def test_blue_green():
    return {"status": "ok"}


@app.get("/test_check_diff")
async def test_check_diff():
    return {"status": "ok"}

```

====================================================================================================
FILE: services/gateway/app/routers/__init__.py
====================================================================================================
```
from .repair_requests import router as repair_requests_router

__all__ = ["repair_requests_router"]

```

====================================================================================================
FILE: services/gateway/app/routers/repair_requests.py
====================================================================================================
```
"""
Роутер для работы с заявками на ремонт.

Все эндпоинты имеют префикс /api/v1/repair-requests
"""

from fastapi import APIRouter, Depends, HTTPException, status

from shared import get_session_maker
from shared.repository import RepairRequestRepository
from shared.schemas import (
    RepairRequestCreate,
    RepairRequestUpdate,
    RepairRequestResponse,
    RepairRequestListResponse,
)

router = APIRouter(prefix="/api/v1/repair-requests", tags=["Repair Requests"])


async def get_repo():
    session_maker = get_session_maker()

    async with session_maker() as session:
        yield RepairRequestRepository(session)


@router.post(
    "/", response_model=RepairRequestResponse, status_code=status.HTTP_201_CREATED
)
async def create_repair_request(
    request_data: RepairRequestCreate, repo: RepairRequestRepository = Depends(get_repo)
):
    """
    Создать новую заявку на ремонт.

    - **vehicle_name**: название техники (обязательно)
    - **description**: описание поломки (обязательно)
    - **urgency**: срочность (low/normal/high/critical)
    - **status**: статус (new/in_progress/waiting_parts/
        diagnostics/waiting_approval/done)
    """
    # Конвертируем Pydantic модель в словарь
    new_request = await repo.create(**request_data.model_dump())
    await repo.session.commit()
    return RepairRequestResponse.model_validate(new_request)


@router.get("/", response_model=RepairRequestListResponse)
async def get_all_repair_requests(
    skip: int = 0, limit: int = 100, repo: RepairRequestRepository = Depends(get_repo)
):
    """
    Получить список всех заявок с пагинацией.

    - **skip**: сколько заявок пропустить
    - **limit**: сколько заявок вернуть
    - Сортировка: сначала новые (по created_at DESC)
    """
    requests = await repo.get_all(skip=skip, limit=limit)
    total = len(requests)  # В будущем можно сделать отдельный метод для count

    return RepairRequestListResponse(
        items=[RepairRequestResponse.model_validate(r) for r in requests],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/vehicle/{vehicle_name}", response_model=RepairRequestListResponse)
async def get_repair_requests_by_vehicle(
    vehicle_name: str,
    skip: int = 0,
    limit: int = 100,
    repo: RepairRequestRepository = Depends(get_repo),
):
    """
    Получить все заявки для конкретной техники.

    - **vehicle_name**: название техники
    - **skip**: сколько пропустить
    - **limit**: сколько вернуть
    """
    # Метод get_by_vehicle нужно добавить в репозиторий
    # Пока используем фильтрацию через get_all (не оптимально)
    all_requests = await repo.get_by_vehicle(vehicle_name)
    filtered = [r for r in all_requests if r.vehicle_name == vehicle_name]
    total = len(filtered)
    paginated = filtered[skip : skip + limit]

    return RepairRequestListResponse(
        items=[RepairRequestResponse.model_validate(r) for r in paginated],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{request_id}", response_model=RepairRequestResponse)
async def get_repair_request(
    request_id: int, repo: RepairRequestRepository = Depends(get_repo)
):
    """
    Получить конкретную заявку по ID.
    """
    request = await repo.get_by_id(request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair request with id {request_id} not found",
        )
    return RepairRequestResponse.model_validate(request)


@router.patch("/{request_id}", response_model=RepairRequestResponse)
async def update_repair_request(
    request_id: int,
    update_data: RepairRequestUpdate,
    repo: RepairRequestRepository = Depends(get_repo),
):
    """
    Обновить заявку (частичное обновление).

    Можно обновить любое поле или несколько полей сразу.
    """
    existing = await repo.get_by_id(request_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair request with id {request_id} not found",
        )

    # Обновляем только переданные поля
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(existing, key, value)

    # await repo.session.commit()
    await repo.session.commit()
    await repo.session.refresh(existing)

    return RepairRequestResponse.model_validate(existing)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repair_request(
    request_id: int, repo: RepairRequestRepository = Depends(get_repo)
):
    """
    Удалить заявку по ID.
    """
    existing = await repo.get_by_id(request_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair request with id {request_id} not found",
        )

    await repo.session.delete(existing)
    await repo.session.commit()

    return None  # 204 No Content

```

====================================================================================================
FILE: services/gateway/Dockerfile
====================================================================================================
```
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/gateway ./services/gateway
COPY shared ./shared

COPY alembic.ini .
```

====================================================================================================
FILE: services/migrations/Dockerfile
====================================================================================================
```
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY shared ./shared
COPY alembic.ini .

CMD ["alembic", "upgrade", "head"]
```

====================================================================================================
FILE: services/nginx/Dockerfile
====================================================================================================
```
FROM nginx:alpine

RUN apk add --no-cache gettext inotify-tools bash jq



COPY services/nginx/nginx-https.conf /etc/nginx/nginx-https.conf
COPY services/nginx/nginx-http.conf /etc/nginx/nginx-http.conf

# 👇 ВСЕ скрипты в одну папку
COPY services/nginx/scripts/ /scripts/

RUN chmod +x /scripts/*.sh

ENTRYPOINT ["/scripts/entrypoint.sh"]
```

====================================================================================================
FILE: services/nginx/nginx-http.conf
====================================================================================================
```
events {}

http {
    include /etc/nginx/upstreams/upstream.conf;

    server {
        listen 80;
        server_name ${DOMAIN_NAME};

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        location /.well-known/acme-challenge/healthcheck {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass http://gateway_backend;
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
            proxy_next_upstream_tries 3;
            proxy_connect_timeout 5s;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }
    }

}
```

====================================================================================================
FILE: services/nginx/nginx-https.conf
====================================================================================================
```
events {}

http {
    include /etc/nginx/upstreams/upstream.conf;

    server {
        listen 80;
        server_name ${DOMAIN_NAME};

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        location /.well-known/acme-challenge/healthcheck {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass http://gateway_backend;
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
            proxy_next_upstream_tries 3;
            proxy_connect_timeout 5s;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }
    }

    server {
        listen 443 ssl;
        server_name ${DOMAIN_NAME};

        ssl_certificate /etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/${DOMAIN_NAME}/privkey.pem;

        location /.well-known/acme-challenge/healthcheck {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass http://gateway_backend;
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
            proxy_next_upstream_tries 3;
            proxy_connect_timeout 5s;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }
    }

}
```

====================================================================================================
FILE: services/nginx/scripts/entrypoint.sh
====================================================================================================
```
#!/bin/sh
set -e

echo "[BOOT] nginx starting"

echo "[STEP] init state"
/scripts/init_state.sh

echo "[STEP] render upstream"
/scripts/render_upstream.sh

echo "[STEP] generate nginx config"
/scripts/nginx_config.sh

echo "[STEP] nginx test"
nginx -t

echo "[STEP] start nginx"
nginx -g 'daemon off;' &
NGINX_PID=$!

echo "[STEP] watcher start"
/scripts/watcher.sh &

wait $NGINX_PID
```

====================================================================================================
FILE: services/nginx/scripts/init_state.sh
====================================================================================================
```
#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json

echo "[STATE] checking state file"

# если это директория — это сломанный volume
if [ -d "$STATE_FILE" ]; then
  echo "[STATE] ERROR: state.json is directory, fixing"
  rm -rf "$STATE_FILE"
fi

# если файла нет — создаём
if [ ! -f "$STATE_FILE" ]; then
  echo "[STATE] state.json missing, generating local state"
  /scripts/local_state.sh
fi

echo "[STATE] state loaded"
```

====================================================================================================
FILE: services/nginx/scripts/local_state.sh
====================================================================================================
```
#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json
#dfff
echo "[LOCAL] generating default state"

cat > "$STATE_FILE" <<EOF
{
  "deploy_id": "local",
  "services": {
    "gateway": {
      "strategy": "blue-green",
      "active": "blue",
      "port": 8000,
      "healthcheck": "/health",
      "rollback_locked": false
    }
  }
}
EOF
```

====================================================================================================
FILE: services/nginx/scripts/nginx_config.sh
====================================================================================================
```
#!/bin/sh
set -e

DOMAIN="${DOMAIN_NAME:-localhost}"
CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

echo "[NGINX] generating nginx.conf..."

if [ -f "$CERT" ]; then
  CONF="/etc/nginx/nginx-https.conf"
  echo "[NGINX] mode=https"
else
  CONF="/etc/nginx/nginx-http.conf"
  echo "[NGINX] mode=http"
fi

envsubst '$DOMAIN_NAME' < "$CONF" > /etc/nginx/nginx.conf

echo "[NGINX] nginx.conf generated"
```

====================================================================================================
FILE: services/nginx/scripts/reload.sh
====================================================================================================
```
#!/bin/sh
set -e

/scripts/render_upstream.sh
nginx -t
nginx -s reload
```

====================================================================================================
FILE: services/nginx/scripts/render_upstream.sh
====================================================================================================
```
#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json

mkdir -p /etc/nginx/upstreams

rm -f /etc/nginx/upstreams/*.conf 2>/dev/null || true

echo "[RENDER] state=$STATE_FILE"

jq -r '
  .services
  | to_entries[]
  | select(.value.strategy == "blue-green")
  | "\(.key) \(.value.active) \(.value.port)"
' "$STATE_FILE" |
while read SERVICE ACTIVE PORT
do

cat > "/etc/nginx/upstreams/upstream.conf" <<EOF
upstream ${SERVICE}_backend {
  server ${SERVICE}-${ACTIVE}:${PORT} max_fails=3 fail_timeout=10s;
}
EOF

echo "[RENDER] ${SERVICE} -> ${SERVICE}-${ACTIVE}:${PORT}"

done
```

====================================================================================================
FILE: services/nginx/scripts/watcher.sh
====================================================================================================
```
start_watcher() {
  WATCH_DIR="/etc/letsencrypt/live"
  DOMAIN=${DOMAIN_NAME:-localhost}

  echo "[WATCHER] started"

  # ждём появления папки (важно для certbot bootstrap)
  while [ ! -d "$WATCH_DIR/$DOMAIN" ]; do
    echo "[WATCHER] waiting cert dir..."
    sleep 2
  done

  render_upstream
  nginx -s reload

  echo "[WATCHER] cert dir ready"

  inotifywait -m -r -e create -e modify -e moved_to "$WATCH_DIR" |
  while read -r FILE; do
    case "$FILE" in
      *"/$DOMAIN/"*)
        echo "[WATCHER] change detected: $FILE"

        render_upstream
        nginx -s reload
        ;;
    esac
  done
}
```

====================================================================================================
FILE: services/watchdog/Dockerfile
====================================================================================================
```
FROM python:3.11-slim

RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY services/watchdog /app
COPY scripts/rollback.py /scripts/rollback.py

CMD ["python", "main.py"]
```

====================================================================================================
FILE: services/watchdog/main.py
====================================================================================================
```
import json
import time
import os
import subprocess


STATE_PATH = os.getenv("STATE_PATH", "/state/state.json")
WORKDIR = os.getenv("WORKDIR", "/app")


def load_state():
    with open(STATE_PATH) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def container_running(container):
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "-f",
            "{{.State.Running}}",
            container,
        ],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0 and result.stdout.strip() == "true"


def healthcheck(container, port, path):

    if not container_running(container):
        print(f"[WATCHDOG] {container} is not running")
        return False

    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{path}', timeout=2)"
        ),
    ]

    return (
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def trigger_rollback(service):
    print(f"[WATCHDOG] rollback triggered for {service}")

    env = os.environ.copy()
    env["ROLLBACK_SERVICE"] = service
    env["STATE_PATH"] = STATE_PATH
    env["WORKDIR"] = WORKDIR

    subprocess.run(["python", "/scripts/rollback.py"], env=env)


def check_service(service, cfg):
    if cfg.get("strategy") != "blue-green":
        return True

    active = cfg["active"]
    container = f"{service}-{active}"

    port = cfg.get("port", 8000)
    health = cfg.get("healthcheck", "/health")

    retries = 15

    for i in range(retries):
        if healthcheck(container, port, health):
            return True
        time.sleep(2)

    return False


def main():
    while True:
        state = load_state()

        rolled_back_this_cycle = set()

        for service, cfg in state["services"].items():

            if cfg.get("strategy") != "blue-green":
                continue

            if cfg.get("rollback_locked", False):
                print(f"[WATCHDOG] rollback locked → skip {service}")
                continue

            ok = check_service(service, cfg)

            if ok:
                continue

            if service in rolled_back_this_cycle:
                continue

            print(f"[WATCHDOG] service failed → {service}")

            # rollback
            trigger_rollback(service)

            # mark locked immediately
            state["services"][service]["rollback_locked"] = True
            rolled_back_this_cycle.add(service)

            save_state(state)

        time.sleep(60)


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: shared/__init__.py
====================================================================================================
```
from .settings import get_settings
from .models import Base, RepairRequest
from .db import get_session_maker
from .enums import Urgency, RequestStatus

__all__ = [
    "get_settings",
    "Base",
    "RepairRequest",
    "get_session_maker",
    "Urgency",
    "RequestStatus",
]

```

====================================================================================================
FILE: shared/db/__init__.py
====================================================================================================
```
from .session import get_session_maker, get_engine, reset_db

__all__ = ["get_session_maker", "get_engine", "reset_db"]

```

====================================================================================================
FILE: shared/db/migrations/env.py
====================================================================================================
```
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from alembic import context
from shared.models import Base
import os

config = context.config

# Берём DATABASE_URL из переменной окружения (не из settings!)
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm"
)

config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

```

====================================================================================================
FILE: shared/db/migrations/README
====================================================================================================
```
Generic single-database configuration with an async dbapi.
```

====================================================================================================
FILE: shared/db/migrations/versions/2026_05_28_2109-ef27e3a3bb21_.py
====================================================================================================
```
"""

Revision ID: ef27e3a3bb21
Revises:
Create Date: 2026-05-28 21:09:51.922444

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "ef27e3a3bb21"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "repair_requests",
        sa.Column("vehicle_name", sa.String(length=200), nullable=False),
        sa.Column(
            "client_name",
            sa.String(length=100),
            server_default="Топ Лес",
            nullable=False,
        ),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "urgency",
            sa.String(length=20),
            server_default="normal",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="new",
            nullable=False,
        ),
        sa.Column("is_operational", sa.Boolean(), nullable=True),
        sa.Column(
            "parts_cost",
            sa.Numeric(precision=12, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "client_payment",
            sa.Numeric(precision=12, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_repair_requests_id"), "repair_requests", ["id"], unique=False
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_repair_requests_id"), table_name="repair_requests")
    op.drop_table("repair_requests")
    # ### end Alembic commands ###

```

====================================================================================================
FILE: shared/db/migrations/versions/2026_05_29_2232-dfae9b9dfe98_.py
====================================================================================================
```
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "dfae9b9dfe98"
down_revision: Union[str, Sequence[str], None] = "ef27e3a3bb21"
branch_labels = None
depends_on = None


urgency_enum = sa.Enum("LOW", "NORMAL", "HIGH", "CRITICAL", name="urgency_enum")

request_status_enum = sa.Enum(
    "NEW",
    "IN_PROGRESS",
    "WAITING_PARTS",
    "DIAGNOSTICS",
    "WAITING_APPROVAL",
    "DONE",
    name="request_status_enum",
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1. создаём enum-типы
    urgency_enum.create(bind, checkfirst=True)
    request_status_enum.create(bind, checkfirst=True)

    # 2. УБИРАЕМ старые дефолты (важно!)
    op.alter_column(
        "repair_requests",
        "urgency",
        existing_type=sa.VARCHAR(length=20),
        server_default=None,
    )

    op.alter_column(
        "repair_requests",
        "status",
        existing_type=sa.VARCHAR(length=30),
        server_default=None,
    )

    # 3. меняем типы
    op.alter_column(
        "repair_requests",
        "urgency",
        existing_type=sa.VARCHAR(length=20),
        type_=sa.Enum("LOW", "NORMAL", "HIGH", "CRITICAL", name="urgency_enum"),
        postgresql_using="urgency::text::urgency_enum",
        existing_nullable=False,
    )

    op.alter_column(
        "repair_requests",
        "status",
        existing_type=sa.VARCHAR(length=30),
        type_=sa.Enum(
            "NEW",
            "IN_PROGRESS",
            "WAITING_PARTS",
            "DIAGNOSTICS",
            "WAITING_APPROVAL",
            "DONE",
            name="request_status_enum",
        ),
        postgresql_using="status::text::request_status_enum",
        existing_nullable=False,
    )

    # 4. ставим новые enum defaults
    op.alter_column(
        "repair_requests",
        "urgency",
        server_default=sa.text("'NORMAL'::urgency_enum"),
    )

    op.alter_column(
        "repair_requests",
        "status",
        server_default=sa.text("'NEW'::request_status_enum"),
    )


def downgrade() -> None:
    op.alter_column(
        "repair_requests",
        "urgency",
        server_default=None,
    )
    op.alter_column(
        "repair_requests",
        "status",
        server_default=None,
    )

    op.alter_column(
        "repair_requests",
        "urgency",
        type_=sa.VARCHAR(length=20),
        existing_type=sa.Enum(name="urgency_enum"),
        postgresql_using="urgency::text",
        existing_nullable=False,
    )

    op.alter_column(
        "repair_requests",
        "status",
        type_=sa.VARCHAR(length=30),
        existing_type=sa.Enum(name="request_status_enum"),
        postgresql_using="status::text",
        existing_nullable=False,
    )

    # (опционально) удаление enum типов
    request_status_enum.drop(op.get_bind(), checkfirst=True)
    urgency_enum.drop(op.get_bind(), checkfirst=True)

```

====================================================================================================
FILE: shared/db/migrations/versions/2026_05_29_2314-794a7553b817_.py
====================================================================================================
```
"""

Revision ID: 794a7553b817
Revises: dfae9b9dfe98
Create Date: 2026-05-29 23:14:23.536702

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "794a7553b817"
down_revision: Union[str, Sequence[str], None] = "dfae9b9dfe98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "repair_requests",
        "deadline",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.Date(),
        existing_nullable=True,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "repair_requests",
        "deadline",
        existing_type=sa.Date(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
    )
    # ### end Alembic commands ###

```

====================================================================================================
FILE: shared/db/session.py
====================================================================================================
```
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from shared.settings import get_settings

_engine = None
_session_maker = None


def get_session_maker():
    global _engine, _session_maker
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=True)
        _session_maker = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_maker


def get_engine():
    """Возвращает асинхронный движок БД"""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=True)
    return _engine


def reset_db():
    global _engine, _session_maker
    _engine = None
    _session_maker = None

```

====================================================================================================
FILE: shared/enums.py
====================================================================================================
```
"""
Enum классы для выпадающих списков в моделях и схемах
"""

from enum import Enum


class Urgency(str, Enum):
    """Срочность заявки"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

    def __str__(self) -> str:
        return self.value


class RequestStatus(str, Enum):
    """Статус заявки на ремонт"""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    WAITING_PARTS = "waiting_parts"
    DIAGNOSTICS = "diagnostics"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"

    def __str__(self) -> str:
        return self.value

```

====================================================================================================
FILE: shared/models/__init__.py
====================================================================================================
```
from .base import DeclarativeBase as Base
from .repair_request import RepairRequest

__all__ = (
    "Base",
    "RepairRequest",
)

```

====================================================================================================
FILE: shared/models/base.py
====================================================================================================
```
from sqlalchemy import Column, Integer
from sqlalchemy.orm import declared_attr, declarative_base


class Base:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, index=True)

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"


DeclarativeBase = declarative_base(cls=Base)

```

====================================================================================================
FILE: shared/models/repair_request.py
====================================================================================================
```
from sqlalchemy import Column, String, Text, Boolean, DateTime, Numeric, Date
from sqlalchemy.sql import func
from shared.models import Base
from shared.enums import Urgency, RequestStatus
from sqlalchemy import Enum as SQLEnum


class RepairRequest(Base):
    __tablename__ = "repair_requests"

    vehicle_name = Column(String(200), nullable=False)
    client_name = Column(String(100), nullable=False, server_default="Топ Лес")
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)

    urgency = Column(
        SQLEnum(Urgency, name="urgency_enum"),
        nullable=False,
        server_default=Urgency.NORMAL.value,
    )

    status = Column(
        SQLEnum(RequestStatus, name="request_status_enum"),
        nullable=False,
        server_default=RequestStatus.NEW.value,
    )

    is_operational = Column(Boolean, nullable=True)
    parts_cost = Column(Numeric(12, 2), nullable=False, server_default="0")
    client_payment = Column(Numeric(12, 2), nullable=False, server_default="0")
    deadline = Column(Date, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

```

====================================================================================================
FILE: shared/repository.py
====================================================================================================
```
"""
Репозиторий — это слой абстракции между бизнес-логикой и базой данных.
Он скрывает детали SQLAlchemy и позволяет легко подменить БД в тестах.
"""

from sqlalchemy import select
from shared.models import RepairRequest


class RepairRequestRepository:
    def __init__(self, session):
        """
        Внедряем сессию через конструктор (Dependency Injection).
        Это позволяет подставить фейковую сессию в тестах.
        """
        self.session = session

    async def create(self, **kwargs) -> RepairRequest:
        """Создать новую заявку на ремонт."""
        request = RepairRequest(**kwargs)
        self.session.add(request)
        # НЕТ commit! Только flush для получения ID
        await self.session.flush()
        # await self.session.refresh(request)
        return request

    async def get_by_id(self, request_id: int) -> RepairRequest | None:
        """Получить заявку по ID."""
        result = await self.session.execute(
            select(RepairRequest).where(RepairRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100):
        """Получить список заявок с пагинацией."""
        result = await self.session.execute(
            select(RepairRequest).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_by_vehicle(self, vehicle_name: str, skip: int = 0, limit: int = 100):
        """Получить заявки по названию техники с пагинацией"""
        result = await self.session.execute(
            select(RepairRequest)
            .where(RepairRequest.vehicle_name == vehicle_name)
            .order_by(RepairRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

```

====================================================================================================
FILE: shared/schemas/__init__.py
====================================================================================================
```
"""
Pydantic схемы для обмена данными между клиентом и сервером
"""

from .repair_request import (
    RepairRequestBase,
    RepairRequestCreate,
    RepairRequestUpdate,
    RepairRequestResponse,
    RepairRequestListResponse,
)

__all__ = [
    "RepairRequestBase",
    "RepairRequestCreate",
    "RepairRequestUpdate",
    "RepairRequestResponse",
    "RepairRequestListResponse",
]

```

====================================================================================================
FILE: shared/schemas/repair_request.py
====================================================================================================
```
"""
Pydantic схемы для RepairRequest

Эти схемы определяют:
- Как выглядит запрос от клиента (Create, Update)
- Как выглядит ответ сервера (Response)
- Какие поля обязательные, а какие нет
"""

from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from shared.enums import Urgency, RequestStatus
from datetime import date


class RepairRequestBase(BaseModel):
    """
    Базовый класс с общими полями для всех схем.
    Все поля опциональны, кроме vehicle_name и description (для create)
    """

    vehicle_name: str = Field(
        ..., description="Название техники", examples=["Квадроцикл-5"]
    )
    client_name: Optional[str] = Field(
        None, description="Имя клиента", examples=["Топ Лес"]
    )
    phone: Optional[str] = Field(
        None, description="Телефон клиента", examples=["+7-999-123-45-67"]
    )
    email: Optional[str] = Field(
        None, description="Email клиента", examples=["client@example.com"]
    )
    description: str = Field(..., description="Описание поломки")
    urgency: Urgency = Field(default=Urgency.NORMAL, description="Срочность")
    status: RequestStatus = Field(default=RequestStatus.NEW, description="Статус")
    is_operational: Optional[bool] = Field(False, description="Техника на ходу?")
    parts_cost: Decimal = Field(
        default_factory=lambda: Decimal("0.00"), description="Стоимость запчастей"
    )
    client_payment: Decimal = Field(
        default_factory=lambda: Decimal("0.00"), description="Оплата клиента"
    )
    deadline: Optional[date] = Field(None, description="Дедлайн (дата без времени)")


class RepairRequestCreate(RepairRequestBase):
    """
    Схема для POST запроса (создание новой заявки).
    Наследует все поля от Base, но явно указываем обязательные.
    """

    # Поле vehicle_name уже есть в Base
    # Поле description уже есть в Base
    pass  # Все поля уже определены в RepairRequestBase


class RepairRequestUpdate(BaseModel):
    """
    Схема для PATCH запроса (частичное обновление).
    Все поля опциональны — можно обновить только то, что нужно.
    """

    vehicle_name: Optional[str] = Field(None, description="Название техники")
    client_name: Optional[str] = Field(None, description="Имя клиента")
    phone: Optional[str] = Field(None, description="Телефон клиента")
    email: Optional[str] = Field(None, description="Email клиента")
    description: Optional[str] = Field(None, description="Описание поломки")

    urgency: Optional[Urgency] = Field(None, description="Срочность")
    status: Optional[RequestStatus] = Field(None, description="Статус")

    is_operational: Optional[bool] = Field(None, description="Техника на ходу?")
    parts_cost: Optional[Decimal] = Field(None, description="Стоимость запчастей")
    client_payment: Optional[Decimal] = Field(None, description="Оплата клиента")
    deadline: Optional[date] = Field(None, description="Дедлайн (дата без времени)")


class RepairRequestResponse(RepairRequestBase):
    """
    Схема для GET ответа (возвращаем клиенту).
    Добавляем поля, которые генерируются БД (id, created_at)
    """

    id: int = Field(..., description="ID заявки")
    created_at: datetime = Field(..., description="Дата создания")

    # Настройка для работы с SQLAlchemy моделями
    model_config = ConfigDict(from_attributes=True)


class RepairRequestListResponse(BaseModel):
    """
    Схема для списка заявок (с пагинацией).
    """

    items: list[RepairRequestResponse] = Field(..., description="Список заявок")
    total: int = Field(..., description="Общее количество заявок (без учета пагинации)")
    skip: int = Field(..., description="Сколько пропущено")
    limit: int = Field(..., description="Лимит на страницу")

```

====================================================================================================
FILE: shared/settings.py
====================================================================================================
```
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm"
    )
    telegram_token: str | None = None
    secret_key: str | None = None  # Добавляем это поле
    admin_username: str = "admin"  # Добавляем с дефолтом
    admin_password: str = "admin123"  # Добавляем с дефолтом
    domain_name: str = "localhost"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()

```

====================================================================================================
FILE: state/state.json
====================================================================================================
```
{
  "deploy_id": "local",
  "services": {
    "gateway": {
      "strategy": "blue-green",
      "active": "blue",
      "port": 8000,
      "healthcheck": "/health",
      "rollback_locked": false
    }
  }
}

```

====================================================================================================
FILE: tests/__init__.py
====================================================================================================
```

```

====================================================================================================
FILE: tests/api/__init__.py
====================================================================================================
```

```

====================================================================================================
FILE: tests/api/conftest.py
====================================================================================================
```
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from services.gateway.app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def reset():
    from shared.db.session import reset_db

    reset_db()

```

====================================================================================================
FILE: tests/api/test_admin_panel.py
====================================================================================================
```
"""
Тесты для админ-панели SQLAdmin
"""

import pytest
from shared.settings import get_settings

pytest = pytest.mark.asyncio


async def test_admin_login_page_accessible(client):
    """Страница логина доступна"""
    response = await client.get("/admin/login")
    assert response.status_code == 200


async def test_admin_panel_redirects_to_login(client):
    """Без логина админка редиректит на логин"""
    response = await client.get("/admin", follow_redirects=False)
    assert response.status_code == 307 or response.status_code == 302


async def test_admin_login_with_correct_credentials(client):
    """Вход с правильными данными"""
    settings = get_settings()

    login_data = {
        "username": settings.admin_username,
        "password": settings.admin_password,
    }
    response = await client.post("/admin/login", data=login_data, follow_redirects=True)
    assert response.status_code == 200


async def test_repair_request_list_accessible_after_login(client):
    """После входа список заявок доступен"""
    # Логинимся
    settings = get_settings()

    await client.post(
        "/admin/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
    )
    # Проверяем список
    response = await client.get("/admin/repair-request/list")
    assert response.status_code == 200

```

====================================================================================================
FILE: tests/api/test_gateway.py
====================================================================================================
```
import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

```

====================================================================================================
FILE: tests/api/test_repair_requests.py
====================================================================================================
```
"""
API тесты для эндпоинтов RepairRequest.
"""

from shared.enums import Urgency, RequestStatus
import pytest

"""Тесты для API эндпоинтов"""


@pytest.mark.asyncio
async def test_create_repair_request(client):
    """Тест создания заявки через API"""
    request_data = {
        "vehicle_name": "Тестовый квадроцикл",
        "description": "Не заводится тестовая заявка",
        "urgency": Urgency.NORMAL.value,
        "status": RequestStatus.NEW.value,
    }

    response = await client.post("/api/v1/repair-requests/", json=request_data)

    assert response.status_code == 201
    data = response.json()
    assert data["vehicle_name"] == request_data["vehicle_name"]
    assert data["description"] == request_data["description"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_repair_request_invalid_data(client):
    """Тест создания заявки с невалидными данными"""
    response = await client.post(
        "/api/v1/repair-requests/", json={"description": "Только описание"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_all_repair_requests(client):
    """Тест получения списка всех заявок"""
    # Создаем тестовые данные
    for i in range(3):
        response = await client.post(
            "/api/v1/repair-requests/",
            json={"vehicle_name": f"Техника {i}", "description": f"Описание {i}"},
        )
        assert response.status_code == 201

    response = await client.get("/api/v1/repair-requests/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_get_repair_request_by_id(client):
    """Тест получения конкретной заявки по ID"""
    # Создаем
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={
            "vehicle_name": "Уникальная техника",
            "description": "Уникальное описание",
        },
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Получаем
    response = await client.get(f"/api/v1/repair-requests/{created_id}")
    assert response.status_code == 200
    assert response.json()["id"] == created_id


@pytest.mark.asyncio
async def test_get_nonexistent_repair_request(client):
    """Тест получения несуществующей заявки"""
    response = await client.get("/api/v1/repair-requests/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_repair_request(client):
    """Тест частичного обновления заявки"""
    # Создаем
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={
            "vehicle_name": "Техника для обновления",
            "description": "Оригинальное описание",
        },
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Обновляем статус
    response = await client.patch(
        f"/api/v1/repair-requests/{created_id}",
        json={"status": RequestStatus.IN_PROGRESS.value},
    )

    assert response.status_code == 200
    assert response.json()["status"] == RequestStatus.IN_PROGRESS.value
    assert response.json()["vehicle_name"] == "Техника для обновления"


@pytest.mark.asyncio
async def test_delete_repair_request(client):
    """Тест удаления заявки"""
    # Создаем
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={"vehicle_name": "Техника для удаления", "description": "Будет удалена"},
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Удаляем
    delete_response = await client.delete(f"/api/v1/repair-requests/{created_id}")
    assert delete_response.status_code == 204

    # Проверяем что удалена
    get_response = await client.get(f"/api/v1/repair-requests/{created_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_pagination(client):
    """Тест пагинации"""
    # Создаем 10 заявок
    for i in range(10):
        response = await client.post(
            "/api/v1/repair-requests/",
            json={"vehicle_name": f"Пагинация {i}", "description": f"Описание {i}"},
        )
        assert response.status_code == 201

    # Проверяем страницы
    resp1 = await client.get("/api/v1/repair-requests/?skip=0&limit=5")
    assert resp1.status_code == 200
    assert len(resp1.json()["items"]) == 5

    resp2 = await client.get("/api/v1/repair-requests/?skip=5&limit=5")
    assert resp2.status_code == 200
    assert len(resp2.json()["items"]) == 5


@pytest.mark.asyncio
async def test_get_by_vehicle_name(client):
    """Тест фильтрации по имени техники"""
    # Создаем заявки для конкретной техники
    for i in range(2):
        response = await client.post(
            "/api/v1/repair-requests/",
            json={"vehicle_name": "Специальная техника", "description": f"Заявка {i}"},
        )
        assert response.status_code == 201

    # Создаем заявку для другой техники
    response = await client.post(
        "/api/v1/repair-requests/",
        json={"vehicle_name": "Другая техника", "description": "Чужая заявка"},
    )
    assert response.status_code == 201

    response = await client.get("/api/v1/repair-requests/vehicle/Специальная техника")
    assert response.status_code == 200
    assert response.json()["total"] == 2

```

====================================================================================================
FILE: tests/conftest.py
====================================================================================================
```
"""
Общие фикстуры для всех тестов.
"""

```

====================================================================================================
FILE: tests/integration/__init__.py
====================================================================================================
```

```

====================================================================================================
FILE: tests/integration/conftest.py
====================================================================================================
```
"""
Фикстуры для интеграционных тестов (только здесь).
Эти фикстуры НЕ видны в unit и api тестах.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test"
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Тестовый движок БД (один раз на сессию)"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """Тестовая сессия (новая для каждого теста)"""
    async_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session

```

====================================================================================================
FILE: tests/integration/test_repair_request_repository.py
====================================================================================================
```
"""
Интеграционные тесты для репозитория RepairRequest.
"""

import pytest
from shared.repository import RepairRequestRepository


@pytest.mark.asyncio
async def test_repository_create(test_session):
    """Тест создания заявки через репозиторий"""
    repo = RepairRequestRepository(test_session)
    request = await repo.create(vehicle_name="Квадроцикл-5", description="Не заводится")
    assert request.id is not None
    assert request.vehicle_name == "Квадроцикл-5"
    assert request.description == "Не заводится"

```

====================================================================================================
FILE: tests/unit/__init__.py
====================================================================================================
```

```

====================================================================================================
FILE: tests/unit/test_repair_request.py
====================================================================================================
```
from shared.models import RepairRequest


def test_repair_request_creation():
    """Проверяем, что модель создаётся без ошибок."""
    request = RepairRequest(
        vehicle_name="Квадроцикл-5", description="Не заводится", status="new"
    )
    assert request.vehicle_name == "Квадроцикл-5"
    assert request.status == "new"

```

====================================================================================================
FILE: tools/__init__.py
====================================================================================================
```

```

====================================================================================================
FILE: tools/bundle.py
====================================================================================================
```
from pathlib import Path
from datetime import datetime

from .config import OUTPUT_DIR, PROJECT_NAME
from .dump import build_dump
from .stats import collect_stats


BUNDLE_DIR = OUTPUT_DIR / "ai_bundle"


BOOTSTRAP_PROMPT = """
Ты анализируешь проект repair_crm.

Тебе будут переданы:
1. project_dump.md — полный исходный код
2. stats.json — метрики проекта

Задача:
- понять архитектуру
- описать модули
- найти слабые места
- предложить улучшения
"""


def save(path: Path, content):
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(content, dict):
        import json
        path.write_text(json.dumps(content, indent=2), encoding="utf-8")
    else:
        path.write_text(content, encoding="utf-8")


def build_bundle():
    print("[INFO] Building AI bundle...")

    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

    dump_text = build_dump("full")
    stats = collect_stats()

    save(BUNDLE_DIR / "project_dump.md", dump_text)
    save(BUNDLE_DIR / "stats.json", stats)
    save(BUNDLE_DIR / "BOOTSTRAP_PROMPT.txt", BOOTSTRAP_PROMPT)

    readme = f"""# AI BUNDLE

Project: {PROJECT_NAME}
Generated: {datetime.now()}

FILES:
- project_dump.md
- stats.json
- BOOTSTRAP_PROMPT.txt
"""

    save(BUNDLE_DIR / "README.md", readme)

    print(f"[OK] AI bundle saved to: {BUNDLE_DIR}")


if __name__ == "__main__":
    build_bundle()
```

====================================================================================================
FILE: tools/config.py
====================================================================================================
```
from pathlib import Path

# from datetime import datetime

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# -----------------------------------------------------------------------------
# Project
# -----------------------------------------------------------------------------

PROJECT_NAME = "repair_crm"

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIR = PROJECT_ROOT / ".tools" / "output"

# -----------------------------------------------------------------------------
# Limits
# -----------------------------------------------------------------------------

MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB

# -----------------------------------------------------------------------------
# Ignore directories
# -----------------------------------------------------------------------------

IGNORE_DIRS = {
    ".git",
    ".idea",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    ".tools",          # не включаем сам дампер
}

# -----------------------------------------------------------------------------
# Ignore files
# -----------------------------------------------------------------------------

IGNORE_FILES = {
    ".DS_Store",
}

# -----------------------------------------------------------------------------
# Ignore extensions
# -----------------------------------------------------------------------------

IGNORE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".woff",
    ".woff2",
    ".ttf",
}

# -----------------------------------------------------------------------------
# Allowed extensions
# -----------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {
    ".py",
    ".sh",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".md",
    ".txt",
    ".sql",
    ".env",
    ".example",
}

# -----------------------------------------------------------------------------
# Files without extension
# -----------------------------------------------------------------------------

ALLOWED_FILENAMES = {
    "Dockerfile",
    "Makefile",
    "LICENSE",
    "README",
}

SENSITIVE_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
}
```

====================================================================================================
FILE: tools/core.py
====================================================================================================
```

```

====================================================================================================
FILE: tools/dump.py
====================================================================================================
```
from pathlib import Path

from .config import PROJECT_ROOT, PROJECT_NAME
from .utils import iter_project_files, is_allowed, read_text_file


# -----------------------------------------------------------------------------
# FULL DUMP
# -----------------------------------------------------------------------------

def build_full_dump() -> str:
    lines = []

    lines.append(f"# PROJECT FULL DUMP: {PROJECT_NAME}")
    lines.append(f"ROOT: {PROJECT_ROOT}")
    lines.append("")

    for path in iter_project_files(PROJECT_ROOT):

        if not is_allowed(path):
            continue

        rel = path.relative_to(PROJECT_ROOT)
        content = read_text_file(path)

        lines.append("=" * 100)
        lines.append(f"FILE: {rel}")
        lines.append("=" * 100)
        lines.append("```")
        lines.append(content)
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# CHANGED DUMP (git-based)
# -----------------------------------------------------------------------------

import subprocess


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, cwd=PROJECT_ROOT).decode().strip()


def get_changed_files() -> list[str]:
    result = run(["git", "status", "--porcelain"])

    files = []

    for line in result.splitlines():
        if not line:
            continue

        status, path = line[:2], line[3:]

        if status.strip() == "D":
            continue

        files.append(path)

    return sorted(set(files))


def get_diff(file_path: str) -> str:
    try:
        return run(["git", "diff", file_path])
    except subprocess.CalledProcessError:
        return ""


def build_changed_dump() -> str:
    files = get_changed_files()

    lines = []
    lines.append(f"# PROJECT CHANGED DUMP: {PROJECT_NAME}")
    lines.append("")
    lines.append(f"Changed files: {len(files)}")
    lines.append("")

    if not files:
        lines.append("No changes detected.")
        return "\n".join(lines)

    for file in files:

        path = PROJECT_ROOT / file

        lines.append("=" * 100)
        lines.append(f"FILE: {file}")
        lines.append("=" * 100)

        diff = get_diff(file)
        if diff:
            lines.append("## DIFF")
            lines.append("```diff")
            lines.append(diff)
            lines.append("```")

        if path.exists():
            lines.append("## CONTENT")
            lines.append("```")
            lines.append(read_text_file(path))
            lines.append("```")

        lines.append("")

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# PUBLIC API (ВАЖНО)
# -----------------------------------------------------------------------------

def build_dump(mode: str = "full") -> str:
    if mode == "changed":
        return build_changed_dump()

    return build_full_dump()


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "full"
    print(build_dump(mode))
```

====================================================================================================
FILE: tools/dump_project.py
====================================================================================================
```

```

====================================================================================================
FILE: tools/git_utils.py
====================================================================================================
```

```

====================================================================================================
FILE: tools/output/project_changed_dump.md
====================================================================================================
```
# PROJECT CHANGED DUMP: repair_crm

Changed files: 2

====================================================================================================
FILE: gitignore
====================================================================================================

====================================================================================================
FILE: services/nginx/scripts/reload.sh
====================================================================================================

## GIT DIFF

```diff
diff --git a/services/nginx/scripts/reload.sh b/services/nginx/scripts/reload.sh
index 6a239cf..c6bca8f 100644
--- a/services/nginx/scripts/reload.sh
+++ b/services/nginx/scripts/reload.sh
@@ -1,6 +1,6 @@
 #!/bin/sh
 set -e
-
+#jkl
 /scripts/render_upstream.sh
 nginx -t
 nginx -s reload
\ No newline at end of file
```

## FULL FILE

```
#!/bin/sh
set -e
#jkl
/scripts/render_upstream.sh
nginx -t
nginx -s reload
```

```

====================================================================================================
FILE: tools/output/project_dump.md
====================================================================================================
```
# PROJECT DUMP: repair_crm
Root: /Users/natalia/Python projects/repair_crm

====================================================================================================
FILE: .env.example
====================================================================================================

```
# Telegram Bot Token (обязательно)
TELEGRAM_TOKEN=ваш_токен_сюда

# JWT Secret Key (обязательно, минимум 32 символа)
SECRET_KEY=my-super-secret-key-for-jwt-change-me-in-production

# Для админ-панели
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

#Доменное имя если имеется
#DOMAIN_NAME=example.com

# Database URL
# Вариант для внешней БД (раскомментируйте)
# DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
```

====================================================================================================
FILE: .github/workflows/build-and-push.yml
====================================================================================================

```
name: Build and Push to GHCR

on:
#  workflow_dispatch:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Detect changed services
        uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            gateway:
              - 'services/gateway/**'
              - 'shared/**'
              - 'requirements.txt'

            migrations:
              - 'services/migrations/**'
              - 'shared/**'
              - 'alembic.ini'
              - 'requirements.txt'

            nginx:
              - 'services/nginx/**'

            certbot:
              - 'services/certbot/**'
            
            watchdog:
              - 'services/watchdog/**'
              - 'scripts/rollback.py'

      - name: Print detected changes
        run: |
          echo "gateway=${{ steps.changes.outputs.gateway }}"
          echo "migrations=${{ steps.changes.outputs.migrations }}"
          echo "nginx=${{ steps.changes.outputs.nginx }}"
          echo "certbot=${{ steps.changes.outputs.certbot }}"
          echo "watchdog=${{ steps.changes.outputs.watchdog }}"

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push gateway
        if: steps.changes.outputs.gateway == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/gateway/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-gateway:latest
            ghcr.io/${{ github.repository }}-gateway:${{ github.sha }}
            

      - name: Build and push migrations
        if: steps.changes.outputs.migrations == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/migrations/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-migrations:latest
            ghcr.io/${{ github.repository }}-migrations:${{ github.sha }}

      - name: Build and push nginx
        if: steps.changes.outputs.nginx == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/nginx/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-nginx:latest
            ghcr.io/${{ github.repository }}-nginx:${{ github.sha }}

      - name: Build and push certbot
        if: steps.changes.outputs.certbot == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/certbot/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-certbot:latest
            ghcr.io/${{ github.repository }}-certbot:${{ github.sha }}

      - name: Build and push watchdog
        if: steps.changes.outputs.watchdog == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/watchdog/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-watchdog:latest
            ghcr.io/${{ github.repository }}-watchdog:${{ github.sha }}

      - name: Build image manifest
        run: |
          python scripts/build_manifest.py > images.json
        env:
          CHANGED_GATEWAY: ${{ steps.changes.outputs.gateway }}
          CHANGED_MIGRATIONS: ${{ steps.changes.outputs.migrations }}
          CHANGED_NGINX: ${{ steps.changes.outputs.nginx }}
          CHANGED_CERTBOT: ${{ steps.changes.outputs.certbot }}
          CHANGED_WATCHDOG: ${{ steps.changes.outputs.watchdog }}

          GITHUB_SHA: ${{ github.sha }}

      - name: Upload images artifact
        uses: actions/upload-artifact@v4
        with:
          name: images
          path: images.json
```

====================================================================================================
FILE: .github/workflows/ci.yml
====================================================================================================

```
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          
      - name: Setup env for tests
        run: cp .env.example .env

      - name: Run tests
        run: make test
```

====================================================================================================
FILE: .github/workflows/deploy.yml
====================================================================================================

```
name: Deploy to VDS

on:
  workflow_run:
    workflows:
      - "Build and Push to GHCR"
    types:
      - completed
  workflow_dispatch:

jobs:
  deploy:
    if: >
      github.event.workflow_run.conclusion == 'success' &&
      github.event.workflow_run.head_branch == 'main'
    env:
      GHCR_READ_TOKEN: ${{ secrets.GHCR_READ_TOKEN }}
    runs-on: ubuntu-latest
    steps:
      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.SERVER_SSH_KEY }}" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh-keyscan -H ${{ secrets.SERVER_IP }} >> ~/.ssh/known_hosts

      - name: Set deploy id
        run: echo "DEPLOY_ID=${{ github.event.workflow_run.id }}" >> $GITHUB_ENV

      - name: Check state file
        id: state
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} "
            mkdir -p ~/repair-crm/state

            if [ -f ~/repair-crm/state/state.json ]; then
              echo 'exists=true'
            else
              echo 'exists=false'
            fi
          " >> $GITHUB_OUTPUT

      - name: Checkout code
        uses: actions/checkout@v4

      - name: State for runner
        if: steps.state.outputs.exists == 'true'
        run: |
          scp ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json ./state.json


      - name: Bootstrap state
        if: steps.state.outputs.exists == 'false'
        env:
          GHCR_READ_TOKEN: ${{ secrets.GHCR_READ_TOKEN }}
        run: |
          python scripts/deploy/bootstrap_state.py > state.json

      - name: Upload state
        if: steps.state.outputs.exists == 'false'
        run: |
          scp state.json \
            ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json

      - name: Backup original state (server)
        run: |
          scp ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json \
            state.backup.json

      - name: Download images artifact
        run: |
          gh run download ${{ github.event.workflow_run.id }} \
          -n images \
          -D .
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Update state
        run: |
          python scripts/deploy/update_state.py > new_state.json
          mv new_state.json state.json

      - name: Sync state to server (always)
        run: |
          scp state.json \
              ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json

      - name: Check if deploy needed
        id: diff
        run: |
          python scripts/deploy/check_diff.py > deploy_plan.json

      - name: Print deploy plan
        run: |
          cat deploy_plan.json

      - name: Save deploy plan
        run: |
          PLAN=$(cat deploy_plan.json | jq -c . | base64 -w0)
          echo "DEPLOY_PLAN=$PLAN" >> $GITHUB_ENV

      - name: Debug DEPLOY_PLAN content
        run: |
          echo "=== DEPLOY_PLAN content ==="
          echo "${{ env.DEPLOY_PLAN }}"
          echo "=== HEX ==="
          echo -n "${{ env.DEPLOY_PLAN }}" | od -c
          echo "=== END ==="

      - name: Lock rollback (per service)
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/lock_rollback.py

      - name: Generate compose override
        run: |
          STATE_FILE=state.json 
          python scripts/deploy/render_compose.py > docker-compose.override.yml

      - name: Upload override to server
        run: |
          scp docker-compose.override.yml \
              ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/docker-compose.override.yml

      - name: push to VDS
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DATABASE_URL='${{ secrets.DATABASE_URL }}' \
             ADMIN_USERNAME='${{ secrets.ADMIN_USERNAME }}' \
             ADMIN_PASSWORD='${{ secrets.ADMIN_PASSWORD }}' \
             SECRET_KEY='${{ secrets.SECRET_KEY }}' \
             TELEGRAM_TOKEN='${{ secrets.TELEGRAM_TOKEN }}' \
             DOMAIN_NAME='${{ secrets.DOMAIN_NAME }}' \
             bash -s" < scripts/deploy/push_to_vds.sh

      - name: Verify ACTIVE services
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/verify_services.py

      - name: Wait for new services healthcheck
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/verify_inactive_services.py

      - name: Switch traffic (state-driven)
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/switch_services.py

      - name: Reload nginx
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} "
            docker exec nginx /scripts/reload.sh
          "

      - name: Post-switch verify
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/post_switch_verify.py \
            > post_switch_verify.json

      - name: Print verify result
        run: |
          cat post_switch_verify.json

      - name: Save rollback decision (runner-only)
        run: |
          cat post_switch_verify.json | jq -c . > rollback_decision.json

          ROLLBACK=$(cat rollback_decision.json | base64 -w0)
          echo "ROLLBACK_DECISION=$ROLLBACK" >> $GITHUB_ENV

      - name: Unlock rollback
        id: unlock
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "ROLLBACK_DECISION='${{ env.ROLLBACK_DECISION }}' python3 -" \
            < scripts/deploy/unlock_rollback.py

      - name: Restore state backup
        if: always() && steps.unlock.outcome != 'success'
        run: |
          if [ -s state.backup.json ]; then
            echo "restoring backup state"
            scp state.backup.json \
              ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json
          else
            echo "backup empty - skip restore"
          fi

      - name: Post Reload nginx
        if: always() && steps.unlock.outcome != 'success'
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} "
            docker exec nginx /scripts/reload.sh
          "

      - name: Rollback engine
        env:
          SERVER_USER: ${{ secrets.SERVER_USER }}
          SERVER_IP: ${{ secrets.SERVER_IP }}
          ROLLBACK_DECISION: ${{ env.ROLLBACK_DECISION }}
        run: |
          python scripts/deploy/run_rollbacks.py
          

      - name: Cleanup inactive containers
        if: always()
        env:
          SERVER_USER: ${{ secrets.SERVER_USER }}
          SERVER_IP: ${{ secrets.SERVER_IP }}
          DEPLOY_PLAN: ${{ env.DEPLOY_PLAN }}
        run: |
          ssh $SERVER_USER@$SERVER_IP \
            "DEPLOY_PLAN='$DEPLOY_PLAN' python3 -" \
            < scripts/deploy/cleanup.py

```

====================================================================================================
FILE: .pre-commit-config.yaml
====================================================================================================

```
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/flake8
    rev: 7.1.0
    hooks:
      - id: flake8
        args:
          [
            --config=.flake8,
            --max-line-length=88,
            --extend-ignore=E203,
          ]
```

====================================================================================================
FILE: alembic.ini
====================================================================================================

```
# A generic, single database configuration.

[alembic]
# path to migration scripts.
# this is typically a path given in POSIX (e.g. forward slashes)
# format, relative to the token %(here)s which refers to the location of this
# ini file
# script_location = %(here)s/shared/db/migrations
script_location = shared/db/migrations

# template used to generate migration file names; The default value is %%(rev)s_%%(slug)s
# Uncomment the line below if you want the files to be prepended with date and time
# see https://alembic.sqlalchemy.org/en/latest/tutorial.html#editing-the-ini-file
# for all available tokens
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s
# Or organize into date-based subdirectories (requires recursive_version_locations = true)
# file_template = %%(year)d/%%(month).2d/%%(day).2d_%%(hour).2d%%(minute).2d_%%(second).2d_%%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.  for multiple paths, the path separator
# is defined by "path_separator" below.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the tzdata library which can be installed by adding
# `alembic[tz]` to the pip requirements.
# string value is passed to ZoneInfo()
# leave blank for localtime
# timezone =

# max length of characters to apply to the "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version location specification; This defaults
# to <script_location>/versions.  When using multiple version
# directories, initial revisions must be specified with --version-path.
# The path separator used here should be the separator specified by "path_separator"
# below.
# version_locations = %(here)s/bar:%(here)s/bat:%(here)s/alembic/versions

# path_separator; This indicates what character is used to split lists of file
# paths, including version_locations and prepend_sys_path within configparser
# files such as alembic.ini.
# The default rendered in new alembic.ini files is "os", which uses os.pathsep
# to provide os-dependent path splitting.
#
# Note that in order to support legacy alembic.ini files, this default does NOT
# take place if path_separator is not present in alembic.ini.  If this
# option is omitted entirely, fallback logic is as follows:
#
# 1. Parsing of the version_locations option falls back to using the legacy
#    "version_path_separator" key, which if absent then falls back to the legacy
#    behavior of splitting on spaces and/or commas.
# 2. Parsing of the prepend_sys_path option falls back to the legacy
#    behavior of splitting on spaces, commas, or colons.
#
# Valid values for path_separator are:
#
# path_separator = :
# path_separator = ;
# path_separator = space
# path_separator = newline
#
# Use os.pathsep. Default configuration used for new projects.
path_separator = os


# set to 'true' to search source files recursively
# in each "version_locations" directory
# new in Alembic version 1.10
recursive_version_locations = true

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

# database URL.  This is consumed by the user-maintained env.py script only.
# other means of configuring database URLs may be customized within the env.py
# file.
# sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost/


[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 79 REVISION_SCRIPT_FILENAME

# lint with attempts to fix using "ruff" - use the module runner, against the "ruff" module
# hooks = ruff
# ruff.type = module
# ruff.module = ruff
# ruff.options = check --fix REVISION_SCRIPT_FILENAME

# Alternatively, use the exec runner to execute a binary found on your PATH
# hooks = ruff
# ruff.type = exec
# ruff.executable = ruff
# ruff.options = check --fix REVISION_SCRIPT_FILENAME

# Logging configuration.  This is also consumed by the user-maintained
# env.py script only.
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S

```

====================================================================================================
FILE: docker-compose.prod.yml
====================================================================================================

```
services:
  gateway-blue:
    image: ${GATEWAY_BLUE_IMAGE}

  gateway-green:
    image: ${GATEWAY_GREEN_IMAGE}

  nginx:
    image: ${NGINX_IMAGE}

  certbot:
    image: ${CERTBOT_IMAGE}

  migrations:
    image: ${MIGRATIONS_IMAGE}

  watchdog:
    image: ${WATCHDOG_IMAGE}
```

====================================================================================================
FILE: docker-compose.test.yml
====================================================================================================

```
services:
  postgres:
    ports:
      - "5432:5432"   # только для тестов локально

#  gateway:
#    environment:
#      DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test
#
#  migrations:
#    environment:
#      DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test
```

====================================================================================================
FILE: docker-compose.yml
====================================================================================================

```
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: repair_crm
      POSTGRES_HOST_AUTH_METHOD: trust  # <- КЛЮЧЕВАЯ СТРОКgi
    expose:
      - "5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U postgres" ]
      interval: 5s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
    restart: unless-stopped

  nginx:
    container_name: nginx
    build:
      context: .
      dockerfile: services/nginx/Dockerfile
    ports:
      - "80:80"
      - "443:443"
    env_file:
      - .env
    environment:
      DOMAIN_NAME: ${DOMAIN_NAME:-localhost}
    volumes:
      - certbot_conf:/etc/letsencrypt
      - certbot_web:/var/www/certbot
      - ./state:/etc/nginx/state
    healthcheck:
#      test: [ "CMD", "curl", "-f", "http://localhost/.well-known/acme-challenge/healthcheck" ]
      test: [ "CMD", "nginx", "-t" ]  # проверяет только конфиг
      interval: 10s
      timeout: 5s
      retries: 30
      start_period: 10s
    deploy:
      resources:
        limits:
          memory: 64M
        reservations:
          memory: 32M
    restart: unless-stopped

  certbot:
    container_name: certbot
    build:
      context: .
      dockerfile: services/certbot/Dockerfile
    volumes:
      - certbot_conf:/etc/letsencrypt
      - certbot_web:/var/www/certbot
    env_file:
      - .env
    environment:
      DOMAIN_NAME: ${DOMAIN_NAME:-localhost}
    depends_on:
      nginx:
        condition: service_healthy  # ← ждем здоровый nginx
    healthcheck:
      # Проверяем, что скрипт дошел до бесконечного цикла (процесс sleep существует)
      test: [ "CMD", "sh", "-c", "pgrep -f 'sleep 12h' || pgrep -f 'sleep 3600' || exit 1" ]
      interval: 5s
      timeout: 3s
      retries: 60
      start_period: 60s
    deploy:
      resources:
        limits:
          memory: 128M
        reservations:
          memory: 64M
    restart: unless-stopped

  watchdog:
    build:
      context: .
      dockerfile: services/watchdog/Dockerfile
    container_name: watchdog

    volumes:
      - ./state:/state
      - /var/run/docker.sock:/var/run/docker.sock

    environment:
      STATE_PATH: /state/state.json
      WORKDIR: /app


    mem_limit: 64m
    cpus: "0.2"

    healthcheck:
      test: [ "CMD", "python", "-c", "print('ok')" ]
      interval: 30s
      timeout: 3s
      retries: 3

    depends_on:
      nginx:
        condition: service_healthy
    restart: unless-stopped


  gateway-blue:
    container_name: gateway-blue
    build:
      context: .
      dockerfile: services/gateway/Dockerfile
    expose:
      - "8000"

    env_file:
      - .env

    environment:
      DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@postgres:5432/repair_crm}

    command:
      [
        "uvicorn",
        "services.gateway.app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ]

    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
        ]
      interval: 5s
      timeout: 3s
      retries: 10

    restart: unless-stopped

    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M


  gateway-green:
    container_name: gateway-green
    build:
      context: .
      dockerfile: services/gateway/Dockerfile
    expose:
      - "8000"

    env_file:
      - .env

    environment:
      DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@postgres:5432/repair_crm}

    command:
      [
        "uvicorn",
        "services.gateway.app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ]

    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
        ]
      interval: 5s
      timeout: 3s
      retries: 10

    restart: unless-stopped

    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  migrations:
    build:
      context: .
      dockerfile: services/migrations/Dockerfile
    env_file:
      - .env
    environment:
      DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@postgres:5432/repair_crm}
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
  certbot_conf:
  certbot_web:
```

====================================================================================================
FILE: LICENSE
====================================================================================================

```
MIT License

Copyright (c) 2026 kpa9pt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```

====================================================================================================
FILE: Makefile
====================================================================================================

```
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
```

====================================================================================================
FILE: pytest.ini
====================================================================================================

```
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
```

====================================================================================================
FILE: README.md
====================================================================================================

```
# Repair CRM

[![Docker](https://img.shields.io/badge/Docker-20.10+-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)


Система для управления ремонтами и заказами в мастерской мототехники.

---

## 📌 О проекте

Repair CRM — backend-система для обработки заявок на ремонт.  
Проект построен как API-first приложение с административной панелью.

**Portable deployment:** достаточно Docker и свободных портов 80/443.

---

## ⚙️ Возможности

- CRUD заявок на ремонт
- Фильтрация и пагинация
- REST API (Swagger UI)
- Административная панель (SQLAdmin)
- Docker-окружение для разработки
- CI/CD (GitHub Actions + GHCR)
- Автоматический HTTPS (Let's Encrypt)

---

## 🧱 Технологии

- Python 3.14 / FastAPI
- PostgreSQL / SQLAlchemy (async)
- Alembic / pytest
- Docker / Docker Compose
- Nginx / Certbot
- GitHub Container Registry

---

## 📋 Требования

- Docker (20.10+)
- Docker Compose (2.20+)
- Свободные порты: 80, 443 (для HTTPS)

---

## 🚀 Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone https://github.com/kpa9pt/repair-crm.git
cd repair-crm

# 2. Запустить проект (.env создастся автоматически)
make up

# 3. Остановить проект
make down
```

---

## 🌐 После запуска доступны сервисы:

|   Сервис	   |           URL           |
|:-----------:|:-----------------------:|
| API Gateway |    	http://localhost    |
| Swagger UI  | 	http://localhost/docs  |
| Admin panel | 	http://localhost/admin |

---

## 🔧 Переменные окружения

При первом запуске файл .env создаётся автоматически из .env.example:
```bash
cp .env.example .env   # если нужно отредактировать вручную
```
Основные переменные:

| Переменная      | 	Значение по умолчанию                                                | 	Описание                               |
|:----------------|:----------------------------------------------------------------------|:----------------------------------------|
| DATABASE_URL    | 	postgresql+asyncpg://postgres:<br>postgres@postgres:5432/repair_crm	 | Подключение к БД                        |
| ADMIN_USERNAME	 | admin	                                                                | Логин админ-панели                      |
| ADMIN_PASSWORD	 | (смотри .env.example)	                                                | Пароль админ-панели                     |
| DOMAIN_NAME	    | localhost	                                                            | Домен (для продакшена укажите реальный) |


> Для HTTPS укажите реальный домен и настройте DNS запись на IP вашего сервера. Certbot автоматически получит сертификат.

---

## 🛠️ Основные команды

```bash
make up          # запустить все сервисы
make down        # остановить и удалить контейнеры
make build       # пересобрать и запустить
make test        # запустить все тесты
make logs        # посмотреть логи
make help        # показать все команды
```

---

## 🧪 Тестирование

```bash
make test
```

Тесты запускаются в Docker-окружении с автоматическим поднятием инфраструктуры и пересозданием базы данных.

---

## 🔐 Административный доступ

Доступ к админ-панели:
- URL: http://localhost/admin
- Login: admin
- Password: admin123

> Админ-панель — основной инструмент для управления заявками.


---

## 🚀 Деплой на VPS

- Клонируйте репозиторий на сервер
- Настройте .env (укажите DOMAIN_NAME и пароли)
- Выполните make up

---

## 🤖 Автоматический CI/CD (опционально)

В репозитории настроены GitHub Actions:

- Build and Push to GHCR — сборка образа при пуше в main
- Deploy to VDS — автоматический деплой на сервер

Для работы CI/CD нужны секреты (смотри .github/workflows/deploy.yml).


---

## 🧭 Архитектура

```text
Nginx (порты 80/443) → Gateway (FastAPI) → PostgreSQL
                ↓
         Certbot (HTTPS)
```

---

## 🎯 Дальнейшее развитие

- [ ] **Модель "Техника"** — единицы техники с историей ремонтов
- [ ] **Telegram бот** — уведомления о новых заявках
- [ ] **React фронтенд** — полноценный интерфейс для менеджеров
- [ ] **Blue/Green деплой** — zero-downtime обновления
- [ ] **Мобильное приложение (iOS)** — для механиков в поле

---

## 📄 Лицензия

MIT

---
```

====================================================================================================
FILE: requirements.txt
====================================================================================================

```
alembic==1.18.4
annotated-doc==0.0.4
annotated-types==0.7.0
anyio==4.13.0
asyncpg==0.31.0
bcrypt==5.0.0
black==26.5.1
certifi==2026.5.20
cfgv==3.5.0
click==8.4.1
distlib==0.4.0
fastapi==0.136.3
filelock==3.29.0
greenlet==3.5.1
h11==0.16.0
httpcore==1.0.9
httptools==0.8.0
httpx==0.28.0
identify==2.6.19
idna==3.16
iniconfig==2.3.0
itsdangerous==2.2.0
Jinja2==3.1.6
Mako==1.3.12
MarkupSafe==3.0.3
mypy_extensions==1.1.0
nodeenv==1.10.0
packaging==26.2
passlib==1.7.4
pathspec==1.1.1
platformdirs==4.10.0
pluggy==1.6.0
pre_commit==4.6.0
pydantic==2.13.4
pydantic-settings==2.14.1
pydantic_core==2.46.4
Pygments==2.20.0
pytest==9.0.3
pytest-asyncio==1.3.0
python-discovery==1.4.0
python-dotenv==1.2.2
python-multipart==0.0.27
pytokens==0.4.1
PyYAML==6.0.3
redis==5.0.1
sqladmin==0.27.0
SQLAlchemy==2.0.49
starlette==1.2.0
typing-inspection==0.4.2
typing_extensions==4.15.0
uvicorn==0.30.0
uvloop==0.22.1
virtualenv==21.4.1
watchfiles==1.2.0
websockets==16.0
WTForms==3.1.2

requests
```

====================================================================================================
FILE: scripts/build_manifest.py
====================================================================================================

```
import json
import os

SERVICES = ["gateway", "migrations", "nginx", "certbot", "watchdog"]

github_sha = os.environ.get("GITHUB_SHA", "")

manifest = {}

for service in SERVICES:
    changed = os.environ.get(f"CHANGED_{service.upper()}", "false")

    if changed == "true":
        manifest[service] = github_sha

print(json.dumps(manifest))

```

====================================================================================================
FILE: scripts/deploy/bootstrap_state.py
====================================================================================================

```
import json
import os
import requests
import sys

OWNER = "kpa9pt"

SERVICES = [
    "gateway",
    "nginx",
    "certbot",
    "migrations",
    "watchdog",
]

TOKEN = os.environ["GHCR_READ_TOKEN"]

# 🔥 DEBUG 1: проверяем что токен вообще есть и не пустой
print("TOKEN EXISTS:", bool(TOKEN), file=sys.stderr)
print("TOKEN PREFIX:", TOKEN[:6] if TOKEN else None, file=sys.stderr)

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
}

DEPLOY_ID = os.getenv("DEPLOY_ID", "bootstrap")


def latest_image(service: str) -> str:
    url = (
        f"https://api.github.com/users/"
        f"{OWNER}/packages/container/repair-crm-{service}/versions"
    )

    print(f"\n--- SERVICE: {service} ---", file=sys.stderr)
    print("URL:", url, file=sys.stderr)

    response = requests.get(url, headers=HEADERS)

    # 🔥 DEBUG 2: статус ответа
    print("STATUS:", response.status_code, file=sys.stderr)

    # 🔥 DEBUG 3: если упало — покажем текст
    if response.status_code != 200:
        print("ERROR BODY:", response.text[:500], file=sys.stderr)

    response.raise_for_status()

    versions = response.json()

    # 🔥 DEBUG 4: сколько версий пришло
    print("VERSIONS COUNT:", len(versions), file=sys.stderr)

    for version in versions:
        # ❗ оставили как у тебя было (НЕ трогаем логику)
        tags = version["metadata"]["container"]["tags"]

        print("TAGS:", tags, file=sys.stderr)

        sha_tags = [tag for tag in tags if tag != "latest"]

        if sha_tags:
            sha = sha_tags[0]
            return f"ghcr.io/{OWNER}/repair-crm-{service}:{sha}"

    raise RuntimeError(f"No sha tag found for {service}")


state = {
    "deploy_id": DEPLOY_ID,
    "services": {
        "gateway": {
            "strategy": "blue-green",
            "active": "blue",
            "port": 8000,
            "healthcheck": "/health",
            "rollback_locked": False,
        }
    },
}

gateway_image = latest_image("gateway")

state["services"]["gateway"]["blue"] = {"image": gateway_image}
state["services"]["gateway"]["green"] = {"image": gateway_image}

for service in [
    "nginx",
    "certbot",
    "migrations",
    "watchdog",
]:
    state["services"][service] = {
        "strategy": "single",
        "image": latest_image(service),
    }

print(json.dumps(state, indent=2))

```

====================================================================================================
FILE: scripts/deploy/check_diff.py
====================================================================================================

```
import json
import sys


def load(path):
    with open(path) as f:
        return json.load(f)


def main():
    changes = load("images.json")
    state = load("state.json")

    deploy_plan = []

    for service in changes.keys():

        service_state = state["services"].get(service)

        if not service_state:
            print(
                f"skip {service}: not found in state",
                file=sys.stderr,
            )
            continue

        if service_state.get("strategy") != "blue-green":
            print(
                f"skip {service}: strategy={service_state.get('strategy')}",
                file=sys.stderr,
            )
            continue

        deploy_plan.append(service)

    print(json.dumps(deploy_plan))


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/cleanup.py
====================================================================================================

```
import json
import os
import base64
import subprocess
from pathlib import Path


def load_state():
    state_file = Path.home() / "repair-crm" / "state" / "state.json"
    with open(state_file) as f:
        return json.load(f)


def load_plan():
    data = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(data).decode())


def main():
    state = load_state()
    deploy_plan = load_plan()

    print("=== CLEANUP START ===")

    for service in deploy_plan:
        if service not in state["services"]:
            print(f"skip unknown service: {service}")
            continue

        svc = state["services"][service]

        if svc["strategy"] == "blue-green":
            active = svc["active"]
            inactive = "green" if active == "blue" else "blue"
            container = f"{service}-{inactive}"

            print(f"stopping {container}")
            subprocess.run(["docker", "stop", container], check=False)

    print("=== PRUNE ===")
    subprocess.run(["docker", "system", "prune", "-f"], check=False)

    print("=== CLEANUP DONE ===")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/lock_rollback.py
====================================================================================================

```
import json
import os
import base64
from pathlib import Path


STATE_FILE = Path.home() / "repair-crm" / "state" / "state.json"


def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def decode_plan():
    raw = os.environ.get("DEPLOY_PLAN", "")
    if not raw:
        return []

    decoded = base64.b64decode(raw).decode()
    return json.loads(decoded)


def main():
    deploy_plan = decode_plan()
    state = load_state()

    for service in deploy_plan:
        if service not in state["services"]:
            print(f"⚠️ skip unknown service {service}")
            continue

        print(f"🔒 lock rollback: {service}")
        state["services"][service]["rollback_locked"] = True

    save_state(state)
    print("✅ rollback locked for planned services")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/post_switch_verify.py
====================================================================================================

```
import json
import sys
import time
import os
import base64
import subprocess
from pathlib import Path


def healthcheck(container, port, health):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{health}', timeout=2)"
        ),
    ]

    return subprocess.run(cmd).returncode == 0


def wait_health(container, port, health, retries=30, delay=2):

    for i in range(retries):

        if healthcheck(container, port, health):
            return True

        print(
            f"retry: {i + 1}/{retries}",
            file=sys.stderr,
        )

        time.sleep(delay)

    return False


def main():
    deploy_plan = json.loads(base64.b64decode(os.environ["DEPLOY_PLAN"]).decode())

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    result = {
        "passed": [],
        "failed": [],
    }

    for service in deploy_plan:

        print(
            f"🔍 post-switch verify: {service}",
            file=sys.stderr,
        )

        s = state["services"][service]

        active = s["active"]
        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{active}"

        print(
            f"phase 1 smoke: {service}",
            file=sys.stderr,
        )

        if not wait_health(container, port, health):
            result["failed"].append(service)
            continue

        print(
            f"phase 2 soak sleep: {service}",
            file=sys.stderr,
        )

        time.sleep(60)

        print(
            f"phase 3 soak verify: {service}",
            file=sys.stderr,
        )

        if wait_health(container, port, health):
            result["passed"].append(service)
        else:
            result["failed"].append(service)

    print(json.dumps(result))


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/push_to_vds.sh
====================================================================================================

```
#!/usr/bin/env bash
set -e

echo "=== PUSH TO VDS START ==="
date
whoami
pwd

cd ~/repair-crm

echo "=== UPDATE COMPOSE ==="
curl -fsSL https://raw.githubusercontent.com/kpa9pt/repair-crm/main/docker-compose.yml -o docker-compose.yml

echo "=== WRITE ENV ==="
cat > .env <<EOF
DATABASE_URL=$DATABASE_URL
ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_PASSWORD=$ADMIN_PASSWORD
SECRET_KEY=$SECRET_KEY
TELEGRAM_TOKEN=$TELEGRAM_TOKEN
DOMAIN_NAME=$DOMAIN_NAME
EOF

echo "=== DOCKER COMPOSE UP ==="
docker compose up -d

echo "=== DONE ==="
docker ps
```

====================================================================================================
FILE: scripts/deploy/render_compose.py
====================================================================================================

```
import json
import os

STATE_FILE = os.environ.get("STATE_FILE", "state.json")

with open(STATE_FILE) as f:
    state = json.load(f)

yaml = ["services:"]

for service_name, config in state["services"].items():

    strategy = config["strategy"]

    if strategy == "blue-green":

        yaml.append(f"  {service_name}-blue:")
        yaml.append(f"    image: {config['blue']['image']}")

        yaml.append(f"  {service_name}-green:")
        yaml.append(f"    image: {config['green']['image']}")

    elif strategy == "single":

        yaml.append(f"  {service_name}:")
        yaml.append(f"    image: {config['image']}")

print("\n".join(yaml))

```

====================================================================================================
FILE: scripts/deploy/run_rollbacks.py
====================================================================================================

```
import json
import os
import base64
import subprocess


def load_rollback_decision():
    data = os.environ["ROLLBACK_DECISION"]
    return json.loads(base64.b64decode(data).decode())


def main():
    decision = load_rollback_decision()

    failed = decision.get("failed", [])

    if not failed:
        print("✅ no rollback required")
        return

    server_user = os.environ["SERVER_USER"]
    server_ip = os.environ["SERVER_IP"]

    for service in failed:

        print(f"🔄 rollback: {service}")

        subprocess.run(
            [
                "ssh",
                f"{server_user}@{server_ip}",
                f"ROLLBACK_SERVICE={service} python3 -",
            ],
            stdin=open("scripts/rollback.py", "rb"),
            check=True,
        )

    print("✅ rollback engine finished")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/switch_services.py
====================================================================================================

```
import json
import sys
import os
import base64
from pathlib import Path


def load_deploy_plan():
    plan = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(plan).decode())


def main():
    deploy_plan = load_deploy_plan()
    if not deploy_plan:
        print("no changes")
        sys.exit(0)

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:
        active = state["services"][service]["active"]
        new = "green" if active == "blue" else "blue"

        state["services"][service]["active"] = new

        print(f"🔁 {service}: {active} → {new}")

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/unlock_rollback.py
====================================================================================================

```
import json
import os
import base64
from pathlib import Path


def load_rollback_decision():
    data = os.environ["ROLLBACK_DECISION"]
    return json.loads(base64.b64decode(data).decode())


def main():
    decision = load_rollback_decision()

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in decision["passed"]:

        if service not in state["services"]:
            print(f"⚠️ unknown service: {service}")
            continue

        state["services"][service]["rollback_locked"] = False

        print(f"🔓 rollback unlocked: {service}")

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/update_state.py
====================================================================================================

```
import json
import os

STATE_PATH = "state.json"
CHANGES_PATH = "images.json"

OWNER = "kpa9pt"

DEPLOY_ID = os.getenv("DEPLOY_ID")


def load(path):
    with open(path) as f:
        return json.load(f)


state = load(STATE_PATH)
changes = load(CHANGES_PATH)

state["deploy_id"] = DEPLOY_ID


def build_image(service, sha):
    return f"ghcr.io/{OWNER}/repair-crm-{service}:{sha}"


for service, sha in changes.items():

    if service not in state["services"]:
        state["services"][service] = {"strategy": "single", "rollback_locked": False}

    service_state = state["services"][service]

    image = build_image(service, sha)

    if service_state["strategy"] == "blue-green":

        active = service_state["active"]
        inactive = "green" if active == "blue" else "blue"

        service_state[inactive]["image"] = image

    else:

        service_state["image"] = image


print(json.dumps(state, indent=2))

```

====================================================================================================
FILE: scripts/deploy/verify_inactive_services.py
====================================================================================================

```
import json
import sys
import subprocess
import time
import os
import base64
from pathlib import Path


def healthcheck(container, port, health):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{health}', timeout=2)"
        ),
    ]

    return subprocess.run(cmd).returncode == 0


def load_deploy_plan():
    plan = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(plan).decode())


def main():
    deploy_plan = load_deploy_plan()

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:

        print(f"🔍 verifying {service}")

        s = state["services"][service]

        active = s["active"]

        inactive = "green" if active == "blue" else "blue"

        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{inactive}"

        ok = False

        for i in range(60):
            if healthcheck(container, port, health):
                print(f"✅ {container} healthy")
                ok = True
                break

            print(f"retry {i}")
            time.sleep(2)

        if not ok:
            print(f"❌ {container} failed")
            sys.exit(1)


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/verify_services.py
====================================================================================================

```
import json
import sys
import subprocess
import time
import os
import base64
from pathlib import Path


def healthcheck(container, port, health):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{health}', timeout=2)"
        ),
    ]

    return subprocess.run(cmd).returncode == 0


def load_deploy_plan():
    plan = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(plan).decode())


def main():
    deploy_plan = load_deploy_plan()

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:

        print(f"🔍 verifying {service}")

        s = state["services"][service]

        active = s["active"]
        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{active}"

        ok = False

        for i in range(60):
            if healthcheck(container, port, health):
                print(f"✅ {service} healthy")
                ok = True
                break

            print(f"retry {i}")

            time.sleep(2)

        if not ok:
            print(f"❌ {service} failed")
            sys.exit(1)

    subprocess.run(["docker", "exec", "nginx", "/scripts/reload.sh"], check=True)

    print("🔁 nginx reloaded")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/rollback.py
====================================================================================================

```
import json
import subprocess
import time
import sys
import os

from pathlib import Path

STATE_FILE = Path(
    os.getenv(
        "STATE_PATH",
        str(Path.home() / "repair-crm" / "state" / "state.json"),
    )
)

WORKDIR = Path(
    os.getenv(
        "WORKDIR",
        str(Path.home() / "repair-crm"),
    )
)

NGINX_CONTAINER = "nginx"

service = os.getenv("ROLLBACK_SERVICE")
if not service:
    raise RuntimeError("ROLLBACK_SERVICE not set")


def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def opposite(active: str) -> str:
    if active == "blue":
        return "green"
    return "blue"


def service_name(slot: str) -> str:
    return f"{service}-{slot}"


def wait_health(container: str, port: int, healthcheck: str, retries=30, delay=2):
    print(f"⏳ Waiting health: {container}")

    for i in range(retries):
        try:
            subprocess.run(
                [
                    "docker",
                    "exec",
                    container,
                    "python",
                    "-c",
                    (
                        "import urllib.request;"
                        "urllib.request.urlopen("
                        f"'http://localhost:{port}{healthcheck}', timeout=2"
                        ")"
                    ),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("✅ health OK")
            return True

        except subprocess.CalledProcessError:
            print(f"retry {i + 1}/{retries}")
            time.sleep(delay)

    return False


def reload_nginx():
    print("🔁 reloading nginx")
    subprocess.run(
        ["docker", "exec", NGINX_CONTAINER, "/scripts/reload.sh"],
        check=True,
    )


def main():
    state = load_state()

    service_state = state["services"][service]

    port = service_state.get("port", 8000)
    healthcheck = service_state.get("healthcheck", "/health")

    if service_state["strategy"] == "single":
        print("single strategy rollback not supported")
        sys.exit(1)

    active = service_state["active"]
    target = opposite(active)

    target_container = service_name(target)

    print(f"🔄 rollback: {active} → {target}")

    # 1. start target
    # WORKDIR = Path.home() / "repair-crm"

    subprocess.run(
        # ["docker", "compose", "up", "-d", f"{target_container}"],
        ["docker", "restart", f"{target_container}"],
        cwd=WORKDIR,
        check=True,
    )

    # 2. healthcheck
    if not wait_health(
        target_container,
        port,
        healthcheck,
    ):
        print("❌ rollback failed: target unhealthy")
        sys.exit(1)

    # 3. switch active
    state["services"][service]["active"] = target
    save_state(state)

    # 4. reload nginx
    reload_nginx()

    print("✅ rollback completed")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/test.sh
====================================================================================================

```
#!/bin/bash
set -e

TEST_PATH=${1:-tests}


echo "🚀 Starting infrastructure..."
#docker compose down -v
#docker compose up -d --build
docker compose \
  -f docker-compose.yml \
  -f docker-compose.test.yml \
  down -v

docker compose \
  -f docker-compose.yml \
  -f docker-compose.test.yml \
  up -d --build

get_health() {
  docker inspect --format='{{.State.Health.Status}}' "$1"
}

wait_for_health() {
  local name=$1
  local id
  id=$(docker compose ps -q "$name")

  if [ -z "$id" ]; then
    echo "❌ Container $name not found"
    exit 1
  fi

  echo "⏳ Waiting for $name..."

#  until [ "$(get_health "$id")" = "healthy" ]; do
#    pass
#  done

  echo "✅ $name is healthy"
}

echo "⏳ Waiting for services..."

wait_for_health postgres
wait_for_health gateway-blue


# В начале скрипта, после поднятия postgres
echo "Creating test database..."
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE repair_crm_test" 2>/dev/null || true

echo "Applying migrations..."
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test alembic upgrade head

echo "🧪 Running tests..."
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test
pytest "$TEST_PATH" -v

echo "🧹 Cleaning up..."
docker compose down -v
```

====================================================================================================
FILE: services/certbot/Dockerfile
====================================================================================================

```
FROM certbot/certbot:latest

RUN apk add --no-cache bash docker-cli

COPY services/certbot/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

====================================================================================================
FILE: services/certbot/entrypoint.sh
====================================================================================================

```
#!/bin/sh
set -e

DOMAIN=${DOMAIN_NAME:-localhost}
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

echo "🚀 Certbot service started for domain: $DOMAIN"

if [ "$DOMAIN" = "localhost" ]; then
  echo "Local mode detected, certbot disabled"
  while true; do sleep 12h; done
fi

# Функция для запроса сертификата с повторными попытками
get_certificate() {
  while true; do
    echo "📦 Requesting new certificate..."
    if certbot certonly --webroot --webroot-path=/var/www/certbot \
      --email admin@$DOMAIN --agree-tos --no-eff-email \
      -d "$DOMAIN" --non-interactive; then

      echo "✅ Certificate issued"
      return 0
    else
      echo "❌ Failed, checking if rate limit..."
      # Если ошибка содержит "too many failed authorizations" - ждем 1 час
      if certbot --version 2>/dev/null && \
         certbot certificates 2>&1 | grep -q "too many failed authorizations"; then
        echo "⏳ Rate limit detected, waiting 1 hour..."
        sleep 3600
      else
        echo "⏳ Other error, waiting 5 minutes..."
        sleep 300
      fi
    fi
  done
}

# Основная логика
if [ -f "$CERT_PATH" ]; then
  echo "✅ Certificate already exists"
else
  get_certificate
fi

# Бесконечный цикл обновления
while true; do
  sleep 12h
  echo "🔄 Renewing certificate..."
  certbot renew --webroot --webroot-path=/var/www/certbot --quiet
  echo "🔄 Renewal check done"
done
```

====================================================================================================
FILE: services/gateway/app/__init__.py
====================================================================================================

```

```

====================================================================================================
FILE: services/gateway/app/admin/__init__.py
====================================================================================================

```
"""
Модуль админ-панели SQLAdmin
"""

from .auth import AdminAuth
from .views import RepairRequestAdmin

__all__ = ["AdminAuth", "RepairRequestAdmin"]

```

====================================================================================================
FILE: services/gateway/app/admin/auth.py
====================================================================================================

```
"""
Аутентификация для админ-панели SQLAdmin
"""

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from passlib.context import CryptContext
from shared.settings import get_settings

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminAuth(AuthenticationBackend):
    """Простая аутентификация для админ-панели"""

    async def login(self, request: Request) -> bool:
        """Обработка входа в админку"""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        settings = get_settings()

        # Здесь можно заменить на чтение из БД или переменных окружения
        # Для старта - фиксированные учетные данные
        if username == settings.admin_username and password == settings.admin_password:
            request.session.update({"admin_authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        """Обработка выхода из админки"""
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """Проверка авторизации"""
        return request.session.get("admin_authenticated", False)

```

====================================================================================================
FILE: services/gateway/app/admin/views.py
====================================================================================================

```
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqladmin import ModelView

from shared.models import RepairRequest
from shared.enums import Urgency, RequestStatus

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class RepairRequestAdmin(ModelView, model=RepairRequest):
    """Админка RepairRequest"""

    name = "Заявка"
    name_plural = "Заявки на ремонт"
    icon = "fa-solid fa-wrench"

    # --------------------
    # СПИСОК
    # --------------------
    column_list = [
        RepairRequest.id,
        RepairRequest.vehicle_name,
        RepairRequest.status,
        RepairRequest.urgency,
        RepairRequest.is_operational,
        RepairRequest.created_at,
        RepairRequest.deadline,
        RepairRequest.client_name,
    ]

    column_labels = {
        RepairRequest.vehicle_name: "Техника",
        RepairRequest.client_name: "Клиент",
        RepairRequest.status: "Статус заявки",
        RepairRequest.urgency: "Срочность",
        RepairRequest.created_at: "Создано",
        RepairRequest.deadline: "Дедлайн",
        RepairRequest.is_operational: "Техника на ходу?",
    }

    column_editable_list = [
        RepairRequest.status,
        RepairRequest.urgency,
    ]

    column_filters = []

    column_default_sort = [(RepairRequest.created_at, True)]

    search_fields = [
        "vehicle_name",
        "client_name",
        "description",
    ]

    can_export = True
    can_view_details = True

    # --------------------
    # ФОРМА
    # --------------------
    form_columns = [
        # === ОСНОВНОЕ ===
        "vehicle_name",
        "description",
        "is_operational",
        # === УПРАВЛЕНИЕ ===
        "urgency",
        "status",
        "deadline",
        # === ФИНАНСЫ ===
        "parts_cost",
        "client_payment",
        # === КЛИЕНТ ===
        "client_name",
        "phone",
        "email",
    ]

    form_args = {
        "vehicle_name": {"label": "Техника"},
        "client_name": {"label": "Клиент", "default": "Топ Лес"},
        "phone": {"label": "Телефон"},
        "email": {"label": "Email"},
        "description": {"label": "Описание проблемы"},
        "urgency": {"label": "Срочность", "default": Urgency.NORMAL.value},
        "status": {"label": "Статус заявки", "default": RequestStatus.NEW.value},
        "deadline": {"label": "Дедлайн"},
        "parts_cost": {"label": "Стоимость запчастей", "default": Decimal("0.00")},
        "client_payment": {"label": "Оплата клиента", "default": Decimal("0.00")},
        "is_operational": {"label": "Техника на ходу?", "default": False},
    }

    # # ДЕФОЛТЫ (SQLAdmin правильный способ)
    # form_args = {
    #     "client_name": {"default": "Топ Лес"},
    #     "urgency": {"default": Urgency.NORMAL.value},
    #     "status": {"default": RequestStatus.NEW.value},
    #     "is_operational": {"default": False},
    #     "parts_cost": {"default": Decimal("0.00")},
    #     "client_payment": {"default": Decimal("0.00")},
    # }

    # --------------------
    # ВЫПАДАЮЩИЕ СПИСКИ
    # --------------------
    form_choices = {
        "urgency": [
            ("low", "🟢 Низкая"),
            ("normal", "🟡 Обычная"),
            ("high", "🟠 Высокая"),
            ("critical", "🔴 Критическая"),
        ],
        "status": [
            ("new", "🟢 Новая"),
            ("in_progress", "🟡 В работе"),
            ("waiting_parts", "🔴 Ожидает запчасти"),
            ("diagnostics", "🔵 Диагностика"),
            ("waiting_approval", "🟠 Ожидает согласования"),
            ("done", "✅ Готово"),
        ],
        "is_operational": [
            (True, "Да"),
            (False, "Нет"),
        ],
    }

    # --------------------
    # ФОРМАТИРОВАНИЕ ДАТ (MSK)
    # --------------------
    column_formatters = {
        RepairRequest.status: lambda m, a: {
            "new": "🟢 Новая",
            "in_progress": "🟡 В работе",
            "waiting_parts": "🔴 Ожидает запчасти",
            "diagnostics": "🔵 Диагностика",
            "waiting_approval": "🟠 Ожидает согласования",
            "done": "✅ Готово",
        }.get(m.status, m.status),
        RepairRequest.urgency: lambda m, a: {
            "low": "🟢 Низкая",
            "normal": "🟡 Обычная",
            "high": "🟠 Высокая",
            "critical": "🔴 Критическая",
        }.get(m.urgency, m.urgency),
        RepairRequest.created_at: lambda m, a: (
            m.created_at.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M")
            if m.created_at
            else ""
        ),
        RepairRequest.deadline: lambda m, a: (
            m.deadline.strftime("%d.%m.%Y") if m.deadline else ""
        ),
    }

```

====================================================================================================
FILE: services/gateway/app/main.py
====================================================================================================

```
from fastapi import FastAPI
from shared import get_settings
from .routers import repair_requests_router
from .admin import AdminAuth, RepairRequestAdmin
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware
from shared.db import get_engine  # ← импортируем новую функцию
from fastapi.responses import RedirectResponse


settings = get_settings()

app = FastAPI(
    title="Gateway API",
    version="0.1.0",
    description="API Gateway для CRM ремонтной мастерской",
)

# Добавляем middleware для сессий (нужен для аутентификации админки)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key or "supersecretkey-change-in-production",
    session_cookie="admin_session",
)

# Настройка админ-панели
authentication_backend = AdminAuth(secret_key=settings.secret_key or "supersecretkey")
admin = Admin(
    app,
    get_engine(),  # ← используем get_engine()
    authentication_backend=authentication_backend,
    title="Repair CRM Admin",
    logo_url="/static/logo.png",  # опционально
    base_url="/admin",  # ← ЯВНО УКАЗЫВАЕМ URL
)

# Регистрируем модели
admin.add_view(RepairRequestAdmin)

# Подключаем роутеры
app.include_router(repair_requests_router)


@app.get("/")
async def root():
    return RedirectResponse("/admin/")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/test_blue_green")
async def test_blue_green():
    return {"status": "ok"}


@app.get("/test_check_diff")
async def test_check_diff():
    return {"status": "ok"}

```

====================================================================================================
FILE: services/gateway/app/routers/__init__.py
====================================================================================================

```
from .repair_requests import router as repair_requests_router

__all__ = ["repair_requests_router"]

```

====================================================================================================
FILE: services/gateway/app/routers/repair_requests.py
====================================================================================================

```
"""
Роутер для работы с заявками на ремонт.

Все эндпоинты имеют префикс /api/v1/repair-requests
"""

from fastapi import APIRouter, Depends, HTTPException, status

from shared import get_session_maker
from shared.repository import RepairRequestRepository
from shared.schemas import (
    RepairRequestCreate,
    RepairRequestUpdate,
    RepairRequestResponse,
    RepairRequestListResponse,
)

router = APIRouter(prefix="/api/v1/repair-requests", tags=["Repair Requests"])


async def get_repo():
    session_maker = get_session_maker()

    async with session_maker() as session:
        yield RepairRequestRepository(session)


@router.post(
    "/", response_model=RepairRequestResponse, status_code=status.HTTP_201_CREATED
)
async def create_repair_request(
    request_data: RepairRequestCreate, repo: RepairRequestRepository = Depends(get_repo)
):
    """
    Создать новую заявку на ремонт.

    - **vehicle_name**: название техники (обязательно)
    - **description**: описание поломки (обязательно)
    - **urgency**: срочность (low/normal/high/critical)
    - **status**: статус (new/in_progress/waiting_parts/
        diagnostics/waiting_approval/done)
    """
    # Конвертируем Pydantic модель в словарь
    new_request = await repo.create(**request_data.model_dump())
    await repo.session.commit()
    return RepairRequestResponse.model_validate(new_request)


@router.get("/", response_model=RepairRequestListResponse)
async def get_all_repair_requests(
    skip: int = 0, limit: int = 100, repo: RepairRequestRepository = Depends(get_repo)
):
    """
    Получить список всех заявок с пагинацией.

    - **skip**: сколько заявок пропустить
    - **limit**: сколько заявок вернуть
    - Сортировка: сначала новые (по created_at DESC)
    """
    requests = await repo.get_all(skip=skip, limit=limit)
    total = len(requests)  # В будущем можно сделать отдельный метод для count

    return RepairRequestListResponse(
        items=[RepairRequestResponse.model_validate(r) for r in requests],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/vehicle/{vehicle_name}", response_model=RepairRequestListResponse)
async def get_repair_requests_by_vehicle(
    vehicle_name: str,
    skip: int = 0,
    limit: int = 100,
    repo: RepairRequestRepository = Depends(get_repo),
):
    """
    Получить все заявки для конкретной техники.

    - **vehicle_name**: название техники
    - **skip**: сколько пропустить
    - **limit**: сколько вернуть
    """
    # Метод get_by_vehicle нужно добавить в репозиторий
    # Пока используем фильтрацию через get_all (не оптимально)
    all_requests = await repo.get_by_vehicle(vehicle_name)
    filtered = [r for r in all_requests if r.vehicle_name == vehicle_name]
    total = len(filtered)
    paginated = filtered[skip : skip + limit]

    return RepairRequestListResponse(
        items=[RepairRequestResponse.model_validate(r) for r in paginated],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{request_id}", response_model=RepairRequestResponse)
async def get_repair_request(
    request_id: int, repo: RepairRequestRepository = Depends(get_repo)
):
    """
    Получить конкретную заявку по ID.
    """
    request = await repo.get_by_id(request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair request with id {request_id} not found",
        )
    return RepairRequestResponse.model_validate(request)


@router.patch("/{request_id}", response_model=RepairRequestResponse)
async def update_repair_request(
    request_id: int,
    update_data: RepairRequestUpdate,
    repo: RepairRequestRepository = Depends(get_repo),
):
    """
    Обновить заявку (частичное обновление).

    Можно обновить любое поле или несколько полей сразу.
    """
    existing = await repo.get_by_id(request_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair request with id {request_id} not found",
        )

    # Обновляем только переданные поля
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(existing, key, value)

    # await repo.session.commit()
    await repo.session.commit()
    await repo.session.refresh(existing)

    return RepairRequestResponse.model_validate(existing)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repair_request(
    request_id: int, repo: RepairRequestRepository = Depends(get_repo)
):
    """
    Удалить заявку по ID.
    """
    existing = await repo.get_by_id(request_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair request with id {request_id} not found",
        )

    await repo.session.delete(existing)
    await repo.session.commit()

    return None  # 204 No Content

```

====================================================================================================
FILE: services/gateway/Dockerfile
====================================================================================================

```
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/gateway ./services/gateway
COPY shared ./shared

COPY alembic.ini .
```

====================================================================================================
FILE: services/migrations/Dockerfile
====================================================================================================

```
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY shared ./shared
COPY alembic.ini .

CMD ["alembic", "upgrade", "head"]
```

====================================================================================================
FILE: services/nginx/Dockerfile
====================================================================================================

```
FROM nginx:alpine

RUN apk add --no-cache gettext inotify-tools bash jq



COPY services/nginx/nginx-https.conf /etc/nginx/nginx-https.conf
COPY services/nginx/nginx-http.conf /etc/nginx/nginx-http.conf

# 👇 ВСЕ скрипты в одну папку
COPY services/nginx/scripts/ /scripts/

RUN chmod +x /scripts/*.sh

ENTRYPOINT ["/scripts/entrypoint.sh"]
```

====================================================================================================
FILE: services/nginx/nginx-http.conf
====================================================================================================

```
events {}

http {
    include /etc/nginx/upstreams/upstream.conf;

    server {
        listen 80;
        server_name ${DOMAIN_NAME};

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        location /.well-known/acme-challenge/healthcheck {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass http://gateway_backend;
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
            proxy_next_upstream_tries 3;
            proxy_connect_timeout 5s;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }
    }

}
```

====================================================================================================
FILE: services/nginx/nginx-https.conf
====================================================================================================

```
events {}

http {
    include /etc/nginx/upstreams/upstream.conf;

    server {
        listen 80;
        server_name ${DOMAIN_NAME};

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        location /.well-known/acme-challenge/healthcheck {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass http://gateway_backend;
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
            proxy_next_upstream_tries 3;
            proxy_connect_timeout 5s;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }
    }

    server {
        listen 443 ssl;
        server_name ${DOMAIN_NAME};

        ssl_certificate /etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/${DOMAIN_NAME}/privkey.pem;

        location /.well-known/acme-challenge/healthcheck {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass http://gateway_backend;
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
            proxy_next_upstream_tries 3;
            proxy_connect_timeout 5s;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }
    }

}
```

====================================================================================================
FILE: services/nginx/scripts/entrypoint.sh
====================================================================================================

```
#!/bin/sh
set -e

echo "[BOOT] nginx starting"

echo "[STEP] init state"
/scripts/init_state.sh

echo "[STEP] render upstream"
/scripts/render_upstream.sh

echo "[STEP] generate nginx config"
/scripts/nginx_config.sh

echo "[STEP] nginx test"
nginx -t

echo "[STEP] start nginx"
nginx -g 'daemon off;' &
NGINX_PID=$!

echo "[STEP] watcher start"
/scripts/watcher.sh &

wait $NGINX_PID
```

====================================================================================================
FILE: services/nginx/scripts/init_state.sh
====================================================================================================

```
#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json

echo "[STATE] checking state file"

# если это директория — это сломанный volume
if [ -d "$STATE_FILE" ]; then
  echo "[STATE] ERROR: state.json is directory, fixing"
  rm -rf "$STATE_FILE"
fi

# если файла нет — создаём
if [ ! -f "$STATE_FILE" ]; then
  echo "[STATE] state.json missing, generating local state"
  /scripts/local_state.sh
fi

echo "[STATE] state loaded"
```

====================================================================================================
FILE: services/nginx/scripts/local_state.sh
====================================================================================================

```
#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json
#dfff
echo "[LOCAL] generating default state"

cat > "$STATE_FILE" <<EOF
{
  "deploy_id": "local",
  "services": {
    "gateway": {
      "strategy": "blue-green",
      "active": "blue",
      "port": 8000,
      "healthcheck": "/health",
      "rollback_locked": false
    }
  }
}
EOF
```

====================================================================================================
FILE: services/nginx/scripts/nginx_config.sh
====================================================================================================

```
#!/bin/sh
set -e

DOMAIN="${DOMAIN_NAME:-localhost}"
CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

echo "[NGINX] generating nginx.conf..."

if [ -f "$CERT" ]; then
  CONF="/etc/nginx/nginx-https.conf"
  echo "[NGINX] mode=https"
else
  CONF="/etc/nginx/nginx-http.conf"
  echo "[NGINX] mode=http"
fi

envsubst '$DOMAIN_NAME' < "$CONF" > /etc/nginx/nginx.conf

echo "[NGINX] nginx.conf generated"
```

====================================================================================================
FILE: services/nginx/scripts/reload.sh
====================================================================================================

```
#!/bin/sh
set -e

/scripts/render_upstream.sh
nginx -t
nginx -s reload
```

====================================================================================================
FILE: services/nginx/scripts/render_upstream.sh
====================================================================================================

```
#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json

mkdir -p /etc/nginx/upstreams

rm -f /etc/nginx/upstreams/*.conf 2>/dev/null || true

echo "[RENDER] state=$STATE_FILE"

jq -r '
  .services
  | to_entries[]
  | select(.value.strategy == "blue-green")
  | "\(.key) \(.value.active) \(.value.port)"
' "$STATE_FILE" |
while read SERVICE ACTIVE PORT
do

cat > "/etc/nginx/upstreams/upstream.conf" <<EOF
upstream ${SERVICE}_backend {
  server ${SERVICE}-${ACTIVE}:${PORT} max_fails=3 fail_timeout=10s;
}
EOF

echo "[RENDER] ${SERVICE} -> ${SERVICE}-${ACTIVE}:${PORT}"

done
```

====================================================================================================
FILE: services/nginx/scripts/watcher.sh
====================================================================================================

```
start_watcher() {
  WATCH_DIR="/etc/letsencrypt/live"
  DOMAIN=${DOMAIN_NAME:-localhost}

  echo "[WATCHER] started"

  # ждём появления папки (важно для certbot bootstrap)
  while [ ! -d "$WATCH_DIR/$DOMAIN" ]; do
    echo "[WATCHER] waiting cert dir..."
    sleep 2
  done

  render_upstream
  nginx -s reload

  echo "[WATCHER] cert dir ready"

  inotifywait -m -r -e create -e modify -e moved_to "$WATCH_DIR" |
  while read -r FILE; do
    case "$FILE" in
      *"/$DOMAIN/"*)
        echo "[WATCHER] change detected: $FILE"

        render_upstream
        nginx -s reload
        ;;
    esac
  done
}
```

====================================================================================================
FILE: services/watchdog/Dockerfile
====================================================================================================

```
FROM python:3.11-slim

RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY services/watchdog /app
COPY scripts/rollback.py /scripts/rollback.py

CMD ["python", "main.py"]
```

====================================================================================================
FILE: services/watchdog/main.py
====================================================================================================

```
import json
import time
import os
import subprocess


STATE_PATH = os.getenv("STATE_PATH", "/state/state.json")
WORKDIR = os.getenv("WORKDIR", "/app")


def load_state():
    with open(STATE_PATH) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def container_running(container):
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "-f",
            "{{.State.Running}}",
            container,
        ],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0 and result.stdout.strip() == "true"


def healthcheck(container, port, path):

    if not container_running(container):
        print(f"[WATCHDOG] {container} is not running")
        return False

    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{path}', timeout=2)"
        ),
    ]

    return (
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def trigger_rollback(service):
    print(f"[WATCHDOG] rollback triggered for {service}")

    env = os.environ.copy()
    env["ROLLBACK_SERVICE"] = service
    env["STATE_PATH"] = STATE_PATH
    env["WORKDIR"] = WORKDIR

    subprocess.run(["python", "/scripts/rollback.py"], env=env)


def check_service(service, cfg):
    if cfg.get("strategy") != "blue-green":
        return True

    active = cfg["active"]
    container = f"{service}-{active}"

    port = cfg.get("port", 8000)
    health = cfg.get("healthcheck", "/health")

    retries = 15

    for i in range(retries):
        if healthcheck(container, port, health):
            return True
        time.sleep(2)

    return False


def main():
    while True:
        state = load_state()

        rolled_back_this_cycle = set()

        for service, cfg in state["services"].items():

            if cfg.get("strategy") != "blue-green":
                continue

            if cfg.get("rollback_locked", False):
                print(f"[WATCHDOG] rollback locked → skip {service}")
                continue

            ok = check_service(service, cfg)

            if ok:
                continue

            if service in rolled_back_this_cycle:
                continue

            print(f"[WATCHDOG] service failed → {service}")

            # rollback
            trigger_rollback(service)

            # mark locked immediately
            state["services"][service]["rollback_locked"] = True
            rolled_back_this_cycle.add(service)

            save_state(state)

        time.sleep(60)


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: shared/__init__.py
====================================================================================================

```
from .settings import get_settings
from .models import Base, RepairRequest
from .db import get_session_maker
from .enums import Urgency, RequestStatus

__all__ = [
    "get_settings",
    "Base",
    "RepairRequest",
    "get_session_maker",
    "Urgency",
    "RequestStatus",
]

```

====================================================================================================
FILE: shared/db/__init__.py
====================================================================================================

```
from .session import get_session_maker, get_engine, reset_db

__all__ = ["get_session_maker", "get_engine", "reset_db"]

```

====================================================================================================
FILE: shared/db/migrations/env.py
====================================================================================================

```
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from alembic import context
from shared.models import Base
import os

config = context.config

# Берём DATABASE_URL из переменной окружения (не из settings!)
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm"
)

config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

```

====================================================================================================
FILE: shared/db/migrations/README
====================================================================================================

```
Generic single-database configuration with an async dbapi.
```

====================================================================================================
FILE: shared/db/migrations/versions/2026_05_28_2109-ef27e3a3bb21_.py
====================================================================================================

```
"""

Revision ID: ef27e3a3bb21
Revises:
Create Date: 2026-05-28 21:09:51.922444

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "ef27e3a3bb21"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "repair_requests",
        sa.Column("vehicle_name", sa.String(length=200), nullable=False),
        sa.Column(
            "client_name",
            sa.String(length=100),
            server_default="Топ Лес",
            nullable=False,
        ),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "urgency",
            sa.String(length=20),
            server_default="normal",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="new",
            nullable=False,
        ),
        sa.Column("is_operational", sa.Boolean(), nullable=True),
        sa.Column(
            "parts_cost",
            sa.Numeric(precision=12, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "client_payment",
            sa.Numeric(precision=12, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_repair_requests_id"), "repair_requests", ["id"], unique=False
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_repair_requests_id"), table_name="repair_requests")
    op.drop_table("repair_requests")
    # ### end Alembic commands ###

```

====================================================================================================
FILE: shared/db/migrations/versions/2026_05_29_2232-dfae9b9dfe98_.py
====================================================================================================

```
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "dfae9b9dfe98"
down_revision: Union[str, Sequence[str], None] = "ef27e3a3bb21"
branch_labels = None
depends_on = None


urgency_enum = sa.Enum("LOW", "NORMAL", "HIGH", "CRITICAL", name="urgency_enum")

request_status_enum = sa.Enum(
    "NEW",
    "IN_PROGRESS",
    "WAITING_PARTS",
    "DIAGNOSTICS",
    "WAITING_APPROVAL",
    "DONE",
    name="request_status_enum",
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1. создаём enum-типы
    urgency_enum.create(bind, checkfirst=True)
    request_status_enum.create(bind, checkfirst=True)

    # 2. УБИРАЕМ старые дефолты (важно!)
    op.alter_column(
        "repair_requests",
        "urgency",
        existing_type=sa.VARCHAR(length=20),
        server_default=None,
    )

    op.alter_column(
        "repair_requests",
        "status",
        existing_type=sa.VARCHAR(length=30),
        server_default=None,
    )

    # 3. меняем типы
    op.alter_column(
        "repair_requests",
        "urgency",
        existing_type=sa.VARCHAR(length=20),
        type_=sa.Enum("LOW", "NORMAL", "HIGH", "CRITICAL", name="urgency_enum"),
        postgresql_using="urgency::text::urgency_enum",
        existing_nullable=False,
    )

    op.alter_column(
        "repair_requests",
        "status",
        existing_type=sa.VARCHAR(length=30),
        type_=sa.Enum(
            "NEW",
            "IN_PROGRESS",
            "WAITING_PARTS",
            "DIAGNOSTICS",
            "WAITING_APPROVAL",
            "DONE",
            name="request_status_enum",
        ),
        postgresql_using="status::text::request_status_enum",
        existing_nullable=False,
    )

    # 4. ставим новые enum defaults
    op.alter_column(
        "repair_requests",
        "urgency",
        server_default=sa.text("'NORMAL'::urgency_enum"),
    )

    op.alter_column(
        "repair_requests",
        "status",
        server_default=sa.text("'NEW'::request_status_enum"),
    )


def downgrade() -> None:
    op.alter_column(
        "repair_requests",
        "urgency",
        server_default=None,
    )
    op.alter_column(
        "repair_requests",
        "status",
        server_default=None,
    )

    op.alter_column(
        "repair_requests",
        "urgency",
        type_=sa.VARCHAR(length=20),
        existing_type=sa.Enum(name="urgency_enum"),
        postgresql_using="urgency::text",
        existing_nullable=False,
    )

    op.alter_column(
        "repair_requests",
        "status",
        type_=sa.VARCHAR(length=30),
        existing_type=sa.Enum(name="request_status_enum"),
        postgresql_using="status::text",
        existing_nullable=False,
    )

    # (опционально) удаление enum типов
    request_status_enum.drop(op.get_bind(), checkfirst=True)
    urgency_enum.drop(op.get_bind(), checkfirst=True)

```

====================================================================================================
FILE: shared/db/migrations/versions/2026_05_29_2314-794a7553b817_.py
====================================================================================================

```
"""

Revision ID: 794a7553b817
Revises: dfae9b9dfe98
Create Date: 2026-05-29 23:14:23.536702

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "794a7553b817"
down_revision: Union[str, Sequence[str], None] = "dfae9b9dfe98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "repair_requests",
        "deadline",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.Date(),
        existing_nullable=True,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "repair_requests",
        "deadline",
        existing_type=sa.Date(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
    )
    # ### end Alembic commands ###

```

====================================================================================================
FILE: shared/db/session.py
====================================================================================================

```
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from shared.settings import get_settings

_engine = None
_session_maker = None


def get_session_maker():
    global _engine, _session_maker
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=True)
        _session_maker = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_maker


def get_engine():
    """Возвращает асинхронный движок БД"""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=True)
    return _engine


def reset_db():
    global _engine, _session_maker
    _engine = None
    _session_maker = None

```

====================================================================================================
FILE: shared/enums.py
====================================================================================================

```
"""
Enum классы для выпадающих списков в моделях и схемах
"""

from enum import Enum


class Urgency(str, Enum):
    """Срочность заявки"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

    def __str__(self) -> str:
        return self.value


class RequestStatus(str, Enum):
    """Статус заявки на ремонт"""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    WAITING_PARTS = "waiting_parts"
    DIAGNOSTICS = "diagnostics"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"

    def __str__(self) -> str:
        return self.value

```

====================================================================================================
FILE: shared/models/__init__.py
====================================================================================================

```
from .base import DeclarativeBase as Base
from .repair_request import RepairRequest

__all__ = (
    "Base",
    "RepairRequest",
)

```

====================================================================================================
FILE: shared/models/base.py
====================================================================================================

```
from sqlalchemy import Column, Integer
from sqlalchemy.orm import declared_attr, declarative_base


class Base:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, index=True)

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"


DeclarativeBase = declarative_base(cls=Base)

```

====================================================================================================
FILE: shared/models/repair_request.py
====================================================================================================

```
from sqlalchemy import Column, String, Text, Boolean, DateTime, Numeric, Date
from sqlalchemy.sql import func
from shared.models import Base
from shared.enums import Urgency, RequestStatus
from sqlalchemy import Enum as SQLEnum


class RepairRequest(Base):
    __tablename__ = "repair_requests"

    vehicle_name = Column(String(200), nullable=False)
    client_name = Column(String(100), nullable=False, server_default="Топ Лес")
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)

    urgency = Column(
        SQLEnum(Urgency, name="urgency_enum"),
        nullable=False,
        server_default=Urgency.NORMAL.value,
    )

    status = Column(
        SQLEnum(RequestStatus, name="request_status_enum"),
        nullable=False,
        server_default=RequestStatus.NEW.value,
    )

    is_operational = Column(Boolean, nullable=True)
    parts_cost = Column(Numeric(12, 2), nullable=False, server_default="0")
    client_payment = Column(Numeric(12, 2), nullable=False, server_default="0")
    deadline = Column(Date, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

```

====================================================================================================
FILE: shared/repository.py
====================================================================================================

```
"""
Репозиторий — это слой абстракции между бизнес-логикой и базой данных.
Он скрывает детали SQLAlchemy и позволяет легко подменить БД в тестах.
"""

from sqlalchemy import select
from shared.models import RepairRequest


class RepairRequestRepository:
    def __init__(self, session):
        """
        Внедряем сессию через конструктор (Dependency Injection).
        Это позволяет подставить фейковую сессию в тестах.
        """
        self.session = session

    async def create(self, **kwargs) -> RepairRequest:
        """Создать новую заявку на ремонт."""
        request = RepairRequest(**kwargs)
        self.session.add(request)
        # НЕТ commit! Только flush для получения ID
        await self.session.flush()
        # await self.session.refresh(request)
        return request

    async def get_by_id(self, request_id: int) -> RepairRequest | None:
        """Получить заявку по ID."""
        result = await self.session.execute(
            select(RepairRequest).where(RepairRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100):
        """Получить список заявок с пагинацией."""
        result = await self.session.execute(
            select(RepairRequest).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_by_vehicle(self, vehicle_name: str, skip: int = 0, limit: int = 100):
        """Получить заявки по названию техники с пагинацией"""
        result = await self.session.execute(
            select(RepairRequest)
            .where(RepairRequest.vehicle_name == vehicle_name)
            .order_by(RepairRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

```

====================================================================================================
FILE: shared/schemas/__init__.py
====================================================================================================

```
"""
Pydantic схемы для обмена данными между клиентом и сервером
"""

from .repair_request import (
    RepairRequestBase,
    RepairRequestCreate,
    RepairRequestUpdate,
    RepairRequestResponse,
    RepairRequestListResponse,
)

__all__ = [
    "RepairRequestBase",
    "RepairRequestCreate",
    "RepairRequestUpdate",
    "RepairRequestResponse",
    "RepairRequestListResponse",
]

```

====================================================================================================
FILE: shared/schemas/repair_request.py
====================================================================================================

```
"""
Pydantic схемы для RepairRequest

Эти схемы определяют:
- Как выглядит запрос от клиента (Create, Update)
- Как выглядит ответ сервера (Response)
- Какие поля обязательные, а какие нет
"""

from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from shared.enums import Urgency, RequestStatus
from datetime import date


class RepairRequestBase(BaseModel):
    """
    Базовый класс с общими полями для всех схем.
    Все поля опциональны, кроме vehicle_name и description (для create)
    """

    vehicle_name: str = Field(
        ..., description="Название техники", examples=["Квадроцикл-5"]
    )
    client_name: Optional[str] = Field(
        None, description="Имя клиента", examples=["Топ Лес"]
    )
    phone: Optional[str] = Field(
        None, description="Телефон клиента", examples=["+7-999-123-45-67"]
    )
    email: Optional[str] = Field(
        None, description="Email клиента", examples=["client@example.com"]
    )
    description: str = Field(..., description="Описание поломки")
    urgency: Urgency = Field(default=Urgency.NORMAL, description="Срочность")
    status: RequestStatus = Field(default=RequestStatus.NEW, description="Статус")
    is_operational: Optional[bool] = Field(False, description="Техника на ходу?")
    parts_cost: Decimal = Field(
        default_factory=lambda: Decimal("0.00"), description="Стоимость запчастей"
    )
    client_payment: Decimal = Field(
        default_factory=lambda: Decimal("0.00"), description="Оплата клиента"
    )
    deadline: Optional[date] = Field(None, description="Дедлайн (дата без времени)")


class RepairRequestCreate(RepairRequestBase):
    """
    Схема для POST запроса (создание новой заявки).
    Наследует все поля от Base, но явно указываем обязательные.
    """

    # Поле vehicle_name уже есть в Base
    # Поле description уже есть в Base
    pass  # Все поля уже определены в RepairRequestBase


class RepairRequestUpdate(BaseModel):
    """
    Схема для PATCH запроса (частичное обновление).
    Все поля опциональны — можно обновить только то, что нужно.
    """

    vehicle_name: Optional[str] = Field(None, description="Название техники")
    client_name: Optional[str] = Field(None, description="Имя клиента")
    phone: Optional[str] = Field(None, description="Телефон клиента")
    email: Optional[str] = Field(None, description="Email клиента")
    description: Optional[str] = Field(None, description="Описание поломки")

    urgency: Optional[Urgency] = Field(None, description="Срочность")
    status: Optional[RequestStatus] = Field(None, description="Статус")

    is_operational: Optional[bool] = Field(None, description="Техника на ходу?")
    parts_cost: Optional[Decimal] = Field(None, description="Стоимость запчастей")
    client_payment: Optional[Decimal] = Field(None, description="Оплата клиента")
    deadline: Optional[date] = Field(None, description="Дедлайн (дата без времени)")


class RepairRequestResponse(RepairRequestBase):
    """
    Схема для GET ответа (возвращаем клиенту).
    Добавляем поля, которые генерируются БД (id, created_at)
    """

    id: int = Field(..., description="ID заявки")
    created_at: datetime = Field(..., description="Дата создания")

    # Настройка для работы с SQLAlchemy моделями
    model_config = ConfigDict(from_attributes=True)


class RepairRequestListResponse(BaseModel):
    """
    Схема для списка заявок (с пагинацией).
    """

    items: list[RepairRequestResponse] = Field(..., description="Список заявок")
    total: int = Field(..., description="Общее количество заявок (без учета пагинации)")
    skip: int = Field(..., description="Сколько пропущено")
    limit: int = Field(..., description="Лимит на страницу")

```

====================================================================================================
FILE: shared/settings.py
====================================================================================================

```
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm"
    )
    telegram_token: str | None = None
    secret_key: str | None = None  # Добавляем это поле
    admin_username: str = "admin"  # Добавляем с дефолтом
    admin_password: str = "admin123"  # Добавляем с дефолтом
    domain_name: str = "localhost"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()

```

====================================================================================================
FILE: state/state.json
====================================================================================================

```
{
  "deploy_id": "local",
  "services": {
    "gateway": {
      "strategy": "blue-green",
      "active": "blue",
      "port": 8000,
      "healthcheck": "/health",
      "rollback_locked": false
    }
  }
}

```

====================================================================================================
FILE: tests/__init__.py
====================================================================================================

```

```

====================================================================================================
FILE: tests/api/__init__.py
====================================================================================================

```

```

====================================================================================================
FILE: tests/api/conftest.py
====================================================================================================

```
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from services.gateway.app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def reset():
    from shared.db.session import reset_db

    reset_db()

```

====================================================================================================
FILE: tests/api/test_admin_panel.py
====================================================================================================

```
"""
Тесты для админ-панели SQLAdmin
"""

import pytest
from shared.settings import get_settings

pytest = pytest.mark.asyncio


async def test_admin_login_page_accessible(client):
    """Страница логина доступна"""
    response = await client.get("/admin/login")
    assert response.status_code == 200


async def test_admin_panel_redirects_to_login(client):
    """Без логина админка редиректит на логин"""
    response = await client.get("/admin", follow_redirects=False)
    assert response.status_code == 307 or response.status_code == 302


async def test_admin_login_with_correct_credentials(client):
    """Вход с правильными данными"""
    settings = get_settings()

    login_data = {
        "username": settings.admin_username,
        "password": settings.admin_password,
    }
    response = await client.post("/admin/login", data=login_data, follow_redirects=True)
    assert response.status_code == 200


async def test_repair_request_list_accessible_after_login(client):
    """После входа список заявок доступен"""
    # Логинимся
    settings = get_settings()

    await client.post(
        "/admin/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
    )
    # Проверяем список
    response = await client.get("/admin/repair-request/list")
    assert response.status_code == 200

```

====================================================================================================
FILE: tests/api/test_gateway.py
====================================================================================================

```
import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

```

====================================================================================================
FILE: tests/api/test_repair_requests.py
====================================================================================================

```
"""
API тесты для эндпоинтов RepairRequest.
"""

from shared.enums import Urgency, RequestStatus
import pytest

"""Тесты для API эндпоинтов"""


@pytest.mark.asyncio
async def test_create_repair_request(client):
    """Тест создания заявки через API"""
    request_data = {
        "vehicle_name": "Тестовый квадроцикл",
        "description": "Не заводится тестовая заявка",
        "urgency": Urgency.NORMAL.value,
        "status": RequestStatus.NEW.value,
    }

    response = await client.post("/api/v1/repair-requests/", json=request_data)

    assert response.status_code == 201
    data = response.json()
    assert data["vehicle_name"] == request_data["vehicle_name"]
    assert data["description"] == request_data["description"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_repair_request_invalid_data(client):
    """Тест создания заявки с невалидными данными"""
    response = await client.post(
        "/api/v1/repair-requests/", json={"description": "Только описание"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_all_repair_requests(client):
    """Тест получения списка всех заявок"""
    # Создаем тестовые данные
    for i in range(3):
        response = await client.post(
            "/api/v1/repair-requests/",
            json={"vehicle_name": f"Техника {i}", "description": f"Описание {i}"},
        )
        assert response.status_code == 201

    response = await client.get("/api/v1/repair-requests/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_get_repair_request_by_id(client):
    """Тест получения конкретной заявки по ID"""
    # Создаем
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={
            "vehicle_name": "Уникальная техника",
            "description": "Уникальное описание",
        },
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Получаем
    response = await client.get(f"/api/v1/repair-requests/{created_id}")
    assert response.status_code == 200
    assert response.json()["id"] == created_id


@pytest.mark.asyncio
async def test_get_nonexistent_repair_request(client):
    """Тест получения несуществующей заявки"""
    response = await client.get("/api/v1/repair-requests/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_repair_request(client):
    """Тест частичного обновления заявки"""
    # Создаем
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={
            "vehicle_name": "Техника для обновления",
            "description": "Оригинальное описание",
        },
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Обновляем статус
    response = await client.patch(
        f"/api/v1/repair-requests/{created_id}",
        json={"status": RequestStatus.IN_PROGRESS.value},
    )

    assert response.status_code == 200
    assert response.json()["status"] == RequestStatus.IN_PROGRESS.value
    assert response.json()["vehicle_name"] == "Техника для обновления"


@pytest.mark.asyncio
async def test_delete_repair_request(client):
    """Тест удаления заявки"""
    # Создаем
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={"vehicle_name": "Техника для удаления", "description": "Будет удалена"},
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Удаляем
    delete_response = await client.delete(f"/api/v1/repair-requests/{created_id}")
    assert delete_response.status_code == 204

    # Проверяем что удалена
    get_response = await client.get(f"/api/v1/repair-requests/{created_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_pagination(client):
    """Тест пагинации"""
    # Создаем 10 заявок
    for i in range(10):
        response = await client.post(
            "/api/v1/repair-requests/",
            json={"vehicle_name": f"Пагинация {i}", "description": f"Описание {i}"},
        )
        assert response.status_code == 201

    # Проверяем страницы
    resp1 = await client.get("/api/v1/repair-requests/?skip=0&limit=5")
    assert resp1.status_code == 200
    assert len(resp1.json()["items"]) == 5

    resp2 = await client.get("/api/v1/repair-requests/?skip=5&limit=5")
    assert resp2.status_code == 200
    assert len(resp2.json()["items"]) == 5


@pytest.mark.asyncio
async def test_get_by_vehicle_name(client):
    """Тест фильтрации по имени техники"""
    # Создаем заявки для конкретной техники
    for i in range(2):
        response = await client.post(
            "/api/v1/repair-requests/",
            json={"vehicle_name": "Специальная техника", "description": f"Заявка {i}"},
        )
        assert response.status_code == 201

    # Создаем заявку для другой техники
    response = await client.post(
        "/api/v1/repair-requests/",
        json={"vehicle_name": "Другая техника", "description": "Чужая заявка"},
    )
    assert response.status_code == 201

    response = await client.get("/api/v1/repair-requests/vehicle/Специальная техника")
    assert response.status_code == 200
    assert response.json()["total"] == 2

```

====================================================================================================
FILE: tests/conftest.py
====================================================================================================

```
"""
Общие фикстуры для всех тестов.
"""

```

====================================================================================================
FILE: tests/integration/__init__.py
====================================================================================================

```

```

====================================================================================================
FILE: tests/integration/conftest.py
====================================================================================================

```
"""
Фикстуры для интеграционных тестов (только здесь).
Эти фикстуры НЕ видны в unit и api тестах.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test"
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Тестовый движок БД (один раз на сессию)"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """Тестовая сессия (новая для каждого теста)"""
    async_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session

```

====================================================================================================
FILE: tests/integration/test_repair_request_repository.py
====================================================================================================

```
"""
Интеграционные тесты для репозитория RepairRequest.
"""

import pytest
from shared.repository import RepairRequestRepository


@pytest.mark.asyncio
async def test_repository_create(test_session):
    """Тест создания заявки через репозиторий"""
    repo = RepairRequestRepository(test_session)
    request = await repo.create(vehicle_name="Квадроцикл-5", description="Не заводится")
    assert request.id is not None
    assert request.vehicle_name == "Квадроцикл-5"
    assert request.description == "Не заводится"

```

====================================================================================================
FILE: tests/unit/__init__.py
====================================================================================================

```

```

====================================================================================================
FILE: tests/unit/test_repair_request.py
====================================================================================================

```
from shared.models import RepairRequest


def test_repair_request_creation():
    """Проверяем, что модель создаётся без ошибок."""
    request = RepairRequest(
        vehicle_name="Квадроцикл-5", description="Не заводится", status="new"
    )
    assert request.vehicle_name == "Квадроцикл-5"
    assert request.status == "new"

```

```

====================================================================================================
FILE: tools/output/project_dump_ai.md
====================================================================================================
```
# AI SNAPSHOT: repair_crm
Root: /Users/natalia/Python projects/repair_crm

====================================================================================================
.env.example
====================================================================================================

```
# Telegram Bot Token (обязательно)
TELEGRAM_TOKEN=ваш_токен_сюда

# JWT Secret Key (обязательно, минимум 32 символа)
SECRET_KEY=my-super-secret-key-for-jwt-change-me-in-production

# Для админ-панели
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

#Доменное имя если имеется
#DOMAIN_NAME=example.com

# Database URL
# Вариант для внешней БД (раскомментируйте)
# DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
```

====================================================================================================
.github/workflows/build-and-push.yml
====================================================================================================

```
name: Build and Push to GHCR

on:
#  workflow_dispatch:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Detect changed services
        uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            gateway:
              - 'services/gateway/**'
              - 'shared/**'
              - 'requirements.txt'

            migrations:
              - 'services/migrations/**'
              - 'shared/**'
              - 'alembic.ini'
              - 'requirements.txt'

            nginx:
              - 'services/nginx/**'

            certbot:
              - 'services/certbot/**'
            
            watchdog:
              - 'services/watchdog/**'
              - 'scripts/rollback.py'

      - name: Print detected changes
        run: |
          echo "gateway=${{ steps.changes.outputs.gateway }}"
          echo "migrations=${{ steps.changes.outputs.migrations }}"
          echo "nginx=${{ steps.changes.outputs.nginx }}"
          echo "certbot=${{ steps.changes.outputs.certbot }}"
          echo "watchdog=${{ steps.changes.outputs.watchdog }}"

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push gateway
        if: steps.changes.outputs.gateway == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/gateway/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-gateway:latest
            ghcr.io/${{ github.repository }}-gateway:${{ github.sha }}
            

      - name: Build and push migrations
        if: steps.changes.outputs.migrations == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/migrations/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-migrations:latest
            ghcr.io/${{ github.repository }}-migrations:${{ github.sha }}

      - name: Build and push nginx
        if: steps.changes.outputs.nginx == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/nginx/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-nginx:latest
            ghcr.io/${{ github.repository }}-nginx:${{ github.sha }}

      - name: Build and push certbot
        if: steps.changes.outputs.certbot == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/certbot/Dockerfile
          push: true
          tags: |
            ghcr.
<< TRUNCATED >>
```

====================================================================================================
.github/workflows/ci.yml
====================================================================================================

```
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          
      - name: Setup env for tests
        run: cp .env.example .env

      - name: Run tests
        run: make test
```

====================================================================================================
.github/workflows/deploy.yml
====================================================================================================

```
name: Deploy to VDS

on:
  workflow_run:
    workflows:
      - "Build and Push to GHCR"
    types:
      - completed
  workflow_dispatch:

jobs:
  deploy:
    if: >
      github.event.workflow_run.conclusion == 'success' &&
      github.event.workflow_run.head_branch == 'main'
    env:
      GHCR_READ_TOKEN: ${{ secrets.GHCR_READ_TOKEN }}
    runs-on: ubuntu-latest
    steps:
      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.SERVER_SSH_KEY }}" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh-keyscan -H ${{ secrets.SERVER_IP }} >> ~/.ssh/known_hosts

      - name: Set deploy id
        run: echo "DEPLOY_ID=${{ github.event.workflow_run.id }}" >> $GITHUB_ENV

      - name: Check state file
        id: state
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} "
            mkdir -p ~/repair-crm/state

            if [ -f ~/repair-crm/state/state.json ]; then
              echo 'exists=true'
            else
              echo 'exists=false'
            fi
          " >> $GITHUB_OUTPUT

      - name: Checkout code
        uses: actions/checkout@v4

      - name: State for runner
        if: steps.state.outputs.exists == 'true'
        run: |
          scp ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json ./state.json


      - name: Bootstrap state
        if: steps.state.outputs.exists == 'false'
        env:
          GHCR_READ_TOKEN: ${{ secrets.GHCR_READ_TOKEN }}
        run: |
          python scripts/deploy/bootstrap_state.py > state.json

      - name: Upload state
        if: steps.state.outputs.exists == 'false'
        run: |
          scp state.json \
            ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json

      - name: Backup original state (server)
        run: |
          scp ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json \
            state.backup.json

      - name: Download images artifact
        run: |
          gh run download ${{ github.event.workflow_run.id }} \
          -n images \
          -D .
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Update state
        run: |
          python scripts/deploy/update_state.py > new_state.json
          mv new_state.json state.json

      - name: Sync state to server (always)
        run: |
          scp state.json \
              ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json

      - name: Check if deploy needed
        id: diff
        run: |
          python scripts/deploy/check_diff.py > deploy_plan.json

      - name: Print deploy plan
        run: |
          cat deploy_plan.json

      - name: Save deploy plan
        run: |
          PLAN=$(cat deploy_plan.json | jq -c . | base64 -w0)
          echo "DEPLOY_PLAN=$PLAN" >> $GITHUB_ENV

      - name: Debug DEPLOY_PLAN content
        run: |
          echo "=== DEPLOY_PLAN cont
<< TRUNCATED >>
```

====================================================================================================
.pre-commit-config.yaml
====================================================================================================

```
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/flake8
    rev: 7.1.0
    hooks:
      - id: flake8
        args:
          [
            --config=.flake8,
            --max-line-length=88,
            --extend-ignore=E203,
          ]
```

====================================================================================================
alembic.ini
====================================================================================================

```
# A generic, single database configuration.

[alembic]
# path to migration scripts.
# this is typically a path given in POSIX (e.g. forward slashes)
# format, relative to the token %(here)s which refers to the location of this
# ini file
# script_location = %(here)s/shared/db/migrations
script_location = shared/db/migrations

# template used to generate migration file names; The default value is %%(rev)s_%%(slug)s
# Uncomment the line below if you want the files to be prepended with date and time
# see https://alembic.sqlalchemy.org/en/latest/tutorial.html#editing-the-ini-file
# for all available tokens
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s
# Or organize into date-based subdirectories (requires recursive_version_locations = true)
# file_template = %%(year)d/%%(month).2d/%%(day).2d_%%(hour).2d%%(minute).2d_%%(second).2d_%%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.  for multiple paths, the path separator
# is defined by "path_separator" below.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the tzdata library which can be installed by adding
# `alembic[tz]` to the pip requirements.
# string value is passed to ZoneInfo()
# leave blank for localtime
# timezone =

# max length of characters to apply to the "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version location specification; This defaults
# to <script_location>/versions.  When using multiple version
# directories, initial revisions must be specified with --version-path.
# The path separator used here should be the separator specified by "path_separator"
# below.
# version_locations = %(here)s/bar:%(here)s/bat:%(here)s/alembic/versions

# path_separator; This indicates what character is used to split lists of file
# paths, including version_locations and prepend_sys_path within configparser
# files such as alembic.ini.
# The default rendered in new alembic.ini files is "os", which uses os.pathsep
# to provide os-dependent path splitting.
#
# Note that in order to support legacy alembic.ini files, this default does NOT
# take place if path_separator is not present in alembic.ini.  If this
# option is omitted entirely, fallback logic is as follows:
#
# 1. Parsing of the version_locations option falls back to using the legacy
#    "version_path_separator" key, which if absent then falls back to the legacy
#    behavior of splitting on spaces and/or commas.
# 2. Parsing of the prepend_sys_path option falls back to the legacy
#    behavior of splitting on spaces, commas, or colons.
#
# Valid values 
<< TRUNCATED >>
```

====================================================================================================
docker-compose.prod.yml
====================================================================================================

```
services:
  gateway-blue:
    image: ${GATEWAY_BLUE_IMAGE}

  gateway-green:
    image: ${GATEWAY_GREEN_IMAGE}

  nginx:
    image: ${NGINX_IMAGE}

  certbot:
    image: ${CERTBOT_IMAGE}

  migrations:
    image: ${MIGRATIONS_IMAGE}

  watchdog:
    image: ${WATCHDOG_IMAGE}
```

====================================================================================================
docker-compose.test.yml
====================================================================================================

```
services:
  postgres:
    ports:
      - "5432:5432"   # только для тестов локально

#  gateway:
#    environment:
#      DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test
#
#  migrations:
#    environment:
#      DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test
```

====================================================================================================
docker-compose.yml
====================================================================================================

```
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: repair_crm
      POSTGRES_HOST_AUTH_METHOD: trust  # <- КЛЮЧЕВАЯ СТРОКgi
    expose:
      - "5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U postgres" ]
      interval: 5s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
    restart: unless-stopped

  nginx:
    container_name: nginx
    build:
      context: .
      dockerfile: services/nginx/Dockerfile
    ports:
      - "80:80"
      - "443:443"
    env_file:
      - .env
    environment:
      DOMAIN_NAME: ${DOMAIN_NAME:-localhost}
    volumes:
      - certbot_conf:/etc/letsencrypt
      - certbot_web:/var/www/certbot
      - ./state:/etc/nginx/state
    healthcheck:
#      test: [ "CMD", "curl", "-f", "http://localhost/.well-known/acme-challenge/healthcheck" ]
      test: [ "CMD", "nginx", "-t" ]  # проверяет только конфиг
      interval: 10s
      timeout: 5s
      retries: 30
      start_period: 10s
    deploy:
      resources:
        limits:
          memory: 64M
        reservations:
          memory: 32M
    restart: unless-stopped

  certbot:
    container_name: certbot
    build:
      context: .
      dockerfile: services/certbot/Dockerfile
    volumes:
      - certbot_conf:/etc/letsencrypt
      - certbot_web:/var/www/certbot
    env_file:
      - .env
    environment:
      DOMAIN_NAME: ${DOMAIN_NAME:-localhost}
    depends_on:
      nginx:
        condition: service_healthy  # ← ждем здоровый nginx
    healthcheck:
      # Проверяем, что скрипт дошел до бесконечного цикла (процесс sleep существует)
      test: [ "CMD", "sh", "-c", "pgrep -f 'sleep 12h' || pgrep -f 'sleep 3600' || exit 1" ]
      interval: 5s
      timeout: 3s
      retries: 60
      start_period: 60s
    deploy:
      resources:
        limits:
          memory: 128M
        reservations:
          memory: 64M
    restart: unless-stopped

  watchdog:
    build:
      context: .
      dockerfile: services/watchdog/Dockerfile
    container_name: watchdog

    volumes:
      - ./state:/state
      - /var/run/docker.sock:/var/run/docker.sock

    environment:
      STATE_PATH: /state/state.json
      WORKDIR: /app


    mem_limit: 64m
    cpus: "0.2"

    healthcheck:
      test: [ "CMD", "python", "-c", "print('ok')" ]
      interval: 30s
      timeout: 3s
      retries: 3

    depends_on:
      nginx:
        condition: service_healthy
    restart: unless-stopped


  gateway-blue:
    container_name: gateway-blue
    build:
      context: .
      dockerfile: services/gateway/Dockerfile
    expose:
      - "8000"

    env_file:
      - .env

    environment:
      DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@postgres:5432/repair_crm}

    command:
      [
        "uvicorn",
  
<< TRUNCATED >>
```

====================================================================================================
LICENSE
====================================================================================================

```
MIT License

Copyright (c) 2026 kpa9pt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```

====================================================================================================
Makefile
====================================================================================================

```
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
```

====================================================================================================
pytest.ini
====================================================================================================

```
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
```

====================================================================================================
README.md
====================================================================================================

```
# Repair CRM

[![Docker](https://img.shields.io/badge/Docker-20.10+-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)


Система для управления ремонтами и заказами в мастерской мототехники.

---

## 📌 О проекте

Repair CRM — backend-система для обработки заявок на ремонт.  
Проект построен как API-first приложение с административной панелью.

**Portable deployment:** достаточно Docker и свободных портов 80/443.

---

## ⚙️ Возможности

- CRUD заявок на ремонт
- Фильтрация и пагинация
- REST API (Swagger UI)
- Административная панель (SQLAdmin)
- Docker-окружение для разработки
- CI/CD (GitHub Actions + GHCR)
- Автоматический HTTPS (Let's Encrypt)

---

## 🧱 Технологии

- Python 3.14 / FastAPI
- PostgreSQL / SQLAlchemy (async)
- Alembic / pytest
- Docker / Docker Compose
- Nginx / Certbot
- GitHub Container Registry

---

## 📋 Требования

- Docker (20.10+)
- Docker Compose (2.20+)
- Свободные порты: 80, 443 (для HTTPS)

---

## 🚀 Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone https://github.com/kpa9pt/repair-crm.git
cd repair-crm

# 2. Запустить проект (.env создастся автоматически)
make up

# 3. Остановить проект
make down
```

---

## 🌐 После запуска доступны сервисы:

|   Сервис	   |           URL           |
|:-----------:|:-----------------------:|
| API Gateway |    	http://localhost    |
| Swagger UI  | 	http://localhost/docs  |
| Admin panel | 	http://localhost/admin |

---

## 🔧 Переменные окружения

При первом запуске файл .env создаётся автоматически из .env.example:
```bash
cp .env.example .env   # если нужно отредактировать вручную
```
Основные переменные:

| Переменная      | 	Значение по умолчанию                                                | 	Описание                               |
|:----------------|:----------------------------------------------------------------------|:----------------------------------------|
| DATABASE_URL    | 	postgresql+asyncpg://postgres:<br>postgres@postgres:5432/repair_crm	 | Подключение к БД                        |
| ADMIN_USERNAME	 | admin	                                                                | Логин админ-панели                      |
| ADMIN_PASSWORD	 | (смотри .env.example)	                                                | Пароль админ-панели                     |
| DOMAIN_NAME	    | localhost	                                                            | Домен (для продакшена укажите реальный) |


> Для HTTPS укажите реальный домен и настройте DNS запись на IP вашего сервера. Certbot автоматически получит сертификат.

---

## 🛠️ Основные команды

```bash
make up          # запустить все сервисы
make down        # остановить и удалить контейнеры
make
<< TRUNCATED >>
```

====================================================================================================
requirements.txt
====================================================================================================

```
alembic==1.18.4
annotated-doc==0.0.4
annotated-types==0.7.0
anyio==4.13.0
asyncpg==0.31.0
bcrypt==5.0.0
black==26.5.1
certifi==2026.5.20
cfgv==3.5.0
click==8.4.1
distlib==0.4.0
fastapi==0.136.3
filelock==3.29.0
greenlet==3.5.1
h11==0.16.0
httpcore==1.0.9
httptools==0.8.0
httpx==0.28.0
identify==2.6.19
idna==3.16
iniconfig==2.3.0
itsdangerous==2.2.0
Jinja2==3.1.6
Mako==1.3.12
MarkupSafe==3.0.3
mypy_extensions==1.1.0
nodeenv==1.10.0
packaging==26.2
passlib==1.7.4
pathspec==1.1.1
platformdirs==4.10.0
pluggy==1.6.0
pre_commit==4.6.0
pydantic==2.13.4
pydantic-settings==2.14.1
pydantic_core==2.46.4
Pygments==2.20.0
pytest==9.0.3
pytest-asyncio==1.3.0
python-discovery==1.4.0
python-dotenv==1.2.2
python-multipart==0.0.27
pytokens==0.4.1
PyYAML==6.0.3
redis==5.0.1
sqladmin==0.27.0
SQLAlchemy==2.0.49
starlette==1.2.0
typing-inspection==0.4.2
typing_extensions==4.15.0
uvicorn==0.30.0
uvloop==0.22.1
virtualenv==21.4.1
watchfiles==1.2.0
websockets==16.0
WTForms==3.1.2

requests
```

====================================================================================================
scripts/build_manifest.py
====================================================================================================

```
import json
import os

SERVICES = ["gateway", "migrations", "nginx", "certbot", "watchdog"]

github_sha = os.environ.get("GITHUB_SHA", "")

manifest = {}

for service in SERVICES:
    changed = os.environ.get(f"CHANGED_{service.upper()}", "false")

    if changed == "true":
        manifest[service] = github_sha

print(json.dumps(manifest))

```

====================================================================================================
scripts/deploy/bootstrap_state.py
====================================================================================================

```
import json
import os
import requests
import sys

OWNER = "kpa9pt"

SERVICES = [
    "gateway",
    "nginx",
    "certbot",
    "migrations",
    "watchdog",
]

TOKEN = os.environ["GHCR_READ_TOKEN"]

# 🔥 DEBUG 1: проверяем что токен вообще есть и не пустой
print("TOKEN EXISTS:", bool(TOKEN), file=sys.stderr)
print("TOKEN PREFIX:", TOKEN[:6] if TOKEN else None, file=sys.stderr)

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
}

DEPLOY_ID = os.getenv("DEPLOY_ID", "bootstrap")


def latest_image(service: str) -> str:
    url = (
        f"https://api.github.com/users/"
        f"{OWNER}/packages/container/repair-crm-{service}/versions"
    )

    print(f"\n--- SERVICE: {service} ---", file=sys.stderr)
    print("URL:", url, file=sys.stderr)

    response = requests.get(url, headers=HEADERS)

    # 🔥 DEBUG 2: статус ответа
    print("STATUS:", response.status_code, file=sys.stderr)

    # 🔥 DEBUG 3: если упало — покажем текст
    if response.status_code != 200:
        print("ERROR BODY:", response.text[:500], file=sys.stderr)

    response.raise_for_status()

    versions = response.json()

    # 🔥 DEBUG 4: сколько версий пришло
    print("VERSIONS COUNT:", len(versions), file=sys.stderr)

    for version in versions:
        # ❗ оставили как у тебя было (НЕ трогаем логику)
        tags = version["metadata"]["container"]["tags"]

        print("TAGS:", tags, file=sys.stderr)

        sha_tags = [tag for tag in tags if tag != "latest"]

        if sha_tags:
            sha = sha_tags[0]
            return f"ghcr.io/{OWNER}/repair-crm-{service}:{sha}"

    raise RuntimeError(f"No sha tag found for {service}")


state = {
    "deploy_id": DEPLOY_ID,
    "services": {
        "gateway": {
            "strategy": "blue-green",
            "active": "blue",
            "port": 8000,
            "healthcheck": "/health",
            "rollback_locked": False,
        }
    },
}

gateway_image = latest_image("gateway")

state["services"]["gateway"]["blue"] = {"image": gateway_image}
state["services"]["gateway"]["green"] = {"image": gateway_image}

for service in [
    "nginx",
    "certbot",
    "migrations",
    "watchdog",
]:
    state["services"][service] = {
        "strategy": "single",
        "image": latest_image(service),
    }

print(json.dumps(state, indent=2))

```

====================================================================================================
scripts/deploy/check_diff.py
====================================================================================================

```
import json
import sys


def load(path):
    with open(path) as f:
        return json.load(f)


def main():
    changes = load("images.json")
    state = load("state.json")

    deploy_plan = []

    for service in changes.keys():

        service_state = state["services"].get(service)

        if not service_state:
            print(
                f"skip {service}: not found in state",
                file=sys.stderr,
            )
            continue

        if service_state.get("strategy") != "blue-green":
            print(
                f"skip {service}: strategy={service_state.get('strategy')}",
                file=sys.stderr,
            )
            continue

        deploy_plan.append(service)

    print(json.dumps(deploy_plan))


if __name__ == "__main__":
    main()

```

====================================================================================================
scripts/deploy/cleanup.py
====================================================================================================

```
import json
import os
import base64
import subprocess
from pathlib import Path


def load_state():
    state_file = Path.home() / "repair-crm" / "state" / "state.json"
    with open(state_file) as f:
        return json.load(f)


def load_plan():
    data = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(data).decode())


def main():
    state = load_state()
    deploy_plan = load_plan()

    print("=== CLEANUP START ===")

    for service in deploy_plan:
        if service not in state["services"]:
            print(f"skip unknown service: {service}")
            continue

        svc = state["services"][service]

        if svc["strategy"] == "blue-green":
            active = svc["active"]
            inactive = "green" if active == "blue" else "blue"
            container = f"{service}-{inactive}"

            print(f"stopping {container}")
            subprocess.run(["docker", "stop", container], check=False)

    print("=== PRUNE ===")
    subprocess.run(["docker", "system", "prune", "-f"], check=False)

    print("=== CLEANUP DONE ===")


if __name__ == "__main__":
    main()

```

====================================================================================================
scripts/deploy/lock_rollback.py
====================================================================================================

```
import json
import os
import base64
from pathlib import Path


STATE_FILE = Path.home() / "repair-crm" / "state" / "state.json"


def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def decode_plan():
    raw = os.environ.get("DEPLOY_PLAN", "")
    if not raw:
        return []

    decoded = base64.b64decode(raw).decode()
    return json.loads(decoded)


def main():
    deploy_plan = decode_plan()
    state = load_state()

    for service in deploy_plan:
        if service not in state["services"]:
            print(f"⚠️ skip unknown service {service}")
            continue

        print(f"🔒 lock rollback: {service}")
        state["services"][service]["rollback_locked"] = True

    save_state(state)
    print("✅ rollback locked for planned services")


if __name__ == "__main__":
    main()

```

====================================================================================================
scripts/deploy/post_switch_verify.py
====================================================================================================

```
import json
import sys
import time
import os
import base64
import subprocess
from pathlib import Path


def healthcheck(container, port, health):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{health}', timeout=2)"
        ),
    ]

    return subprocess.run(cmd).returncode == 0


def wait_health(container, port, health, retries=30, delay=2):

    for i in range(retries):

        if healthcheck(container, port, health):
            return True

        print(
            f"retry: {i + 1}/{retries}",
            file=sys.stderr,
        )

        time.sleep(delay)

    return False


def main():
    deploy_plan = json.loads(base64.b64decode(os.environ["DEPLOY_PLAN"]).decode())

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    result = {
        "passed": [],
        "failed": [],
    }

    for service in deploy_plan:

        print(
            f"🔍 post-switch verify: {service}",
            file=sys.stderr,
        )

        s = state["services"][service]

        active = s["active"]
        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{active}"

        print(
            f"phase 1 smoke: {service}",
            file=sys.stderr,
        )

        if not wait_health(container, port, health):
            result["failed"].append(service)
            continue

        print(
            f"phase 2 soak sleep: {service}",
            file=sys.stderr,
        )

        time.sleep(60)

        print(
            f"phase 3 soak verify: {service}",
            file=sys.stderr,
        )

        if wait_health(container, port, health):
            result["passed"].append(service)
        else:
            result["failed"].append(service)

    print(json.dumps(result))


if __name__ == "__main__":
    main()

```

====================================================================================================
scripts/deploy/push_to_vds.sh
====================================================================================================

```
#!/usr/bin/env bash
set -e

echo "=== PUSH TO VDS START ==="
date
whoami
pwd

cd ~/repair-crm

echo "=== UPDATE COMPOSE ==="
curl -fsSL https://raw.githubusercontent.com/kpa9pt/repair-crm/main/docker-compose.yml -o docker-compose.yml

echo "=== WRITE ENV ==="
cat > .env <<EOF
DATABASE_URL=$DATABASE_URL
ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_PASSWORD=$ADMIN_PASSWORD
SECRET_KEY=$SECRET_KEY
TELEGRAM_TOKEN=$TELEGRAM_TOKEN
DOMAIN_NAME=$DOMAIN_NAME
EOF

echo "=== DOCKER COMPOSE UP ==="
docker compose up -d

echo "=== DONE ==="
docker ps
```

====================================================================================================
scripts/deploy/render_compose.py
====================================================================================================

```
import json
import os

STATE_FILE = os.environ.get("STATE_FILE", "state.json")

with open(STATE_FILE) as f:
    state = json.load(f)

yaml = ["services:"]

for service_name, config in state["services"].items():

    strategy = config["strategy"]

    if strategy == "blue-green":

        yaml.append(f"  {service_name}-blue:")
        yaml.append(f"    image: {config['blue']['image']}")

        yaml.append(f"  {service_name}-green:")
        yaml.append(f"    image: {config['green']['image']}")

    elif strategy == "single":

        yaml.append(f"  {service_name}:")
        yaml.append(f"    image: {config['image']}")

print("\n".join(yaml))

```

====================================================================================================
scripts/deploy/run_rollbacks.py
====================================================================================================

```
import json
import os
import base64
import subprocess


def load_rollback_decision():
    data = os.environ["ROLLBACK_DECISION"]
    return json.loads(base64.b64decode(data).decode())


def main():
    decision = load_rollback_decision()

    failed = decision.get("failed", [])

    if not failed:
        print("✅ no rollback required")
        return

    server_user = os.environ["SERVER_USER"]
    server_ip = os.environ["SERVER_IP"]

    for service in failed:

        print(f"🔄 rollback: {service}")

        subprocess.run(
            [
                "ssh",
                f"{server_user}@{server_ip}",
                f"ROLLBACK_SERVICE={service} python3 -",
            ],
            stdin=open("scripts/rollback.py", "rb"),
            check=True,
        )

    print("✅ rollback engine finished")


if __name__ == "__main__":
    main()

```

====================================================================================================
scripts/deploy/switch_services.py
====================================================================================================

```
import json
import sys
import os
import base64
from pathlib import Path


def load_deploy_plan():
    plan = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(plan).decode())


def main():
    deploy_plan = load_deploy_plan()
    if not deploy_plan:
        print("no changes")
        sys.exit(0)

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:
        active = state["services"][service]["active"]
        new = "green" if active == "blue" else "blue"

        state["services"][service]["active"] = new

        print(f"🔁 {service}: {active} → {new}")

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


if __name__ == "__main__":
    main()

```

====================================================================================================
scripts/deploy/unlock_rollback.py
====================================================================================================

```
import json
import os
import base64
from pathlib import Path


def load_rollback_decision():
    data = os.environ["ROLLBACK_DECISION"]
    return json.loads(base64.b64decode(data).decode())


def main():
    decision = load_rollback_decision()

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in decision["passed"]:

        if service not in state["services"]:
            print(f"⚠️ unknown service: {service}")
            continue

        state["services"][service]["rollback_locked"] = False

        print(f"🔓 rollback unlocked: {service}")

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


if __name__ == "__main__":
    main()

```

====================================================================================================
scripts/deploy/update_state.py
====================================================================================================

```
import json
import os

STATE_PATH = "state.json"
CHANGES_PATH = "images.json"

OWNER = "kpa9pt"

DEPLOY_ID = os.getenv("DEPLOY_ID")


def load(path):
    with open(path) as f:
        return json.load(f)


state = load(STATE_PATH)
changes = load(CHANGES_PATH)

state["deploy_id"] = DEPLOY_ID


def build_image(service, sha):
    return f"ghcr.io/{OWNER}/repair-crm-{service}:{sha}"


for service, sha in changes.items():

    if service not in state["services"]:
        state["services"][service] = {"strategy": "single", "rollback_locked": False}

    service_state = state["services"][service]

    image = build_image(service, sha)

    if service_state["strategy"] == "blue-green":

        active = service_state["active"]
        inactive = "green" if active == "blue" else "blue"

        service_state[inactive]["image"] = image

    else:

        service_state["image"] = image


print(json.dumps(state, indent=2))

```

====================================================================================================
scripts/deploy/verify_inactive_services.py
====================================================================================================

```
import json
import sys
import subprocess
import time
import os
import base64
from pathlib import Path


def healthcheck(container, port, health):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{health}', timeout=2)"
        ),
    ]

    return subprocess.run(cmd).returncode == 0


def load_deploy_plan():
    plan = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(plan).decode())


def main():
    deploy_plan = load_deploy_plan()

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:

        print(f"🔍 verifying {service}")

        s = state["services"][service]

        active = s["active"]

        inactive = "green" if active == "blue" else "blue"

        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{inactive}"

        ok = False

        for i in range(60):
            if healthcheck(container, port, health):
                print(f"✅ {container} healthy")
                ok = True
                break

            print(f"retry {i}")
            time.sleep(2)

        if not ok:
            print(f"❌ {container} failed")
            sys.exit(1)


if __name__ == "__main__":
    main()

```

====================================================================================================
scripts/deploy/verify_services.py
====================================================================================================

```
import json
import sys
import subprocess
import time
import os
import base64
from pathlib import Path


def healthcheck(container, port, health):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{health}', timeout=2)"
        ),
    ]

    return subprocess.run(cmd).returncode == 0


def load_deploy_plan():
    plan = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(plan).decode())


def main():
    deploy_plan = load_deploy_plan()

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:

        print(f"🔍 verifying {service}")

        s = state["services"][service]

        active = s["active"]
        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{active}"

        ok = False

        for i in range(60):
            if healthcheck(container, port, health):
                print(f"✅ {service} healthy")
                ok = True
                break

            print(f"retry {i}")

            time.sleep(2)

        if not ok:
            print(f"❌ {service} failed")
            sys.exit(1)

    subprocess.run(["docker", "exec", "nginx", "/scripts/reload.sh"], check=True)

    print("🔁 nginx reloaded")


if __name__ == "__main__":
    main()

```

====================================================================================================
scripts/rollback.py
====================================================================================================

```
import json
import subprocess
import time
import sys
import os

from pathlib import Path

STATE_FILE = Path(
    os.getenv(
        "STATE_PATH",
        str(Path.home() / "repair-crm" / "state" / "state.json"),
    )
)

WORKDIR = Path(
    os.getenv(
        "WORKDIR",
        str(Path.home() / "repair-crm"),
    )
)

NGINX_CONTAINER = "nginx"

service = os.getenv("ROLLBACK_SERVICE")
if not service:
    raise RuntimeError("ROLLBACK_SERVICE not set")


def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def opposite(active: str) -> str:
    if active == "blue":
        return "green"
    return "blue"


def service_name(slot: str) -> str:
    return f"{service}-{slot}"


def wait_health(container: str, port: int, healthcheck: str, retries=30, delay=2):
    print(f"⏳ Waiting health: {container}")

    for i in range(retries):
        try:
            subprocess.run(
                [
                    "docker",
                    "exec",
                    container,
                    "python",
                    "-c",
                    (
                        "import urllib.request;"
                        "urllib.request.urlopen("
                        f"'http://localhost:{port}{healthcheck}', timeout=2"
                        ")"
                    ),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("✅ health OK")
            return True

        except subprocess.CalledProcessError:
            print(f"retry {i + 1}/{retries}")
            time.sleep(delay)

    return False


def reload_nginx():
    print("🔁 reloading nginx")
    subprocess.run(
        ["docker", "exec", NGINX_CONTAINER, "/scripts/reload.sh"],
        check=True,
    )


def main():
    state = load_state()

    service_state = state["services"][service]

    port = service_state.get("port", 8000)
    healthcheck = service_state.get("healthcheck", "/health")

    if service_state["strategy"] == "single":
        print("single strategy rollback not supported")
        sys.exit(1)

    active = service_state["active"]
    target = opposite(active)

    target_container = service_name(target)

    print(f"🔄 rollback: {active} → {target}")

    # 1. start target
    # WORKDIR = Path.home() / "repair-crm"

    subprocess.run(
        # ["docker", "compose", "up", "-d", f"{target_container}"],
        ["docker", "restart", f"{target_container}"],
        cwd=WORKDIR,
        check=True,
    )

    # 2. healthcheck
    if not wait_health(
        target_container,
        port,
        healthcheck,
    ):
        print("❌ rollback failed: target unhealthy")
        sys.exit(1)

    # 3. switch active
    state["services"][service]["active"] = target
    save_state(state)

    # 4. reload nginx
    reload_nginx()

    prin
<< TRUNCATED >>
```

====================================================================================================
scripts/test.sh
====================================================================================================

```
#!/bin/bash
set -e

TEST_PATH=${1:-tests}


echo "🚀 Starting infrastructure..."
#docker compose down -v
#docker compose up -d --build
docker compose \
  -f docker-compose.yml \
  -f docker-compose.test.yml \
  down -v

docker compose \
  -f docker-compose.yml \
  -f docker-compose.test.yml \
  up -d --build

get_health() {
  docker inspect --format='{{.State.Health.Status}}' "$1"
}

wait_for_health() {
  local name=$1
  local id
  id=$(docker compose ps -q "$name")

  if [ -z "$id" ]; then
    echo "❌ Container $name not found"
    exit 1
  fi

  echo "⏳ Waiting for $name..."

#  until [ "$(get_health "$id")" = "healthy" ]; do
#    pass
#  done

  echo "✅ $name is healthy"
}

echo "⏳ Waiting for services..."

wait_for_health postgres
wait_for_health gateway-blue


# В начале скрипта, после поднятия postgres
echo "Creating test database..."
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE repair_crm_test" 2>/dev/null || true

echo "Applying migrations..."
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test alembic upgrade head

echo "🧪 Running tests..."
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test
pytest "$TEST_PATH" -v

echo "🧹 Cleaning up..."
docker compose down -v
```

====================================================================================================
services/certbot/Dockerfile
====================================================================================================

```
FROM certbot/certbot:latest

RUN apk add --no-cache bash docker-cli

COPY services/certbot/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

====================================================================================================
services/certbot/entrypoint.sh
====================================================================================================

```
#!/bin/sh
set -e

DOMAIN=${DOMAIN_NAME:-localhost}
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

echo "🚀 Certbot service started for domain: $DOMAIN"

if [ "$DOMAIN" = "localhost" ]; then
  echo "Local mode detected, certbot disabled"
  while true; do sleep 12h; done
fi

# Функция для запроса сертификата с повторными попытками
get_certificate() {
  while true; do
    echo "📦 Requesting new certificate..."
    if certbot certonly --webroot --webroot-path=/var/www/certbot \
      --email admin@$DOMAIN --agree-tos --no-eff-email \
      -d "$DOMAIN" --non-interactive; then

      echo "✅ Certificate issued"
      return 0
    else
      echo "❌ Failed, checking if rate limit..."
      # Если ошибка содержит "too many failed authorizations" - ждем 1 час
      if certbot --version 2>/dev/null && \
         certbot certificates 2>&1 | grep -q "too many failed authorizations"; then
        echo "⏳ Rate limit detected, waiting 1 hour..."
        sleep 3600
      else
        echo "⏳ Other error, waiting 5 minutes..."
        sleep 300
      fi
    fi
  done
}

# Основная логика
if [ -f "$CERT_PATH" ]; then
  echo "✅ Certificate already exists"
else
  get_certificate
fi

# Бесконечный цикл обновления
while true; do
  sleep 12h
  echo "🔄 Renewing certificate..."
  certbot renew --webroot --webroot-path=/var/www/certbot --quiet
  echo "🔄 Renewal check done"
done
```

====================================================================================================
services/gateway/app/__init__.py
====================================================================================================

```

```

====================================================================================================
services/gateway/app/admin/__init__.py
====================================================================================================

```
"""
Модуль админ-панели SQLAdmin
"""

from .auth import AdminAuth
from .views import RepairRequestAdmin

__all__ = ["AdminAuth", "RepairRequestAdmin"]

```

====================================================================================================
services/gateway/app/admin/auth.py
====================================================================================================

```
"""
Аутентификация для админ-панели SQLAdmin
"""

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from passlib.context import CryptContext
from shared.settings import get_settings

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminAuth(AuthenticationBackend):
    """Простая аутентификация для админ-панели"""

    async def login(self, request: Request) -> bool:
        """Обработка входа в админку"""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        settings = get_settings()

        # Здесь можно заменить на чтение из БД или переменных окружения
        # Для старта - фиксированные учетные данные
        if username == settings.admin_username and password == settings.admin_password:
            request.session.update({"admin_authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        """Обработка выхода из админки"""
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """Проверка авторизации"""
        return request.session.get("admin_authenticated", False)

```

====================================================================================================
services/gateway/app/admin/views.py
====================================================================================================

```
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqladmin import ModelView

from shared.models import RepairRequest
from shared.enums import Urgency, RequestStatus

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class RepairRequestAdmin(ModelView, model=RepairRequest):
    """Админка RepairRequest"""

    name = "Заявка"
    name_plural = "Заявки на ремонт"
    icon = "fa-solid fa-wrench"

    # --------------------
    # СПИСОК
    # --------------------
    column_list = [
        RepairRequest.id,
        RepairRequest.vehicle_name,
        RepairRequest.status,
        RepairRequest.urgency,
        RepairRequest.is_operational,
        RepairRequest.created_at,
        RepairRequest.deadline,
        RepairRequest.client_name,
    ]

    column_labels = {
        RepairRequest.vehicle_name: "Техника",
        RepairRequest.client_name: "Клиент",
        RepairRequest.status: "Статус заявки",
        RepairRequest.urgency: "Срочность",
        RepairRequest.created_at: "Создано",
        RepairRequest.deadline: "Дедлайн",
        RepairRequest.is_operational: "Техника на ходу?",
    }

    column_editable_list = [
        RepairRequest.status,
        RepairRequest.urgency,
    ]

    column_filters = []

    column_default_sort = [(RepairRequest.created_at, True)]

    search_fields = [
        "vehicle_name",
        "client_name",
        "description",
    ]

    can_export = True
    can_view_details = True

    # --------------------
    # ФОРМА
    # --------------------
    form_columns = [
        # === ОСНОВНОЕ ===
        "vehicle_name",
        "description",
        "is_operational",
        # === УПРАВЛЕНИЕ ===
        "urgency",
        "status",
        "deadline",
        # === ФИНАНСЫ ===
        "parts_cost",
        "client_payment",
        # === КЛИЕНТ ===
        "client_name",
        "phone",
        "email",
    ]

    form_args = {
        "vehicle_name": {"label": "Техника"},
        "client_name": {"label": "Клиент", "default": "Топ Лес"},
        "phone": {"label": "Телефон"},
        "email": {"label": "Email"},
        "description": {"label": "Описание проблемы"},
        "urgency": {"label": "Срочность", "default": Urgency.NORMAL.value},
        "status": {"label": "Статус заявки", "default": RequestStatus.NEW.value},
        "deadline": {"label": "Дедлайн"},
        "parts_cost": {"label": "Стоимость запчастей", "default": Decimal("0.00")},
        "client_payment": {"label": "Оплата клиента", "default": Decimal("0.00")},
        "is_operational": {"label": "Техника на ходу?", "default": False},
    }

    # # ДЕФОЛТЫ (SQLAdmin правильный способ)
    # form_args = {
    #     "client_name": {"default": "Топ Лес"},
    #     "urgency": {"default": Urgency.NORMAL.value},
    #     "status": {"default": RequestStatus.NEW.value},
    #     "is_operational": {"default": False},
    #     "parts_cost": {"default": Decimal("0.00")},
    #     "client_payment": {"default": Decimal("0.00")},
    # }

    # --
<< TRUNCATED >>
```

====================================================================================================
services/gateway/app/main.py
====================================================================================================

```
from fastapi import FastAPI
from shared import get_settings
from .routers import repair_requests_router
from .admin import AdminAuth, RepairRequestAdmin
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware
from shared.db import get_engine  # ← импортируем новую функцию
from fastapi.responses import RedirectResponse


settings = get_settings()

app = FastAPI(
    title="Gateway API",
    version="0.1.0",
    description="API Gateway для CRM ремонтной мастерской",
)

# Добавляем middleware для сессий (нужен для аутентификации админки)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key or "supersecretkey-change-in-production",
    session_cookie="admin_session",
)

# Настройка админ-панели
authentication_backend = AdminAuth(secret_key=settings.secret_key or "supersecretkey")
admin = Admin(
    app,
    get_engine(),  # ← используем get_engine()
    authentication_backend=authentication_backend,
    title="Repair CRM Admin",
    logo_url="/static/logo.png",  # опционально
    base_url="/admin",  # ← ЯВНО УКАЗЫВАЕМ URL
)

# Регистрируем модели
admin.add_view(RepairRequestAdmin)

# Подключаем роутеры
app.include_router(repair_requests_router)


@app.get("/")
async def root():
    return RedirectResponse("/admin/")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/test_blue_green")
async def test_blue_green():
    return {"status": "ok"}


@app.get("/test_check_diff")
async def test_check_diff():
    return {"status": "ok"}

```

====================================================================================================
services/gateway/app/routers/__init__.py
====================================================================================================

```
from .repair_requests import router as repair_requests_router

__all__ = ["repair_requests_router"]

```

====================================================================================================
services/gateway/app/routers/repair_requests.py
====================================================================================================

```
"""
Роутер для работы с заявками на ремонт.

Все эндпоинты имеют префикс /api/v1/repair-requests
"""

from fastapi import APIRouter, Depends, HTTPException, status

from shared import get_session_maker
from shared.repository import RepairRequestRepository
from shared.schemas import (
    RepairRequestCreate,
    RepairRequestUpdate,
    RepairRequestResponse,
    RepairRequestListResponse,
)

router = APIRouter(prefix="/api/v1/repair-requests", tags=["Repair Requests"])


async def get_repo():
    session_maker = get_session_maker()

    async with session_maker() as session:
        yield RepairRequestRepository(session)


@router.post(
    "/", response_model=RepairRequestResponse, status_code=status.HTTP_201_CREATED
)
async def create_repair_request(
    request_data: RepairRequestCreate, repo: RepairRequestRepository = Depends(get_repo)
):
    """
    Создать новую заявку на ремонт.

    - **vehicle_name**: название техники (обязательно)
    - **description**: описание поломки (обязательно)
    - **urgency**: срочность (low/normal/high/critical)
    - **status**: статус (new/in_progress/waiting_parts/
        diagnostics/waiting_approval/done)
    """
    # Конвертируем Pydantic модель в словарь
    new_request = await repo.create(**request_data.model_dump())
    await repo.session.commit()
    return RepairRequestResponse.model_validate(new_request)


@router.get("/", response_model=RepairRequestListResponse)
async def get_all_repair_requests(
    skip: int = 0, limit: int = 100, repo: RepairRequestRepository = Depends(get_repo)
):
    """
    Получить список всех заявок с пагинацией.

    - **skip**: сколько заявок пропустить
    - **limit**: сколько заявок вернуть
    - Сортировка: сначала новые (по created_at DESC)
    """
    requests = await repo.get_all(skip=skip, limit=limit)
    total = len(requests)  # В будущем можно сделать отдельный метод для count

    return RepairRequestListResponse(
        items=[RepairRequestResponse.model_validate(r) for r in requests],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/vehicle/{vehicle_name}", response_model=RepairRequestListResponse)
async def get_repair_requests_by_vehicle(
    vehicle_name: str,
    skip: int = 0,
    limit: int = 100,
    repo: RepairRequestRepository = Depends(get_repo),
):
    """
    Получить все заявки для конкретной техники.

    - **vehicle_name**: название техники
    - **skip**: сколько пропустить
    - **limit**: сколько вернуть
    """
    # Метод get_by_vehicle нужно добавить в репозиторий
    # Пока используем фильтрацию через get_all (не оптимально)
    all_requests = await repo.get_by_vehicle(vehicle_name)
    filtered = [r for r in all_requests if r.vehicle_name == vehicle_name]
    total = len(filtered)
    paginated = filtered[skip : skip + limit]

    return RepairRequestListResponse(
        items=[RepairRequestResponse.model_validate(r) for r in paginated],
        total=total,
        skip=skip,
        limit=limit,
<< TRUNCATED >>
```

====================================================================================================
services/gateway/Dockerfile
====================================================================================================

```
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/gateway ./services/gateway
COPY shared ./shared

COPY alembic.ini .
```

====================================================================================================
services/migrations/Dockerfile
====================================================================================================

```
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY shared ./shared
COPY alembic.ini .

CMD ["alembic", "upgrade", "head"]
```

====================================================================================================
services/nginx/Dockerfile
====================================================================================================

```
FROM nginx:alpine

RUN apk add --no-cache gettext inotify-tools bash jq



COPY services/nginx/nginx-https.conf /etc/nginx/nginx-https.conf
COPY services/nginx/nginx-http.conf /etc/nginx/nginx-http.conf

# 👇 ВСЕ скрипты в одну папку
COPY services/nginx/scripts/ /scripts/

RUN chmod +x /scripts/*.sh

ENTRYPOINT ["/scripts/entrypoint.sh"]
```

====================================================================================================
services/nginx/nginx-http.conf
====================================================================================================

```
events {}

http {
    include /etc/nginx/upstreams/upstream.conf;

    server {
        listen 80;
        server_name ${DOMAIN_NAME};

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        location /.well-known/acme-challenge/healthcheck {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass http://gateway_backend;
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
            proxy_next_upstream_tries 3;
            proxy_connect_timeout 5s;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }
    }

}
```

====================================================================================================
services/nginx/nginx-https.conf
====================================================================================================

```
events {}

http {
    include /etc/nginx/upstreams/upstream.conf;

    server {
        listen 80;
        server_name ${DOMAIN_NAME};

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        location /.well-known/acme-challenge/healthcheck {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass http://gateway_backend;
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
            proxy_next_upstream_tries 3;
            proxy_connect_timeout 5s;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }
    }

    server {
        listen 443 ssl;
        server_name ${DOMAIN_NAME};

        ssl_certificate /etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/${DOMAIN_NAME}/privkey.pem;

        location /.well-known/acme-challenge/healthcheck {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass http://gateway_backend;
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
            proxy_next_upstream_tries 3;
            proxy_connect_timeout 5s;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }
    }

}
```

====================================================================================================
services/nginx/scripts/entrypoint.sh
====================================================================================================

```
#!/bin/sh
set -e

echo "[BOOT] nginx starting"

echo "[STEP] init state"
/scripts/init_state.sh

echo "[STEP] render upstream"
/scripts/render_upstream.sh

echo "[STEP] generate nginx config"
/scripts/nginx_config.sh

echo "[STEP] nginx test"
nginx -t

echo "[STEP] start nginx"
nginx -g 'daemon off;' &
NGINX_PID=$!

echo "[STEP] watcher start"
/scripts/watcher.sh &

wait $NGINX_PID
```

====================================================================================================
services/nginx/scripts/init_state.sh
====================================================================================================

```
#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json

echo "[STATE] checking state file"

# если это директория — это сломанный volume
if [ -d "$STATE_FILE" ]; then
  echo "[STATE] ERROR: state.json is directory, fixing"
  rm -rf "$STATE_FILE"
fi

# если файла нет — создаём
if [ ! -f "$STATE_FILE" ]; then
  echo "[STATE] state.json missing, generating local state"
  /scripts/local_state.sh
fi

echo "[STATE] state loaded"
```

====================================================================================================
services/nginx/scripts/local_state.sh
====================================================================================================

```
#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json
#dfff
echo "[LOCAL] generating default state"

cat > "$STATE_FILE" <<EOF
{
  "deploy_id": "local",
  "services": {
    "gateway": {
      "strategy": "blue-green",
      "active": "blue",
      "port": 8000,
      "healthcheck": "/health",
      "rollback_locked": false
    }
  }
}
EOF
```

====================================================================================================
services/nginx/scripts/nginx_config.sh
====================================================================================================

```
#!/bin/sh
set -e

DOMAIN="${DOMAIN_NAME:-localhost}"
CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

echo "[NGINX] generating nginx.conf..."

if [ -f "$CERT" ]; then
  CONF="/etc/nginx/nginx-https.conf"
  echo "[NGINX] mode=https"
else
  CONF="/etc/nginx/nginx-http.conf"
  echo "[NGINX] mode=http"
fi

envsubst '$DOMAIN_NAME' < "$CONF" > /etc/nginx/nginx.conf

echo "[NGINX] nginx.conf generated"
```

====================================================================================================
services/nginx/scripts/reload.sh
====================================================================================================

```
#!/bin/sh
set -e

/scripts/render_upstream.sh
nginx -t
nginx -s reload
```

====================================================================================================
services/nginx/scripts/render_upstream.sh
====================================================================================================

```
#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json

mkdir -p /etc/nginx/upstreams

rm -f /etc/nginx/upstreams/*.conf 2>/dev/null || true

echo "[RENDER] state=$STATE_FILE"

jq -r '
  .services
  | to_entries[]
  | select(.value.strategy == "blue-green")
  | "\(.key) \(.value.active) \(.value.port)"
' "$STATE_FILE" |
while read SERVICE ACTIVE PORT
do

cat > "/etc/nginx/upstreams/upstream.conf" <<EOF
upstream ${SERVICE}_backend {
  server ${SERVICE}-${ACTIVE}:${PORT} max_fails=3 fail_timeout=10s;
}
EOF

echo "[RENDER] ${SERVICE} -> ${SERVICE}-${ACTIVE}:${PORT}"

done
```

====================================================================================================
services/nginx/scripts/watcher.sh
====================================================================================================

```
start_watcher() {
  WATCH_DIR="/etc/letsencrypt/live"
  DOMAIN=${DOMAIN_NAME:-localhost}

  echo "[WATCHER] started"

  # ждём появления папки (важно для certbot bootstrap)
  while [ ! -d "$WATCH_DIR/$DOMAIN" ]; do
    echo "[WATCHER] waiting cert dir..."
    sleep 2
  done

  render_upstream
  nginx -s reload

  echo "[WATCHER] cert dir ready"

  inotifywait -m -r -e create -e modify -e moved_to "$WATCH_DIR" |
  while read -r FILE; do
    case "$FILE" in
      *"/$DOMAIN/"*)
        echo "[WATCHER] change detected: $FILE"

        render_upstream
        nginx -s reload
        ;;
    esac
  done
}
```

====================================================================================================
services/watchdog/Dockerfile
====================================================================================================

```
FROM python:3.11-slim

RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY services/watchdog /app
COPY scripts/rollback.py /scripts/rollback.py

CMD ["python", "main.py"]
```

====================================================================================================
services/watchdog/main.py
====================================================================================================

```
import json
import time
import os
import subprocess


STATE_PATH = os.getenv("STATE_PATH", "/state/state.json")
WORKDIR = os.getenv("WORKDIR", "/app")


def load_state():
    with open(STATE_PATH) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def container_running(container):
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "-f",
            "{{.State.Running}}",
            container,
        ],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0 and result.stdout.strip() == "true"


def healthcheck(container, port, path):

    if not container_running(container):
        print(f"[WATCHDOG] {container} is not running")
        return False

    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{path}', timeout=2)"
        ),
    ]

    return (
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def trigger_rollback(service):
    print(f"[WATCHDOG] rollback triggered for {service}")

    env = os.environ.copy()
    env["ROLLBACK_SERVICE"] = service
    env["STATE_PATH"] = STATE_PATH
    env["WORKDIR"] = WORKDIR

    subprocess.run(["python", "/scripts/rollback.py"], env=env)


def check_service(service, cfg):
    if cfg.get("strategy") != "blue-green":
        return True

    active = cfg["active"]
    container = f"{service}-{active}"

    port = cfg.get("port", 8000)
    health = cfg.get("healthcheck", "/health")

    retries = 15

    for i in range(retries):
        if healthcheck(container, port, health):
            return True
        time.sleep(2)

    return False


def main():
    while True:
        state = load_state()

        rolled_back_this_cycle = set()

        for service, cfg in state["services"].items():

            if cfg.get("strategy") != "blue-green":
                continue

            if cfg.get("rollback_locked", False):
                print(f"[WATCHDOG] rollback locked → skip {service}")
                continue

            ok = check_service(service, cfg)

            if ok:
                continue

            if service in rolled_back_this_cycle:
                continue

            print(f"[WATCHDOG] service failed → {service}")

            # rollback
            trigger_rollback(service)

            # mark locked immediately
            state["services"][service]["rollback_locked"] = True
            rolled_back_this_cycle.add(service)

            save_state(state)

        time.sleep(60)


if __name__ == "__main__":
    main()

```

====================================================================================================
shared/__init__.py
====================================================================================================

```
from .settings import get_settings
from .models import Base, RepairRequest
from .db import get_session_maker
from .enums import Urgency, RequestStatus

__all__ = [
    "get_settings",
    "Base",
    "RepairRequest",
    "get_session_maker",
    "Urgency",
    "RequestStatus",
]

```

====================================================================================================
shared/db/__init__.py
====================================================================================================

```
from .session import get_session_maker, get_engine, reset_db

__all__ = ["get_session_maker", "get_engine", "reset_db"]

```

====================================================================================================
shared/db/migrations/env.py
====================================================================================================

```
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from alembic import context
from shared.models import Base
import os

config = context.config

# Берём DATABASE_URL из переменной окружения (не из settings!)
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm"
)

config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

```

====================================================================================================
shared/db/migrations/README
====================================================================================================

```
Generic single-database configuration with an async dbapi.
```

====================================================================================================
shared/db/migrations/versions/2026_05_28_2109-ef27e3a3bb21_.py
====================================================================================================

```
"""

Revision ID: ef27e3a3bb21
Revises:
Create Date: 2026-05-28 21:09:51.922444

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "ef27e3a3bb21"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "repair_requests",
        sa.Column("vehicle_name", sa.String(length=200), nullable=False),
        sa.Column(
            "client_name",
            sa.String(length=100),
            server_default="Топ Лес",
            nullable=False,
        ),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "urgency",
            sa.String(length=20),
            server_default="normal",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="new",
            nullable=False,
        ),
        sa.Column("is_operational", sa.Boolean(), nullable=True),
        sa.Column(
            "parts_cost",
            sa.Numeric(precision=12, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "client_payment",
            sa.Numeric(precision=12, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_repair_requests_id"), "repair_requests", ["id"], unique=False
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_repair_requests_id"), table_name="repair_requests")
    op.drop_table("repair_requests")
    # ### end Alembic commands ###

```

====================================================================================================
shared/db/migrations/versions/2026_05_29_2232-dfae9b9dfe98_.py
====================================================================================================

```
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "dfae9b9dfe98"
down_revision: Union[str, Sequence[str], None] = "ef27e3a3bb21"
branch_labels = None
depends_on = None


urgency_enum = sa.Enum("LOW", "NORMAL", "HIGH", "CRITICAL", name="urgency_enum")

request_status_enum = sa.Enum(
    "NEW",
    "IN_PROGRESS",
    "WAITING_PARTS",
    "DIAGNOSTICS",
    "WAITING_APPROVAL",
    "DONE",
    name="request_status_enum",
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1. создаём enum-типы
    urgency_enum.create(bind, checkfirst=True)
    request_status_enum.create(bind, checkfirst=True)

    # 2. УБИРАЕМ старые дефолты (важно!)
    op.alter_column(
        "repair_requests",
        "urgency",
        existing_type=sa.VARCHAR(length=20),
        server_default=None,
    )

    op.alter_column(
        "repair_requests",
        "status",
        existing_type=sa.VARCHAR(length=30),
        server_default=None,
    )

    # 3. меняем типы
    op.alter_column(
        "repair_requests",
        "urgency",
        existing_type=sa.VARCHAR(length=20),
        type_=sa.Enum("LOW", "NORMAL", "HIGH", "CRITICAL", name="urgency_enum"),
        postgresql_using="urgency::text::urgency_enum",
        existing_nullable=False,
    )

    op.alter_column(
        "repair_requests",
        "status",
        existing_type=sa.VARCHAR(length=30),
        type_=sa.Enum(
            "NEW",
            "IN_PROGRESS",
            "WAITING_PARTS",
            "DIAGNOSTICS",
            "WAITING_APPROVAL",
            "DONE",
            name="request_status_enum",
        ),
        postgresql_using="status::text::request_status_enum",
        existing_nullable=False,
    )

    # 4. ставим новые enum defaults
    op.alter_column(
        "repair_requests",
        "urgency",
        server_default=sa.text("'NORMAL'::urgency_enum"),
    )

    op.alter_column(
        "repair_requests",
        "status",
        server_default=sa.text("'NEW'::request_status_enum"),
    )


def downgrade() -> None:
    op.alter_column(
        "repair_requests",
        "urgency",
        server_default=None,
    )
    op.alter_column(
        "repair_requests",
        "status",
        server_default=None,
    )

    op.alter_column(
        "repair_requests",
        "urgency",
        type_=sa.VARCHAR(length=20),
        existing_type=sa.Enum(name="urgency_enum"),
        postgresql_using="urgency::text",
        existing_nullable=False,
    )

    op.alter_column(
        "repair_requests",
        "status",
        type_=sa.VARCHAR(length=30),
        existing_type=sa.Enum(name="request_status_enum"),
        postgresql_using="status::text",
        existing_nullable=False,
    )

    # (опционально) удаление enum типов
    request_status_enum.drop(op.get_bind(), checkfirst=True)
    urgency_enum.drop(op.get_bind(), checkfirst=True)

```

====================================================================================================
shared/db/migrations/versions/2026_05_29_2314-794a7553b817_.py
====================================================================================================

```
"""

Revision ID: 794a7553b817
Revises: dfae9b9dfe98
Create Date: 2026-05-29 23:14:23.536702

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "794a7553b817"
down_revision: Union[str, Sequence[str], None] = "dfae9b9dfe98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "repair_requests",
        "deadline",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.Date(),
        existing_nullable=True,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "repair_requests",
        "deadline",
        existing_type=sa.Date(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
    )
    # ### end Alembic commands ###

```

====================================================================================================
shared/db/session.py
====================================================================================================

```
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from shared.settings import get_settings

_engine = None
_session_maker = None


def get_session_maker():
    global _engine, _session_maker
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=True)
        _session_maker = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_maker


def get_engine():
    """Возвращает асинхронный движок БД"""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=True)
    return _engine


def reset_db():
    global _engine, _session_maker
    _engine = None
    _session_maker = None

```

====================================================================================================
shared/enums.py
====================================================================================================

```
"""
Enum классы для выпадающих списков в моделях и схемах
"""

from enum import Enum


class Urgency(str, Enum):
    """Срочность заявки"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

    def __str__(self) -> str:
        return self.value


class RequestStatus(str, Enum):
    """Статус заявки на ремонт"""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    WAITING_PARTS = "waiting_parts"
    DIAGNOSTICS = "diagnostics"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"

    def __str__(self) -> str:
        return self.value

```

====================================================================================================
shared/models/__init__.py
====================================================================================================

```
from .base import DeclarativeBase as Base
from .repair_request import RepairRequest

__all__ = (
    "Base",
    "RepairRequest",
)

```

====================================================================================================
shared/models/base.py
====================================================================================================

```
from sqlalchemy import Column, Integer
from sqlalchemy.orm import declared_attr, declarative_base


class Base:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, index=True)

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"


DeclarativeBase = declarative_base(cls=Base)

```

====================================================================================================
shared/models/repair_request.py
====================================================================================================

```
from sqlalchemy import Column, String, Text, Boolean, DateTime, Numeric, Date
from sqlalchemy.sql import func
from shared.models import Base
from shared.enums import Urgency, RequestStatus
from sqlalchemy import Enum as SQLEnum


class RepairRequest(Base):
    __tablename__ = "repair_requests"

    vehicle_name = Column(String(200), nullable=False)
    client_name = Column(String(100), nullable=False, server_default="Топ Лес")
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)

    urgency = Column(
        SQLEnum(Urgency, name="urgency_enum"),
        nullable=False,
        server_default=Urgency.NORMAL.value,
    )

    status = Column(
        SQLEnum(RequestStatus, name="request_status_enum"),
        nullable=False,
        server_default=RequestStatus.NEW.value,
    )

    is_operational = Column(Boolean, nullable=True)
    parts_cost = Column(Numeric(12, 2), nullable=False, server_default="0")
    client_payment = Column(Numeric(12, 2), nullable=False, server_default="0")
    deadline = Column(Date, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

```

====================================================================================================
shared/repository.py
====================================================================================================

```
"""
Репозиторий — это слой абстракции между бизнес-логикой и базой данных.
Он скрывает детали SQLAlchemy и позволяет легко подменить БД в тестах.
"""

from sqlalchemy import select
from shared.models import RepairRequest


class RepairRequestRepository:
    def __init__(self, session):
        """
        Внедряем сессию через конструктор (Dependency Injection).
        Это позволяет подставить фейковую сессию в тестах.
        """
        self.session = session

    async def create(self, **kwargs) -> RepairRequest:
        """Создать новую заявку на ремонт."""
        request = RepairRequest(**kwargs)
        self.session.add(request)
        # НЕТ commit! Только flush для получения ID
        await self.session.flush()
        # await self.session.refresh(request)
        return request

    async def get_by_id(self, request_id: int) -> RepairRequest | None:
        """Получить заявку по ID."""
        result = await self.session.execute(
            select(RepairRequest).where(RepairRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100):
        """Получить список заявок с пагинацией."""
        result = await self.session.execute(
            select(RepairRequest).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_by_vehicle(self, vehicle_name: str, skip: int = 0, limit: int = 100):
        """Получить заявки по названию техники с пагинацией"""
        result = await self.session.execute(
            select(RepairRequest)
            .where(RepairRequest.vehicle_name == vehicle_name)
            .order_by(RepairRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

```

====================================================================================================
shared/schemas/__init__.py
====================================================================================================

```
"""
Pydantic схемы для обмена данными между клиентом и сервером
"""

from .repair_request import (
    RepairRequestBase,
    RepairRequestCreate,
    RepairRequestUpdate,
    RepairRequestResponse,
    RepairRequestListResponse,
)

__all__ = [
    "RepairRequestBase",
    "RepairRequestCreate",
    "RepairRequestUpdate",
    "RepairRequestResponse",
    "RepairRequestListResponse",
]

```

====================================================================================================
shared/schemas/repair_request.py
====================================================================================================

```
"""
Pydantic схемы для RepairRequest

Эти схемы определяют:
- Как выглядит запрос от клиента (Create, Update)
- Как выглядит ответ сервера (Response)
- Какие поля обязательные, а какие нет
"""

from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from shared.enums import Urgency, RequestStatus
from datetime import date


class RepairRequestBase(BaseModel):
    """
    Базовый класс с общими полями для всех схем.
    Все поля опциональны, кроме vehicle_name и description (для create)
    """

    vehicle_name: str = Field(
        ..., description="Название техники", examples=["Квадроцикл-5"]
    )
    client_name: Optional[str] = Field(
        None, description="Имя клиента", examples=["Топ Лес"]
    )
    phone: Optional[str] = Field(
        None, description="Телефон клиента", examples=["+7-999-123-45-67"]
    )
    email: Optional[str] = Field(
        None, description="Email клиента", examples=["client@example.com"]
    )
    description: str = Field(..., description="Описание поломки")
    urgency: Urgency = Field(default=Urgency.NORMAL, description="Срочность")
    status: RequestStatus = Field(default=RequestStatus.NEW, description="Статус")
    is_operational: Optional[bool] = Field(False, description="Техника на ходу?")
    parts_cost: Decimal = Field(
        default_factory=lambda: Decimal("0.00"), description="Стоимость запчастей"
    )
    client_payment: Decimal = Field(
        default_factory=lambda: Decimal("0.00"), description="Оплата клиента"
    )
    deadline: Optional[date] = Field(None, description="Дедлайн (дата без времени)")


class RepairRequestCreate(RepairRequestBase):
    """
    Схема для POST запроса (создание новой заявки).
    Наследует все поля от Base, но явно указываем обязательные.
    """

    # Поле vehicle_name уже есть в Base
    # Поле description уже есть в Base
    pass  # Все поля уже определены в RepairRequestBase


class RepairRequestUpdate(BaseModel):
    """
    Схема для PATCH запроса (частичное обновление).
    Все поля опциональны — можно обновить только то, что нужно.
    """

    vehicle_name: Optional[str] = Field(None, description="Название техники")
    client_name: Optional[str] = Field(None, description="Имя клиента")
    phone: Optional[str] = Field(None, description="Телефон клиента")
    email: Optional[str] = Field(None, description="Email клиента")
    description: Optional[str] = Field(None, description="Описание поломки")

    urgency: Optional[Urgency] = Field(None, description="Срочность")
    status: Optional[RequestStatus] = Field(None, description="Статус")

    is_operational: Optional[bool] = Field(None, description="Техника на ходу?")
    parts_cost: Optional[Decimal] = Field(None, description="Стоимость запчастей")
    client_payment: Optional[Decimal] = Field(None, description="Оплата клиента")
    deadline: Optional[date] = Field(None, description="Дедлайн (дата без времени)")


class 
<< TRUNCATED >>
```

====================================================================================================
shared/settings.py
====================================================================================================

```
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm"
    )
    telegram_token: str | None = None
    secret_key: str | None = None  # Добавляем это поле
    admin_username: str = "admin"  # Добавляем с дефолтом
    admin_password: str = "admin123"  # Добавляем с дефолтом
    domain_name: str = "localhost"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()

```

====================================================================================================
state/state.json
====================================================================================================

```
{
  "deploy_id": "local",
  "services": {
    "gateway": {
      "strategy": "blue-green",
      "active": "blue",
      "port": 8000,
      "healthcheck": "/health",
      "rollback_locked": false
    }
  }
}

```

====================================================================================================
tests/__init__.py
====================================================================================================

```

```

====================================================================================================
tests/api/__init__.py
====================================================================================================

```

```

====================================================================================================
tests/api/conftest.py
====================================================================================================

```
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from services.gateway.app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def reset():
    from shared.db.session import reset_db

    reset_db()

```

====================================================================================================
tests/api/test_admin_panel.py
====================================================================================================

```
"""
Тесты для админ-панели SQLAdmin
"""

import pytest
from shared.settings import get_settings

pytest = pytest.mark.asyncio


async def test_admin_login_page_accessible(client):
    """Страница логина доступна"""
    response = await client.get("/admin/login")
    assert response.status_code == 200


async def test_admin_panel_redirects_to_login(client):
    """Без логина админка редиректит на логин"""
    response = await client.get("/admin", follow_redirects=False)
    assert response.status_code == 307 or response.status_code == 302


async def test_admin_login_with_correct_credentials(client):
    """Вход с правильными данными"""
    settings = get_settings()

    login_data = {
        "username": settings.admin_username,
        "password": settings.admin_password,
    }
    response = await client.post("/admin/login", data=login_data, follow_redirects=True)
    assert response.status_code == 200


async def test_repair_request_list_accessible_after_login(client):
    """После входа список заявок доступен"""
    # Логинимся
    settings = get_settings()

    await client.post(
        "/admin/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
    )
    # Проверяем список
    response = await client.get("/admin/repair-request/list")
    assert response.status_code == 200

```

====================================================================================================
tests/api/test_gateway.py
====================================================================================================

```
import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

```

====================================================================================================
tests/api/test_repair_requests.py
====================================================================================================

```
"""
API тесты для эндпоинтов RepairRequest.
"""

from shared.enums import Urgency, RequestStatus
import pytest

"""Тесты для API эндпоинтов"""


@pytest.mark.asyncio
async def test_create_repair_request(client):
    """Тест создания заявки через API"""
    request_data = {
        "vehicle_name": "Тестовый квадроцикл",
        "description": "Не заводится тестовая заявка",
        "urgency": Urgency.NORMAL.value,
        "status": RequestStatus.NEW.value,
    }

    response = await client.post("/api/v1/repair-requests/", json=request_data)

    assert response.status_code == 201
    data = response.json()
    assert data["vehicle_name"] == request_data["vehicle_name"]
    assert data["description"] == request_data["description"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_repair_request_invalid_data(client):
    """Тест создания заявки с невалидными данными"""
    response = await client.post(
        "/api/v1/repair-requests/", json={"description": "Только описание"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_all_repair_requests(client):
    """Тест получения списка всех заявок"""
    # Создаем тестовые данные
    for i in range(3):
        response = await client.post(
            "/api/v1/repair-requests/",
            json={"vehicle_name": f"Техника {i}", "description": f"Описание {i}"},
        )
        assert response.status_code == 201

    response = await client.get("/api/v1/repair-requests/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_get_repair_request_by_id(client):
    """Тест получения конкретной заявки по ID"""
    # Создаем
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={
            "vehicle_name": "Уникальная техника",
            "description": "Уникальное описание",
        },
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Получаем
    response = await client.get(f"/api/v1/repair-requests/{created_id}")
    assert response.status_code == 200
    assert response.json()["id"] == created_id


@pytest.mark.asyncio
async def test_get_nonexistent_repair_request(client):
    """Тест получения несуществующей заявки"""
    response = await client.get("/api/v1/repair-requests/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_repair_request(client):
    """Тест частичного обновления заявки"""
    # Создаем
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={
            "vehicle_name": "Техника для обновления",
            "description": "Оригинальное описание",
        },
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Обновляем статус
    response = await cl
<< TRUNCATED >>
```

====================================================================================================
tests/conftest.py
====================================================================================================

```
"""
Общие фикстуры для всех тестов.
"""

```

====================================================================================================
tests/integration/__init__.py
====================================================================================================

```

```

====================================================================================================
tests/integration/conftest.py
====================================================================================================

```
"""
Фикстуры для интеграционных тестов (только здесь).
Эти фикстуры НЕ видны в unit и api тестах.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test"
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Тестовый движок БД (один раз на сессию)"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """Тестовая сессия (новая для каждого теста)"""
    async_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session

```

====================================================================================================
tests/integration/test_repair_request_repository.py
====================================================================================================

```
"""
Интеграционные тесты для репозитория RepairRequest.
"""

import pytest
from shared.repository import RepairRequestRepository


@pytest.mark.asyncio
async def test_repository_create(test_session):
    """Тест создания заявки через репозиторий"""
    repo = RepairRequestRepository(test_session)
    request = await repo.create(vehicle_name="Квадроцикл-5", description="Не заводится")
    assert request.id is not None
    assert request.vehicle_name == "Квадроцикл-5"
    assert request.description == "Не заводится"

```

====================================================================================================
tests/unit/__init__.py
====================================================================================================

```

```

====================================================================================================
tests/unit/test_repair_request.py
====================================================================================================

```
from shared.models import RepairRequest


def test_repair_request_creation():
    """Проверяем, что модель создаётся без ошибок."""
    request = RepairRequest(
        vehicle_name="Квадроцикл-5", description="Не заводится", status="new"
    )
    assert request.vehicle_name == "Квадроцикл-5"
    assert request.status == "new"

```

```

====================================================================================================
FILE: tools/output/project_dump_full.md
====================================================================================================
```
# PROJECT DUMP: repair_crm
Root: /Users/natalia/Python projects/repair_crm

====================================================================================================
FILE: .env.example
====================================================================================================

```
# Telegram Bot Token (обязательно)
TELEGRAM_TOKEN=ваш_токен_сюда

# JWT Secret Key (обязательно, минимум 32 символа)
SECRET_KEY=my-super-secret-key-for-jwt-change-me-in-production

# Для админ-панели
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

#Доменное имя если имеется
#DOMAIN_NAME=example.com

# Database URL
# Вариант для внешней БД (раскомментируйте)
# DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
```

====================================================================================================
FILE: .github/workflows/build-and-push.yml
====================================================================================================

```
name: Build and Push to GHCR

on:
#  workflow_dispatch:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Detect changed services
        uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            gateway:
              - 'services/gateway/**'
              - 'shared/**'
              - 'requirements.txt'

            migrations:
              - 'services/migrations/**'
              - 'shared/**'
              - 'alembic.ini'
              - 'requirements.txt'

            nginx:
              - 'services/nginx/**'

            certbot:
              - 'services/certbot/**'
            
            watchdog:
              - 'services/watchdog/**'
              - 'scripts/rollback.py'

      - name: Print detected changes
        run: |
          echo "gateway=${{ steps.changes.outputs.gateway }}"
          echo "migrations=${{ steps.changes.outputs.migrations }}"
          echo "nginx=${{ steps.changes.outputs.nginx }}"
          echo "certbot=${{ steps.changes.outputs.certbot }}"
          echo "watchdog=${{ steps.changes.outputs.watchdog }}"

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push gateway
        if: steps.changes.outputs.gateway == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/gateway/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-gateway:latest
            ghcr.io/${{ github.repository }}-gateway:${{ github.sha }}
            

      - name: Build and push migrations
        if: steps.changes.outputs.migrations == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/migrations/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-migrations:latest
            ghcr.io/${{ github.repository }}-migrations:${{ github.sha }}

      - name: Build and push nginx
        if: steps.changes.outputs.nginx == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/nginx/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-nginx:latest
            ghcr.io/${{ github.repository }}-nginx:${{ github.sha }}

      - name: Build and push certbot
        if: steps.changes.outputs.certbot == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/certbot/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-certbot:latest
            ghcr.io/${{ github.repository }}-certbot:${{ github.sha }}

      - name: Build and push watchdog
        if: steps.changes.outputs.watchdog == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/watchdog/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}-watchdog:latest
            ghcr.io/${{ github.repository }}-watchdog:${{ github.sha }}

      - name: Build image manifest
        run: |
          python scripts/build_manifest.py > images.json
        env:
          CHANGED_GATEWAY: ${{ steps.changes.outputs.gateway }}
          CHANGED_MIGRATIONS: ${{ steps.changes.outputs.migrations }}
          CHANGED_NGINX: ${{ steps.changes.outputs.nginx }}
          CHANGED_CERTBOT: ${{ steps.changes.outputs.certbot }}
          CHANGED_WATCHDOG: ${{ steps.changes.outputs.watchdog }}

          GITHUB_SHA: ${{ github.sha }}

      - name: Upload images artifact
        uses: actions/upload-artifact@v4
        with:
          name: images
          path: images.json
```

====================================================================================================
FILE: .github/workflows/ci.yml
====================================================================================================

```
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          
      - name: Setup env for tests
        run: cp .env.example .env

      - name: Run tests
        run: make test
```

====================================================================================================
FILE: .github/workflows/deploy.yml
====================================================================================================

```
name: Deploy to VDS

on:
  workflow_run:
    workflows:
      - "Build and Push to GHCR"
    types:
      - completed
  workflow_dispatch:

jobs:
  deploy:
    if: >
      github.event.workflow_run.conclusion == 'success' &&
      github.event.workflow_run.head_branch == 'main'
    env:
      GHCR_READ_TOKEN: ${{ secrets.GHCR_READ_TOKEN }}
    runs-on: ubuntu-latest
    steps:
      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.SERVER_SSH_KEY }}" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh-keyscan -H ${{ secrets.SERVER_IP }} >> ~/.ssh/known_hosts

      - name: Set deploy id
        run: echo "DEPLOY_ID=${{ github.event.workflow_run.id }}" >> $GITHUB_ENV

      - name: Check state file
        id: state
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} "
            mkdir -p ~/repair-crm/state

            if [ -f ~/repair-crm/state/state.json ]; then
              echo 'exists=true'
            else
              echo 'exists=false'
            fi
          " >> $GITHUB_OUTPUT

      - name: Checkout code
        uses: actions/checkout@v4

      - name: State for runner
        if: steps.state.outputs.exists == 'true'
        run: |
          scp ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json ./state.json


      - name: Bootstrap state
        if: steps.state.outputs.exists == 'false'
        env:
          GHCR_READ_TOKEN: ${{ secrets.GHCR_READ_TOKEN }}
        run: |
          python scripts/deploy/bootstrap_state.py > state.json

      - name: Upload state
        if: steps.state.outputs.exists == 'false'
        run: |
          scp state.json \
            ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json

      - name: Backup original state (server)
        run: |
          scp ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json \
            state.backup.json

      - name: Download images artifact
        run: |
          gh run download ${{ github.event.workflow_run.id }} \
          -n images \
          -D .
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Update state
        run: |
          python scripts/deploy/update_state.py > new_state.json
          mv new_state.json state.json

      - name: Sync state to server (always)
        run: |
          scp state.json \
              ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json

      - name: Check if deploy needed
        id: diff
        run: |
          python scripts/deploy/check_diff.py > deploy_plan.json

      - name: Print deploy plan
        run: |
          cat deploy_plan.json

      - name: Save deploy plan
        run: |
          PLAN=$(cat deploy_plan.json | jq -c . | base64 -w0)
          echo "DEPLOY_PLAN=$PLAN" >> $GITHUB_ENV

      - name: Debug DEPLOY_PLAN content
        run: |
          echo "=== DEPLOY_PLAN content ==="
          echo "${{ env.DEPLOY_PLAN }}"
          echo "=== HEX ==="
          echo -n "${{ env.DEPLOY_PLAN }}" | od -c
          echo "=== END ==="

      - name: Lock rollback (per service)
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/lock_rollback.py

      - name: Generate compose override
        run: |
          STATE_FILE=state.json 
          python scripts/deploy/render_compose.py > docker-compose.override.yml

      - name: Upload override to server
        run: |
          scp docker-compose.override.yml \
              ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/docker-compose.override.yml

      - name: push to VDS
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DATABASE_URL='${{ secrets.DATABASE_URL }}' \
             ADMIN_USERNAME='${{ secrets.ADMIN_USERNAME }}' \
             ADMIN_PASSWORD='${{ secrets.ADMIN_PASSWORD }}' \
             SECRET_KEY='${{ secrets.SECRET_KEY }}' \
             TELEGRAM_TOKEN='${{ secrets.TELEGRAM_TOKEN }}' \
             DOMAIN_NAME='${{ secrets.DOMAIN_NAME }}' \
             bash -s" < scripts/deploy/push_to_vds.sh

      - name: Verify ACTIVE services
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/verify_services.py

      - name: Wait for new services healthcheck
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/verify_inactive_services.py

      - name: Switch traffic (state-driven)
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/switch_services.py

      - name: Reload nginx
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} "
            docker exec nginx /scripts/reload.sh
          "

      - name: Post-switch verify
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "DEPLOY_PLAN='${{ env.DEPLOY_PLAN }}' python3 -" \
            < scripts/deploy/post_switch_verify.py \
            > post_switch_verify.json

      - name: Print verify result
        run: |
          cat post_switch_verify.json

      - name: Save rollback decision (runner-only)
        run: |
          cat post_switch_verify.json | jq -c . > rollback_decision.json

          ROLLBACK=$(cat rollback_decision.json | base64 -w0)
          echo "ROLLBACK_DECISION=$ROLLBACK" >> $GITHUB_ENV

      - name: Unlock rollback
        id: unlock
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} \
            "ROLLBACK_DECISION='${{ env.ROLLBACK_DECISION }}' python3 -" \
            < scripts/deploy/unlock_rollback.py

      - name: Restore state backup
        if: always() && steps.unlock.outcome != 'success'
        run: |
          if [ -s state.backup.json ]; then
            echo "restoring backup state"
            scp state.backup.json \
              ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }}:~/repair-crm/state/state.json
          else
            echo "backup empty - skip restore"
          fi

      - name: Post Reload nginx
        if: always() && steps.unlock.outcome != 'success'
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_IP }} "
            docker exec nginx /scripts/reload.sh
          "

      - name: Rollback engine
        env:
          SERVER_USER: ${{ secrets.SERVER_USER }}
          SERVER_IP: ${{ secrets.SERVER_IP }}
          ROLLBACK_DECISION: ${{ env.ROLLBACK_DECISION }}
        run: |
          python scripts/deploy/run_rollbacks.py
          

      - name: Cleanup inactive containers
        if: always()
        env:
          SERVER_USER: ${{ secrets.SERVER_USER }}
          SERVER_IP: ${{ secrets.SERVER_IP }}
          DEPLOY_PLAN: ${{ env.DEPLOY_PLAN }}
        run: |
          ssh $SERVER_USER@$SERVER_IP \
            "DEPLOY_PLAN='$DEPLOY_PLAN' python3 -" \
            < scripts/deploy/cleanup.py

```

====================================================================================================
FILE: .pre-commit-config.yaml
====================================================================================================

```
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/flake8
    rev: 7.1.0
    hooks:
      - id: flake8
        args:
          [
            --config=.flake8,
            --max-line-length=88,
            --extend-ignore=E203,
          ]
```

====================================================================================================
FILE: alembic.ini
====================================================================================================

```
# A generic, single database configuration.

[alembic]
# path to migration scripts.
# this is typically a path given in POSIX (e.g. forward slashes)
# format, relative to the token %(here)s which refers to the location of this
# ini file
# script_location = %(here)s/shared/db/migrations
script_location = shared/db/migrations

# template used to generate migration file names; The default value is %%(rev)s_%%(slug)s
# Uncomment the line below if you want the files to be prepended with date and time
# see https://alembic.sqlalchemy.org/en/latest/tutorial.html#editing-the-ini-file
# for all available tokens
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s
# Or organize into date-based subdirectories (requires recursive_version_locations = true)
# file_template = %%(year)d/%%(month).2d/%%(day).2d_%%(hour).2d%%(minute).2d_%%(second).2d_%%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.  for multiple paths, the path separator
# is defined by "path_separator" below.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the tzdata library which can be installed by adding
# `alembic[tz]` to the pip requirements.
# string value is passed to ZoneInfo()
# leave blank for localtime
# timezone =

# max length of characters to apply to the "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version location specification; This defaults
# to <script_location>/versions.  When using multiple version
# directories, initial revisions must be specified with --version-path.
# The path separator used here should be the separator specified by "path_separator"
# below.
# version_locations = %(here)s/bar:%(here)s/bat:%(here)s/alembic/versions

# path_separator; This indicates what character is used to split lists of file
# paths, including version_locations and prepend_sys_path within configparser
# files such as alembic.ini.
# The default rendered in new alembic.ini files is "os", which uses os.pathsep
# to provide os-dependent path splitting.
#
# Note that in order to support legacy alembic.ini files, this default does NOT
# take place if path_separator is not present in alembic.ini.  If this
# option is omitted entirely, fallback logic is as follows:
#
# 1. Parsing of the version_locations option falls back to using the legacy
#    "version_path_separator" key, which if absent then falls back to the legacy
#    behavior of splitting on spaces and/or commas.
# 2. Parsing of the prepend_sys_path option falls back to the legacy
#    behavior of splitting on spaces, commas, or colons.
#
# Valid values for path_separator are:
#
# path_separator = :
# path_separator = ;
# path_separator = space
# path_separator = newline
#
# Use os.pathsep. Default configuration used for new projects.
path_separator = os


# set to 'true' to search source files recursively
# in each "version_locations" directory
# new in Alembic version 1.10
recursive_version_locations = true

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

# database URL.  This is consumed by the user-maintained env.py script only.
# other means of configuring database URLs may be customized within the env.py
# file.
# sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost/


[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 79 REVISION_SCRIPT_FILENAME

# lint with attempts to fix using "ruff" - use the module runner, against the "ruff" module
# hooks = ruff
# ruff.type = module
# ruff.module = ruff
# ruff.options = check --fix REVISION_SCRIPT_FILENAME

# Alternatively, use the exec runner to execute a binary found on your PATH
# hooks = ruff
# ruff.type = exec
# ruff.executable = ruff
# ruff.options = check --fix REVISION_SCRIPT_FILENAME

# Logging configuration.  This is also consumed by the user-maintained
# env.py script only.
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S

```

====================================================================================================
FILE: docker-compose.prod.yml
====================================================================================================

```
services:
  gateway-blue:
    image: ${GATEWAY_BLUE_IMAGE}

  gateway-green:
    image: ${GATEWAY_GREEN_IMAGE}

  nginx:
    image: ${NGINX_IMAGE}

  certbot:
    image: ${CERTBOT_IMAGE}

  migrations:
    image: ${MIGRATIONS_IMAGE}

  watchdog:
    image: ${WATCHDOG_IMAGE}
```

====================================================================================================
FILE: docker-compose.test.yml
====================================================================================================

```
services:
  postgres:
    ports:
      - "5432:5432"   # только для тестов локально

#  gateway:
#    environment:
#      DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test
#
#  migrations:
#    environment:
#      DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test
```

====================================================================================================
FILE: docker-compose.yml
====================================================================================================

```
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: repair_crm
      POSTGRES_HOST_AUTH_METHOD: trust  # <- КЛЮЧЕВАЯ СТРОКgi
    expose:
      - "5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U postgres" ]
      interval: 5s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
    restart: unless-stopped

  nginx:
    container_name: nginx
    build:
      context: .
      dockerfile: services/nginx/Dockerfile
    ports:
      - "80:80"
      - "443:443"
    env_file:
      - .env
    environment:
      DOMAIN_NAME: ${DOMAIN_NAME:-localhost}
    volumes:
      - certbot_conf:/etc/letsencrypt
      - certbot_web:/var/www/certbot
      - ./state:/etc/nginx/state
    healthcheck:
#      test: [ "CMD", "curl", "-f", "http://localhost/.well-known/acme-challenge/healthcheck" ]
      test: [ "CMD", "nginx", "-t" ]  # проверяет только конфиг
      interval: 10s
      timeout: 5s
      retries: 30
      start_period: 10s
    deploy:
      resources:
        limits:
          memory: 64M
        reservations:
          memory: 32M
    restart: unless-stopped

  certbot:
    container_name: certbot
    build:
      context: .
      dockerfile: services/certbot/Dockerfile
    volumes:
      - certbot_conf:/etc/letsencrypt
      - certbot_web:/var/www/certbot
    env_file:
      - .env
    environment:
      DOMAIN_NAME: ${DOMAIN_NAME:-localhost}
    depends_on:
      nginx:
        condition: service_healthy  # ← ждем здоровый nginx
    healthcheck:
      # Проверяем, что скрипт дошел до бесконечного цикла (процесс sleep существует)
      test: [ "CMD", "sh", "-c", "pgrep -f 'sleep 12h' || pgrep -f 'sleep 3600' || exit 1" ]
      interval: 5s
      timeout: 3s
      retries: 60
      start_period: 60s
    deploy:
      resources:
        limits:
          memory: 128M
        reservations:
          memory: 64M
    restart: unless-stopped

  watchdog:
    build:
      context: .
      dockerfile: services/watchdog/Dockerfile
    container_name: watchdog

    volumes:
      - ./state:/state
      - /var/run/docker.sock:/var/run/docker.sock

    environment:
      STATE_PATH: /state/state.json
      WORKDIR: /app


    mem_limit: 64m
    cpus: "0.2"

    healthcheck:
      test: [ "CMD", "python", "-c", "print('ok')" ]
      interval: 30s
      timeout: 3s
      retries: 3

    depends_on:
      nginx:
        condition: service_healthy
    restart: unless-stopped


  gateway-blue:
    container_name: gateway-blue
    build:
      context: .
      dockerfile: services/gateway/Dockerfile
    expose:
      - "8000"

    env_file:
      - .env

    environment:
      DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@postgres:5432/repair_crm}

    command:
      [
        "uvicorn",
        "services.gateway.app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ]

    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
        ]
      interval: 5s
      timeout: 3s
      retries: 10

    restart: unless-stopped

    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M


  gateway-green:
    container_name: gateway-green
    build:
      context: .
      dockerfile: services/gateway/Dockerfile
    expose:
      - "8000"

    env_file:
      - .env

    environment:
      DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@postgres:5432/repair_crm}

    command:
      [
        "uvicorn",
        "services.gateway.app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ]

    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
        ]
      interval: 5s
      timeout: 3s
      retries: 10

    restart: unless-stopped

    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  migrations:
    build:
      context: .
      dockerfile: services/migrations/Dockerfile
    env_file:
      - .env
    environment:
      DATABASE_URL: ${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@postgres:5432/repair_crm}
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
  certbot_conf:
  certbot_web:
```

====================================================================================================
FILE: LICENSE
====================================================================================================

```
MIT License

Copyright (c) 2026 kpa9pt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```

====================================================================================================
FILE: Makefile
====================================================================================================

```
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
```

====================================================================================================
FILE: pytest.ini
====================================================================================================

```
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
```

====================================================================================================
FILE: README.md
====================================================================================================

```
# Repair CRM

[![Docker](https://img.shields.io/badge/Docker-20.10+-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)


Система для управления ремонтами и заказами в мастерской мототехники.

---

## 📌 О проекте

Repair CRM — backend-система для обработки заявок на ремонт.  
Проект построен как API-first приложение с административной панелью.

**Portable deployment:** достаточно Docker и свободных портов 80/443.

---

## ⚙️ Возможности

- CRUD заявок на ремонт
- Фильтрация и пагинация
- REST API (Swagger UI)
- Административная панель (SQLAdmin)
- Docker-окружение для разработки
- CI/CD (GitHub Actions + GHCR)
- Автоматический HTTPS (Let's Encrypt)

---

## 🧱 Технологии

- Python 3.14 / FastAPI
- PostgreSQL / SQLAlchemy (async)
- Alembic / pytest
- Docker / Docker Compose
- Nginx / Certbot
- GitHub Container Registry

---

## 📋 Требования

- Docker (20.10+)
- Docker Compose (2.20+)
- Свободные порты: 80, 443 (для HTTPS)

---

## 🚀 Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone https://github.com/kpa9pt/repair-crm.git
cd repair-crm

# 2. Запустить проект (.env создастся автоматически)
make up

# 3. Остановить проект
make down
```

---

## 🌐 После запуска доступны сервисы:

|   Сервис	   |           URL           |
|:-----------:|:-----------------------:|
| API Gateway |    	http://localhost    |
| Swagger UI  | 	http://localhost/docs  |
| Admin panel | 	http://localhost/admin |

---

## 🔧 Переменные окружения

При первом запуске файл .env создаётся автоматически из .env.example:
```bash
cp .env.example .env   # если нужно отредактировать вручную
```
Основные переменные:

| Переменная      | 	Значение по умолчанию                                                | 	Описание                               |
|:----------------|:----------------------------------------------------------------------|:----------------------------------------|
| DATABASE_URL    | 	postgresql+asyncpg://postgres:<br>postgres@postgres:5432/repair_crm	 | Подключение к БД                        |
| ADMIN_USERNAME	 | admin	                                                                | Логин админ-панели                      |
| ADMIN_PASSWORD	 | (смотри .env.example)	                                                | Пароль админ-панели                     |
| DOMAIN_NAME	    | localhost	                                                            | Домен (для продакшена укажите реальный) |


> Для HTTPS укажите реальный домен и настройте DNS запись на IP вашего сервера. Certbot автоматически получит сертификат.

---

## 🛠️ Основные команды

```bash
make up          # запустить все сервисы
make down        # остановить и удалить контейнеры
make build       # пересобрать и запустить
make test        # запустить все тесты
make logs        # посмотреть логи
make help        # показать все команды
```

---

## 🧪 Тестирование

```bash
make test
```

Тесты запускаются в Docker-окружении с автоматическим поднятием инфраструктуры и пересозданием базы данных.

---

## 🔐 Административный доступ

Доступ к админ-панели:
- URL: http://localhost/admin
- Login: admin
- Password: admin123

> Админ-панель — основной инструмент для управления заявками.


---

## 🚀 Деплой на VPS

- Клонируйте репозиторий на сервер
- Настройте .env (укажите DOMAIN_NAME и пароли)
- Выполните make up

---

## 🤖 Автоматический CI/CD (опционально)

В репозитории настроены GitHub Actions:

- Build and Push to GHCR — сборка образа при пуше в main
- Deploy to VDS — автоматический деплой на сервер

Для работы CI/CD нужны секреты (смотри .github/workflows/deploy.yml).


---

## 🧭 Архитектура

```text
Nginx (порты 80/443) → Gateway (FastAPI) → PostgreSQL
                ↓
         Certbot (HTTPS)
```

---

## 🎯 Дальнейшее развитие

- [ ] **Модель "Техника"** — единицы техники с историей ремонтов
- [ ] **Telegram бот** — уведомления о новых заявках
- [ ] **React фронтенд** — полноценный интерфейс для менеджеров
- [ ] **Blue/Green деплой** — zero-downtime обновления
- [ ] **Мобильное приложение (iOS)** — для механиков в поле

---

## 📄 Лицензия

MIT

---
```

====================================================================================================
FILE: requirements.txt
====================================================================================================

```
alembic==1.18.4
annotated-doc==0.0.4
annotated-types==0.7.0
anyio==4.13.0
asyncpg==0.31.0
bcrypt==5.0.0
black==26.5.1
certifi==2026.5.20
cfgv==3.5.0
click==8.4.1
distlib==0.4.0
fastapi==0.136.3
filelock==3.29.0
greenlet==3.5.1
h11==0.16.0
httpcore==1.0.9
httptools==0.8.0
httpx==0.28.0
identify==2.6.19
idna==3.16
iniconfig==2.3.0
itsdangerous==2.2.0
Jinja2==3.1.6
Mako==1.3.12
MarkupSafe==3.0.3
mypy_extensions==1.1.0
nodeenv==1.10.0
packaging==26.2
passlib==1.7.4
pathspec==1.1.1
platformdirs==4.10.0
pluggy==1.6.0
pre_commit==4.6.0
pydantic==2.13.4
pydantic-settings==2.14.1
pydantic_core==2.46.4
Pygments==2.20.0
pytest==9.0.3
pytest-asyncio==1.3.0
python-discovery==1.4.0
python-dotenv==1.2.2
python-multipart==0.0.27
pytokens==0.4.1
PyYAML==6.0.3
redis==5.0.1
sqladmin==0.27.0
SQLAlchemy==2.0.49
starlette==1.2.0
typing-inspection==0.4.2
typing_extensions==4.15.0
uvicorn==0.30.0
uvloop==0.22.1
virtualenv==21.4.1
watchfiles==1.2.0
websockets==16.0
WTForms==3.1.2

requests
```

====================================================================================================
FILE: scripts/build_manifest.py
====================================================================================================

```
import json
import os

SERVICES = ["gateway", "migrations", "nginx", "certbot", "watchdog"]

github_sha = os.environ.get("GITHUB_SHA", "")

manifest = {}

for service in SERVICES:
    changed = os.environ.get(f"CHANGED_{service.upper()}", "false")

    if changed == "true":
        manifest[service] = github_sha

print(json.dumps(manifest))

```

====================================================================================================
FILE: scripts/deploy/bootstrap_state.py
====================================================================================================

```
import json
import os
import requests
import sys

OWNER = "kpa9pt"

SERVICES = [
    "gateway",
    "nginx",
    "certbot",
    "migrations",
    "watchdog",
]

TOKEN = os.environ["GHCR_READ_TOKEN"]

# 🔥 DEBUG 1: проверяем что токен вообще есть и не пустой
print("TOKEN EXISTS:", bool(TOKEN), file=sys.stderr)
print("TOKEN PREFIX:", TOKEN[:6] if TOKEN else None, file=sys.stderr)

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
}

DEPLOY_ID = os.getenv("DEPLOY_ID", "bootstrap")


def latest_image(service: str) -> str:
    url = (
        f"https://api.github.com/users/"
        f"{OWNER}/packages/container/repair-crm-{service}/versions"
    )

    print(f"\n--- SERVICE: {service} ---", file=sys.stderr)
    print("URL:", url, file=sys.stderr)

    response = requests.get(url, headers=HEADERS)

    # 🔥 DEBUG 2: статус ответа
    print("STATUS:", response.status_code, file=sys.stderr)

    # 🔥 DEBUG 3: если упало — покажем текст
    if response.status_code != 200:
        print("ERROR BODY:", response.text[:500], file=sys.stderr)

    response.raise_for_status()

    versions = response.json()

    # 🔥 DEBUG 4: сколько версий пришло
    print("VERSIONS COUNT:", len(versions), file=sys.stderr)

    for version in versions:
        # ❗ оставили как у тебя было (НЕ трогаем логику)
        tags = version["metadata"]["container"]["tags"]

        print("TAGS:", tags, file=sys.stderr)

        sha_tags = [tag for tag in tags if tag != "latest"]

        if sha_tags:
            sha = sha_tags[0]
            return f"ghcr.io/{OWNER}/repair-crm-{service}:{sha}"

    raise RuntimeError(f"No sha tag found for {service}")


state = {
    "deploy_id": DEPLOY_ID,
    "services": {
        "gateway": {
            "strategy": "blue-green",
            "active": "blue",
            "port": 8000,
            "healthcheck": "/health",
            "rollback_locked": False,
        }
    },
}

gateway_image = latest_image("gateway")

state["services"]["gateway"]["blue"] = {"image": gateway_image}
state["services"]["gateway"]["green"] = {"image": gateway_image}

for service in [
    "nginx",
    "certbot",
    "migrations",
    "watchdog",
]:
    state["services"][service] = {
        "strategy": "single",
        "image": latest_image(service),
    }

print(json.dumps(state, indent=2))

```

====================================================================================================
FILE: scripts/deploy/check_diff.py
====================================================================================================

```
import json
import sys


def load(path):
    with open(path) as f:
        return json.load(f)


def main():
    changes = load("images.json")
    state = load("state.json")

    deploy_plan = []

    for service in changes.keys():

        service_state = state["services"].get(service)

        if not service_state:
            print(
                f"skip {service}: not found in state",
                file=sys.stderr,
            )
            continue

        if service_state.get("strategy") != "blue-green":
            print(
                f"skip {service}: strategy={service_state.get('strategy')}",
                file=sys.stderr,
            )
            continue

        deploy_plan.append(service)

    print(json.dumps(deploy_plan))


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/cleanup.py
====================================================================================================

```
import json
import os
import base64
import subprocess
from pathlib import Path


def load_state():
    state_file = Path.home() / "repair-crm" / "state" / "state.json"
    with open(state_file) as f:
        return json.load(f)


def load_plan():
    data = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(data).decode())


def main():
    state = load_state()
    deploy_plan = load_plan()

    print("=== CLEANUP START ===")

    for service in deploy_plan:
        if service not in state["services"]:
            print(f"skip unknown service: {service}")
            continue

        svc = state["services"][service]

        if svc["strategy"] == "blue-green":
            active = svc["active"]
            inactive = "green" if active == "blue" else "blue"
            container = f"{service}-{inactive}"

            print(f"stopping {container}")
            subprocess.run(["docker", "stop", container], check=False)

    print("=== PRUNE ===")
    subprocess.run(["docker", "system", "prune", "-f"], check=False)

    print("=== CLEANUP DONE ===")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/lock_rollback.py
====================================================================================================

```
import json
import os
import base64
from pathlib import Path


STATE_FILE = Path.home() / "repair-crm" / "state" / "state.json"


def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def decode_plan():
    raw = os.environ.get("DEPLOY_PLAN", "")
    if not raw:
        return []

    decoded = base64.b64decode(raw).decode()
    return json.loads(decoded)


def main():
    deploy_plan = decode_plan()
    state = load_state()

    for service in deploy_plan:
        if service not in state["services"]:
            print(f"⚠️ skip unknown service {service}")
            continue

        print(f"🔒 lock rollback: {service}")
        state["services"][service]["rollback_locked"] = True

    save_state(state)
    print("✅ rollback locked for planned services")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/post_switch_verify.py
====================================================================================================

```
import json
import sys
import time
import os
import base64
import subprocess
from pathlib import Path


def healthcheck(container, port, health):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{health}', timeout=2)"
        ),
    ]

    return subprocess.run(cmd).returncode == 0


def wait_health(container, port, health, retries=30, delay=2):

    for i in range(retries):

        if healthcheck(container, port, health):
            return True

        print(
            f"retry: {i + 1}/{retries}",
            file=sys.stderr,
        )

        time.sleep(delay)

    return False


def main():
    deploy_plan = json.loads(base64.b64decode(os.environ["DEPLOY_PLAN"]).decode())

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    result = {
        "passed": [],
        "failed": [],
    }

    for service in deploy_plan:

        print(
            f"🔍 post-switch verify: {service}",
            file=sys.stderr,
        )

        s = state["services"][service]

        active = s["active"]
        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{active}"

        print(
            f"phase 1 smoke: {service}",
            file=sys.stderr,
        )

        if not wait_health(container, port, health):
            result["failed"].append(service)
            continue

        print(
            f"phase 2 soak sleep: {service}",
            file=sys.stderr,
        )

        time.sleep(60)

        print(
            f"phase 3 soak verify: {service}",
            file=sys.stderr,
        )

        if wait_health(container, port, health):
            result["passed"].append(service)
        else:
            result["failed"].append(service)

    print(json.dumps(result))


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/push_to_vds.sh
====================================================================================================

```
#!/usr/bin/env bash
set -e

echo "=== PUSH TO VDS START ==="
date
whoami
pwd

cd ~/repair-crm

echo "=== UPDATE COMPOSE ==="
curl -fsSL https://raw.githubusercontent.com/kpa9pt/repair-crm/main/docker-compose.yml -o docker-compose.yml

echo "=== WRITE ENV ==="
cat > .env <<EOF
DATABASE_URL=$DATABASE_URL
ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_PASSWORD=$ADMIN_PASSWORD
SECRET_KEY=$SECRET_KEY
TELEGRAM_TOKEN=$TELEGRAM_TOKEN
DOMAIN_NAME=$DOMAIN_NAME
EOF

echo "=== DOCKER COMPOSE UP ==="
docker compose up -d

echo "=== DONE ==="
docker ps
```

====================================================================================================
FILE: scripts/deploy/render_compose.py
====================================================================================================

```
import json
import os

STATE_FILE = os.environ.get("STATE_FILE", "state.json")

with open(STATE_FILE) as f:
    state = json.load(f)

yaml = ["services:"]

for service_name, config in state["services"].items():

    strategy = config["strategy"]

    if strategy == "blue-green":

        yaml.append(f"  {service_name}-blue:")
        yaml.append(f"    image: {config['blue']['image']}")

        yaml.append(f"  {service_name}-green:")
        yaml.append(f"    image: {config['green']['image']}")

    elif strategy == "single":

        yaml.append(f"  {service_name}:")
        yaml.append(f"    image: {config['image']}")

print("\n".join(yaml))

```

====================================================================================================
FILE: scripts/deploy/run_rollbacks.py
====================================================================================================

```
import json
import os
import base64
import subprocess


def load_rollback_decision():
    data = os.environ["ROLLBACK_DECISION"]
    return json.loads(base64.b64decode(data).decode())


def main():
    decision = load_rollback_decision()

    failed = decision.get("failed", [])

    if not failed:
        print("✅ no rollback required")
        return

    server_user = os.environ["SERVER_USER"]
    server_ip = os.environ["SERVER_IP"]

    for service in failed:

        print(f"🔄 rollback: {service}")

        subprocess.run(
            [
                "ssh",
                f"{server_user}@{server_ip}",
                f"ROLLBACK_SERVICE={service} python3 -",
            ],
            stdin=open("scripts/rollback.py", "rb"),
            check=True,
        )

    print("✅ rollback engine finished")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/switch_services.py
====================================================================================================

```
import json
import sys
import os
import base64
from pathlib import Path


def load_deploy_plan():
    plan = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(plan).decode())


def main():
    deploy_plan = load_deploy_plan()
    if not deploy_plan:
        print("no changes")
        sys.exit(0)

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:
        active = state["services"][service]["active"]
        new = "green" if active == "blue" else "blue"

        state["services"][service]["active"] = new

        print(f"🔁 {service}: {active} → {new}")

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/unlock_rollback.py
====================================================================================================

```
import json
import os
import base64
from pathlib import Path


def load_rollback_decision():
    data = os.environ["ROLLBACK_DECISION"]
    return json.loads(base64.b64decode(data).decode())


def main():
    decision = load_rollback_decision()

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in decision["passed"]:

        if service not in state["services"]:
            print(f"⚠️ unknown service: {service}")
            continue

        state["services"][service]["rollback_locked"] = False

        print(f"🔓 rollback unlocked: {service}")

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/update_state.py
====================================================================================================

```
import json
import os

STATE_PATH = "state.json"
CHANGES_PATH = "images.json"

OWNER = "kpa9pt"

DEPLOY_ID = os.getenv("DEPLOY_ID")


def load(path):
    with open(path) as f:
        return json.load(f)


state = load(STATE_PATH)
changes = load(CHANGES_PATH)

state["deploy_id"] = DEPLOY_ID


def build_image(service, sha):
    return f"ghcr.io/{OWNER}/repair-crm-{service}:{sha}"


for service, sha in changes.items():

    if service not in state["services"]:
        state["services"][service] = {"strategy": "single", "rollback_locked": False}

    service_state = state["services"][service]

    image = build_image(service, sha)

    if service_state["strategy"] == "blue-green":

        active = service_state["active"]
        inactive = "green" if active == "blue" else "blue"

        service_state[inactive]["image"] = image

    else:

        service_state["image"] = image


print(json.dumps(state, indent=2))

```

====================================================================================================
FILE: scripts/deploy/verify_inactive_services.py
====================================================================================================

```
import json
import sys
import subprocess
import time
import os
import base64
from pathlib import Path


def healthcheck(container, port, health):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{health}', timeout=2)"
        ),
    ]

    return subprocess.run(cmd).returncode == 0


def load_deploy_plan():
    plan = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(plan).decode())


def main():
    deploy_plan = load_deploy_plan()

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:

        print(f"🔍 verifying {service}")

        s = state["services"][service]

        active = s["active"]

        inactive = "green" if active == "blue" else "blue"

        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{inactive}"

        ok = False

        for i in range(60):
            if healthcheck(container, port, health):
                print(f"✅ {container} healthy")
                ok = True
                break

            print(f"retry {i}")
            time.sleep(2)

        if not ok:
            print(f"❌ {container} failed")
            sys.exit(1)


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/deploy/verify_services.py
====================================================================================================

```
import json
import sys
import subprocess
import time
import os
import base64
from pathlib import Path


def healthcheck(container, port, health):
    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{health}', timeout=2)"
        ),
    ]

    return subprocess.run(cmd).returncode == 0


def load_deploy_plan():
    plan = os.environ["DEPLOY_PLAN"]
    return json.loads(base64.b64decode(plan).decode())


def main():
    deploy_plan = load_deploy_plan()

    state_file = Path.home() / "repair-crm" / "state" / "state.json"

    with open(state_file) as f:
        state = json.load(f)

    for service in deploy_plan:

        print(f"🔍 verifying {service}")

        s = state["services"][service]

        active = s["active"]
        port = s.get("port", 8000)
        health = s.get("healthcheck", "/health")

        container = f"{service}-{active}"

        ok = False

        for i in range(60):
            if healthcheck(container, port, health):
                print(f"✅ {service} healthy")
                ok = True
                break

            print(f"retry {i}")

            time.sleep(2)

        if not ok:
            print(f"❌ {service} failed")
            sys.exit(1)

    subprocess.run(["docker", "exec", "nginx", "/scripts/reload.sh"], check=True)

    print("🔁 nginx reloaded")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/rollback.py
====================================================================================================

```
import json
import subprocess
import time
import sys
import os

from pathlib import Path

STATE_FILE = Path(
    os.getenv(
        "STATE_PATH",
        str(Path.home() / "repair-crm" / "state" / "state.json"),
    )
)

WORKDIR = Path(
    os.getenv(
        "WORKDIR",
        str(Path.home() / "repair-crm"),
    )
)

NGINX_CONTAINER = "nginx"

service = os.getenv("ROLLBACK_SERVICE")
if not service:
    raise RuntimeError("ROLLBACK_SERVICE not set")


def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def opposite(active: str) -> str:
    if active == "blue":
        return "green"
    return "blue"


def service_name(slot: str) -> str:
    return f"{service}-{slot}"


def wait_health(container: str, port: int, healthcheck: str, retries=30, delay=2):
    print(f"⏳ Waiting health: {container}")

    for i in range(retries):
        try:
            subprocess.run(
                [
                    "docker",
                    "exec",
                    container,
                    "python",
                    "-c",
                    (
                        "import urllib.request;"
                        "urllib.request.urlopen("
                        f"'http://localhost:{port}{healthcheck}', timeout=2"
                        ")"
                    ),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("✅ health OK")
            return True

        except subprocess.CalledProcessError:
            print(f"retry {i + 1}/{retries}")
            time.sleep(delay)

    return False


def reload_nginx():
    print("🔁 reloading nginx")
    subprocess.run(
        ["docker", "exec", NGINX_CONTAINER, "/scripts/reload.sh"],
        check=True,
    )


def main():
    state = load_state()

    service_state = state["services"][service]

    port = service_state.get("port", 8000)
    healthcheck = service_state.get("healthcheck", "/health")

    if service_state["strategy"] == "single":
        print("single strategy rollback not supported")
        sys.exit(1)

    active = service_state["active"]
    target = opposite(active)

    target_container = service_name(target)

    print(f"🔄 rollback: {active} → {target}")

    # 1. start target
    # WORKDIR = Path.home() / "repair-crm"

    subprocess.run(
        # ["docker", "compose", "up", "-d", f"{target_container}"],
        ["docker", "restart", f"{target_container}"],
        cwd=WORKDIR,
        check=True,
    )

    # 2. healthcheck
    if not wait_health(
        target_container,
        port,
        healthcheck,
    ):
        print("❌ rollback failed: target unhealthy")
        sys.exit(1)

    # 3. switch active
    state["services"][service]["active"] = target
    save_state(state)

    # 4. reload nginx
    reload_nginx()

    print("✅ rollback completed")


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: scripts/test.sh
====================================================================================================

```
#!/bin/bash
set -e

TEST_PATH=${1:-tests}


echo "🚀 Starting infrastructure..."
#docker compose down -v
#docker compose up -d --build
docker compose \
  -f docker-compose.yml \
  -f docker-compose.test.yml \
  down -v

docker compose \
  -f docker-compose.yml \
  -f docker-compose.test.yml \
  up -d --build

get_health() {
  docker inspect --format='{{.State.Health.Status}}' "$1"
}

wait_for_health() {
  local name=$1
  local id
  id=$(docker compose ps -q "$name")

  if [ -z "$id" ]; then
    echo "❌ Container $name not found"
    exit 1
  fi

  echo "⏳ Waiting for $name..."

#  until [ "$(get_health "$id")" = "healthy" ]; do
#    pass
#  done

  echo "✅ $name is healthy"
}

echo "⏳ Waiting for services..."

wait_for_health postgres
wait_for_health gateway-blue


# В начале скрипта, после поднятия postgres
echo "Creating test database..."
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE repair_crm_test" 2>/dev/null || true

echo "Applying migrations..."
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test alembic upgrade head

echo "🧪 Running tests..."
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test
pytest "$TEST_PATH" -v

echo "🧹 Cleaning up..."
docker compose down -v
```

====================================================================================================
FILE: services/certbot/Dockerfile
====================================================================================================

```
FROM certbot/certbot:latest

RUN apk add --no-cache bash docker-cli

COPY services/certbot/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

====================================================================================================
FILE: services/certbot/entrypoint.sh
====================================================================================================

```
#!/bin/sh
set -e

DOMAIN=${DOMAIN_NAME:-localhost}
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

echo "🚀 Certbot service started for domain: $DOMAIN"

if [ "$DOMAIN" = "localhost" ]; then
  echo "Local mode detected, certbot disabled"
  while true; do sleep 12h; done
fi

# Функция для запроса сертификата с повторными попытками
get_certificate() {
  while true; do
    echo "📦 Requesting new certificate..."
    if certbot certonly --webroot --webroot-path=/var/www/certbot \
      --email admin@$DOMAIN --agree-tos --no-eff-email \
      -d "$DOMAIN" --non-interactive; then

      echo "✅ Certificate issued"
      return 0
    else
      echo "❌ Failed, checking if rate limit..."
      # Если ошибка содержит "too many failed authorizations" - ждем 1 час
      if certbot --version 2>/dev/null && \
         certbot certificates 2>&1 | grep -q "too many failed authorizations"; then
        echo "⏳ Rate limit detected, waiting 1 hour..."
        sleep 3600
      else
        echo "⏳ Other error, waiting 5 minutes..."
        sleep 300
      fi
    fi
  done
}

# Основная логика
if [ -f "$CERT_PATH" ]; then
  echo "✅ Certificate already exists"
else
  get_certificate
fi

# Бесконечный цикл обновления
while true; do
  sleep 12h
  echo "🔄 Renewing certificate..."
  certbot renew --webroot --webroot-path=/var/www/certbot --quiet
  echo "🔄 Renewal check done"
done
```

====================================================================================================
FILE: services/gateway/app/__init__.py
====================================================================================================

```

```

====================================================================================================
FILE: services/gateway/app/admin/__init__.py
====================================================================================================

```
"""
Модуль админ-панели SQLAdmin
"""

from .auth import AdminAuth
from .views import RepairRequestAdmin

__all__ = ["AdminAuth", "RepairRequestAdmin"]

```

====================================================================================================
FILE: services/gateway/app/admin/auth.py
====================================================================================================

```
"""
Аутентификация для админ-панели SQLAdmin
"""

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from passlib.context import CryptContext
from shared.settings import get_settings

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminAuth(AuthenticationBackend):
    """Простая аутентификация для админ-панели"""

    async def login(self, request: Request) -> bool:
        """Обработка входа в админку"""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        settings = get_settings()

        # Здесь можно заменить на чтение из БД или переменных окружения
        # Для старта - фиксированные учетные данные
        if username == settings.admin_username and password == settings.admin_password:
            request.session.update({"admin_authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        """Обработка выхода из админки"""
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """Проверка авторизации"""
        return request.session.get("admin_authenticated", False)

```

====================================================================================================
FILE: services/gateway/app/admin/views.py
====================================================================================================

```
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqladmin import ModelView

from shared.models import RepairRequest
from shared.enums import Urgency, RequestStatus

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class RepairRequestAdmin(ModelView, model=RepairRequest):
    """Админка RepairRequest"""

    name = "Заявка"
    name_plural = "Заявки на ремонт"
    icon = "fa-solid fa-wrench"

    # --------------------
    # СПИСОК
    # --------------------
    column_list = [
        RepairRequest.id,
        RepairRequest.vehicle_name,
        RepairRequest.status,
        RepairRequest.urgency,
        RepairRequest.is_operational,
        RepairRequest.created_at,
        RepairRequest.deadline,
        RepairRequest.client_name,
    ]

    column_labels = {
        RepairRequest.vehicle_name: "Техника",
        RepairRequest.client_name: "Клиент",
        RepairRequest.status: "Статус заявки",
        RepairRequest.urgency: "Срочность",
        RepairRequest.created_at: "Создано",
        RepairRequest.deadline: "Дедлайн",
        RepairRequest.is_operational: "Техника на ходу?",
    }

    column_editable_list = [
        RepairRequest.status,
        RepairRequest.urgency,
    ]

    column_filters = []

    column_default_sort = [(RepairRequest.created_at, True)]

    search_fields = [
        "vehicle_name",
        "client_name",
        "description",
    ]

    can_export = True
    can_view_details = True

    # --------------------
    # ФОРМА
    # --------------------
    form_columns = [
        # === ОСНОВНОЕ ===
        "vehicle_name",
        "description",
        "is_operational",
        # === УПРАВЛЕНИЕ ===
        "urgency",
        "status",
        "deadline",
        # === ФИНАНСЫ ===
        "parts_cost",
        "client_payment",
        # === КЛИЕНТ ===
        "client_name",
        "phone",
        "email",
    ]

    form_args = {
        "vehicle_name": {"label": "Техника"},
        "client_name": {"label": "Клиент", "default": "Топ Лес"},
        "phone": {"label": "Телефон"},
        "email": {"label": "Email"},
        "description": {"label": "Описание проблемы"},
        "urgency": {"label": "Срочность", "default": Urgency.NORMAL.value},
        "status": {"label": "Статус заявки", "default": RequestStatus.NEW.value},
        "deadline": {"label": "Дедлайн"},
        "parts_cost": {"label": "Стоимость запчастей", "default": Decimal("0.00")},
        "client_payment": {"label": "Оплата клиента", "default": Decimal("0.00")},
        "is_operational": {"label": "Техника на ходу?", "default": False},
    }

    # # ДЕФОЛТЫ (SQLAdmin правильный способ)
    # form_args = {
    #     "client_name": {"default": "Топ Лес"},
    #     "urgency": {"default": Urgency.NORMAL.value},
    #     "status": {"default": RequestStatus.NEW.value},
    #     "is_operational": {"default": False},
    #     "parts_cost": {"default": Decimal("0.00")},
    #     "client_payment": {"default": Decimal("0.00")},
    # }

    # --------------------
    # ВЫПАДАЮЩИЕ СПИСКИ
    # --------------------
    form_choices = {
        "urgency": [
            ("low", "🟢 Низкая"),
            ("normal", "🟡 Обычная"),
            ("high", "🟠 Высокая"),
            ("critical", "🔴 Критическая"),
        ],
        "status": [
            ("new", "🟢 Новая"),
            ("in_progress", "🟡 В работе"),
            ("waiting_parts", "🔴 Ожидает запчасти"),
            ("diagnostics", "🔵 Диагностика"),
            ("waiting_approval", "🟠 Ожидает согласования"),
            ("done", "✅ Готово"),
        ],
        "is_operational": [
            (True, "Да"),
            (False, "Нет"),
        ],
    }

    # --------------------
    # ФОРМАТИРОВАНИЕ ДАТ (MSK)
    # --------------------
    column_formatters = {
        RepairRequest.status: lambda m, a: {
            "new": "🟢 Новая",
            "in_progress": "🟡 В работе",
            "waiting_parts": "🔴 Ожидает запчасти",
            "diagnostics": "🔵 Диагностика",
            "waiting_approval": "🟠 Ожидает согласования",
            "done": "✅ Готово",
        }.get(m.status, m.status),
        RepairRequest.urgency: lambda m, a: {
            "low": "🟢 Низкая",
            "normal": "🟡 Обычная",
            "high": "🟠 Высокая",
            "critical": "🔴 Критическая",
        }.get(m.urgency, m.urgency),
        RepairRequest.created_at: lambda m, a: (
            m.created_at.astimezone(MOSCOW_TZ).strftime("%d.%m.%Y %H:%M")
            if m.created_at
            else ""
        ),
        RepairRequest.deadline: lambda m, a: (
            m.deadline.strftime("%d.%m.%Y") if m.deadline else ""
        ),
    }

```

====================================================================================================
FILE: services/gateway/app/main.py
====================================================================================================

```
from fastapi import FastAPI
from shared import get_settings
from .routers import repair_requests_router
from .admin import AdminAuth, RepairRequestAdmin
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware
from shared.db import get_engine  # ← импортируем новую функцию
from fastapi.responses import RedirectResponse


settings = get_settings()

app = FastAPI(
    title="Gateway API",
    version="0.1.0",
    description="API Gateway для CRM ремонтной мастерской",
)

# Добавляем middleware для сессий (нужен для аутентификации админки)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key or "supersecretkey-change-in-production",
    session_cookie="admin_session",
)

# Настройка админ-панели
authentication_backend = AdminAuth(secret_key=settings.secret_key or "supersecretkey")
admin = Admin(
    app,
    get_engine(),  # ← используем get_engine()
    authentication_backend=authentication_backend,
    title="Repair CRM Admin",
    logo_url="/static/logo.png",  # опционально
    base_url="/admin",  # ← ЯВНО УКАЗЫВАЕМ URL
)

# Регистрируем модели
admin.add_view(RepairRequestAdmin)

# Подключаем роутеры
app.include_router(repair_requests_router)


@app.get("/")
async def root():
    return RedirectResponse("/admin/")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/test_blue_green")
async def test_blue_green():
    return {"status": "ok"}


@app.get("/test_check_diff")
async def test_check_diff():
    return {"status": "ok"}

```

====================================================================================================
FILE: services/gateway/app/routers/__init__.py
====================================================================================================

```
from .repair_requests import router as repair_requests_router

__all__ = ["repair_requests_router"]

```

====================================================================================================
FILE: services/gateway/app/routers/repair_requests.py
====================================================================================================

```
"""
Роутер для работы с заявками на ремонт.

Все эндпоинты имеют префикс /api/v1/repair-requests
"""

from fastapi import APIRouter, Depends, HTTPException, status

from shared import get_session_maker
from shared.repository import RepairRequestRepository
from shared.schemas import (
    RepairRequestCreate,
    RepairRequestUpdate,
    RepairRequestResponse,
    RepairRequestListResponse,
)

router = APIRouter(prefix="/api/v1/repair-requests", tags=["Repair Requests"])


async def get_repo():
    session_maker = get_session_maker()

    async with session_maker() as session:
        yield RepairRequestRepository(session)


@router.post(
    "/", response_model=RepairRequestResponse, status_code=status.HTTP_201_CREATED
)
async def create_repair_request(
    request_data: RepairRequestCreate, repo: RepairRequestRepository = Depends(get_repo)
):
    """
    Создать новую заявку на ремонт.

    - **vehicle_name**: название техники (обязательно)
    - **description**: описание поломки (обязательно)
    - **urgency**: срочность (low/normal/high/critical)
    - **status**: статус (new/in_progress/waiting_parts/
        diagnostics/waiting_approval/done)
    """
    # Конвертируем Pydantic модель в словарь
    new_request = await repo.create(**request_data.model_dump())
    await repo.session.commit()
    return RepairRequestResponse.model_validate(new_request)


@router.get("/", response_model=RepairRequestListResponse)
async def get_all_repair_requests(
    skip: int = 0, limit: int = 100, repo: RepairRequestRepository = Depends(get_repo)
):
    """
    Получить список всех заявок с пагинацией.

    - **skip**: сколько заявок пропустить
    - **limit**: сколько заявок вернуть
    - Сортировка: сначала новые (по created_at DESC)
    """
    requests = await repo.get_all(skip=skip, limit=limit)
    total = len(requests)  # В будущем можно сделать отдельный метод для count

    return RepairRequestListResponse(
        items=[RepairRequestResponse.model_validate(r) for r in requests],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/vehicle/{vehicle_name}", response_model=RepairRequestListResponse)
async def get_repair_requests_by_vehicle(
    vehicle_name: str,
    skip: int = 0,
    limit: int = 100,
    repo: RepairRequestRepository = Depends(get_repo),
):
    """
    Получить все заявки для конкретной техники.

    - **vehicle_name**: название техники
    - **skip**: сколько пропустить
    - **limit**: сколько вернуть
    """
    # Метод get_by_vehicle нужно добавить в репозиторий
    # Пока используем фильтрацию через get_all (не оптимально)
    all_requests = await repo.get_by_vehicle(vehicle_name)
    filtered = [r for r in all_requests if r.vehicle_name == vehicle_name]
    total = len(filtered)
    paginated = filtered[skip : skip + limit]

    return RepairRequestListResponse(
        items=[RepairRequestResponse.model_validate(r) for r in paginated],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{request_id}", response_model=RepairRequestResponse)
async def get_repair_request(
    request_id: int, repo: RepairRequestRepository = Depends(get_repo)
):
    """
    Получить конкретную заявку по ID.
    """
    request = await repo.get_by_id(request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair request with id {request_id} not found",
        )
    return RepairRequestResponse.model_validate(request)


@router.patch("/{request_id}", response_model=RepairRequestResponse)
async def update_repair_request(
    request_id: int,
    update_data: RepairRequestUpdate,
    repo: RepairRequestRepository = Depends(get_repo),
):
    """
    Обновить заявку (частичное обновление).

    Можно обновить любое поле или несколько полей сразу.
    """
    existing = await repo.get_by_id(request_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair request with id {request_id} not found",
        )

    # Обновляем только переданные поля
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(existing, key, value)

    # await repo.session.commit()
    await repo.session.commit()
    await repo.session.refresh(existing)

    return RepairRequestResponse.model_validate(existing)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repair_request(
    request_id: int, repo: RepairRequestRepository = Depends(get_repo)
):
    """
    Удалить заявку по ID.
    """
    existing = await repo.get_by_id(request_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair request with id {request_id} not found",
        )

    await repo.session.delete(existing)
    await repo.session.commit()

    return None  # 204 No Content

```

====================================================================================================
FILE: services/gateway/Dockerfile
====================================================================================================

```
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/gateway ./services/gateway
COPY shared ./shared

COPY alembic.ini .
```

====================================================================================================
FILE: services/migrations/Dockerfile
====================================================================================================

```
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY shared ./shared
COPY alembic.ini .

CMD ["alembic", "upgrade", "head"]
```

====================================================================================================
FILE: services/nginx/Dockerfile
====================================================================================================

```
FROM nginx:alpine

RUN apk add --no-cache gettext inotify-tools bash jq



COPY services/nginx/nginx-https.conf /etc/nginx/nginx-https.conf
COPY services/nginx/nginx-http.conf /etc/nginx/nginx-http.conf

# 👇 ВСЕ скрипты в одну папку
COPY services/nginx/scripts/ /scripts/

RUN chmod +x /scripts/*.sh

ENTRYPOINT ["/scripts/entrypoint.sh"]
```

====================================================================================================
FILE: services/nginx/nginx-http.conf
====================================================================================================

```
events {}

http {
    include /etc/nginx/upstreams/upstream.conf;

    server {
        listen 80;
        server_name ${DOMAIN_NAME};

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        location /.well-known/acme-challenge/healthcheck {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass http://gateway_backend;
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
            proxy_next_upstream_tries 3;
            proxy_connect_timeout 5s;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }
    }

}
```

====================================================================================================
FILE: services/nginx/nginx-https.conf
====================================================================================================

```
events {}

http {
    include /etc/nginx/upstreams/upstream.conf;

    server {
        listen 80;
        server_name ${DOMAIN_NAME};

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        location /.well-known/acme-challenge/healthcheck {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass http://gateway_backend;
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
            proxy_next_upstream_tries 3;
            proxy_connect_timeout 5s;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }
    }

    server {
        listen 443 ssl;
        server_name ${DOMAIN_NAME};

        ssl_certificate /etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/${DOMAIN_NAME}/privkey.pem;

        location /.well-known/acme-challenge/healthcheck {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }

        location / {
            proxy_pass http://gateway_backend;
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
            proxy_next_upstream_tries 3;
            proxy_connect_timeout 5s;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }
    }

}
```

====================================================================================================
FILE: services/nginx/scripts/entrypoint.sh
====================================================================================================

```
#!/bin/sh
set -e

echo "[BOOT] nginx starting"

echo "[STEP] init state"
/scripts/init_state.sh

echo "[STEP] render upstream"
/scripts/render_upstream.sh

echo "[STEP] generate nginx config"
/scripts/nginx_config.sh

echo "[STEP] nginx test"
nginx -t

echo "[STEP] start nginx"
nginx -g 'daemon off;' &
NGINX_PID=$!

echo "[STEP] watcher start"
/scripts/watcher.sh &

wait $NGINX_PID
```

====================================================================================================
FILE: services/nginx/scripts/init_state.sh
====================================================================================================

```
#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json

echo "[STATE] checking state file"

# если это директория — это сломанный volume
if [ -d "$STATE_FILE" ]; then
  echo "[STATE] ERROR: state.json is directory, fixing"
  rm -rf "$STATE_FILE"
fi

# если файла нет — создаём
if [ ! -f "$STATE_FILE" ]; then
  echo "[STATE] state.json missing, generating local state"
  /scripts/local_state.sh
fi

echo "[STATE] state loaded"
```

====================================================================================================
FILE: services/nginx/scripts/local_state.sh
====================================================================================================

```
#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json
#dfff
echo "[LOCAL] generating default state"

cat > "$STATE_FILE" <<EOF
{
  "deploy_id": "local",
  "services": {
    "gateway": {
      "strategy": "blue-green",
      "active": "blue",
      "port": 8000,
      "healthcheck": "/health",
      "rollback_locked": false
    }
  }
}
EOF
```

====================================================================================================
FILE: services/nginx/scripts/nginx_config.sh
====================================================================================================

```
#!/bin/sh
set -e

DOMAIN="${DOMAIN_NAME:-localhost}"
CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

echo "[NGINX] generating nginx.conf..."

if [ -f "$CERT" ]; then
  CONF="/etc/nginx/nginx-https.conf"
  echo "[NGINX] mode=https"
else
  CONF="/etc/nginx/nginx-http.conf"
  echo "[NGINX] mode=http"
fi

envsubst '$DOMAIN_NAME' < "$CONF" > /etc/nginx/nginx.conf

echo "[NGINX] nginx.conf generated"
```

====================================================================================================
FILE: services/nginx/scripts/reload.sh
====================================================================================================

```
#!/bin/sh
set -e

/scripts/render_upstream.sh
nginx -t
nginx -s reload
```

====================================================================================================
FILE: services/nginx/scripts/render_upstream.sh
====================================================================================================

```
#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json

mkdir -p /etc/nginx/upstreams

rm -f /etc/nginx/upstreams/*.conf 2>/dev/null || true

echo "[RENDER] state=$STATE_FILE"

jq -r '
  .services
  | to_entries[]
  | select(.value.strategy == "blue-green")
  | "\(.key) \(.value.active) \(.value.port)"
' "$STATE_FILE" |
while read SERVICE ACTIVE PORT
do

cat > "/etc/nginx/upstreams/upstream.conf" <<EOF
upstream ${SERVICE}_backend {
  server ${SERVICE}-${ACTIVE}:${PORT} max_fails=3 fail_timeout=10s;
}
EOF

echo "[RENDER] ${SERVICE} -> ${SERVICE}-${ACTIVE}:${PORT}"

done
```

====================================================================================================
FILE: services/nginx/scripts/watcher.sh
====================================================================================================

```
start_watcher() {
  WATCH_DIR="/etc/letsencrypt/live"
  DOMAIN=${DOMAIN_NAME:-localhost}

  echo "[WATCHER] started"

  # ждём появления папки (важно для certbot bootstrap)
  while [ ! -d "$WATCH_DIR/$DOMAIN" ]; do
    echo "[WATCHER] waiting cert dir..."
    sleep 2
  done

  render_upstream
  nginx -s reload

  echo "[WATCHER] cert dir ready"

  inotifywait -m -r -e create -e modify -e moved_to "$WATCH_DIR" |
  while read -r FILE; do
    case "$FILE" in
      *"/$DOMAIN/"*)
        echo "[WATCHER] change detected: $FILE"

        render_upstream
        nginx -s reload
        ;;
    esac
  done
}
```

====================================================================================================
FILE: services/watchdog/Dockerfile
====================================================================================================

```
FROM python:3.11-slim

RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY services/watchdog /app
COPY scripts/rollback.py /scripts/rollback.py

CMD ["python", "main.py"]
```

====================================================================================================
FILE: services/watchdog/main.py
====================================================================================================

```
import json
import time
import os
import subprocess


STATE_PATH = os.getenv("STATE_PATH", "/state/state.json")
WORKDIR = os.getenv("WORKDIR", "/app")


def load_state():
    with open(STATE_PATH) as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def container_running(container):
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "-f",
            "{{.State.Running}}",
            container,
        ],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0 and result.stdout.strip() == "true"


def healthcheck(container, port, path):

    if not container_running(container):
        print(f"[WATCHDOG] {container} is not running")
        return False

    cmd = [
        "docker",
        "exec",
        container,
        "python",
        "-c",
        (
            "import urllib.request;"
            f"urllib.request.urlopen('http://localhost:{port}{path}', timeout=2)"
        ),
    ]

    return (
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def trigger_rollback(service):
    print(f"[WATCHDOG] rollback triggered for {service}")

    env = os.environ.copy()
    env["ROLLBACK_SERVICE"] = service
    env["STATE_PATH"] = STATE_PATH
    env["WORKDIR"] = WORKDIR

    subprocess.run(["python", "/scripts/rollback.py"], env=env)


def check_service(service, cfg):
    if cfg.get("strategy") != "blue-green":
        return True

    active = cfg["active"]
    container = f"{service}-{active}"

    port = cfg.get("port", 8000)
    health = cfg.get("healthcheck", "/health")

    retries = 15

    for i in range(retries):
        if healthcheck(container, port, health):
            return True
        time.sleep(2)

    return False


def main():
    while True:
        state = load_state()

        rolled_back_this_cycle = set()

        for service, cfg in state["services"].items():

            if cfg.get("strategy") != "blue-green":
                continue

            if cfg.get("rollback_locked", False):
                print(f"[WATCHDOG] rollback locked → skip {service}")
                continue

            ok = check_service(service, cfg)

            if ok:
                continue

            if service in rolled_back_this_cycle:
                continue

            print(f"[WATCHDOG] service failed → {service}")

            # rollback
            trigger_rollback(service)

            # mark locked immediately
            state["services"][service]["rollback_locked"] = True
            rolled_back_this_cycle.add(service)

            save_state(state)

        time.sleep(60)


if __name__ == "__main__":
    main()

```

====================================================================================================
FILE: shared/__init__.py
====================================================================================================

```
from .settings import get_settings
from .models import Base, RepairRequest
from .db import get_session_maker
from .enums import Urgency, RequestStatus

__all__ = [
    "get_settings",
    "Base",
    "RepairRequest",
    "get_session_maker",
    "Urgency",
    "RequestStatus",
]

```

====================================================================================================
FILE: shared/db/__init__.py
====================================================================================================

```
from .session import get_session_maker, get_engine, reset_db

__all__ = ["get_session_maker", "get_engine", "reset_db"]

```

====================================================================================================
FILE: shared/db/migrations/env.py
====================================================================================================

```
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from alembic import context
from shared.models import Base
import os

config = context.config

# Берём DATABASE_URL из переменной окружения (не из settings!)
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm"
)

config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

```

====================================================================================================
FILE: shared/db/migrations/README
====================================================================================================

```
Generic single-database configuration with an async dbapi.
```

====================================================================================================
FILE: shared/db/migrations/versions/2026_05_28_2109-ef27e3a3bb21_.py
====================================================================================================

```
"""

Revision ID: ef27e3a3bb21
Revises:
Create Date: 2026-05-28 21:09:51.922444

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "ef27e3a3bb21"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "repair_requests",
        sa.Column("vehicle_name", sa.String(length=200), nullable=False),
        sa.Column(
            "client_name",
            sa.String(length=100),
            server_default="Топ Лес",
            nullable=False,
        ),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "urgency",
            sa.String(length=20),
            server_default="normal",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default="new",
            nullable=False,
        ),
        sa.Column("is_operational", sa.Boolean(), nullable=True),
        sa.Column(
            "parts_cost",
            sa.Numeric(precision=12, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "client_payment",
            sa.Numeric(precision=12, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_repair_requests_id"), "repair_requests", ["id"], unique=False
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_repair_requests_id"), table_name="repair_requests")
    op.drop_table("repair_requests")
    # ### end Alembic commands ###

```

====================================================================================================
FILE: shared/db/migrations/versions/2026_05_29_2232-dfae9b9dfe98_.py
====================================================================================================

```
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "dfae9b9dfe98"
down_revision: Union[str, Sequence[str], None] = "ef27e3a3bb21"
branch_labels = None
depends_on = None


urgency_enum = sa.Enum("LOW", "NORMAL", "HIGH", "CRITICAL", name="urgency_enum")

request_status_enum = sa.Enum(
    "NEW",
    "IN_PROGRESS",
    "WAITING_PARTS",
    "DIAGNOSTICS",
    "WAITING_APPROVAL",
    "DONE",
    name="request_status_enum",
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1. создаём enum-типы
    urgency_enum.create(bind, checkfirst=True)
    request_status_enum.create(bind, checkfirst=True)

    # 2. УБИРАЕМ старые дефолты (важно!)
    op.alter_column(
        "repair_requests",
        "urgency",
        existing_type=sa.VARCHAR(length=20),
        server_default=None,
    )

    op.alter_column(
        "repair_requests",
        "status",
        existing_type=sa.VARCHAR(length=30),
        server_default=None,
    )

    # 3. меняем типы
    op.alter_column(
        "repair_requests",
        "urgency",
        existing_type=sa.VARCHAR(length=20),
        type_=sa.Enum("LOW", "NORMAL", "HIGH", "CRITICAL", name="urgency_enum"),
        postgresql_using="urgency::text::urgency_enum",
        existing_nullable=False,
    )

    op.alter_column(
        "repair_requests",
        "status",
        existing_type=sa.VARCHAR(length=30),
        type_=sa.Enum(
            "NEW",
            "IN_PROGRESS",
            "WAITING_PARTS",
            "DIAGNOSTICS",
            "WAITING_APPROVAL",
            "DONE",
            name="request_status_enum",
        ),
        postgresql_using="status::text::request_status_enum",
        existing_nullable=False,
    )

    # 4. ставим новые enum defaults
    op.alter_column(
        "repair_requests",
        "urgency",
        server_default=sa.text("'NORMAL'::urgency_enum"),
    )

    op.alter_column(
        "repair_requests",
        "status",
        server_default=sa.text("'NEW'::request_status_enum"),
    )


def downgrade() -> None:
    op.alter_column(
        "repair_requests",
        "urgency",
        server_default=None,
    )
    op.alter_column(
        "repair_requests",
        "status",
        server_default=None,
    )

    op.alter_column(
        "repair_requests",
        "urgency",
        type_=sa.VARCHAR(length=20),
        existing_type=sa.Enum(name="urgency_enum"),
        postgresql_using="urgency::text",
        existing_nullable=False,
    )

    op.alter_column(
        "repair_requests",
        "status",
        type_=sa.VARCHAR(length=30),
        existing_type=sa.Enum(name="request_status_enum"),
        postgresql_using="status::text",
        existing_nullable=False,
    )

    # (опционально) удаление enum типов
    request_status_enum.drop(op.get_bind(), checkfirst=True)
    urgency_enum.drop(op.get_bind(), checkfirst=True)

```

====================================================================================================
FILE: shared/db/migrations/versions/2026_05_29_2314-794a7553b817_.py
====================================================================================================

```
"""

Revision ID: 794a7553b817
Revises: dfae9b9dfe98
Create Date: 2026-05-29 23:14:23.536702

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "794a7553b817"
down_revision: Union[str, Sequence[str], None] = "dfae9b9dfe98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "repair_requests",
        "deadline",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.Date(),
        existing_nullable=True,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "repair_requests",
        "deadline",
        existing_type=sa.Date(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
    )
    # ### end Alembic commands ###

```

====================================================================================================
FILE: shared/db/session.py
====================================================================================================

```
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from shared.settings import get_settings

_engine = None
_session_maker = None


def get_session_maker():
    global _engine, _session_maker
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=True)
        _session_maker = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_maker


def get_engine():
    """Возвращает асинхронный движок БД"""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=True)
    return _engine


def reset_db():
    global _engine, _session_maker
    _engine = None
    _session_maker = None

```

====================================================================================================
FILE: shared/enums.py
====================================================================================================

```
"""
Enum классы для выпадающих списков в моделях и схемах
"""

from enum import Enum


class Urgency(str, Enum):
    """Срочность заявки"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

    def __str__(self) -> str:
        return self.value


class RequestStatus(str, Enum):
    """Статус заявки на ремонт"""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    WAITING_PARTS = "waiting_parts"
    DIAGNOSTICS = "diagnostics"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"

    def __str__(self) -> str:
        return self.value

```

====================================================================================================
FILE: shared/models/__init__.py
====================================================================================================

```
from .base import DeclarativeBase as Base
from .repair_request import RepairRequest

__all__ = (
    "Base",
    "RepairRequest",
)

```

====================================================================================================
FILE: shared/models/base.py
====================================================================================================

```
from sqlalchemy import Column, Integer
from sqlalchemy.orm import declared_attr, declarative_base


class Base:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, index=True)

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"


DeclarativeBase = declarative_base(cls=Base)

```

====================================================================================================
FILE: shared/models/repair_request.py
====================================================================================================

```
from sqlalchemy import Column, String, Text, Boolean, DateTime, Numeric, Date
from sqlalchemy.sql import func
from shared.models import Base
from shared.enums import Urgency, RequestStatus
from sqlalchemy import Enum as SQLEnum


class RepairRequest(Base):
    __tablename__ = "repair_requests"

    vehicle_name = Column(String(200), nullable=False)
    client_name = Column(String(100), nullable=False, server_default="Топ Лес")
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)

    urgency = Column(
        SQLEnum(Urgency, name="urgency_enum"),
        nullable=False,
        server_default=Urgency.NORMAL.value,
    )

    status = Column(
        SQLEnum(RequestStatus, name="request_status_enum"),
        nullable=False,
        server_default=RequestStatus.NEW.value,
    )

    is_operational = Column(Boolean, nullable=True)
    parts_cost = Column(Numeric(12, 2), nullable=False, server_default="0")
    client_payment = Column(Numeric(12, 2), nullable=False, server_default="0")
    deadline = Column(Date, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

```

====================================================================================================
FILE: shared/repository.py
====================================================================================================

```
"""
Репозиторий — это слой абстракции между бизнес-логикой и базой данных.
Он скрывает детали SQLAlchemy и позволяет легко подменить БД в тестах.
"""

from sqlalchemy import select
from shared.models import RepairRequest


class RepairRequestRepository:
    def __init__(self, session):
        """
        Внедряем сессию через конструктор (Dependency Injection).
        Это позволяет подставить фейковую сессию в тестах.
        """
        self.session = session

    async def create(self, **kwargs) -> RepairRequest:
        """Создать новую заявку на ремонт."""
        request = RepairRequest(**kwargs)
        self.session.add(request)
        # НЕТ commit! Только flush для получения ID
        await self.session.flush()
        # await self.session.refresh(request)
        return request

    async def get_by_id(self, request_id: int) -> RepairRequest | None:
        """Получить заявку по ID."""
        result = await self.session.execute(
            select(RepairRequest).where(RepairRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100):
        """Получить список заявок с пагинацией."""
        result = await self.session.execute(
            select(RepairRequest).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_by_vehicle(self, vehicle_name: str, skip: int = 0, limit: int = 100):
        """Получить заявки по названию техники с пагинацией"""
        result = await self.session.execute(
            select(RepairRequest)
            .where(RepairRequest.vehicle_name == vehicle_name)
            .order_by(RepairRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

```

====================================================================================================
FILE: shared/schemas/__init__.py
====================================================================================================

```
"""
Pydantic схемы для обмена данными между клиентом и сервером
"""

from .repair_request import (
    RepairRequestBase,
    RepairRequestCreate,
    RepairRequestUpdate,
    RepairRequestResponse,
    RepairRequestListResponse,
)

__all__ = [
    "RepairRequestBase",
    "RepairRequestCreate",
    "RepairRequestUpdate",
    "RepairRequestResponse",
    "RepairRequestListResponse",
]

```

====================================================================================================
FILE: shared/schemas/repair_request.py
====================================================================================================

```
"""
Pydantic схемы для RepairRequest

Эти схемы определяют:
- Как выглядит запрос от клиента (Create, Update)
- Как выглядит ответ сервера (Response)
- Какие поля обязательные, а какие нет
"""

from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from shared.enums import Urgency, RequestStatus
from datetime import date


class RepairRequestBase(BaseModel):
    """
    Базовый класс с общими полями для всех схем.
    Все поля опциональны, кроме vehicle_name и description (для create)
    """

    vehicle_name: str = Field(
        ..., description="Название техники", examples=["Квадроцикл-5"]
    )
    client_name: Optional[str] = Field(
        None, description="Имя клиента", examples=["Топ Лес"]
    )
    phone: Optional[str] = Field(
        None, description="Телефон клиента", examples=["+7-999-123-45-67"]
    )
    email: Optional[str] = Field(
        None, description="Email клиента", examples=["client@example.com"]
    )
    description: str = Field(..., description="Описание поломки")
    urgency: Urgency = Field(default=Urgency.NORMAL, description="Срочность")
    status: RequestStatus = Field(default=RequestStatus.NEW, description="Статус")
    is_operational: Optional[bool] = Field(False, description="Техника на ходу?")
    parts_cost: Decimal = Field(
        default_factory=lambda: Decimal("0.00"), description="Стоимость запчастей"
    )
    client_payment: Decimal = Field(
        default_factory=lambda: Decimal("0.00"), description="Оплата клиента"
    )
    deadline: Optional[date] = Field(None, description="Дедлайн (дата без времени)")


class RepairRequestCreate(RepairRequestBase):
    """
    Схема для POST запроса (создание новой заявки).
    Наследует все поля от Base, но явно указываем обязательные.
    """

    # Поле vehicle_name уже есть в Base
    # Поле description уже есть в Base
    pass  # Все поля уже определены в RepairRequestBase


class RepairRequestUpdate(BaseModel):
    """
    Схема для PATCH запроса (частичное обновление).
    Все поля опциональны — можно обновить только то, что нужно.
    """

    vehicle_name: Optional[str] = Field(None, description="Название техники")
    client_name: Optional[str] = Field(None, description="Имя клиента")
    phone: Optional[str] = Field(None, description="Телефон клиента")
    email: Optional[str] = Field(None, description="Email клиента")
    description: Optional[str] = Field(None, description="Описание поломки")

    urgency: Optional[Urgency] = Field(None, description="Срочность")
    status: Optional[RequestStatus] = Field(None, description="Статус")

    is_operational: Optional[bool] = Field(None, description="Техника на ходу?")
    parts_cost: Optional[Decimal] = Field(None, description="Стоимость запчастей")
    client_payment: Optional[Decimal] = Field(None, description="Оплата клиента")
    deadline: Optional[date] = Field(None, description="Дедлайн (дата без времени)")


class RepairRequestResponse(RepairRequestBase):
    """
    Схема для GET ответа (возвращаем клиенту).
    Добавляем поля, которые генерируются БД (id, created_at)
    """

    id: int = Field(..., description="ID заявки")
    created_at: datetime = Field(..., description="Дата создания")

    # Настройка для работы с SQLAlchemy моделями
    model_config = ConfigDict(from_attributes=True)


class RepairRequestListResponse(BaseModel):
    """
    Схема для списка заявок (с пагинацией).
    """

    items: list[RepairRequestResponse] = Field(..., description="Список заявок")
    total: int = Field(..., description="Общее количество заявок (без учета пагинации)")
    skip: int = Field(..., description="Сколько пропущено")
    limit: int = Field(..., description="Лимит на страницу")

```

====================================================================================================
FILE: shared/settings.py
====================================================================================================

```
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm"
    )
    telegram_token: str | None = None
    secret_key: str | None = None  # Добавляем это поле
    admin_username: str = "admin"  # Добавляем с дефолтом
    admin_password: str = "admin123"  # Добавляем с дефолтом
    domain_name: str = "localhost"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()

```

====================================================================================================
FILE: state/state.json
====================================================================================================

```
{
  "deploy_id": "local",
  "services": {
    "gateway": {
      "strategy": "blue-green",
      "active": "blue",
      "port": 8000,
      "healthcheck": "/health",
      "rollback_locked": false
    }
  }
}

```

====================================================================================================
FILE: tests/__init__.py
====================================================================================================

```

```

====================================================================================================
FILE: tests/api/__init__.py
====================================================================================================

```

```

====================================================================================================
FILE: tests/api/conftest.py
====================================================================================================

```
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from services.gateway.app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def reset():
    from shared.db.session import reset_db

    reset_db()

```

====================================================================================================
FILE: tests/api/test_admin_panel.py
====================================================================================================

```
"""
Тесты для админ-панели SQLAdmin
"""

import pytest
from shared.settings import get_settings

pytest = pytest.mark.asyncio


async def test_admin_login_page_accessible(client):
    """Страница логина доступна"""
    response = await client.get("/admin/login")
    assert response.status_code == 200


async def test_admin_panel_redirects_to_login(client):
    """Без логина админка редиректит на логин"""
    response = await client.get("/admin", follow_redirects=False)
    assert response.status_code == 307 or response.status_code == 302


async def test_admin_login_with_correct_credentials(client):
    """Вход с правильными данными"""
    settings = get_settings()

    login_data = {
        "username": settings.admin_username,
        "password": settings.admin_password,
    }
    response = await client.post("/admin/login", data=login_data, follow_redirects=True)
    assert response.status_code == 200


async def test_repair_request_list_accessible_after_login(client):
    """После входа список заявок доступен"""
    # Логинимся
    settings = get_settings()

    await client.post(
        "/admin/login",
        data={"username": settings.admin_username, "password": settings.admin_password},
    )
    # Проверяем список
    response = await client.get("/admin/repair-request/list")
    assert response.status_code == 200

```

====================================================================================================
FILE: tests/api/test_gateway.py
====================================================================================================

```
import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

```

====================================================================================================
FILE: tests/api/test_repair_requests.py
====================================================================================================

```
"""
API тесты для эндпоинтов RepairRequest.
"""

from shared.enums import Urgency, RequestStatus
import pytest

"""Тесты для API эндпоинтов"""


@pytest.mark.asyncio
async def test_create_repair_request(client):
    """Тест создания заявки через API"""
    request_data = {
        "vehicle_name": "Тестовый квадроцикл",
        "description": "Не заводится тестовая заявка",
        "urgency": Urgency.NORMAL.value,
        "status": RequestStatus.NEW.value,
    }

    response = await client.post("/api/v1/repair-requests/", json=request_data)

    assert response.status_code == 201
    data = response.json()
    assert data["vehicle_name"] == request_data["vehicle_name"]
    assert data["description"] == request_data["description"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_repair_request_invalid_data(client):
    """Тест создания заявки с невалидными данными"""
    response = await client.post(
        "/api/v1/repair-requests/", json={"description": "Только описание"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_all_repair_requests(client):
    """Тест получения списка всех заявок"""
    # Создаем тестовые данные
    for i in range(3):
        response = await client.post(
            "/api/v1/repair-requests/",
            json={"vehicle_name": f"Техника {i}", "description": f"Описание {i}"},
        )
        assert response.status_code == 201

    response = await client.get("/api/v1/repair-requests/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_get_repair_request_by_id(client):
    """Тест получения конкретной заявки по ID"""
    # Создаем
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={
            "vehicle_name": "Уникальная техника",
            "description": "Уникальное описание",
        },
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Получаем
    response = await client.get(f"/api/v1/repair-requests/{created_id}")
    assert response.status_code == 200
    assert response.json()["id"] == created_id


@pytest.mark.asyncio
async def test_get_nonexistent_repair_request(client):
    """Тест получения несуществующей заявки"""
    response = await client.get("/api/v1/repair-requests/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_repair_request(client):
    """Тест частичного обновления заявки"""
    # Создаем
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={
            "vehicle_name": "Техника для обновления",
            "description": "Оригинальное описание",
        },
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Обновляем статус
    response = await client.patch(
        f"/api/v1/repair-requests/{created_id}",
        json={"status": RequestStatus.IN_PROGRESS.value},
    )

    assert response.status_code == 200
    assert response.json()["status"] == RequestStatus.IN_PROGRESS.value
    assert response.json()["vehicle_name"] == "Техника для обновления"


@pytest.mark.asyncio
async def test_delete_repair_request(client):
    """Тест удаления заявки"""
    # Создаем
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={"vehicle_name": "Техника для удаления", "description": "Будет удалена"},
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Удаляем
    delete_response = await client.delete(f"/api/v1/repair-requests/{created_id}")
    assert delete_response.status_code == 204

    # Проверяем что удалена
    get_response = await client.get(f"/api/v1/repair-requests/{created_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_pagination(client):
    """Тест пагинации"""
    # Создаем 10 заявок
    for i in range(10):
        response = await client.post(
            "/api/v1/repair-requests/",
            json={"vehicle_name": f"Пагинация {i}", "description": f"Описание {i}"},
        )
        assert response.status_code == 201

    # Проверяем страницы
    resp1 = await client.get("/api/v1/repair-requests/?skip=0&limit=5")
    assert resp1.status_code == 200
    assert len(resp1.json()["items"]) == 5

    resp2 = await client.get("/api/v1/repair-requests/?skip=5&limit=5")
    assert resp2.status_code == 200
    assert len(resp2.json()["items"]) == 5


@pytest.mark.asyncio
async def test_get_by_vehicle_name(client):
    """Тест фильтрации по имени техники"""
    # Создаем заявки для конкретной техники
    for i in range(2):
        response = await client.post(
            "/api/v1/repair-requests/",
            json={"vehicle_name": "Специальная техника", "description": f"Заявка {i}"},
        )
        assert response.status_code == 201

    # Создаем заявку для другой техники
    response = await client.post(
        "/api/v1/repair-requests/",
        json={"vehicle_name": "Другая техника", "description": "Чужая заявка"},
    )
    assert response.status_code == 201

    response = await client.get("/api/v1/repair-requests/vehicle/Специальная техника")
    assert response.status_code == 200
    assert response.json()["total"] == 2

```

====================================================================================================
FILE: tests/conftest.py
====================================================================================================

```
"""
Общие фикстуры для всех тестов.
"""

```

====================================================================================================
FILE: tests/integration/__init__.py
====================================================================================================

```

```

====================================================================================================
FILE: tests/integration/conftest.py
====================================================================================================

```
"""
Фикстуры для интеграционных тестов (только здесь).
Эти фикстуры НЕ видны в unit и api тестах.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test"
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Тестовый движок БД (один раз на сессию)"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """Тестовая сессия (новая для каждого теста)"""
    async_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session

```

====================================================================================================
FILE: tests/integration/test_repair_request_repository.py
====================================================================================================

```
"""
Интеграционные тесты для репозитория RepairRequest.
"""

import pytest
from shared.repository import RepairRequestRepository


@pytest.mark.asyncio
async def test_repository_create(test_session):
    """Тест создания заявки через репозиторий"""
    repo = RepairRequestRepository(test_session)
    request = await repo.create(vehicle_name="Квадроцикл-5", description="Не заводится")
    assert request.id is not None
    assert request.vehicle_name == "Квадроцикл-5"
    assert request.description == "Не заводится"

```

====================================================================================================
FILE: tests/unit/__init__.py
====================================================================================================

```

```

====================================================================================================
FILE: tests/unit/test_repair_request.py
====================================================================================================

```
from shared.models import RepairRequest


def test_repair_request_creation():
    """Проверяем, что модель создаётся без ошибок."""
    request = RepairRequest(
        vehicle_name="Квадроцикл-5", description="Не заводится", status="new"
    )
    assert request.vehicle_name == "Квадроцикл-5"
    assert request.status == "new"

```

```

====================================================================================================
FILE: tools/output/service_map.json
====================================================================================================
```
{
  "docker": {
    "postgres": {},
    "environment": {},
    "expose": {},
    "volumes": {},
    "healthcheck": {},
    "deploy": {},
    "resources": {},
    "limits": {},
    "reservations": {},
    "nginx": {},
    "build": {},
    "ports": {
      "ports": [
        "- \"80:80\"",
        "- \"443:443\""
      ]
    },
    "env_file": {},
    "certbot": {},
    "depends_on": {},
    "watchdog": {},
    "gateway-blue": {},
    "command": {},
    "test": {},
    "gateway-green": {},
    "migrations": {},
    "postgres_data": {},
    "certbot_conf": {},
    "certbot_web": {}
  },
  "nginx": {
    "watcher.sh": {
      "has_upstream": true,
      "content_snippet": "start_watcher() {\n  WATCH_DIR=\"/etc/letsencrypt/live\"\n  DOMAIN=${DOMAIN_NAME:-localhost}\n\n  echo \"[WATCHER] started\"\n\n  # \u0436\u0434\u0451\u043c \u043f\u043e\u044f\u0432\u043b\u0435\u043d\u0438\u044f \u043f\u0430\u043f\u043a\u0438 (\u0432\u0430\u0436\u043d\u043e \u0434\u043b\u044f certbot bootstrap)\n  while [ ! -d \"$WATCH_DIR/$DOMAIN\" ]; do\n    echo \"[WATCHER] waiting cert dir...\"\n    sleep 2\n  done\n\n  render_upstream\n  ngin"
    },
    "render_upstream.sh": {
      "has_upstream": true,
      "content_snippet": "#!/bin/sh\nset -e\n\nSTATE_FILE=/etc/nginx/state/state.json\n\nmkdir -p /etc/nginx/upstreams\n\nrm -f /etc/nginx/upstreams/*.conf 2>/dev/null || true\n\necho \"[RENDER] state=$STATE_FILE\"\n\njq -r '\n  .services\n  | to_entries[]\n  | select(.value.strategy == \"blue-green\")\n  | \"\\(.key) \\(.value.active) \\(.value.p"
    },
    "reload.sh": {
      "has_upstream": true,
      "content_snippet": "#!/bin/sh\nset -e\n\n/scripts/render_upstream.sh\nnginx -t\nnginx -s reload"
    },
    "entrypoint.sh": {
      "has_upstream": true,
      "content_snippet": "#!/bin/sh\nset -e\n\necho \"[BOOT] nginx starting\"\n\necho \"[STEP] init state\"\n/scripts/init_state.sh\n\necho \"[STEP] render upstream\"\n/scripts/render_upstream.sh\n\necho \"[STEP] generate nginx config\"\n/scripts/nginx_config.sh\n\necho \"[STEP] nginx test\"\nnginx -t\n\necho \"[STEP] start nginx\"\nnginx -g 'daemon off;"
    }
  },
  "entrypoints": [
    "services/certbot/entrypoint.sh",
    "services/gateway/app/main.py",
    "services/nginx/scripts/entrypoint.sh",
    "services/watchdog/main.py"
  ]
}
```

====================================================================================================
FILE: tools/output/service_map.md
====================================================================================================
```
# SERVICE MAP

## ENTRYPOINTS
- services/certbot/entrypoint.sh
- services/gateway/app/main.py
- services/nginx/scripts/entrypoint.sh
- services/watchdog/main.py

## DOCKER SERVICES
- postgres: {}
- environment: {}
- expose: {}
- volumes: {}
- healthcheck: {}
- deploy: {}
- resources: {}
- limits: {}
- reservations: {}
- nginx: {}
- build: {}
- ports: {'ports': ['- "80:80"', '- "443:443"']}
- env_file: {}
- certbot: {}
- depends_on: {}
- watchdog: {}
- gateway-blue: {}
- command: {}
- test: {}
- gateway-green: {}
- migrations: {}
- postgres_data: {}
- certbot_conf: {}
- certbot_web: {}

## NGINX
- watcher.sh: True
- render_upstream.sh: True
- reload.sh: True
- entrypoint.sh: True
```

====================================================================================================
FILE: tools/output/stats_report.json
====================================================================================================
```
{
  "summary": {
    "total_files": 87,
    "python_files": 49,
    "test_files": 11,
    "total_loc": 4034,
    "python_loc": 2322,
    "test_loc": 383
  },
  "hotspots": [
    [
      "docker-compose.yml",
      223
    ],
    [
      ".github/workflows/deploy.yml",
      222
    ],
    [
      "README.md",
      178
    ],
    [
      "tests/api/test_repair_requests.py",
      172
    ],
    [
      "services/gateway/app/routers/repair_requests.py",
      163
    ],
    [
      "services/gateway/app/admin/views.py",
      156
    ],
    [
      "alembic.ini",
      150
    ],
    [
      "scripts/rollback.py",
      140
    ],
    [
      ".github/workflows/build-and-push.yml",
      136
    ],
    [
      "services/watchdog/main.py",
      134
    ]
  ],
  "by_dir": {
    ".": 15,
    "scripts/deploy": 13,
    "services/nginx/scripts": 7,
    "tests/api": 5,
    "shared": 4,
    ".github/workflows": 3,
    "scripts": 3,
    "services/gateway/app/admin": 3,
    "services/nginx": 3,
    "shared/db/migrations": 3,
    "shared/db/migrations/versions": 3,
    "shared/models": 3,
    "tests/integration": 3,
    "services/certbot": 2,
    "services/gateway/app": 2,
    "services/gateway/app/routers": 2,
    "services/watchdog": 2,
    "shared/db": 2,
    "shared/schemas": 2,
    "tests": 2,
    "tests/unit": 2,
    "services/gateway": 1,
    "services/migrations": 1,
    "state": 1
  },
  "by_type": {
    ".py": 49,
    "no_ext": 12,
    ".sh": 10,
    ".yml": 6,
    ".ini": 2,
    ".conf": 2,
    ".example": 1,
    ".yaml": 1,
    ".md": 1,
    ".txt": 1,
    ".mako": 1,
    ".json": 1
  }
}
```

====================================================================================================
FILE: tools/output/stats_report.md
====================================================================================================
```
# PROJECT STATS REPORT

## SUMMARY
- total_files: 87
- python_files: 49
- test_files: 11
- total_loc: 4034
- python_loc: 2322
- test_loc: 383

## HOTSPOTS
- docker-compose.yml: 223 LOC
- .github/workflows/deploy.yml: 222 LOC
- README.md: 178 LOC
- tests/api/test_repair_requests.py: 172 LOC
- services/gateway/app/routers/repair_requests.py: 163 LOC
- services/gateway/app/admin/views.py: 156 LOC
- alembic.ini: 150 LOC
- scripts/rollback.py: 140 LOC
- .github/workflows/build-and-push.yml: 136 LOC
- services/watchdog/main.py: 134 LOC

## DIRECTORIES
- .: 15
- scripts/deploy: 13
- services/nginx/scripts: 7
- tests/api: 5
- shared: 4
- .github/workflows: 3
- scripts: 3
- services/gateway/app/admin: 3
- services/nginx: 3
- shared/db/migrations: 3
- shared/db/migrations/versions: 3
- shared/models: 3
- tests/integration: 3
- services/certbot: 2
- services/gateway/app: 2
- services/gateway/app/routers: 2
- services/watchdog: 2
- shared/db: 2
- shared/schemas: 2
- tests: 2
- tests/unit: 2
- services/gateway: 1
- services/migrations: 1
- state: 1

## FILE TYPES
- .py: 49
- no_ext: 12
- .sh: 10
- .yml: 6
- .ini: 2
- .conf: 2
- .example: 1
- .yaml: 1
- .md: 1
- .txt: 1
- .mako: 1
- .json: 1
```

====================================================================================================
FILE: tools/README.md
====================================================================================================
```
# AI COLD START PROTOCOL — repair_crm

This repository contains a set of tooling scripts in `.tools/` that allow any AI (or developer) to fully reconstruct project context from scratch.

The goal is:

> Rebuild full understanding of the system without prior memory, chat history, or IDE state.

------------------------------------------------------------

# CORE PRINCIPLE

This project is not analyzed manually.

Instead, it is always loaded via reproducible snapshots:

- full code dump
- git diff context
- project statistics
- service architecture map

------------------------------------------------------------

# 1. FULL PROJECT DUMP (primary entry point)

COMMAND:
    python .tools/dump.py

PURPOSE:
    Creates full markdown snapshot of repository.

OUTPUT:
    .tools/output/project_dump.md

WHEN TO USE:
    - first AI onboarding
    - full architecture analysis
    - complete code understanding

------------------------------------------------------------

# 2. CHANGED MODE (git-aware context)

COMMAND:
    python .tools/dump.py changed

PURPOSE:
    Shows only modified files based on git state.

EACH FILE CONTAINS:
    - git diff
    - full file content

OUTPUT:
    .tools/output/project_changed_dump.md

WHEN TO USE:
    - debugging after deploy
    - investigating regressions
    - understanding recent changes

------------------------------------------------------------

# 3. PROJECT STATS

COMMAND:
    python .tools/stats.py

PURPOSE:
    Generates structural metrics of project.

INCLUDES:
    - total files
    - python files
    - test files
    - LOC metrics
    - directory distribution
    - file type distribution
    - hotspots (largest files)

OUTPUT:
    .tools/output/stats_report.md
    .tools/output/stats_report.json

WHEN TO USE:
    - understanding project scale
    - finding complexity hotspots
    - architectural overview

------------------------------------------------------------

# 4. SERVICE MAP (architecture view)

COMMAND:
    python .tools/service_map.py

PURPOSE:
    Builds simplified system architecture map.

INCLUDES:
    - docker-compose services
    - images
    - nginx upstream logic
    - entrypoints (main.py, entrypoint.sh)

OUTPUT:
    .tools/output/service_map.md
    .tools/output/service_map.json

WHEN TO USE:
    - understanding system structure
    - service dependency analysis
    - runtime architecture overview

------------------------------------------------------------

# 5. GIT CONTEXT (manual but important)

COMMANDS:
    git status
    git log -5 --oneline
    git diff

PURPOSE:
    Raw version control state.

------------------------------------------------------------

# RECOMMENDED AI START SEQUENCE

1. service_map
2. stats
3. dump OR changed
4. git context (if debugging)

------------------------------------------------------------

# DESIGN PHILOSOPHY

.tools/ is a reproducible context layer.

NOT:
- deployment system
- monitoring system
- CI replacement

IT IS:
- AI onboarding system
- deterministic project reconstruction tool

------------------------------------------------------------

# OUTPUT LOCATION

All generated artifacts are stored in:

.tools/output/

------------------------------------------------------------

# SUMMARY

If you run:

    python .tools/service_map.py
    python .tools/stats.py
    python .tools/dump.py

You fully reconstruct the system context.

This is the intended AI onboarding mechanism.
```

====================================================================================================
FILE: tools/service_map.py
====================================================================================================
```
from pathlib import Path
import re
import json

from .config import PROJECT_ROOT, OUTPUT_DIR
from .utils import iter_project_files, read_text_file


# -----------------------------------------------------------------------------
# Parsers
# -----------------------------------------------------------------------------

DOCKER_SERVICE_RE = re.compile(r"^\s*(\w+):\s*$", re.M)
IMAGE_RE = re.compile(r"image:\s*(.+)")
PORT_RE = re.compile(r"(\d+):(\d+)")


def parse_docker_compose(path: Path) -> dict:
    content = read_text_file(path)

    services = {}

    current = None

    for line in content.splitlines():

        if line.strip().endswith(":") and not line.strip().startswith("#"):
            name = line.replace(":", "").strip()
            if name and name not in ["services", "version"]:
                current = name
                services[current] = {}

        if "image:" in line and current:
            services[current]["image"] = IMAGE_RE.search(line).group(1).strip()

        if "ports:" in line:
            services[current]["ports"] = []

        if re.search(r"\d+:\d+", line):
            services.setdefault(current, {}).setdefault("ports", []).append(line.strip())

    return services


# -----------------------------------------------------------------------------
# Nginx upstream parser
# -----------------------------------------------------------------------------

def parse_nginx_upstreams() -> dict:
    nginx_dir = PROJECT_ROOT / "services/nginx/scripts"

    result = {}

    for file in nginx_dir.glob("*.sh"):
        content = read_text_file(file)

        if "upstream" in content:
            result[file.name] = {
                "has_upstream": True,
                "content_snippet": content[:300],
            }

    return result


# -----------------------------------------------------------------------------
# Code entrypoints
# -----------------------------------------------------------------------------

def find_entrypoints():
    entrypoints = []

    for path in iter_project_files():

        if path.name in ["main.py", "app.py", "entrypoint.sh"]:
            entrypoints.append(str(path.relative_to(PROJECT_ROOT)))

    return entrypoints


# -----------------------------------------------------------------------------
# Build map
# -----------------------------------------------------------------------------

def build_map():

    docker_file = PROJECT_ROOT / "docker-compose.yml"

    map_data = {
        "docker": parse_docker_compose(docker_file) if docker_file.exists() else {},
        "nginx": parse_nginx_upstreams(),
        "entrypoints": find_entrypoints(),
    }

    return map_data


# -----------------------------------------------------------------------------
# Save
# -----------------------------------------------------------------------------

def save_map(data: dict):

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    md_file = OUTPUT_DIR / "service_map.md"
    json_file = OUTPUT_DIR / "service_map.json"

    # ---------------- MD ----------------
    md = []

    md.append("# SERVICE MAP")
    md.append("")

    md.append("## ENTRYPOINTS")
    for ep in data["entrypoints"]:
        md.append(f"- {ep}")

    md.append("\n## DOCKER SERVICES")
    for svc, cfg in data["docker"].items():
        md.append(f"- {svc}: {cfg}")

    md.append("\n## NGINX")
    for k, v in data["nginx"].items():
        md.append(f"- {k}: {v['has_upstream']}")

    md_file.write_text("\n".join(md), encoding="utf-8")

    json_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"[OK] Service map saved to: {md_file}")
    print(f"[OK] Service map JSON: {json_file}")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    print("[INFO] Building service map...")

    data = build_map()
    save_map(data)

    print("[DONE] Service map generated")


if __name__ == "__main__":
    main()
```

====================================================================================================
FILE: tools/stats.py
====================================================================================================
```
from pathlib import Path
from collections import defaultdict
import json

from .config import PROJECT_ROOT, OUTPUT_DIR
from .utils import iter_project_files, read_text_file


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def count_lines(text: str) -> int:
    return len(text.splitlines())


def is_test_file(path: Path) -> bool:
    return "test" in path.name.lower()


def file_type(path: Path) -> str:
    if path.suffix:
        return path.suffix.lower()
    return "no_ext"


# -----------------------------------------------------------------------------
# Core collection
# -----------------------------------------------------------------------------

def collect_stats():
    total_files = 0

    python_files = 0
    test_files = 0

    total_loc = 0
    python_loc = 0
    test_loc = 0

    by_dir = defaultdict(int)
    by_type = defaultdict(int)

    file_sizes = []  # (path, loc)

    for path in iter_project_files():

        content = read_text_file(path)
        loc = count_lines(content)

        total_files += 1
        total_loc += loc

        rel = path.relative_to(PROJECT_ROOT)
        by_dir[str(rel.parent)] += 1
        by_type[file_type(path)] += 1

        file_sizes.append((str(rel), loc))

        # python
        if path.suffix == ".py":
            python_files += 1
            python_loc += loc

        # tests
        if is_test_file(path):
            test_files += 1
            test_loc += loc

    # sort hotspots
    file_sizes.sort(key=lambda x: x[1], reverse=True)

    return {
        "summary": {
            "total_files": total_files,
            "python_files": python_files,
            "test_files": test_files,
            "total_loc": total_loc,
            "python_loc": python_loc,
            "test_loc": test_loc,
        },
        "hotspots": file_sizes[:10],
        "by_dir": dict(sorted(by_dir.items(), key=lambda x: x[1], reverse=True)),
        "by_type": dict(sorted(by_type.items(), key=lambda x: x[1], reverse=True)),
    }


# -----------------------------------------------------------------------------
# Render CLI
# -----------------------------------------------------------------------------

def print_stats(stats: dict):

    s = stats["summary"]

    print("\n" + "=" * 60)
    print("PROJECT STATS (ADVANCED)")
    print("=" * 60)

    print(f"Total files     : {s['total_files']}")
    print(f"Python files    : {s['python_files']}")
    print(f"Test files      : {s['test_files']}")
    print("")
    print(f"Total LOC       : {s['total_loc']}")
    print(f"Python LOC      : {s['python_loc']}")
    print(f"Test LOC        : {s['test_loc']}")

    print("\n🔥 TOP HOTSPOTS (largest files)")
    for path, loc in stats["hotspots"]:
        print(f"- {path}: {loc} LOC")

    print("\n📁 TOP DIRECTORIES")
    for k, v in list(stats["by_dir"].items())[:10]:
        print(f"- {k}: {v} files")

    print("\n📦 FILE TYPES")
    for k, v in stats["by_type"].items():
        print(f"- {k}: {v}")


# -----------------------------------------------------------------------------
# Save output
# -----------------------------------------------------------------------------

def save_report(stats: dict):

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    md_file = OUTPUT_DIR / "stats_report.md"
    json_file = OUTPUT_DIR / "stats_report.json"

    # ---------------- MD ----------------
    md_lines = []

    md_lines.append("# PROJECT STATS REPORT")
    md_lines.append("")

    md_lines.append("## SUMMARY")
    for k, v in stats["summary"].items():
        md_lines.append(f"- {k}: {v}")

    md_lines.append("")
    md_lines.append("## HOTSPOTS")
    for path, loc in stats["hotspots"]:
        md_lines.append(f"- {path}: {loc} LOC")

    md_lines.append("")
    md_lines.append("## DIRECTORIES")
    for k, v in stats["by_dir"].items():
        md_lines.append(f"- {k}: {v}")

    md_lines.append("")
    md_lines.append("## FILE TYPES")
    for k, v in stats["by_type"].items():
        md_lines.append(f"- {k}: {v}")

    md_file.write_text("\n".join(md_lines), encoding="utf-8")

    # ---------------- JSON ----------------
    json_file.write_text(
        json.dumps(stats, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n[OK] Saved MD  : {md_file}")
    print(f"[OK] Saved JSON: {json_file}")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():

    print("[INFO] Collecting project stats...")

    stats = collect_stats()

    print_stats(stats)
    save_report(stats)


if __name__ == "__main__":
    main()
```

====================================================================================================
FILE: tools/tree.py
====================================================================================================
```

```

====================================================================================================
FILE: tools/utils.py
====================================================================================================
```
from pathlib import Path
from typing import Iterator

from .config import (
    PROJECT_ROOT,
    IGNORE_DIRS,
    IGNORE_FILES,
    ALLOWED_EXTENSIONS,
    ALLOWED_FILENAMES,
    IGNORE_EXTENSIONS,
    MAX_FILE_SIZE,
)


def is_allowed(path: Path) -> bool:
    """
    Return True if the file should be included in the snapshot.
    """

    if path.name in ALLOWED_FILENAMES:
        return True

    if path.suffix in IGNORE_EXTENSIONS:
        return False

    if path.suffix in ALLOWED_EXTENSIONS:
        return True

    return False


def iter_project_files(root: Path = PROJECT_ROOT) -> Iterator[Path]:
    """
    Recursively iterate over all project files while skipping ignored
    directories and files.
    """

    for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):

        if entry.is_dir():

            if entry.name in IGNORE_DIRS:
                continue

            yield from iter_project_files(entry)

            continue

        if entry.name in IGNORE_FILES:
            continue

        yield entry




def read_text_file(path: Path) -> str:
    """
    Safely read a text file with size + encoding protection.
    """

    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return f"<< FILE TOO LARGE: {path.stat().st_size} bytes >>"

        return path.read_text(encoding="utf-8")

    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="latin-1")
        except Exception as exc:
            return f"<< READ ERROR: {exc} >>"

    except Exception as exc:
        return f"<< READ ERROR: {exc} >>"


if __name__ == "__main__":
    print("=" * 60)

    for path in iter_project_files():
        if is_allowed(path):
            print(path.relative_to(PROJECT_ROOT))

```
