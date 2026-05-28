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
        await self.session.commit()
        await self.session.refresh(request)
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
