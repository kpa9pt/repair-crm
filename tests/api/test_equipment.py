"""API тесты для эндпоинтов Equipment"""

import pytest


@pytest.mark.asyncio
async def test_create_equipment(client):
    """Тест создания техники через API"""
    data = {
        "name": "Тестовый квадроцикл",
        "type": "квадроцикл",
        "serial_number": "TEST-001",
        "owner_name": "Тестовый владелец",
        "owner_phone": "+7-999-000-00-00",
    }
    response = await client.post("/api/v1/equipment/", json=data)
    assert response.status_code == 201
    result = response.json()
    assert result["name"] == data["name"]
    assert result["type"] == data["type"]
    assert "id" in result
    assert "created_at" in result


@pytest.mark.asyncio
async def test_get_equipment_list(client):
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
        )

    response = await client.get("/api/v1/equipment/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_get_equipment_by_id(client):
    """Тест получения техники по ID"""
    # Создаем
    create_response = await client.post(
        "/api/v1/equipment/",
        json={
            "name": "Уникальная техника",
            "type": "уникальный тип",
            "serial_number": "UNIQUE-001",
        },
    )
    assert create_response.status_code == 201
    equipment_id = create_response.json()["id"]

    # Получаем
    response = await client.get(f"/api/v1/equipment/{equipment_id}")
    assert response.status_code == 200
    assert response.json()["id"] == equipment_id
    assert response.json()["name"] == "Уникальная техника"


@pytest.mark.asyncio
async def test_update_equipment(client):
    """Тест обновления техники"""
    # Создаем
    create_response = await client.post(
        "/api/v1/equipment/", json={"name": "Старое название", "type": "старый тип"}
    )
    assert create_response.status_code == 201
    equipment_id = create_response.json()["id"]

    # Обновляем
    response = await client.put(
        f"/api/v1/equipment/{equipment_id}", json={"name": "Новое название"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Новое название"


@pytest.mark.asyncio
async def test_delete_equipment(client):
    """Тест удаления техники"""
    # Создаем
    create_response = await client.post(
        "/api/v1/equipment/", json={"name": "Техника для удаления", "type": "тип"}
    )
    assert create_response.status_code == 201
    equipment_id = create_response.json()["id"]

    # Удаляем
    response = await client.delete(f"/api/v1/equipment/{equipment_id}")
    assert response.status_code == 204

    # Проверяем что удалена
    get_response = await client.get(f"/api/v1/equipment/{equipment_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_search_equipment(client):
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
    )

    # Ищем по имени
    response = await client.get("/api/v1/equipment/?search=поисковая")
    assert response.status_code == 200
    assert response.json()["total"] >= 1

    # Ищем по серийному номеру
    response = await client.get("/api/v1/equipment/?search=SEARCH-001")
    assert response.status_code == 200
    assert response.json()["total"] >= 1
