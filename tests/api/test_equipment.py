"""API тесты для эндпоинтов Equipment"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_equipment(client, admin_token):
    """Тест создания техники через API (авторизованный)"""
    data = {
        "name": "Тестовый квадроцикл",
        "type": "квадроцикл",
        "serial_number": "TEST-001",
        "owner_name": "Тестовый владелец",
        "owner_phone": "+7-999-000-00-00",
    }
    response = await client.post(
        "/api/v1/equipment/",
        json=data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    result = response.json()
    assert result["name"] == data["name"]
    assert result["type"] == data["type"]
    assert "id" in result
    assert "created_at" in result


async def test_get_equipment_list(client, admin_token):
    """Тест получения списка техники"""
    # Создаем несколько записей
    for i in range(3):
        await client.post(
            "/api/v1/equipment/",
            json={
                "name": f"Техника {i}",
                "type": f"тип {i}",
                "serial_number": f"SN-{i}",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    response = await client.get(
        "/api/v1/equipment/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 3


async def test_get_equipment_by_id(client, admin_token):
    """Тест получения техники по ID"""
    # Создаем
    create_response = await client.post(
        "/api/v1/equipment/",
        json={
            "name": "Уникальная техника",
            "type": "уникальный тип",
            "serial_number": "UNIQUE-001",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    equipment_id = create_response.json()["id"]

    # Получаем
    response = await client.get(
        f"/api/v1/equipment/{equipment_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == equipment_id
    assert response.json()["name"] == "Уникальная техника"


async def test_update_equipment(client, admin_token):
    """Тест обновления техники"""
    # Создаем
    create_response = await client.post(
        "/api/v1/equipment/",
        json={"name": "Старое название", "type": "старый тип"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    equipment_id = create_response.json()["id"]

    # Обновляем
    response = await client.put(
        f"/api/v1/equipment/{equipment_id}",
        json={"name": "Новое название"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Новое название"


async def test_delete_equipment(client, admin_token):
    """Тест удаления техники"""
    # Создаем
    create_response = await client.post(
        "/api/v1/equipment/",
        json={"name": "Техника для удаления", "type": "тип"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    equipment_id = create_response.json()["id"]

    # Удаляем
    response = await client.delete(
        f"/api/v1/equipment/{equipment_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    # Проверяем что удалена
    get_response = await client.get(
        f"/api/v1/equipment/{equipment_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_response.status_code == 404


async def test_search_equipment(client, admin_token):
    """Тест поиска техники"""
    # Создаем
    await client.post(
        "/api/v1/equipment/",
        json={
            "name": "Поисковая техника",
            "type": "тип",
            "serial_number": "SEARCH-001",
            "owner_name": "Иван Петров",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Ищем по имени
    response = await client.get(
        "/api/v1/equipment/?search=поисковая",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1

    # Ищем по серийному номеру
    response = await client.get(
        "/api/v1/equipment/?search=SEARCH-001",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1
