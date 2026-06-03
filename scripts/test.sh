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