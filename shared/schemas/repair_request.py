"""
Pydantic схемы для RepairRequest

Эти схемы определяют:
- Как выглядит запрос от клиента (Create, Update)
- Как выглядит ответ сервера (Response)
- Какие поля обязательные, а какие нет
"""

from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from shared.enums import Urgency, RequestStatus
from datetime import date


class RepairRequestBase(BaseModel):
    """
    Базовый класс с общими полями для всех схем.
    Все поля опциональны, кроме vehicle_name и description (для create)
    """

    vehicle_name: str = Field(
        ..., description="Название техники", examples=["Квадроцикл-5"]
    )

    equipment_id: Optional[int] = Field(None, description="ID техники из базы")

    client_name: Optional[str] = Field(
        None, description="Имя клиента", examples=["Топ Лес"]
    )
    phone: Optional[str] = Field(
        None, description="Телефон клиента", examples=["+7-999-123-45-67"]
    )
    email: Optional[str] = Field(
        None, description="Email клиента", examples=["client@example.com"]
    )
    description: str = Field(..., description="Описание поломки")
    urgency: Urgency = Field(default=Urgency.NORMAL, description="Срочность")
    status: RequestStatus = Field(default=RequestStatus.NEW, description="Статус")
    is_operational: Optional[bool] = Field(False, description="Техника на ходу?")
    parts_cost: Decimal = Field(
        default_factory=lambda: Decimal("0.00"), description="Стоимость запчастей"
    )
    client_payment: Decimal = Field(
        default_factory=lambda: Decimal("0.00"), description="Оплата клиента"
    )
    deadline: Optional[date] = Field(None, description="Дедлайн (дата без времени)")

    created_by_id: Optional[int] = Field(
        None, description="ID пользователя, создавшего заявку"
    )


class RepairRequestCreate(RepairRequestBase):
    """
    Схема для POST запроса (создание новой заявки).
    Наследует все поля от Base, но явно указываем обязательные.
    """

    # Поле vehicle_name уже есть в Base
    # Поле description уже есть в Base
    pass  # Все поля уже определены в RepairRequestBase


class RepairRequestUpdate(BaseModel):
    """
    Схема для PATCH запроса (частичное обновление).
    Все поля опциональны — можно обновить только то, что нужно.
    """

    vehicle_name: Optional[str] = Field(None, description="Название техники")
    equipment_id: Optional[int] = Field(None, description="ID техники из базы")
    client_name: Optional[str] = Field(None, description="Имя клиента")
    phone: Optional[str] = Field(None, description="Телефон клиента")
    email: Optional[str] = Field(None, description="Email клиента")
    description: Optional[str] = Field(None, description="Описание поломки")

    urgency: Optional[Urgency] = Field(None, description="Срочность")
    status: Optional[RequestStatus] = Field(None, description="Статус")

    is_operational: Optional[bool] = Field(None, description="Техника на ходу?")
    parts_cost: Optional[Decimal] = Field(None, description="Стоимость запчастей")
    client_payment: Optional[Decimal] = Field(None, description="Оплата клиента")
    deadline: Optional[date] = Field(None, description="Дедлайн (дата без времени)")


class RepairRequestResponse(RepairRequestBase):
    """
    Схема для GET ответа (возвращаем клиенту).
    Добавляем поля, которые генерируются БД (id, created_at)
    """

    id: int = Field(..., description="ID заявки")
    created_at: datetime = Field(..., description="Дата создания")
    created_by_username: Optional[str] = Field(None, description="Имя создателя")

    # Настройка для работы с SQLAlchemy моделями
    model_config = ConfigDict(from_attributes=True)


class RepairRequestListResponse(BaseModel):
    """
    Схема для списка заявок (с пагинацией).
    """

    items: list[RepairRequestResponse] = Field(..., description="Список заявок")
    total: int = Field(..., description="Общее количество заявок (без учета пагинации)")
    skip: int = Field(..., description="Сколько пропущено")
    limit: int = Field(..., description="Лимит на страницу")
