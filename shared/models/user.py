from sqlalchemy import Column, Integer, String, DateTime, BigInteger
from sqlalchemy.sql import func
from shared.models import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        String(20), nullable=False, default="instructor"
    )  # instructor, mechanic, admin
    telegram_id = Column(
        BigInteger, nullable=True, unique=True
    )  # для будущей интеграции
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"

    def __str__(self):
        return self.username
