FROM nginx:alpine

#WORKDIR /app

RUN apk add --no-cache gettext
RUN apk add --no-cache inotify-tools

COPY services/nginx/nginx-https.conf /etc/nginx/nginx-https.conf
COPY services/nginx/nginx-http.conf /etc/nginx/nginx-http.conf
COPY services/nginx/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]