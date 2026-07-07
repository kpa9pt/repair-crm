from fastapi import FastAPI
from shared import get_settings
from .routers import repair_requests_router, equipment_router
from .admin import AdminAuth, RepairRequestAdmin, EquipmentAdmin
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from shared.db import get_engine
from fastapi.responses import RedirectResponse
from fastapi import Request

settings = get_settings()


class ForceHTTPSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # ✅ Если Nginx сказал что запрос пришел по HTTPS — доверяем
        if request.headers.get("X-Forwarded-Proto") == "https":
            request.scope["scheme"] = "https"

        # ✅ Если это healthcheck — вообще не трогаем
        if request.url.path == "/health":
            response = await call_next(request)
            return response

        response = await call_next(request)
        return response


app = FastAPI(
    title="Gateway API",
    version="0.1.0",
    description="API Gateway для CRM ремонтной мастерской",
    root_path="/gateway",
    root_path_in_servers=True,
)

app.add_middleware(ForceHTTPSMiddleware)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key or "supersecretkey-change-in-production",
    session_cookie="admin_session",
)

authentication_backend = AdminAuth(secret_key=settings.secret_key or "supersecretkey")
admin = Admin(
    app,
    get_engine(),
    authentication_backend=authentication_backend,
    title="Repair CRM Admin",
    logo_url="/static/logo.png",
    base_url="/admin",
)

admin.add_view(RepairRequestAdmin)
admin.add_view(EquipmentAdmin)

app.include_router(repair_requests_router)
app.include_router(equipment_router)


@app.get("/")
async def root(request: Request):
    admin_url = str(request.base_url) + "admin/"
    return RedirectResponse(url=admin_url)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/test_blue_green")
async def test_blue_green():
    return {"status": "ok"}
