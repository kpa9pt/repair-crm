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