from fastapi import FastAPI
from shared import get_settings
from .routers import repair_requests_router

settings = get_settings()

app = FastAPI(
    title="Gateway API",
    version="0.1.0",
    description="API Gateway для CRM ремонтной мастерской",
)

# Подключаем роутеры
app.include_router(repair_requests_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
