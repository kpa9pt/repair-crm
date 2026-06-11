#!/bin/sh
set -e

STATE_FILE=/etc/nginx/state/state.json

echo "[STATE] checking state file"

# если это директория — это сломанный volume
if [ -d "$STATE_FILE" ]; then
  echo "[STATE] ERROR: state.json is directory, fixing"
  rm -rf "$STATE_FILE"
fi

# если файла нет — создаём
if [ ! -f "$STATE_FILE" ]; then
  echo "[STATE] state.json missing, generating local state"
  /scripts/local_state.sh
fi

echo "[STATE] state loaded"