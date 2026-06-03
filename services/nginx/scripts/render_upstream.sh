#!/bin/sh
set -e

STATE=$(cat /etc/nginx/state/active 2>/dev/null || echo "blue")

echo "[RENDER] state=$STATE"

case "$STATE" in
  green)
    SERVER="gateway-green:8000"
    ;;
  *)
    SERVER="gateway-blue:8000"
    ;;
esac

cat > /etc/nginx/upstream.conf <<EOF
upstream gateway_backend {
  server $SERVER max_fails=3 fail_timeout=10s;
}
EOF

echo "[RENDER] upstream -> $SERVER"