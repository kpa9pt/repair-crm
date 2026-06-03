start_watcher() {
  WATCH_DIR="/etc/letsencrypt/live"
  DOMAIN=${DOMAIN_NAME:-localhost}

  echo "[WATCHER] started"

  # ждём появления папки (важно для certbot bootstrap)
  while [ ! -d "$WATCH_DIR/$DOMAIN" ]; do
    echo "[WATCHER] waiting cert dir..."
    sleep 2
  done

  echo "[WATCHER] cert dir ready"

  inotifywait -m -r -e create -e modify -e moved_to "$WATCH_DIR" |
  while read -r FILE; do
    case "$FILE" in
      *"/$DOMAIN/"*)
        echo "[WATCHER] change detected: $FILE"

        render_upstream
        nginx -s reload
        ;;
    esac
  done
}