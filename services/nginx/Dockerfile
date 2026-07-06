FROM nginx:alpine

RUN apk add --no-cache gettext inotify-tools bash jq



COPY services/nginx/nginx-https.conf /etc/nginx/nginx-https.conf
COPY services/nginx/nginx-http.conf /etc/nginx/nginx-http.conf
# Копируем картинки в образ
COPY services/nginx/favicon.ico /usr/share/nginx/html/favicon.ico
COPY services/nginx/logo.png /usr/share/nginx/html/static/logo.png

# 👇 ВСЕ скрипты в одну папку
COPY services/nginx/scripts/ /scripts/

RUN chmod +x /scripts/*.sh

ENTRYPOINT ["/scripts/entrypoint.sh"]