"""
Тесты для админ-панели SQLAdmin
"""

import pytest
from shared.settings import get_settings

pytest = pytest.mark.asyncio


async def test_admin_login_page_accessible(client):
    """Страница логина доступна"""
    response = await client.get("/admin/login")
    assert response.status_code == 200


async def test_admin_panel_redirects_to_login(client):
    """Без логина админка редиректит на логин"""
    response = await client.get("/admin", follow_redirects=False)
    assert response.status_code == 307 or response.status_code == 302


async def test_admin_login_with_correct_credentials(client):
    """Вход с правильными данными"""
    settings = get_settings()

    login_data = {
        "username": settings.admin_username,
        "password": settings.admin_password,
    }
    response = await client.post("/admin/login", data=login_data, follow_redirects=True)
    assert response.status_code == 200


async def test_repair_request_list_accessible_after_login(client):
    """После входа список заявок доступен"""
    # Логинимся
    await client.post(
        "/admin/login", data={"username": "admin", "password": "repair_crm_2026"}
    )
    # Проверяем список
    response = await client.get("/admin/repair-request/list")
    assert response.status_code == 200
