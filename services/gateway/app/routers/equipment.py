"""
Роутер для работы с техникой (Equipment).

Все эндпоинты имеют префикс /api/v1/equipment
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional

from shared import get_session_maker, EquipmentRepository
from shared.schemas import (
    EquipmentCreate,
    EquipmentUpdate,
    EquipmentResponse,
    EquipmentListResponse,
)

router = APIRouter(prefix="/api/v1/equipment", tags=["Equipment"])


async def get_repo():
    """Dependency Injection для репозитория Equipment"""
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield EquipmentRepository(session)


@router.post(
    "/",
    response_model=EquipmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую технику",
)
async def create_equipment(
    data: EquipmentCreate,
    repo: EquipmentRepository = Depends(get_repo),
):
    """
    Создать новую единицу техники.

    - **name**: название техники (обязательно)
    - **type**: тип техники (обязательно): квадроцикл, питбайк, эндуро и т.д.
    - **serial_number**: серийный номер (опционально)
    - **owner_name**: имя владельца (опционально)
    - **owner_phone**: телефон владельца (опционально)
    """
    equipment = await repo.create(**data.model_dump())
    await repo.session.commit()
    return EquipmentResponse.model_validate(equipment)


@router.get(
    "/",
    response_model=EquipmentListResponse,
    summary="Получить список техники",
)
async def get_all_equipment(
    skip: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(100, ge=1, le=100, description="Сколько записей вернуть"),
    search: Optional[str] = Query(
        None,
        description="Поиск по name, serial_number, owner_name",
    ),
    repo: EquipmentRepository = Depends(get_repo),
):
    """
    Получить список техники с пагинацией и поиском.

    - **skip**: сколько записей пропустить (по умолчанию 0)
    - **limit**: сколько записей вернуть (по умолчанию 100, максимум 100)
    - **search**: текст для поиска по name, serial_number, owner_name
    """
    items = await repo.get_all(skip=skip, limit=limit, search=search)
    total = await repo.get_count(search=search)

    return EquipmentListResponse(
        items=[EquipmentResponse.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{equipment_id}",
    response_model=EquipmentResponse,
    summary="Получить технику по ID",
)
async def get_equipment_by_id(
    equipment_id: int,
    repo: EquipmentRepository = Depends(get_repo),
):
    """
    Получить технику по ID.
    """
    equipment = await repo.get_by_id(equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with id {equipment_id} not found",
        )
    return EquipmentResponse.model_validate(equipment)


@router.put(
    "/{equipment_id}",
    response_model=EquipmentResponse,
    summary="Обновить технику",
)
async def update_equipment(
    equipment_id: int,
    data: EquipmentUpdate,
    repo: EquipmentRepository = Depends(get_repo),
):
    """
    Обновить технику (частичное обновление).
    Можно обновить любое поле или несколько полей сразу.
    """
    # Убираем None значения, чтобы не перезаписывать их в БД
    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    equipment = await repo.update(equipment_id, **update_data)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with id {equipment_id} not found",
        )

    await repo.session.commit()
    await repo.session.refresh(equipment)  # ← ДОБАВИТЬ ЭТУ СТРОКУ
    return EquipmentResponse.model_validate(equipment)


@router.delete(
    "/{equipment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить технику",
)
async def delete_equipment(
    equipment_id: int,
    repo: EquipmentRepository = Depends(get_repo),
):
    """
    Удалить технику по ID.
    """
    deleted = await repo.delete(equipment_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with id {equipment_id} not found",
        )

    await repo.session.commit()
    return None  # 204 No Content
