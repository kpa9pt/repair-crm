#!/bin/sh
set -e

DOMAIN=${DOMAIN_NAME:-localhost}

CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

echo "🚀 Certbot service started for domain: $DOMAIN"

# 1. бесконечный цикл "поддержки сертификата"
while true; do

  # если сертификата НЕТ → выпускаем
  if [ ! -f "$CERT_PATH" ]; then
    echo "📦 No cert found, requesting new certificate..."

    certbot certonly \
      --webroot \
      --webroot-path=/var/www/certbot \
      --email admin@$DOMAIN \
      --agree-tos \
      --no-eff-email \
      -d "$DOMAIN" \
      --non-interactive

    echo "✅ Certificate issued"
    docker exec nginx nginx -s reload
  fi

  # 2. пробуем обновить (если уже есть)
  certbot renew \
    --webroot \
    --webroot-path=/var/www/certbot \
    --quiet

  echo "🔄 Renewal check done"
  docker exec nginx nginx -s reload

  # 3. ждём (certbot не нужен каждую минуту)
  sleep 12h
done