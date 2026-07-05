from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth_router

app = FastAPI(
    title="Auth Service",
    version="0.1.0",
    description="Сервис аутентификации и авторизации",
    root_path="/auth",  # ← для красивых URL
)

# CORS (для разработки)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутер
app.include_router(auth_router)


@app.get("/health")
async def health():
    """Проверка здоровья сервиса"""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Корневой путь"""
    return {"service": "Auth Service", "status": "running"}
