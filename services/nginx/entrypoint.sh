#!/bin/sh
set -e

DOMAIN=${DOMAIN_NAME:-localhost}
CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
STATE_DIR="/etc/letsencrypt/live/$DOMAIN"

echo "Starting nginx bootstrap..."

load_config() {
  if [ -f "$CERT" ]; then
    echo "SSL mode ON"
    envsubst '$DOMAIN_NAME' \
      < /etc/nginx/nginx-https.conf \
      > /etc/nginx/nginx.conf
  else
    echo "SSL mode OFF (HTTP only)"
    envsubst '$DOMAIN_NAME' \
      < /etc/nginx/nginx-http.conf \
      > /etc/nginx/nginx.conf
  fi
}

reload_nginx() {
  # reload lock (anti-spam)
  NOW=$(date +%s)
  LAST_FILE="/tmp/nginx_last_reload"

  LAST=0
  if [ -f "$LAST_FILE" ]; then
    LAST=$(cat "$LAST_FILE")
  fi

  DIFF=$((NOW - LAST))

  if [ "$DIFF" -lt 2 ]; then
    echo "Reload skipped (lock active)"
    return
  fi

  echo "$NOW" > "$LAST_FILE"
  echo "Reloading nginx..."
  nginx -s reload
}

# initial setup
load_config

# start nginx
nginx -g 'daemon off;' &
NGINX_PID=$!

echo "Watching certificate directory..."

# ========== ИЗМЕНЕНИЕ ТУТ ==========
# Ждем появления папки перед запуском inotifywait
while [ ! -d "$STATE_DIR" ]; do
  echo "Waiting for $STATE_DIR to be created..."
  sleep 2
done
# ==================================

# event-driven watcher
inotifywait -m -r -e create -e modify -e moved_to "$STATE_DIR" |
while read -r _; do
  echo "Certificate change detected"

  load_config
  reload_nginx
done &

wait $NGINX_PID