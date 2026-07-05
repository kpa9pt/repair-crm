from .base import DeclarativeBase as Base
from .repair_request import RepairRequest
from .equipment import Equipment
from .user import User  # ← добавить

__all__ = (
    "Base",
    "RepairRequest",
    "Equipment",
    "User",  # ← добавить
)
