# shared/repositories/__init__.py
from .equipment import EquipmentRepository
from .repair_request import RepairRequestRepository

__all__ = ["EquipmentRepository", "RepairRequestRepository"]
