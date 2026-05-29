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

__all__ = [
    "RepairRequestBase",
    "RepairRequestCreate",
    "RepairRequestUpdate",
    "RepairRequestResponse",
    "RepairRequestListResponse",
]
