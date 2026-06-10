#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json

ACTIVE=$(
  jq -r '.services.gateway.active // "blue"' \
  "$STATE_FILE" 2>/dev/null || echo "blue"
)
echo "[STATE] active=$ACTIVE"