"""
Роутер для работы с заявками на ремонт.

Все эндпоинты имеют префикс /api/v1/repair-requests
"""

from fastapi import APIRouter, Depends, HTTPException, status

from shared import get_session_maker, RepairRequestRepository, EquipmentRepository

from shared.schemas import (
    RepairRequestCreate,
    RepairRequestUpdate,
    RepairRequestResponse,
    RepairRequestListResponse,
)
from shared.auth import get_current_user, require_role, User


router = APIRouter(prefix="/api/v1/repair-requests", tags=["Repair Requests"])


async def get_repo():
    session_maker = get_session_maker()

    async with session_maker() as session:
        yield RepairRequestRepository(session)


@router.post(
    "/", response_model=RepairRequestResponse, status_code=status.HTTP_201_CREATED
)
async def create_repair_request(
    request_data: RepairRequestCreate,
    repo: RepairRequestRepository = Depends(get_repo),
    current_user: User = Depends(require_role(["instructor", "mechanic", "admin"])),
):
    """
    Создать новую заявку на ремонт.

    - **vehicle_name**: название техники (обязательно)
    - **description**: описание поломки (обязательно)
    - **urgency**: срочность (low/normal/high/critical)
    - **status**: статус (new/in_progress/waiting_parts/
        diagnostics/waiting_approval/done)
    """

    data = request_data.model_dump()

    # Если equipment_id не передан, но есть vehicle_name — ищем в БД
    if data.get("equipment_id") is None and data.get("vehicle_name"):
        # Ищем технику по имени
        session_maker = get_session_maker()
        async with session_maker() as session:
            equipment_repo = EquipmentRepository(session)
            equipment = await equipment_repo.get_by_name_ignore_case(
                data["vehicle_name"]
            )
            if equipment:
                data["equipment_id"] = equipment.id

    # Добавляем создателя заявки
    data["created_by_id"] = current_user.id
    data["created_by_username"] = current_user.username  # ← ДОБАВИТЬ

    # Конвертируем Pydantic модель в словарь
    new_request = await repo.create(**data)
    await repo.session.commit()
    return RepairRequestResponse.model_validate(new_request)


@router.get("/", response_model=RepairRequestListResponse)
async def get_all_repair_requests(
    skip: int = 0,
    limit: int = 100,
    repo: RepairRequestRepository = Depends(get_repo),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список всех заявок с пагинацией.

    - **skip**: сколько заявок пропустить
    - **limit**: сколько заявок вернуть
    - Сортировка: сначала новые (по created_at DESC)
    """
    requests = await repo.get_all(skip=skip, limit=limit)
    total = len(requests)  # В будущем можно сделать отдельный метод для count

    return RepairRequestListResponse(
        items=[RepairRequestResponse.model_validate(r) for r in requests],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/vehicle/{vehicle_name}", response_model=RepairRequestListResponse)
async def get_repair_requests_by_vehicle(
    vehicle_name: str,
    skip: int = 0,
    limit: int = 100,
    repo: RepairRequestRepository = Depends(get_repo),
    current_user: User = Depends(get_current_user),
):
    """
    Получить все заявки для конкретной техники.

    - **vehicle_name**: название техники
    - **skip**: сколько пропустить
    - **limit**: сколько вернуть
    """
    # Метод get_by_vehicle нужно добавить в репозиторий
    # Пока используем фильтрацию через get_all (не оптимально)
    all_requests = await repo.get_by_vehicle(vehicle_name)
    filtered = [r for r in all_requests if r.vehicle_name == vehicle_name]
    total = len(filtered)
    paginated = filtered[skip : skip + limit]

    return RepairRequestListResponse(
        items=[RepairRequestResponse.model_validate(r) for r in paginated],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{request_id}", response_model=RepairRequestResponse)
async def get_repair_request(
    request_id: int,
    repo: RepairRequestRepository = Depends(get_repo),
    current_user: User = Depends(get_current_user),
):
    """
    Получить конкретную заявку по ID.
    """
    request = await repo.get_by_id(request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair request with id {request_id} not found",
        )
    return RepairRequestResponse.model_validate(request)


@router.patch("/{request_id}", response_model=RepairRequestResponse)
async def update_repair_request(
    request_id: int,
    update_data: RepairRequestUpdate,
    repo: RepairRequestRepository = Depends(get_repo),
    current_user: User = Depends(require_role(["mechanic", "admin"])),
):
    """
    Обновить заявку (частичное обновление).
    Можно обновить любое поле или несколько полей сразу.
    """
    update_dict = update_data.model_dump(exclude_unset=True)

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    # 👇 Используем метод репозитория
    request = await repo.update(request_id, **update_dict)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair request with id {request_id} not found",
        )

    # 👇 Роутер управляет транзакцией
    await repo.session.commit()
    await repo.session.refresh(request)  # ← ВАЖНО!

    return RepairRequestResponse.model_validate(request)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repair_request(
    request_id: int,
    repo: RepairRequestRepository = Depends(get_repo),
    current_user: User = Depends(require_role(["admin"])),
):
    """
    Удалить заявку по ID.
    """
    existing = await repo.get_by_id(request_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair request with id {request_id} not found",
        )

    await repo.session.delete(existing)
    await repo.session.commit()

    return None  # 204 No Content
