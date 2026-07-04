"""Интеграционные тесты для репозитория Equipment"""

import pytest


@pytest.mark.asyncio
async def test_repository_create(test_session):
    """Тест создания техники через репозиторий"""
    from shared.repositories import EquipmentRepository

    repo = EquipmentRepository(test_session)
    equipment = await repo.create(
        name="Квадроцикл-5",
        type="квадроцикл",
        serial_number="SN-12345",
        owner_name="Топ Лес",
        owner_phone="+7-999-123-45-67",
    )
    await test_session.commit()
    await test_session.refresh(equipment)

    assert equipment.id is not None
    assert equipment.name == "Квадроцикл-5"
    assert equipment.type == "квадроцикл"


@pytest.mark.asyncio
async def test_repository_get_by_id(test_session):
    """Тест получения техники по ID"""
    from shared.repositories import EquipmentRepository

    repo = EquipmentRepository(test_session)
    equipment = await repo.create(name="Тест", type="тип")
    await test_session.commit()
    await test_session.refresh(equipment)

    found = await repo.get_by_id(equipment.id)
    assert found is not None
    assert found.id == equipment.id
    assert found.name == "Тест"


@pytest.mark.asyncio
async def test_repository_update(test_session):
    """Тест обновления техники"""
    from shared.repositories import EquipmentRepository

    repo = EquipmentRepository(test_session)
    equipment = await repo.create(name="Старое имя", type="тип")
    await test_session.commit()
    await test_session.refresh(equipment)

    updated = await repo.update(equipment.id, name="Новое имя")
    await test_session.commit()
    await test_session.refresh(updated)

    assert updated is not None
    assert updated.name == "Новое имя"


@pytest.mark.asyncio
async def test_repository_delete(test_session):
    """Тест удаления техники"""
    from shared.repositories import EquipmentRepository

    repo = EquipmentRepository(test_session)
    equipment = await repo.create(name="Для удаления", type="тип")
    await test_session.commit()
    await test_session.refresh(equipment)

    result = await repo.delete(equipment.id)
    await test_session.commit()
    assert result is True

    deleted = await repo.get_by_id(equipment.id)
    assert deleted is None
