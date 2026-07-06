# services/telegram-bot/Dockerfile
FROM python:3.14-slim

WORKDIR /app

COPY services/telegram-bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/telegram-bot /app
COPY shared /app/shared

ENV PYTHONPATH=/app

CMD ["python", "main.py"]