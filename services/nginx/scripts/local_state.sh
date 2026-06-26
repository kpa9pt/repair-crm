#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json
#dfff
echo "[LOCAL] generating default state"

cat > "$STATE_FILE" <<EOF
{
  "deploy_id": "local",
  "services": {
    "gateway": {
      "strategy": "blue-green",
      "active": "blue",
      "port": 8000,
      "healthcheck": "/health",
      "rollback_locked": false,
       "compose_hash": ""
    }
  }
}
EOF