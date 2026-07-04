from sqlalchemy import select
from shared.models import Equipment
from typing import Optional, List
from sqlalchemy import func


class EquipmentRepository:
    """
    Репозиторий для работы с техникой (Equipment).
    Содержит все методы для CRUD операций.
    """

    def __init__(self, session):
        """
        Внедряем сессию SQLAlchemy через конструктор.
        Это позволяет легко подменять сессию в тестах.
        """
        self.session = session

    async def create(self, **kwargs) -> Equipment:
        """
        Создать новую единицу техники.

        Пример использования:
        equipment = await repo.create(
            name="Квадроцикл-5",
            type="квадроцикл",
            serial_number="SN-12345",
            owner_name="Топ Лес"
        )
        """
        equipment = Equipment(**kwargs)
        self.session.add(equipment)
        await self.session.flush()  # Отправляем в БД, но НЕ коммитим
        return equipment

    async def get_by_id(self, equipment_id: int) -> Optional[Equipment]:
        """
        Получить технику по ID.

        Возвращает Equipment или None, если не найдено.
        """
        result = await self.session.execute(
            select(Equipment).where(Equipment.id == equipment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Equipment]:
        """Найти технику по точному названию"""
        result = await self.session.execute(
            select(Equipment).where(Equipment.name == name)
        )
        return result.scalar_one_or_none()

    async def get_by_name_ignore_case(self, name: str) -> Optional[Equipment]:
        """Найти технику по названию (без учета регистра)"""
        result = await self.session.execute(
            select(Equipment).where(func.lower(Equipment.name) == func.lower(name))
        )
        return result.scalar_one_or_none()

    async def get_all(
        self, skip: int = 0, limit: int = 100, search: Optional[str] = None
    ) -> List[Equipment]:
        """
        Получить список техники с пагинацией и опциональным поиском.

        Параметры:
        - skip: сколько записей пропустить
        - limit: сколько записей вернуть
        - search: текст для поиска по name, serial_number, owner_name
        """
        query = select(Equipment)

        # Если есть поисковый запрос — фильтруем
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                Equipment.name.ilike(search_pattern)
                | Equipment.serial_number.ilike(search_pattern)
                | Equipment.owner_name.ilike(search_pattern)
            )

        # Пагинация
        query = query.offset(skip).limit(limit)

        # Выполняем запрос
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_count(self, search: Optional[str] = None) -> int:
        """
        Получить общее количество техники (для пагинации).

        Если передан search, считает только совпадающие записи.
        """
        query = select(Equipment)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                Equipment.name.ilike(search_pattern)
                | Equipment.serial_number.ilike(search_pattern)
                | Equipment.owner_name.ilike(search_pattern)
            )

        result = await self.session.execute(query)
        return len(result.scalars().all())

    async def update(self, equipment_id: int, **kwargs) -> Optional[Equipment]:
        """
        Обновить технику по ID.
        Принимает только переданные поля (partial update).

        Пример:
        equipment = await repo.update(
            1,
            name="Новое название",
            owner_name="Новый владелец"
        )
        """
        equipment = await self.get_by_id(equipment_id)
        if not equipment:
            return None

        # Обновляем только переданные поля
        for key, value in kwargs.items():
            if hasattr(equipment, key) and value is not None:
                setattr(equipment, key, value)

        await self.session.flush()
        return equipment

    async def delete(self, equipment_id: int) -> bool:
        """
        Удалить технику по ID.

        Возвращает True, если удаление прошло успешно, иначе False.
        """
        equipment = await self.get_by_id(equipment_id)
        if not equipment:
            return False

        await self.session.delete(equipment)
        await self.session.flush()
        return True
