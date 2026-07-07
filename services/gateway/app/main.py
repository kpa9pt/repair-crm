from fastapi import FastAPI
from shared import get_settings
from .routers import repair_requests_router, equipment_router
from .admin import AdminAuth, RepairRequestAdmin, EquipmentAdmin
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware
from shared.db import get_engine  # ← импортируем новую функцию
from fastapi.responses import RedirectResponse
from fastapi import Request
from starlette.middleware.proxy_headers import ProxyHeadersMiddleware

settings = get_settings()

app = FastAPI(
    title="Gateway API",
    version="0.1.0",
    description="API Gateway для CRM ремонтной мастерской",
    root_path="/gateway",
    root_path_in_servers=True,  # ← ДОБАВИТЬ ЭТО
)

# ✅ ДОБАВИТЬ ЭТО
app.add_middleware(
    ProxyHeadersMiddleware,
    trusted_hosts=["*"],
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
admin.add_view(EquipmentAdmin)  # ← добавить

# Подключаем роутеры
app.include_router(repair_requests_router)

app.include_router(equipment_router)


@app.get("/")
async def root(request: Request):
    # base_url включает root_path
    admin_url = str(request.base_url) + "admin/"
    return RedirectResponse(url=admin_url)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/test_blue_green")
async def test_blue_green():
    return {"status": "ok"}


# @app.get("/test_check_diff")
# async def test_check_diff():
#     return {"status": "ok"}
