FROM nginx:alpine

RUN apk add --no-cache gettext inotify-tools bash jq



COPY services/nginx/nginx-https.conf /etc/nginx/nginx-https.conf
COPY services/nginx/nginx-http.conf /etc/nginx/nginx-http.conf

# 👇 ВСЕ скрипты в одну папку
COPY services/nginx/scripts/ /scripts/

RUN chmod +x /scripts/*.sh

ENTRYPOINT ["/scripts/entrypoint.sh"]