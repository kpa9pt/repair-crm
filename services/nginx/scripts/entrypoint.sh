#!/bin/sh
set -e

echo "[BOOT] nginx starting"

echo "[STEP] init state"
/scripts/init_state.sh

echo "[STEP] render upstream"
/scripts/render_upstream.sh

echo "[STEP] generate nginx config"
/scripts/nginx_config.sh

echo "[STEP] nginx test"
nginx -t

echo "[STEP] start nginx"
nginx -g 'daemon off;' &
NGINX_PID=$!

echo "[STEP] watcher start"
/scripts/watcher.sh &

wait $NGINX_PID