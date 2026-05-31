FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/gateway ./services/gateway
COPY shared ./shared

COPY alembic.ini .