#!/bin/sh
set -e

mkdir -p /etc/nginx/state

if [ ! -f /etc/nginx/state/active ]; then
  echo "blue" > /etc/nginx/state/active
fi

echo "[STATE] active=$(cat /etc/nginx/state/active)"