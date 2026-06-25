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