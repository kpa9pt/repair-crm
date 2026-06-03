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