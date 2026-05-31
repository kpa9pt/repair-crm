#!/bin/sh
set -e

DOMAIN=${DOMAIN_NAME:-localhost}
CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

echo "Generating nginx config..."

if [ -f "$CERT" ]; then
  echo "SSL mode ON"
  # shellcheck disable=SC2016
  envsubst '$DOMAIN_NAME' \
  < /etc/nginx/nginx-https.conf \
  > /etc/nginx/nginx.conf
else
  echo "SSL mode OFF (HTTP only)"
  # shellcheck disable=SC2016
  envsubst '$DOMAIN_NAME' \
  < /etc/nginx/nginx-http.conf \
  > /etc/nginx/nginx.conf
fi


nginx -g 'daemon off;'