FROM certbot/certbot:latest

#WORKDIR /app

RUN apk add --no-cache bash docker-cli



COPY services/certbot/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]