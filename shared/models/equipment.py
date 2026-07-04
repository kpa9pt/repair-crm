from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from shared.models import Base


class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False)  # "квадроцикл", "скутер", "мотоцикл"
    serial_number = Column(String(100), nullable=True)
    owner_name = Column(String(100), nullable=True)
    owner_phone = Column(String(20), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Связь с заявками (один ко многим)
    repair_requests = relationship("RepairRequest", back_populates="equipment")

    def __repr__(self):
        return f"<Equipment(id={self.id}, name={self.name})>"

    def __str__(self):
        return self.name  # или f"{self.name} (ID: {self.id})"
