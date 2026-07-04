# shared/repositories/repair_request.py
"""
Репозиторий — это слой абстракции между бизнес-логикой и базой данных.
Он скрывает детали SQLAlchemy и позволяет легко подменить БД в тестах.
"""

from sqlalchemy import select
from shared.models import RepairRequest


class RepairRequestRepository:
    def __init__(self, session):
        """
        Внедряем сессию через конструктор (Dependency Injection).
        Это позволяет подставить фейковую сессию в тестах.
        """
        self.session = session

    async def create(self, **kwargs) -> RepairRequest:
        """Создать новую заявку на ремонт."""
        request = RepairRequest(**kwargs)
        self.session.add(request)
        await self.session.flush()
        return request

    async def get_by_id(self, request_id: int) -> RepairRequest | None:
        """Получить заявку по ID."""
        result = await self.session.execute(
            select(RepairRequest).where(RepairRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100):
        """Получить список заявок с пагинацией."""
        result = await self.session.execute(
            select(RepairRequest).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_by_vehicle(self, vehicle_name: str, skip: int = 0, limit: int = 100):
        """Получить заявки по названию техники с пагинацией"""
        result = await self.session.execute(
            select(RepairRequest)
            .where(RepairRequest.vehicle_name == vehicle_name)
            .order_by(RepairRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def update(self, request_id: int, **kwargs) -> RepairRequest | None:
        """
        Обновить заявку по ID.
        Принимает только переданные поля (partial update).
        """
        request = await self.get_by_id(request_id)
        if not request:
            return None

        # Обновляем только переданные поля
        for key, value in kwargs.items():
            if hasattr(request, key) and value is not None:
                setattr(request, key, value)

        await self.session.flush()
        return request

    async def delete(self, request_id: int) -> bool:
        """
        Удалить заявку по ID.
        Возвращает True, если удаление прошло успешно, иначе False.
        """
        request = await self.get_by_id(request_id)
        if not request:
            return False

        await self.session.delete(request)
        await self.session.flush()
        return True
