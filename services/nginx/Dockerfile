FROM nginx:alpine

RUN apk add --no-cache gettext
RUN apk add --no-cache inotify-tools

COPY nginx-https.conf /etc/nginx/nginx-https.conf
COPY nginx-http.conf /etc/nginx/nginx-http.conf
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]