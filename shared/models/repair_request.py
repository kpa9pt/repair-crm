from sqlalchemy import Column, String, Text, Boolean, DateTime, Numeric
from sqlalchemy.sql import func
from shared.models import Base


class RepairRequest(Base):
    __tablename__ = "repair_requests"

    vehicle_name = Column(String(200), nullable=False)
    client_name = Column(String(100), nullable=False, server_default="Топ Лес")
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    urgency = Column(String(20), nullable=False, server_default="normal")
    status = Column(String(30), nullable=False, server_default="new")
    is_operational = Column(Boolean, nullable=True)
    parts_cost = Column(Numeric(12, 2), nullable=False, server_default="0")
    client_payment = Column(Numeric(12, 2), nullable=False, server_default="0")
    deadline = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
