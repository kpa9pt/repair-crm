"""
Pydantic схемы для обмена данными между клиентом и сервером
"""

from .repair_request import (
    RepairRequestBase,
    RepairRequestCreate,
    RepairRequestUpdate,
    RepairRequestResponse,
    RepairRequestListResponse,
)

from .equipment import (  # ← добавить
    EquipmentBase,
    EquipmentCreate,
    EquipmentUpdate,
    EquipmentResponse,
    EquipmentListResponse,
)

__all__ = [
    "RepairRequestBase",
    "RepairRequestCreate",
    "RepairRequestUpdate",
    "RepairRequestResponse",
    "RepairRequestListResponse",
    "EquipmentBase",
    "EquipmentCreate",
    "EquipmentUpdate",
    "EquipmentResponse",
    "EquipmentListResponse",
]
