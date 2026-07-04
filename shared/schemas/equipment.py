from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class EquipmentBase(BaseModel):
    """Базовые поля техники (общие для всех схем)"""

    name: str = Field(..., description="Название техники", examples=["Квадроцикл-5"])
    type: str = Field(
        ..., description="Тип техники", examples=["квадроцикл", "питбайк", "эндуро"]
    )
    serial_number: Optional[str] = Field(
        None, description="Серийный номер", examples=["SN-12345"]
    )
    owner_name: Optional[str] = Field(
        None, description="Имя владельца", examples=["Топ Лес"]
    )
    owner_phone: Optional[str] = Field(
        None, description="Телефон владельца", examples=["+7-999-123-45-67"]
    )


class EquipmentCreate(EquipmentBase):
    """Схема для создания техники (POST /api/v1/equipment)"""

    pass


class EquipmentUpdate(BaseModel):
    """Схема для частичного обновления техники (PATCH /api/v1/equipment/{id})"""

    name: Optional[str] = Field(None, description="Название техники")
    type: Optional[str] = Field(None, description="Тип техники")
    serial_number: Optional[str] = Field(None, description="Серийный номер")
    owner_name: Optional[str] = Field(None, description="Имя владельца")
    owner_phone: Optional[str] = Field(None, description="Телефон владельца")


class EquipmentResponse(EquipmentBase):
    """Схема для ответа (GET /api/v1/equipment)"""

    id: int = Field(..., description="ID техники")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    model_config = ConfigDict(from_attributes=True)


class EquipmentListResponse(BaseModel):
    """Схема для списка техники (с пагинацией)"""

    items: list[EquipmentResponse] = Field(..., description="Список техники")
    total: int = Field(..., description="Общее количество")
    skip: int = Field(..., description="Сколько пропущено")
    limit: int = Field(..., description="Лимит на страницу")
