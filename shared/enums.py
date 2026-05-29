"""
Enum классы для выпадающих списков в моделях и схемах
"""

from enum import Enum


class Urgency(str, Enum):
    """Срочность заявки"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

    def __str__(self) -> str:
        return self.value


class RequestStatus(str, Enum):
    """Статус заявки на ремонт"""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    WAITING_PARTS = "waiting_parts"
    DIAGNOSTICS = "diagnostics"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"

    def __str__(self) -> str:
        return self.value
