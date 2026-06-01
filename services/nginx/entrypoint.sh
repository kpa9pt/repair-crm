#!/bin/sh
set -e

DOMAIN=${DOMAIN_NAME:-localhost}
CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
WATCH_DIR="/etc/letsencrypt/live"

echo "Starting nginx bootstrap..."

# Если localhost - просто запускаем HTTP и выходим (без watcher'а)
if [ "$DOMAIN" = "localhost" ]; then
  echo "Localhost mode detected, running HTTP only"
  envsubst '$DOMAIN_NAME' < /etc/nginx/nginx-http.conf > /etc/nginx/nginx.conf
  exec nginx -g 'daemon off;'
fi

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

# Ждем появления папки перед запуском inotifywait
while [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; do
  echo "Waiting for /etc/letsencrypt/live/$DOMAIN to be created..."
  sleep 2
done

# Правильный watcher: следим за родительской папкой, фильтруем по домену
inotifywait -m -r -e create -e modify -e moved_to --format '%w%f' "$WATCH_DIR" 2>/dev/null |
while read -r FILE; do
  # Реагируем на создание папки домена или изменение файлов внутри нее
  case "$FILE" in
    *"/$DOMAIN/"*|*"/$DOMAIN")
      echo "Change detected: $FILE"
      load_config
      reload_nginx
      ;;
  esac
done &

wait $NGINX_PID