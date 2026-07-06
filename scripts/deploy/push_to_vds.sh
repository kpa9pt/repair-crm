#!/bin/bash
set -e

echo "=== PUSH TO VDS START ==="
date
whoami
pwd

cd ~/repair-crm

echo "=== UPDATE COMPOSE ==="
for i in {1..3}; do
    echo "Attempt $i to download docker-compose.yml..."
    if curl -fsSL --connect-timeout 10 --max-time 30 \
        https://raw.githubusercontent.com/kpa9pt/repair-crm/main/docker-compose.yml \
        -o docker-compose.yml; then
        echo "✅ docker-compose.yml downloaded"
        break
    fi
    echo "❌ Attempt $i failed, waiting 5 seconds..."
    sleep 5
done

if [ ! -f docker-compose.yml ]; then
    echo "❌ Failed to download docker-compose.yml after 3 attempts"
    exit 1
fi

echo "=== CREATE VOLUME ==="
docker volume create repair_crm_postgres_data || true

echo "=== DOCKER COMPOSE UP ==="
docker compose up -d

echo "=== DONE ==="
docker ps