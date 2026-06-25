FROM python:3.11-slim

RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY services/watchdog /app
COPY scripts/rollback.py /scripts/rollback.py

CMD ["python", "main.py"]