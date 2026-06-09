#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json

ACTIVE=$(cat "$STATE_FILE" 2>/dev/null | jq -r '.active // "blue"' || echo "blue")

echo "[STATE] active=$ACTIVE"