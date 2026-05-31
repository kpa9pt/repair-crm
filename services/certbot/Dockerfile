FROM certbot/certbot:latest

RUN apk add --no-cache bash docker-cli

WORKDIR /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]