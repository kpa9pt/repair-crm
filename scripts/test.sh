#!/bin/bash
set -e

echo "🚀 Starting infrastructure..."
docker compose up -d --build

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

  until [ "$(get_health "$id")" = "healthy" ]; do
    sleep 2
  done

  echo "✅ $name is healthy"
}

echo "⏳ Waiting for services..."

wait_for_health postgres
wait_for_health gateway

echo "🧪 Running tests..."
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/orders
pytest tests -v

echo "🧹 Cleaning up..."
docker compose down -v