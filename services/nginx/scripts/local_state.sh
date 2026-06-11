#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json

echo "[LOCAL] generating default state"

cat > "$STATE_FILE" <<EOF
{
  "deploy_id": "local",
  "rollback_locked": false,
  "services": {
    "gateway": {
      "strategy": "blue-green",
      "active": "blue",
      "port": 8000,
      "healthcheck": "/health"
    }
  }
}
EOF