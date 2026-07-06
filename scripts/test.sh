#!/bin/bash
set -e

TEST_PATH=${1:-tests}
FULL_TEST=${FULL_TEST:-false}

# Если FULL_TEST=false — это отдельный тест, нужно поднять инфру
if [ "$FULL_TEST" = "false" ]; then
  echo "🚀 Starting infrastructure for single test..."

  # Всегда поднимаем с нуля для отдельных тестов
  docker compose \
    -f docker-compose.yml \
    -f docker-compose.test.yml \
    down -v 2>/dev/null || true

  docker compose \
    -f docker-compose.yml \
    -f docker-compose.test.yml \
    up -d --build
else
  # FULL_TEST=true — проверяем, запущена ли инфраструктура
  if docker compose -f docker-compose.yml -f docker-compose.test.yml ps --quiet postgres 2>/dev/null | grep -q .; then
    echo "✅ Infrastructure already running, reusing..."
  else
    echo "🚀 Starting infrastructure for full test..."
    docker compose \
      -f docker-compose.yml \
      -f docker-compose.test.yml \
      up -d --build
  fi
fi

# Функция получения статуса health контейнера
get_health() {
  local container_name=$1
  docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none"
}

# Функция ожидания healthy статуса
wait_for_health() {
  local service_name=$1
  echo "⏳ Waiting for $service_name..."

  local max_attempts=30
  local attempt=0

  while [ $attempt -lt $max_attempts ]; do
    # Получаем ID контейнера по имени сервиса
    local container_id=$(docker compose -f docker-compose.yml -f docker-compose.test.yml ps -q "$service_name" 2>/dev/null)

    if [ -n "$container_id" ]; then
      local status=$(get_health "$container_id")
      if [ "$status" = "healthy" ]; then
        echo "✅ $service_name is healthy"
        return 0
      fi
    fi

    attempt=$((attempt + 1))
    sleep 2
  done

  echo "❌ $service_name failed to become healthy after $max_attempts attempts"
  exit 1
}

echo "⏳ Waiting for services..."
wait_for_health postgres
wait_for_health gateway-blue

# Создаем test database
echo "Creating test database..."
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE repair_crm_test" 2>/dev/null || true

echo "Applying migrations..."
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test alembic upgrade head

echo "🧪 Running tests..."
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/repair_crm_test
pytest "$TEST_PATH" -v

# Если FULL_TEST=false — останавливаем
if [ "$FULL_TEST" = "false" ]; then
  echo "🧹 Cleaning up..."
  docker compose -f docker-compose.yml -f docker-compose.test.yml down -v
else
  echo "⏭️ Skipping teardown (full test mode)"
fi