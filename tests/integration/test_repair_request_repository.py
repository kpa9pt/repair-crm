"""
Интеграционные тесты для репозитория RepairRequest.
"""

import pytest
from shared.repository import RepairRequestRepository


@pytest.mark.asyncio
async def test_repository_create(test_session):
    """Тест создания заявки через репозиторий"""
    repo = RepairRequestRepository(test_session)
    request = await repo.create(vehicle_name="Квадроцикл-5", description="Не заводится")
    assert request.id is not None
    assert request.vehicle_name == "Квадроцикл-5"
    assert request.description == "Не заводится"
