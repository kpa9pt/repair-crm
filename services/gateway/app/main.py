from fastapi import FastAPI
from shared import get_settings
from .routers import repair_requests_router
from .admin import AdminAuth, RepairRequestAdmin
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware
from shared.db import get_engine  # ← импортируем новую функцию
from fastapi.responses import RedirectResponse


settings = get_settings()

app = FastAPI(
    title="Gateway API",
    version="0.1.0",
    description="API Gateway для CRM ремонтной мастерской",
)

# Добавляем middleware для сессий (нужен для аутентификации админки)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key or "supersecretkey-change-in-production",
    session_cookie="admin_session",
)

# Настройка админ-панели
authentication_backend = AdminAuth(secret_key=settings.secret_key or "supersecretkey")
admin = Admin(
    app,
    get_engine(),  # ← используем get_engine()
    authentication_backend=authentication_backend,
    title="Repair CRM Admin",
    logo_url="/static/logo.png",  # опционально
    base_url="/admin",  # ← ЯВНО УКАЗЫВАЕМ URL
)

# Регистрируем модели
admin.add_view(RepairRequestAdmin)

# Подключаем роутеры
app.include_router(repair_requests_router)


@app.get("/")
async def root():
    return RedirectResponse("/admin/")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/test_blue_green")
async def test_blue_green():
    return {"status": "ok"}


#
# @app.get("/test_check_diff")
# async def test_check_diff():
#     return {"status": "ok"}
