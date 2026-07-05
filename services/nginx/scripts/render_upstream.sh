#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json

mkdir -p /etc/nginx/upstreams

rm -f /etc/nginx/upstreams/*.conf 2>/dev/null || true

echo "[RENDER] state=$STATE_FILE"

jq -r '
  .services
  | to_entries[]
  | select(.value.strategy == "blue-green")
  | "\(.key) \(.value.active) \(.value.port)"
' "$STATE_FILE" |
while read SERVICE ACTIVE PORT
do

cat >> "/etc/nginx/upstreams/upstream.conf" <<EOF
upstream ${SERVICE}_backend {
  server ${SERVICE}-${ACTIVE}:${PORT} max_fails=3 fail_timeout=10s;
}
EOF

echo "[RENDER] ${SERVICE} -> ${SERVICE}-${ACTIVE}:${PORT}"

done