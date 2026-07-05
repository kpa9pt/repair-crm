"""
API тесты для эндпоинтов RepairRequest.
"""

from shared.enums import Urgency, RequestStatus
import pytest

pytestmark = pytest.mark.asyncio


async def test_create_repair_request(client, admin_token):
    """Тест создания заявки через API (авторизованный)"""
    request_data = {
        "vehicle_name": "Тестовый квадроцикл",
        "description": "Не заводится тестовая заявка",
        "urgency": Urgency.NORMAL.value,
        "status": RequestStatus.NEW.value,
    }

    response = await client.post(
        "/api/v1/repair-requests/",
        json=request_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["vehicle_name"] == request_data["vehicle_name"]
    assert data["description"] == request_data["description"]
    assert "id" in data
    assert "created_at" in data
    assert "created_by_username" in data
    assert data["created_by_username"] == "admin"


async def test_create_repair_request_invalid_data(client, admin_token):
    """Тест создания заявки с невалидными данными"""
    response = await client.post(
        "/api/v1/repair-requests/",
        json={"description": "Только описание"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


async def test_get_all_repair_requests(client, admin_token):
    """Тест получения списка всех заявок"""
    # Создаем тестовые данные
    for i in range(3):
        response = await client.post(
            "/api/v1/repair-requests/",
            json={"vehicle_name": f"Техника {i}", "description": f"Описание {i}"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201

    response = await client.get(
        "/api/v1/repair-requests/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 3


async def test_get_repair_request_by_id(client, admin_token):
    """Тест получения конкретной заявки по ID"""
    # Создаем
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={
            "vehicle_name": "Уникальная техника",
            "description": "Уникальное описание",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Получаем
    response = await client.get(
        f"/api/v1/repair-requests/{created_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == created_id


async def test_get_nonexistent_repair_request(client, admin_token):
    """Тест получения несуществующей заявки"""
    response = await client.get(
        "/api/v1/repair-requests/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


async def test_update_repair_request(client, admin_token):
    """Тест частичного обновления заявки"""
    # Создаем
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={
            "vehicle_name": "Техника для обновления",
            "description": "Оригинальное описание",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Обновляем статус
    response = await client.patch(
        f"/api/v1/repair-requests/{created_id}",
        json={"status": RequestStatus.IN_PROGRESS.value},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == RequestStatus.IN_PROGRESS.value
    assert response.json()["vehicle_name"] == "Техника для обновления"


async def test_delete_repair_request(client, admin_token):
    """Тест удаления заявки"""
    # Создаем
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={"vehicle_name": "Техника для удаления", "description": "Будет удалена"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Удаляем
    delete_response = await client.delete(
        f"/api/v1/repair-requests/{created_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_response.status_code == 204

    # Проверяем что удалена
    get_response = await client.get(
        f"/api/v1/repair-requests/{created_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_response.status_code == 404


async def test_pagination(client, admin_token):
    """Тест пагинации"""
    # Создаем 10 заявок
    for i in range(10):
        response = await client.post(
            "/api/v1/repair-requests/",
            json={"vehicle_name": f"Пагинация {i}", "description": f"Описание {i}"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201

    # Проверяем страницы
    resp1 = await client.get(
        "/api/v1/repair-requests/?skip=0&limit=5",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp1.status_code == 200
    assert len(resp1.json()["items"]) == 5

    resp2 = await client.get(
        "/api/v1/repair-requests/?skip=5&limit=5",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 200
    assert len(resp2.json()["items"]) == 5


async def test_get_by_vehicle_name(client, admin_token):
    """Тест фильтрации по имени техники"""
    # Создаем заявки для конкретной техники
    for i in range(2):
        response = await client.post(
            "/api/v1/repair-requests/",
            json={"vehicle_name": "Специальная техника", "description": f"Заявка {i}"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201

    # Создаем заявку для другой техники
    response = await client.post(
        "/api/v1/repair-requests/",
        json={"vehicle_name": "Другая техника", "description": "Чужая заявка"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201

    response = await client.get(
        "/api/v1/repair-requests/vehicle/Специальная техника",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2


async def test_unauthorized_access(client):
    """Тест доступа без токена → 401"""
    response = await client.get("/api/v1/repair-requests/")
    assert response.status_code == 401

    response = await client.post(
        "/api/v1/repair-requests/",
        json={"vehicle_name": "Тест", "description": "Тест"},
    )
    assert response.status_code == 401


async def test_create_repair_request_as_instructor(client, instructor_token):
    """Тест создания заявки от имени instructor"""
    request_data = {
        "vehicle_name": "Тест инструктора",
        "description": "Создано инструктором",
    }

    response = await client.post(
        "/api/v1/repair-requests/",
        json=request_data,
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["created_by_username"] == "instructor1"


async def test_delete_repair_request_as_instructor(
    client, instructor_token, admin_token
):
    """Тест: instructor не может удалять заявки → 403"""
    # Создаем заявку (от имени admin)
    create_response = await client.post(
        "/api/v1/repair-requests/",
        json={"vehicle_name": "Тест удаления", "description": "Будет удалена"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    request_id = create_response.json()["id"]

    # Пытаемся удалить от имени instructor
    delete_response = await client.delete(
        f"/api/v1/repair-requests/{request_id}",
        headers={"Authorization": f"Bearer {instructor_token}"},
    )
    assert delete_response.status_code == 403
