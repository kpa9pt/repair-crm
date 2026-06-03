#!/bin/sh
set -e

echo "[BOOT] nginx starting"

echo "[STEP] init state"
/scripts/render.sh init

echo "[STEP] render config"
/scripts/render.sh render

echo "[STEP] nginx test"
nginx -t || exit 1

echo "[STEP] start nginx"
nginx -g 'daemon off;' &
NGINX_PID=$!

echo "[STEP] watcher start"
/scripts/watcher.sh &

wait $NGINX_PID